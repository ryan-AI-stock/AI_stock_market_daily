import unittest

from daily_stock.runtime import parse_runtime_options


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


if __name__ == "__main__":
    unittest.main()
