"""Configuration loading and per-stock override merging."""

import json
from pathlib import Path


def load_config(base_dir: Path | None = None) -> dict:
    root = base_dir or Path(__file__).resolve().parent.parent
    with open(root / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_stock_cfg(stock: dict, global_cfg: dict) -> dict:
    """
    Merge global settings with per-stock overrides.
    Per-stock settings always take precedence.
    """
    overrides = stock.get("overrides", {})
    thresholds = dict(global_cfg["thresholds"])
    ma_periods = dict(global_cfg["ma_periods"])

    for key in (
        "kd_buy",
        "kd_sell",
        "bias20_buy",
        "bias20_sell",
        "bias60_p_low",
        "bias60_p_high",
        "vol_ma_period",
        "obv_ma_period",
    ):
        if key in overrides:
            thresholds[key] = overrides[key]

    if "bias_buy" in thresholds and "bias20_buy" not in thresholds:
        thresholds["bias20_buy"] = thresholds["bias_buy"]
    if "bias_sell" in thresholds and "bias20_sell" not in thresholds:
        thresholds["bias20_sell"] = thresholds["bias_sell"]

    if "ma_periods" in overrides:
        ma_periods.update(overrides["ma_periods"])

    return {
        "thresholds": thresholds,
        "ma_periods": ma_periods,
        "pyramid": global_cfg.get("pyramid", {}),
        "use_obv": overrides.get("use_obv", True),
        "use_vol_trend": overrides.get("use_vol_trend", True),
        "use_institutional": overrides.get("use_institutional", True),
        "use_fx": overrides.get("use_fx", True),
        "use_rates": overrides.get("use_rates", True),
        "macro_sensitivity": overrides.get("macro_sensitivity", "market"),
        "leverage_warning": overrides.get("leverage_warning", False),
        "bias60_locked": overrides.get("bias60_locked", True),
    }
