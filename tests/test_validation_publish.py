from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

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


if __name__ == "__main__":
    unittest.main()
