import unittest
from pathlib import Path

from daily_stock.drive_publish import (
    DEFAULT_PUBLIC_REPORT_FILE_NAME,
    HTML_MIME_TYPE,
    GOOGLE_DRIVE_SCOPES,
    PDF_MIME_TYPE,
    PNG_MIME_TYPE,
    resolve_daily_report_folder_id,
    resolve_google_oauth_config,
    resolve_public_report_fixed_name,
    resolve_public_report_file_id,
    resolve_public_report_folder_id,
    resolve_public_report_mime_type,
    resolve_self_report_mime_type,
)


class DrivePublishOptionTests(unittest.TestCase):
    def test_google_oauth_config_requires_all_secret_fields(self):
        options = resolve_google_oauth_config({
            "GOOGLE_OAUTH_REFRESH_TOKEN": "refresh-token",
            "GOOGLE_OAUTH_CLIENT_ID": "client-id",
        })

        self.assertFalse(options.is_configured)

    def test_google_oauth_config_trims_values_and_uses_drive_scope(self):
        options = resolve_google_oauth_config({
            "GOOGLE_OAUTH_REFRESH_TOKEN": " refresh-token ",
            "GOOGLE_OAUTH_CLIENT_ID": " client-id ",
            "GOOGLE_OAUTH_CLIENT_SECRET": " client-secret ",
        })

        self.assertTrue(options.is_configured)
        self.assertEqual(options.refresh_token, "refresh-token")
        self.assertEqual(options.client_id, "client-id")
        self.assertEqual(options.client_secret, "client-secret")
        self.assertEqual(options.scopes, GOOGLE_DRIVE_SCOPES)

    def test_daily_report_folder_prefers_env_over_config(self):
        folder_id = resolve_daily_report_folder_id(
            {"folder_id": "config-folder"},
            {"DAILY_REPORT_DRIVE_FOLDER_ID": "env-folder"},
        )

        self.assertEqual(folder_id, "env-folder")

    def test_daily_report_folder_falls_back_to_config(self):
        folder_id = resolve_daily_report_folder_id({"folder_id": "config-folder"}, {})

        self.assertEqual(folder_id, "config-folder")

    def test_public_report_folder_uses_existing_priority(self):
        public_cfg = {"folder_id": "config-folder"}

        self.assertEqual(
            resolve_public_report_folder_id(
                public_cfg,
                {
                    "PUBLIC_REPORT_DRIVE_FOLDER_ID": "public-env",
                    "FREE_REPORT_DRIVE_FOLDER_ID": "free-env",
                },
            ),
            "public-env",
        )
        self.assertEqual(
            resolve_public_report_folder_id(public_cfg, {"FREE_REPORT_DRIVE_FOLDER_ID": "free-env"}),
            "free-env",
        )
        self.assertEqual(resolve_public_report_folder_id(public_cfg, {}), "config-folder")

    def test_public_report_file_id_prefers_env_over_config(self):
        self.assertEqual(
            resolve_public_report_file_id(
                {"fixed_file_id": "config-file"},
                {"PUBLIC_REPORT_DRIVE_FILE_ID": "env-file"},
            ),
            "env-file",
        )
        self.assertEqual(resolve_public_report_file_id({"fixed_file_id": "config-file"}, {}), "config-file")

    def test_self_report_mime_keeps_existing_pdf_or_png_behavior(self):
        self.assertEqual(resolve_self_report_mime_type(Path("report.pdf")), PDF_MIME_TYPE)
        self.assertEqual(resolve_self_report_mime_type(Path("report.png")), PNG_MIME_TYPE)
        self.assertEqual(resolve_self_report_mime_type(Path("report.html")), PNG_MIME_TYPE)
        self.assertEqual(
            resolve_self_report_mime_type(Path("report.html"), "custom/type"),
            "custom/type",
        )

    def test_public_report_mime_keeps_existing_pdf_or_html_behavior(self):
        self.assertEqual(resolve_public_report_mime_type(Path("report.pdf")), PDF_MIME_TYPE)
        self.assertEqual(resolve_public_report_mime_type(Path("report.html")), HTML_MIME_TYPE)
        self.assertEqual(resolve_public_report_mime_type(Path("report.png")), HTML_MIME_TYPE)

    def test_public_report_fixed_name_uses_config_then_fallback_then_default(self):
        self.assertEqual(resolve_public_report_fixed_name({"fixed_file_name": "固定.pdf"}), "固定.pdf")
        self.assertEqual(resolve_public_report_fixed_name({}, "fallback.html"), "fallback.html")
        self.assertEqual(resolve_public_report_fixed_name({}), DEFAULT_PUBLIC_REPORT_FILE_NAME)


if __name__ == "__main__":
    unittest.main()
