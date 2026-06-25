import unittest
from datetime import datetime
from types import SimpleNamespace

import stock_market_tracking_system as sm


WATCHLIST = [
    {"ticker": "^TWII", "name": "台灣加權指數"},
    {"ticker": "2330.TW", "name": "台積電"},
]


class ValidateReportCompletenessTests(unittest.TestCase):
    def test_accepts_all_watchlist_results_for_expected_date(self):
        results = [
            ("台灣加權指數", "^TWII", {"data_date": "2026-06-04"}),
            ("台積電", "2330.TW", {"data_date": "2026-06-04"}),
        ]

        sm.validate_report_completeness(results, [], WATCHLIST, "2026-06-04")

    def test_rejects_missing_stock_after_analysis_failure(self):
        results = [("台灣加權指數", "^TWII", {"data_date": "2026-06-04"})]
        failures = [
            {
                "name": "台積電",
                "ticker": "2330.TW",
                "error": "IndexError: list index out of range",
            }
        ]

        with self.assertRaisesRegex(RuntimeError, "報告資料不完整.*2330.TW"):
            sm.validate_report_completeness(results, failures, WATCHLIST, "2026-06-04")

    def test_rejects_stale_data(self):
        results = [
            ("台灣加權指數", "^TWII", {"data_date": "2026-06-04"}),
            ("台積電", "2330.TW", {"data_date": "2026-06-03"}),
        ]

        with self.assertRaisesRegex(RuntimeError, "資料日非 2026-06-04=2330.TW") as raised:
            sm.validate_report_completeness(results, [], WATCHLIST, "2026-06-04")

        self.assertIsInstance(raised.exception, sm.ReportCompletenessError)
        self.assertEqual(raised.exception.stale_tickers, ["2330.TW"])
        self.assertEqual(raised.exception.missing_tickers, [])
        self.assertEqual(raised.exception.failures, [])

    def test_defer_incomplete_scheduled_run_only_for_stale_data(self):
        runtime = SimpleNamespace(github_actions=True, github_event_name="schedule")
        stale_error = sm.ReportCompletenessError(
            "報告資料不完整",
            failures=[],
            missing_tickers=[],
            stale_tickers=["^TWII"],
        )

        self.assertTrue(sm.should_defer_incomplete_scheduled_run(runtime, stale_error))

    def test_does_not_defer_manual_or_analysis_failure(self):
        manual_runtime = SimpleNamespace(github_actions=True, github_event_name="workflow_dispatch")
        schedule_runtime = SimpleNamespace(github_actions=True, github_event_name="schedule")
        failure_error = sm.ReportCompletenessError(
            "報告資料不完整",
            failures=[{"ticker": "2330.TW"}],
            missing_tickers=[],
            stale_tickers=[],
        )
        stale_error = sm.ReportCompletenessError(
            "報告資料不完整",
            failures=[],
            missing_tickers=[],
            stale_tickers=["^TWII"],
        )

        self.assertFalse(sm.should_defer_incomplete_scheduled_run(manual_runtime, stale_error))
        self.assertFalse(sm.should_defer_incomplete_scheduled_run(schedule_runtime, failure_error))


class GetReportDateTests(unittest.TestCase):
    def test_starts_new_cycle_at_15_taiwan_time(self):
        self.assertEqual(sm.get_report_date(datetime(2026, 6, 4, 15, 0)), "2026-06-04")

    def test_keeps_previous_cycle_after_midnight(self):
        self.assertEqual(sm.get_report_date(datetime(2026, 6, 5, 2, 0)), "2026-06-04")

    def test_keeps_friday_cycle_through_weekend(self):
        self.assertEqual(sm.get_report_date(datetime(2026, 6, 6, 18, 0)), "2026-06-05")

    def test_keeps_friday_cycle_until_monday_15(self):
        self.assertEqual(sm.get_report_date(datetime(2026, 6, 8, 14, 59)), "2026-06-05")


class PublicReportCompletionTests(unittest.TestCase):
    def test_drive_modified_time_is_current_cycle_after_15_taipei(self):
        self.assertTrue(
            sm.drive_modified_time_is_current_cycle("2026-06-08T07:05:00Z", "2026-06-08")
        )

    def test_drive_modified_time_is_not_current_cycle_before_15_taipei(self):
        self.assertFalse(
            sm.drive_modified_time_is_current_cycle("2026-06-08T06:59:59Z", "2026-06-08")
        )


class NeutralizeReportLanguageTests(unittest.TestCase):
    def test_replaces_transaction_instructions_without_changing_html(self):
        source = (
            "<div>買進或加碼 50%｜賣出或減碼 40%｜買進提醒｜賣出弱訊號｜"
            "強勢續抱｜禁止追買｜今日操作分群｜可小部位布局｜買／賣分數｜"
            "建議降低部位或暫緩操作｜分批試單｜停損｜重倉｜建倉</div>"
        )

        result = sm.neutralize_report_language(source)

        self.assertIn("<div>", result)
        self.assertIn("正向條件通過 5／10", result)
        self.assertIn("風險條件通過 4／10", result)
        self.assertIn("正向條件成立", result)
        self.assertIn("風險條件增加", result)
        self.assertIn("趨勢條件仍成立", result)
        self.assertIn("追價風險偏高", result)
        self.assertIn("今日條件分群", result)
        self.assertIn("正向條件／風險條件分數", result)
        for banned in (
            "買進", "賣出", "加碼", "減碼", "續抱", "布局", "禁止追買",
            "停損", "重倉", "建倉", "分批", "部位", "操作", "建議", "執行",
        ):
            self.assertNotIn(banned, result)

    def test_public_report_applies_neutral_language(self):
        result = {
            "summary": "買進提醒",
            "trade_plan": {"headline": "買進或加碼 50%", "reason": "可小部位布局"},
            "level": "BUY_STRONG",
            "border": "#000",
            "close": 100,
            "effective_buy": 50,
            "effective_sell": 10,
            "items": [],
            "regime": {},
            "b60": {},
        }

        html = sm.build_public_report_html(
            [("台灣加權指數", "^TWII", result), ("台積電", "2330.TW", result)],
            "2026-06-05",
            cfg={},
            macro={},
            news_items=[],
            market_events=[],
        )

        self.assertIn("正向條件通過 5／10", html)
        self.assertIn("今日條件分群", html)
        for banned in ("買進或加碼", "買進提醒", "可小部位布局", "今日操作分群"):
            self.assertNotIn(banned, html)


if __name__ == "__main__":
    unittest.main()
