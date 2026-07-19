from pathlib import Path
import unittest


class WorkflowContractTests(unittest.TestCase):
    def test_manual_dispatch_is_always_forced_and_schedule_uses_shared_gate(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "daily_run.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("repository: ryan-AI-stock/AI_stock_schedule_rules", workflow)
        self.assertIn("--profile daily", workflow)
        self.assertIn("- cron: '0 7-15 * * 1-5'", workflow)
        self.assertNotIn("- cron: '0 * * * *'", workflow)
        self.assertIn("default: 'true'", workflow)
        self.assertIn(
            "FORCE_RUN_REPORT: ${{ github.event_name == 'workflow_dispatch' && 'true' || 'false' }}",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
