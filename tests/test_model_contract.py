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


def synthetic_downtrend_data(rows: int = 280) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=rows)
    close = pd.Series(
        [150 - day * 0.18 + (day % 7) * 0.15 for day in range(rows)],
        index=index,
    )
    return pd.DataFrame(
        {
            "Open": close.shift(1).fillna(close.iloc[0]),
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": [1_000_000 + (day % 5) * 10_000 for day in range(rows)],
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

    def test_calc_indicators_adds_risk_adjusted_momentum_columns(self):
        indicators = sm.calc_indicators(
            self.market_data.copy(),
            self.stock_config,
        )

        for column_name in (
            "Ret20",
            "Ret60",
            "Ret120",
            "Vol20_Ann",
            "MA120",
            "MA200",
            "MA200_Slope20",
            "Drawdown252",
            "RiskAdjustedMomentum",
        ):
            self.assertIn(column_name, indicators.columns)
        self.assertTrue(pd.notna(indicators["RiskAdjustedMomentum"].iloc[-1]))

    def test_long_term_downtrend_increases_risk_score(self):
        indicators = sm.calc_indicators(
            synthetic_downtrend_data(),
            self.stock_config,
        )
        result = sm.evaluate_weighted(
            indicators,
            self.stock_config,
            inst=None,
            macro={},
            fundamentals={},
        )

        trend_item = next(item for item in result["items"] if item[0] == "趨勢環境")
        self.assertEqual(result["regime"]["key"], "BEAR")
        self.assertEqual(trend_item[1], "長期趨勢轉弱")
        self.assertGreater(result["effective_sell"], result["effective_buy"])
        self.assertIn("中長期動能同步轉弱", result["trade_plan"]["reason"])


if __name__ == "__main__":
    unittest.main()
