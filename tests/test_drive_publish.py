import unittest

from daily_stock.drive_publish import (
    GOOGLE_DRIVE_SCOPES,
    resolve_daily_report_folder_id,
    resolve_google_oauth_config,
    resolve_public_report_file_id,
    resolve_public_report_folder_id,
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


if __name__ == "__main__":
    unittest.main()
