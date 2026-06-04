import unittest

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

        with self.assertRaisesRegex(RuntimeError, "資料日非 2026-06-04=2330.TW"):
            sm.validate_report_completeness(results, [], WATCHLIST, "2026-06-04")


if __name__ == "__main__":
    unittest.main()
