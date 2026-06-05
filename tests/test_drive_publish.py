import unittest

from daily_stock.drive_publish import (
    resolve_daily_report_folder_id,
    resolve_public_report_file_id,
    resolve_public_report_folder_id,
)


class DrivePublishOptionTests(unittest.TestCase):
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
