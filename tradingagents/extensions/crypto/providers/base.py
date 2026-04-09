from __future__ import annotations

from datetime import date, timedelta

from tradingagents.extensions.crypto.normalize import normalize_ticker


class ProviderError(Exception):
    pass


def chunk_date_range(
    start_date: str | None,
    end_date: str | None,
    *,
    max_points: int | None,
) -> list[tuple[str | None, str | None]]:
    """Split an inclusive daily date range into API-friendly chunks."""
    if not start_date or not end_date or max_points is None:
        return [(start_date, end_date)]

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        return []

    max_span_days = max(max_points - 1, 0)
    windows: list[tuple[str, str]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_span_days), end)
        windows.append((cursor.isoformat(), window_end.isoformat()))
        cursor = window_end + timedelta(days=1)

    return windows


def format_gate_symbol(ticker: str) -> str:
    instrument = normalize_ticker(ticker)
    return f"{instrument.base_symbol}_{instrument.quote_symbol}"
