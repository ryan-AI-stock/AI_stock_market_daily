"""
backtest_twii_0050.py

用途：
用現有 stock_market_tracking_system.py 的台灣加權指數邏輯，
回測操作 0050.TW 的績效。

核心邏輯：
1. 用 ^TWII 產生每日訊號
2. 用 0050.TW 執行交易
3. 比較策略績效 vs 買進持有 0050
4. 計入買進手續費、賣出手續費、ETF 證交稅
5. 跑多組參數，找出較通用的操作組合

注意：
目前使用 yfinance 日線資料，因此交易價格先用 0050 當日收盤價。
若要精準模擬 10:30 / 13:15，需要之後接台股分鐘線資料。
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

import stock_market_tracking_system as sm


BUY_FEE = 0.001425          # 買進手續費 0.1425%
SELL_FEE = 0.001425         # 賣出手續費 0.1425%
ETF_TAX = 0.001             # ETF 證交稅 0.1%
SELL_TOTAL_COST = SELL_FEE + ETF_TAX

INITIAL_CAPITAL = 1_000_000
MIN_TRADE_RATIO = 0.05      # 部位差異小於 5%，不交易，避免過度進出


def download_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
    )

    if df.empty:
        raise ValueError(f"無法取得 {ticker} 資料")

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def download_close(ticker: str, start: str, end: str) -> pd.Series:
    df = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
    )

    if df.empty:
        raise ValueError(f"無法取得 {ticker} 資料")

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    s = df["Close"].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s


def change_pct(series: pd.Series, date: pd.Timestamp, periods: int) -> float | None:
    hist = series.loc[:date].dropna()
    if len(hist) <= periods:
        return None

    prev = float(hist.iloc[-1 - periods])
    curr = float(hist.iloc[-1])

    if prev == 0:
        return None

    return (curr - prev) / prev * 100


def change_bp(series: pd.Series, date: pd.Timestamp, periods: int) -> float | None:
    hist = series.loc[:date].dropna()
    if len(hist) <= periods:
        return None

    prev = float(hist.iloc[-1 - periods])
    curr = float(hist.iloc[-1])
    return (curr - prev) * 100


def build_macro_at(
    date: pd.Timestamp,
    fx_series: pd.Series | None,
    rate_series: pd.Series | None,
) -> dict[str, Any]:
    macro = {
        "success": True,
        "fx": None,
        "rates": None,
        "errors": [],
    }

    if fx_series is not None:
        fx_hist = fx_series.loc[:date].dropna()
        if len(fx_hist) > 21:
            macro["fx"] = {
                "ticker": "TWD=X",
                "label": "美元/台幣",
                "value": float(fx_hist.iloc[-1]),
                "chg_5d_pct": change_pct(fx_series, date, 5),
                "chg_20d_pct": change_pct(fx_series, date, 20),
            }
        else:
            macro["errors"].append("匯率資料不足")

    if rate_series is not None:
        rate_hist = rate_series.loc[:date].dropna()
        if len(rate_hist) > 21:
            macro["rates"] = {
                "ticker": "^TNX",
                "label": "美國10年期公債殖利率",
                "value": float(rate_hist.iloc[-1]),
                "chg_5d_bp": change_bp(rate_series, date, 5),
                "chg_20d_bp": change_bp(rate_series, date, 20),
            }
        else:
            macro["errors"].append("利率資料不足")

    if macro["errors"]:
        macro["success"] = False

    return macro


def find_twii_config(cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    for stock in cfg["watchlist"]:
        if stock["ticker"] == "^TWII":
            return stock, sm.get_stock_cfg(stock, cfg)

    raise ValueError("config.json 找不到 ^TWII 設定")


def parse_level(level: str) -> tuple[str, str]:
    if level.startswith("BUY_"):
        return "BUY", level.replace("BUY_", "")
    if level.startswith("SELL_"):
        return "SELL", level.replace("SELL_", "")
    if level.startswith("OVERHEATED_"):
        return "OVERHEATED", level.replace("OVERHEATED_", "")
    if level == "OVERHEATED":
        return "OVERHEATED", "NEUTRAL"
    return "HOLD", "NEUTRAL"


def is_extreme_risk(result: dict[str, Any]) -> bool:
    """
    極端風險才允許空手。
    這裡不用新聞事件，先純用模型內部條件判斷。
    之後如果要加入川普關稅、美伊戰爭、COVID 類事件，
    可以新增外部事件風險分數。
    """
    regime_key = result.get("regime", {}).get("key")
    level = result.get("level", "")
    effective_sell = float(result.get("effective_sell", 0))
    b60_zone = result.get("b60", {}).get("zone")

    if level == "SELL_STRONG" and regime_key == "BEAR" and effective_sell >= 50:
        return True

    if regime_key == "BEAR" and effective_sell >= 70:
        return True

    if level.startswith("OVERHEATED") and effective_sell >= 70 and b60_zone == "overheated":
        return True

    return False


def target_position_from_signal(
    result: dict[str, Any],
    current_position: float,
    policy: dict[str, Any],
) -> float:
    """
    把 ^TWII 訊號轉成 0050 目標持股比例。
    0.0 = 空手
    1.0 = 滿倉
    """
    level = result.get("level", "NEUTRAL")
    direction, strength = parse_level(level)

    regime_key = result.get("regime", {}).get("key", "")
    b60 = result.get("b60", {})
    b60_zone = b60.get("zone")

    if is_extreme_risk(result):
        return policy["extreme_risk_position"]

    if direction == "BUY":
        if strength == "STRONG":
            target = policy["buy_strong"]
        elif strength == "MID":
            target = policy["buy_mid"]
        elif strength == "WEAK":
            target = policy["buy_weak"]
        else:
            target = current_position

        # 超跌但不是明確空頭時，至少保留一定部位
        if b60_zone == "oversold" and regime_key != "BEAR":
            target = max(target, policy["oversold_min_position"])

        # 空頭反彈不重倉
        if regime_key == "BEAR":
            target = min(target, policy["bear_buy_cap"])

        return target

    if direction == "SELL":
        if strength == "STRONG":
            return policy["sell_strong"]
        if strength == "MID":
            return policy["sell_mid"]
        if strength == "WEAK":
            return policy["sell_weak"]
        return current_position

    if direction == "OVERHEATED":
        # 單純過熱：不追買，但不一定賣光
        if strength == "STRONG":
            return min(current_position, policy["overheated_strong_cap"])
        if strength == "MID":
            return min(current_position, policy["overheated_mid_cap"])
        return current_position

    return current_position


def apply_overrides(base_stock: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    stock = json.loads(json.dumps(base_stock))
    overrides = stock.setdefault("overrides", {})

    overrides["kd_buy"] = params["kd_buy"]
    overrides["kd_sell"] = params["kd_sell"]
    overrides["bias60_p_low"] = params["bias60_p_low"]
    overrides["bias60_p_high"] = params["bias60_p_high"]
    overrides["use_fx"] = params["use_fx"]
    overrides["use_rates"] = params["use_rates"]
    overrides["ma_periods"] = {
        "short": params["ma_short"],
        "mid": params["ma_mid"],
        "long": params["ma_long"],
    }

    # 台灣加權指數不使用個股籌碼、OBV、量能
    overrides["use_institutional"] = False
    overrides["use_obv"] = False
    overrides["use_vol_trend"] = False

    return stock


def simulate_strategy(
    twii_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    fx_series: pd.Series | None,
    rate_series: pd.Series | None,
    cfg: dict[str, Any],
    base_stock: dict[str, Any],
    params: dict[str, Any],
    policy: dict[str, Any],
    start_date: str,
    initial_capital: float = INITIAL_CAPITAL,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    stock = apply_overrides(base_stock, params)
    scfg = sm.get_stock_cfg(stock, cfg)

    cash = initial_capital
    shares = 0.0
    position = 0.0
    trades = []
    rows = []

    start_ts = pd.Timestamp(start_date)

    for date in etf_df.index:
        if date < start_ts:
            continue

        if date not in twii_df.index:
            continue

        twii_slice = twii_df.loc[:date].copy()

        # 指標至少需要一段暖機資料
        if len(twii_slice) < 120:
            continue

        try:
            ind = sm.calc_indicators(twii_slice, scfg)
            ind = ind.dropna()
            if len(ind) < 80:
                continue

            macro = build_macro_at(date, fx_series, rate_series)

            result = sm.evaluate_weighted(
                ind,
                scfg,
                inst=None,
                macro=macro,
                fundamentals={"success": False, "error": "指數不使用基本面", "data": {}},
            )
        except Exception as exc:
            rows.append({
                "date": date,
                "error": str(exc),
            })
            continue

        price = float(etf_df.loc[date, "Close"])
        equity_before = cash + shares * price
        current_value = shares * price

        target = target_position_from_signal(result, position, policy)
        target = max(0.0, min(1.0, float(target)))

        target_value = equity_before * target
        diff_value = target_value - current_value

        traded = False
        trade_action = "HOLD"
        trade_value = 0.0
        cost = 0.0

        if equity_before > 0 and abs(diff_value) / equity_before >= MIN_TRADE_RATIO:
            if diff_value > 0:
                # 買進
                buy_value = min(diff_value, cash / (1 + BUY_FEE))
                if buy_value > 0:
                    buy_shares = buy_value / price
                    fee = buy_value * BUY_FEE
                    shares += buy_shares
                    cash -= buy_value + fee

                    traded = True
                    trade_action = "BUY"
                    trade_value = buy_value
                    cost = fee

            elif diff_value < 0:
                # 賣出
                sell_value = min(-diff_value, current_value)
                if sell_value > 0:
                    sell_shares = sell_value / price
                    fee_tax = sell_value * SELL_TOTAL_COST
                    shares -= sell_shares
                    cash += sell_value - fee_tax

                    traded = True
                    trade_action = "SELL"
                    trade_value = sell_value
                    cost = fee_tax

        equity_after = cash + shares * price
        position = (shares * price / equity_after) if equity_after > 0 else 0.0

        if traded:
            trades.append({
                "date": date,
                "action": trade_action,
                "price": price,
                "trade_value": trade_value,
                "cost": cost,
                "target_position": target,
                "actual_position": position,
                "level": result.get("level"),
                "summary": result.get("summary"),
            })

        rows.append({
            "date": date,
            "price_0050": price,
            "equity": equity_after,
            "cash": cash,
            "shares": shares,
            "position": position,
            "target_position": target,
            "level": result.get("level"),
            "summary": result.get("summary"),
            "effective_buy": result.get("effective_buy"),
            "effective_sell": result.get("effective_sell"),
            "regime": result.get("regime", {}).get("key"),
            "b60_zone": result.get("b60", {}).get("zone"),
            "b60": result.get("b60", {}).get("bias60"),
            "trade_action": trade_action,
            "trade_value": trade_value,
            "cost": cost,
            "error": "",
        })

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        raise ValueError("回測結果為空，請檢查資料日期或參數")

    result_df = result_df.dropna(subset=["equity"]).copy()
    result_df["date"] = pd.to_datetime(result_df["date"])
    result_df = result_df.set_index("date")

    summary = summarize_result(result_df, etf_df, trades, start_date, initial_capital)
    summary["params"] = params
    summary["policy"] = policy
    return result_df, summary


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1
    return float(dd.min())


def summarize_result(
    result_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    trades: list[dict[str, Any]],
    start_date: str,
    initial_capital: float,
) -> dict[str, Any]:
    equity = result_df["equity"]
    strategy_return = float(equity.iloc[-1] / initial_capital - 1)

    etf_test = etf_df.loc[result_df.index]
    buy_hold_return = float(etf_test["Close"].iloc[-1] / etf_test["Close"].iloc[0] - 1)

    strategy_mdd = max_drawdown(equity)

    buy_hold_equity = initial_capital * etf_test["Close"] / etf_test["Close"].iloc[0]
    buy_hold_mdd = max_drawdown(buy_hold_equity)

    total_cost = float(result_df["cost"].sum()) if "cost" in result_df else 0.0

    return {
        "start": str(result_df.index[0].date()),
        "end": str(result_df.index[-1].date()),
        "strategy_return_pct": strategy_return * 100,
        "buy_hold_return_pct": buy_hold_return * 100,
        "excess_return_pct": (strategy_return - buy_hold_return) * 100,
        "strategy_mdd_pct": strategy_mdd * 100,
        "buy_hold_mdd_pct": buy_hold_mdd * 100,
        "trade_count": len(trades),
        "total_cost": total_cost,
        "final_equity": float(equity.iloc[-1]),
    }


def build_param_grid() -> list[dict[str, Any]]:
    grid = []

    ma_sets = [
        (5, 20, 60),
        (10, 20, 60),
        (10, 30, 60),
        (20, 60, 120),
    ]

    kd_sets = [
        (30, 70),
        (35, 75),
        (40, 80),
    ]

    bias_sets = [
        (5, 95),
        (10, 90),
        (5, 90),
    ]

    macro_sets = [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ]

    for ma, kd, bias, macro in itertools.product(ma_sets, kd_sets, bias_sets, macro_sets):
        grid.append({
            "ma_short": ma[0],
            "ma_mid": ma[1],
            "ma_long": ma[2],
            "kd_buy": kd[0],
            "kd_sell": kd[1],
            "bias60_p_low": bias[0],
            "bias60_p_high": bias[1],
            "use_fx": macro[0],
            "use_rates": macro[1],
        })

    return grid


def build_policy_grid() -> list[dict[str, Any]]:
    return [
        {
            "name": "balanced",
            "buy_strong": 1.0,
            "buy_mid": 0.7,
            "buy_weak": 0.4,
            "oversold_min_position": 0.6,
            "bear_buy_cap": 0.3,
            "sell_strong": 0.2,
            "sell_mid": 0.4,
            "sell_weak": 0.7,
            "overheated_strong_cap": 0.5,
            "overheated_mid_cap": 0.7,
            "extreme_risk_position": 0.0,
        },
        {
            "name": "conservative",
            "buy_strong": 0.8,
            "buy_mid": 0.5,
            "buy_weak": 0.3,
            "oversold_min_position": 0.5,
            "bear_buy_cap": 0.2,
            "sell_strong": 0.1,
            "sell_mid": 0.3,
            "sell_weak": 0.6,
            "overheated_strong_cap": 0.4,
            "overheated_mid_cap": 0.6,
            "extreme_risk_position": 0.0,
        },
        {
            "name": "trend_follow",
            "buy_strong": 1.0,
            "buy_mid": 0.8,
            "buy_weak": 0.5,
            "oversold_min_position": 0.7,
            "bear_buy_cap": 0.2,
            "sell_strong": 0.2,
            "sell_mid": 0.5,
            "sell_weak": 0.8,
            "overheated_strong_cap": 0.7,
            "overheated_mid_cap": 0.9,
            "extreme_risk_position": 0.0,
        },
    ]


def run_optimization(args: argparse.Namespace) -> None:
    cfg = sm.load_config()
    base_stock, _ = find_twii_config(cfg)

    # 為了有足夠暖機資料，實際下載從 start 往前抓
    download_start = pd.Timestamp(args.start) - pd.DateOffset(days=900)
    download_start_str = download_start.strftime("%Y-%m-%d")

    twii_df = download_ohlcv("^TWII", download_start_str, args.end)
    etf_df = download_ohlcv("0050.TW", download_start_str, args.end)

    fx_series = download_close("TWD=X", download_start_str, args.end)
    rate_series = download_close("^TNX", download_start_str, args.end)

    param_grid = build_param_grid()
    policy_grid = build_policy_grid()

    summaries = []
    best_detail = None
    best_score = -999999

    total = len(param_grid) * len(policy_grid)
    count = 0

    for params, policy in itertools.product(param_grid, policy_grid):
        count += 1
        print(f"[{count}/{total}] 測試中：{policy['name']} {params}")

        try:
            detail, summary = simulate_strategy(
                twii_df=twii_df,
                etf_df=etf_df,
                fx_series=fx_series,
                rate_series=rate_series,
                cfg=cfg,
                base_stock=base_stock,
                params=params,
                policy=policy,
                start_date=args.start,
                initial_capital=args.capital,
            )
        except Exception as exc:
            print(f"失敗：{exc}")
            continue

        # 評分：超額報酬優先，但懲罰過大回撤與交易過度
        score = (
            summary["excess_return_pct"]
            + abs(summary["buy_hold_mdd_pct"] - summary["strategy_mdd_pct"]) * 0.5
            - max(0, summary["trade_count"] - 30) * 0.2
        )

        summary["score"] = score
        summary["policy_name"] = policy["name"]
        summaries.append(summary)

        if score > best_score:
            best_score = score
            best_detail = detail

    if not summaries:
        raise RuntimeError("沒有任何成功的回測結果")

    summary_df = pd.DataFrame(summaries)
    summary_df = summary_df.sort_values(
        ["score", "excess_return_pct", "strategy_mdd_pct"],
        ascending=[False, False, False],
    )

    out_dir = Path("backtest_outputs")
    out_dir.mkdir(exist_ok=True)

    summary_path = out_dir / "twii_0050_backtest_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    if best_detail is not None:
        detail_path = out_dir / "twii_0050_best_detail.csv"
        best_detail.to_csv(detail_path, encoding="utf-8-sig")

    print("\n====== 前 10 名結果 ======")
    cols = [
        "policy_name",
        "strategy_return_pct",
        "buy_hold_return_pct",
        "excess_return_pct",
        "strategy_mdd_pct",
        "buy_hold_mdd_pct",
        "trade_count",
        "total_cost",
        "score",
        "params",
    ]
    print(summary_df[cols].head(10).to_string(index=False))

    print(f"\n已輸出：{summary_path}")
    if best_detail is not None:
        print(f"已輸出：{detail_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--capital", type=float, default=INITIAL_CAPITAL)
    args = parser.parse_args()

    if args.end is None:
        args.end = pd.Timestamp.today().strftime("%Y-%m-%d")

    run_optimization(args)


if __name__ == "__main__":
    main()