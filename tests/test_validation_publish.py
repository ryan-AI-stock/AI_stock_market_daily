from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

from daily_stock.runtime import build_report_run_context
from daily_stock.validation_reports import validation_report_file_name
import stock_market_tracking_system as sm


class ValidationPublishTests(unittest.TestCase):
    def test_builds_validation_report_file_name(self):
        self.assertEqual(
            validation_report_file_name(Path("public_report") / "每日台股報告.pdf", "2026-06-04"),
            "每日台股報告_驗收_20260604.pdf",
        )

    def test_trims_intraday_or_future_rows_to_complete_report_date(self):
        data = pd.DataFrame(
            {"Close": [100.0, 101.0, 102.0]},
            index=pd.to_datetime(["2026-06-03", "2026-06-04", "2026-06-05"]),
        )

        trimmed = sm.trim_market_data_to_report_date(data, "2026-06-04")

        self.assertEqual(trimmed.index[-1].strftime("%Y-%m-%d"), "2026-06-04")
        self.assertEqual(len(trimmed), 2)

    def test_rejects_validation_date_without_market_data(self):
        data = pd.DataFrame(
            {"Close": [100.0]},
            index=pd.to_datetime(["2026-06-05"]),
        )

        with self.assertRaisesRegex(ValueError, "無 2026-06-04"):
            sm.trim_market_data_to_report_date(data, "2026-06-04")

    @patch("stock_market_tracking_system.evaluate_weighted")
    @patch("stock_market_tracking_system.fetch_fundamental_context")
    @patch("stock_market_tracking_system.fetch_institutional")
    @patch("stock_market_tracking_system.calc_indicators")
    @patch("stock_market_tracking_system.fetch_data")
    def test_formal_analysis_trims_future_rows_to_report_date(
        self,
        fetch_data,
        calc_indicators,
        fetch_institutional,
        fetch_fundamental_context,
        evaluate_weighted,
    ):
        fetch_data.return_value = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.to_datetime(["2026-06-11", "2026-06-12"]),
        )
        calc_indicators.side_effect = lambda df, _scfg: df
        fetch_institutional.return_value = None
        fetch_fundamental_context.return_value = {}
        evaluate_weighted.return_value = {
            "emoji": "⚪",
            "summary": "觀察",
            "effective_buy": 0,
            "effective_sell": 0,
            "buy_score": 0,
            "sell_score": 0,
            "b60": {"bias60": 0},
        }

        results, failures = sm.analyze_watchlist(
            {
                "watchlist": [{"ticker": "2330.TW", "name": "台積電"}],
                "lookback_days": 10,
                "thresholds": {},
                "ma_periods": {},
            },
            "2026-06-11",
            False,
            {},
            {},
        )

        self.assertEqual(failures, [])
        self.assertEqual(results[0][2]["data_date"], "2026-06-11")
        self.assertEqual(calc_indicators.call_args.args[0].index[-1].strftime("%Y-%m-%d"), "2026-06-11")

    def test_finds_latest_common_complete_market_date(self):
        market_data = {
            "^TWII": pd.DataFrame(
                {"Close": [100.0, 101.0]},
                index=pd.to_datetime(["2026-06-02", "2026-06-03"]),
            ),
            "2330.TW": pd.DataFrame(
                {"Close": [100.0, 101.0]},
                index=pd.to_datetime(["2026-06-03", "2026-06-04"]),
            ),
        }

        self.assertEqual(
            sm.find_latest_common_market_date(market_data, "2026-06-04"),
            "2026-06-03",
        )

    @patch("stock_market_tracking_system.fetch_data")
    def test_workflow_dispatch_falls_back_to_latest_complete_market_date(self, fetch_data):
        cfg = {
            "lookback_days": 10,
            "watchlist": [
                {"ticker": "^TWII", "name": "加權指數"},
                {"ticker": "2330.TW", "name": "台積電"},
            ],
        }
        fetch_data.side_effect = [
            pd.DataFrame(
                {"Close": [100.0, 101.0]},
                index=pd.to_datetime(["2026-06-03", "2026-06-04"]),
            ),
            pd.DataFrame(
                {"Close": [200.0]},
                index=pd.to_datetime(["2026-06-03"]),
            ),
        ]
        context = build_report_run_context(
            pd.Timestamp("2026-06-05 15:30").to_pydatetime(),
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
            },
        )

        updated, market_data, requested_date, fallback_reason = sm.resolve_report_date_for_run(
            cfg,
            context,
        )

        self.assertEqual(requested_date, "2026-06-05")
        self.assertEqual(updated.report_date, "2026-06-03")
        self.assertEqual(fallback_reason, "workflow_dispatch_latest_complete_market_date")
        self.assertEqual(set(market_data), {"^TWII", "2330.TW"})

    @patch("stock_market_tracking_system.fetch_data")
    def test_workflow_dispatch_with_report_date_override_keeps_exact_mode(self, fetch_data):
        cfg = {"lookback_days": 10, "watchlist": [{"ticker": "^TWII", "name": "加權指數"}]}
        context = build_report_run_context(
            pd.Timestamp("2026-06-05 15:30").to_pydatetime(),
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "REPORT_DATE": "2026-06-04",
            },
        )

        updated, market_data, requested_date, fallback_reason = sm.resolve_report_date_for_run(
            cfg,
            context,
        )

        self.assertEqual(requested_date, "2026-06-04")
        self.assertEqual(updated.report_date, "2026-06-04")
        self.assertEqual(fallback_reason, "none")
        self.assertEqual(market_data, {})
        fetch_data.assert_not_called()

    @patch("stock_market_tracking_system.fetch_data")
    def test_scheduled_report_date_override_keeps_exact_mode(self, fetch_data):
        cfg = {"lookback_days": 10, "watchlist": [{"ticker": "^TWII", "name": "加權指數"}]}
        context = build_report_run_context(
            pd.Timestamp("2026-06-05 15:30").to_pydatetime(),
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_EVENT_NAME": "schedule",
                "REPORT_DATE": "2026-06-04",
            },
        )

        updated, market_data, requested_date, fallback_reason = sm.resolve_report_date_for_run(
            cfg,
            context,
        )

        self.assertEqual(requested_date, "2026-06-04")
        self.assertEqual(updated.report_date, "2026-06-04")
        self.assertEqual(fallback_reason, "none")
        self.assertEqual(market_data, {})
        fetch_data.assert_not_called()

    def test_rejects_when_tickers_have_no_common_market_date(self):
        market_data = {
            "^TWII": pd.DataFrame(
                {"Close": [100.0]},
                index=pd.to_datetime(["2026-06-03"]),
            ),
            "2330.TW": pd.DataFrame(
                {"Close": [100.0]},
                index=pd.to_datetime(["2026-06-04"]),
            ),
        }

        with self.assertRaisesRegex(ValueError, "沒有共同市場資料日"):
            sm.find_latest_common_market_date(market_data, "2026-06-04")

    @patch("stock_market_tracking_system.upload_file_to_drive")
    def test_uploads_isolated_validation_report(self, upload_file_to_drive):
        upload_file_to_drive.return_value = "https://drive.google.com/file/d/test/view"
        report_path = Path("public_report") / "每日台股報告.pdf"

        link = sm.upload_validation_report_file(
            report_path,
            "validation-folder-id",
            "2026-06-04",
        )

        self.assertEqual(link, "https://drive.google.com/file/d/test/view")
        upload_file_to_drive.assert_called_once_with(
            report_path,
            "validation-folder-id",
            "application/pdf",
            file_name="每日台股報告_驗收_20260604.pdf",
            make_public=False,
        )

    @patch("stock_market_tracking_system.upload_file_to_drive")
    def test_skips_upload_without_report_or_folder(self, upload_file_to_drive):
        self.assertIsNone(sm.upload_validation_report_file(None, "folder", "2026-06-04"))
        self.assertIsNone(
            sm.upload_validation_report_file(Path("report.pdf"), "", "2026-06-04")
        )
        upload_file_to_drive.assert_not_called()

    @patch("stock_market_tracking_system.upload_public_report_file")
    @patch("stock_market_tracking_system.save_public_report_file")
    @patch("stock_market_tracking_system.build_public_report_html")
    @patch("stock_market_tracking_system.save_email_preview")
    @patch("stock_market_tracking_system.build_email_html")
    def test_github_actions_fails_when_public_pdf_publish_fails_with_email_disabled(
        self,
        build_email_html,
        save_email_preview,
        build_public_report_html,
        save_public_report_file,
        upload_public_report_file,
    ):
        build_email_html.return_value = "<html>Email</html>"
        save_email_preview.return_value = Path("email_preview.html")
        build_public_report_html.return_value = "<html>Public</html>"
        save_public_report_file.return_value = Path("public_report") / "每日台股報告.pdf"
        upload_public_report_file.return_value = None

        with self.assertRaisesRegex(RuntimeError, "免費觀眾 Google Drive PDF 上傳失敗"):
            sm.publish_report_outputs(
                {
                    "email": {"enabled": False},
                    "public_report": {"enabled": True},
                },
                "2026-06-18",
                "20260618",
                [],
                {},
                [],
                [],
                validation_mode=False,
                validation_folder_id="",
                runtime_options=SimpleNamespace(github_actions=True),
            )


if __name__ == "__main__":
    unittest.main()
