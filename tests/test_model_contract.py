import math
import unittest

import pandas as pd

import stock_market_tracking_system as sm


def synthetic_market_data(rows: int = 260) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=rows)
    close = pd.Series(
        [100 + day * 0.12 + math.sin(day / 7) * 2.5 for day in range(rows)],
        index=index,
    )
    return pd.DataFrame(
        {
            "Open": close.shift(1).fillna(close.iloc[0]) * 1.001,
            "High": close * 1.012,
            "Low": close * 0.988,
            "Close": close,
            "Volume": [1_000_000 + (day % 13) * 25_000 for day in range(rows)],
        },
        index=index,
    )


class WeightedModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = sm.load_config()
        cls.stock_config = sm.get_stock_cfg(config["watchlist"][0], config)
        cls.market_data = synthetic_market_data()

    def evaluate_slice(self, rows: int) -> dict:
        indicators = sm.calc_indicators(
            self.market_data.iloc[:rows].copy(),
            self.stock_config,
        )
        return sm.evaluate_weighted(
            indicators,
            self.stock_config,
            inst=None,
            macro={},
            fundamentals={},
        )

    def test_weighted_model_accepts_historical_slices(self):
        result = self.evaluate_slice(220)

        self.assertEqual(result["level"], "BUY_NOTICE")
        self.assertEqual(result["effective_buy"], 24.0)
        self.assertEqual(result["effective_sell"], 0.0)
        self.assertEqual(result["regime"]["key"], "STRONG_BULL")
        self.assertEqual(result["trade_plan"]["trade_pct"], 0)
        self.assertAlmostEqual(result["close"], 125.95538850276967)

    def test_weighted_model_matches_current_full_history_baseline(self):
        result = self.evaluate_slice(260)

        self.assertEqual(result["level"], "BUY_WEAK")
        self.assertEqual(result["effective_buy"], 34.0)
        self.assertEqual(result["effective_sell"], 0.0)
        self.assertEqual(result["regime"]["key"], "BULL_PULLBACK")
        self.assertEqual(result["trade_plan"]["trade_pct"], 10)
        self.assertAlmostEqual(result["close"], 129.47115466660748)


if __name__ == "__main__":
    unittest.main()
