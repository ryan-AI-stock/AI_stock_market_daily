import json
from pathlib import Path
import unittest

from daily_stock.html_snapshot import build_html_structure_snapshot
import stock_market_tracking_system as sm


SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "public_report_structure.json"


def fixture_result() -> dict:
    return {
        "summary": "中訊號",
        "trade_plan": {"headline": "觀察", "reason": "條件觀察"},
        "level": "MID",
        "border": "#3498db",
        "close": 100.0,
        "effective_buy": 40.0,
        "effective_sell": 20.0,
        "items": [],
        "regime": {"label": "中性", "color": "#95a5a6"},
        "b60": {"label": "正常", "color": "#95a5a6", "bias60": 0.0},
    }


class PublicReportSnapshotTests(unittest.TestCase):
    def test_public_report_structure_matches_approved_baseline(self):
        results = [
            (f"標的{index}", f"{1000 + index}.TW", fixture_result())
            for index in range(8)
        ]
        html = sm.build_public_report_html(
            results,
            "2026-06-05",
            cfg={},
            macro={},
            news_items=[],
            market_events=[],
        )

        expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(build_html_structure_snapshot(html), expected)


class CompatibilityEntryPointTests(unittest.TestCase):
    def test_backtest_entry_points_remain_available(self):
        for function_name in (
            "load_config",
            "get_stock_cfg",
            "calc_indicators",
            "evaluate_weighted",
        ):
            self.assertTrue(callable(getattr(sm, function_name, None)), function_name)

    def test_retained_legacy_and_email_entry_points_remain_available(self):
        self.assertTrue(callable(sm.evaluate))
        self.assertTrue(callable(sm.send_email))


if __name__ == "__main__":
    unittest.main()
