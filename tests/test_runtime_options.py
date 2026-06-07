import unittest
from datetime import datetime

from daily_stock.runtime import build_report_run_context, parse_runtime_options


class RuntimeOptionsTests(unittest.TestCase):
    def test_defaults_to_normal_scheduled_run(self):
        options = parse_runtime_options({})

        self.assertEqual(options.validation_folder_id, "")
        self.assertFalse(options.validation_mode)
        self.assertFalse(options.force_run_report)
        self.assertFalse(options.should_force_run)
        self.assertFalse(options.github_actions)

    def test_validation_folder_enables_validation_and_force_run(self):
        options = parse_runtime_options({
            "REPORT_VALIDATION_DRIVE_FOLDER_ID": " folder-id ",
        })

        self.assertEqual(options.validation_folder_id, "folder-id")
        self.assertTrue(options.validation_mode)
        self.assertTrue(options.should_force_run)

    def test_force_run_accepts_existing_truthy_values(self):
        for value in ("1", "true", "yes", "y", " TRUE "):
            with self.subTest(value=value):
                self.assertTrue(parse_runtime_options({"FORCE_RUN_REPORT": value}).force_run_report)

    def test_github_actions_keeps_existing_true_only_behavior(self):
        self.assertTrue(parse_runtime_options({"GITHUB_ACTIONS": "true"}).github_actions)

        for value in ("1", "yes", "y", "false", ""):
            with self.subTest(value=value):
                self.assertFalse(parse_runtime_options({"GITHUB_ACTIONS": value}).github_actions)


class ReportRunContextTests(unittest.TestCase):
    def test_builds_report_date_and_date_key_from_cycle_rule(self):
        context = build_report_run_context(datetime(2026, 6, 5, 14, 59), {})

        self.assertEqual(context.report_date, "2026-06-04")
        self.assertEqual(context.date_key, "20260604")

    def test_report_date_env_overrides_cycle_rule(self):
        context = build_report_run_context(
            datetime(2026, 6, 6, 15, 0),
            {"REPORT_DATE": "2026-06-05"},
        )

        self.assertEqual(context.report_date, "2026-06-05")
        self.assertEqual(context.date_key, "20260605")

    def test_report_date_env_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            build_report_run_context(datetime(2026, 6, 6, 15, 0), {"REPORT_DATE": "20260605"})

    def test_keeps_runtime_options_with_report_date_override(self):
        context = build_report_run_context(
            datetime(2026, 6, 5, 15, 0),
            {"REPORT_VALIDATION_DRIVE_FOLDER_ID": "folder"},
        )
        updated = context.with_report_date("2026-06-03")

        self.assertEqual(updated.report_date, "2026-06-03")
        self.assertEqual(updated.date_key, "20260603")
        self.assertTrue(updated.runtime_options.validation_mode)
        self.assertEqual(updated.runtime_options.validation_folder_id, "folder")
        self.assertIs(context.runtime_options, updated.runtime_options)


if __name__ == "__main__":
    unittest.main()
