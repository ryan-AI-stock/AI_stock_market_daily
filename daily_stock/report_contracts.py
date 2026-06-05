"""Pure report-cycle and completeness contracts."""

from datetime import datetime, timedelta


def validate_report_completeness(
    results: list,
    failures: list,
    watchlist: list,
    expected_date: str,
) -> None:
    """Prevent partial or stale stock data from reaching any report output."""
    expected_tickers = {stock["ticker"] for stock in watchlist}
    result_by_ticker = {ticker: result for _, ticker, result in results}
    missing_tickers = sorted(expected_tickers - set(result_by_ticker))
    stale_tickers = sorted(
        ticker
        for ticker, result in result_by_ticker.items()
        if result.get("data_date") != expected_date
    )

    issues = []
    if failures:
        issues.append(
            "分析失敗=" + "；".join(
                f"{failure['name']}({failure['ticker']}): {failure['error']}"
                for failure in failures
            )
        )
    if missing_tickers:
        issues.append("缺少標的=" + "、".join(missing_tickers))
    if stale_tickers:
        issues.append(f"資料日非 {expected_date}=" + "、".join(stale_tickers))

    if issues:
        raise RuntimeError("報告資料不完整，禁止產生與發布檔案｜" + "｜".join(issues))


def get_report_date(now_tw: datetime) -> str:
    """Use 15:00 Taiwan time as the start of a report cycle and carry it across midnight."""
    candidate = now_tw.date()
    if now_tw.hour < 15 or candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate.strftime("%Y-%m-%d")
