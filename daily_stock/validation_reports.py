"""Helpers for isolated validation report publishing."""

from pathlib import Path

import pandas as pd


def validation_report_file_name(fixed_path: Path, report_date: str) -> str:
    return f"每日台股報告_驗收_{report_date.replace('-', '')}{fixed_path.suffix.lower()}"


def trim_market_data_to_report_date(df: pd.DataFrame, report_date: str) -> pd.DataFrame:
    """Return market data available through the requested report date."""
    trimmed = df.loc[df.index.strftime("%Y-%m-%d") <= report_date].copy()
    if trimmed.empty:
        raise ValueError(f"無 {report_date} 或更早的市場資料")
    return trimmed


def find_latest_common_market_date(
    market_data_by_ticker: dict[str, pd.DataFrame],
    latest_date: str,
) -> str:
    """Find the latest date available for every tracked ticker."""
    common_dates: set[str] | None = None
    for df in market_data_by_ticker.values():
        dates = {
            value
            for value in df.index.strftime("%Y-%m-%d")
            if value <= latest_date
        }
        common_dates = dates if common_dates is None else common_dates & dates
    if not common_dates:
        raise ValueError(f"所有追蹤標的在 {latest_date} 前沒有共同市場資料日")
    return max(common_dates)
