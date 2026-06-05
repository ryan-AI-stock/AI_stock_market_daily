from pathlib import Path
import unittest
from unittest.mock import patch

import stock_market_tracking_system as sm


class ValidationPublishTests(unittest.TestCase):
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
