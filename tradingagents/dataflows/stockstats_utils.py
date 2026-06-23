import logging
import os
import time
from typing import Annotated

import pandas as pd
import yfinance as yf
from stockstats import wrap
from yfinance.exceptions import YFRateLimitError

from tradingagents.extensions.market_ext import resolve_extension, route_market_extension

from .config import get_config
from .symbol_utils import NoMarketDataError, normalize_symbol
from .utils import safe_ticker_component

logger = logging.getLogger(__name__)

# A vendor's latest OHLCV row this many calendar days before the requested date
# is treated as stale. Generous enough to span long holiday weekends, tight
# enough to catch the year-old frames yfinance occasionally returns (#1021).
MAX_OHLCV_STALE_DAYS = 10


def yf_retry(func, max_retries=3, base_delay=2.0):
    """Execute a yfinance call with exponential backoff on rate limits."""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except YFRateLimitError:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Yahoo Finance rate limited, retrying in {delay:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise


def _ensure_date_column(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize the date column to ``Date``."""
    if "Date" in data.columns:
        return data
    for candidate in ("index", "Datetime", "date"):
        if candidate in data.columns:
            return data.rename(columns={candidate: "Date"})
    return data


def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a stock DataFrame for stockstats: parse dates, drop invalid rows, fill price gaps."""
    data = _ensure_date_column(data)
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])

    price_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    data[price_cols] = data[price_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["Close"])
    data[price_cols] = data[price_cols].ffill().bfill()

    return data


def _load_extension_ohlcv(symbol: str, start_str: str, end_str: str) -> pd.DataFrame:
    result = route_market_extension("get_stock_data", symbol, start_str, end_str)
    if not isinstance(result, dict):
        raise RuntimeError(f"Extension OHLCV route failed for {symbol}: {result}")

    records = result.get("data") or []
    if not records:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame(records)
    rename_map = {
        "date": "Date",
        "trade_date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "vol": "Volume",
    }
    df = df.rename(columns=rename_map)
    for col in ["Date", "Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = None
    return df[["Date", "Open", "High", "Low", "Close", "Volume"]]


def _history_window_for_symbol(curr_date_dt: pd.Timestamp) -> tuple[str, str]:
    end_dt = curr_date_dt.normalize()
    start_dt = end_dt - pd.DateOffset(years=5)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def _coerce_ohlcv_dates(data: pd.DataFrame) -> pd.Series:
    """Return parsed dates from an OHLCV frame, whether Date is a column or the index."""
    if "Date" in data.columns:
        return pd.to_datetime(data["Date"], errors="coerce").dropna()
    if isinstance(data.index, pd.DatetimeIndex):
        return pd.Series(pd.to_datetime(data.index, errors="coerce")).dropna()
    df = data.reset_index()
    for col in ("Date", "Datetime", "date", "index"):
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce").dropna()
            if not parsed.empty:
                return parsed
    return pd.Series(dtype="datetime64[ns]")


def _assert_ohlcv_not_stale(
    data: pd.DataFrame,
    curr_date: str,
    symbol: str,
    canonical: str | None = None,
    *,
    max_stale_days: int = MAX_OHLCV_STALE_DAYS,
) -> None:
    """Reject OHLCV whose latest row is far older than curr_date."""
    if data is None or data.empty:
        return
    requested = pd.to_datetime(curr_date, errors="coerce")
    if pd.isna(requested):
        return
    requested = requested.normalize()
    dates = _coerce_ohlcv_dates(data)
    if dates.empty:
        return
    latest = dates.max().normalize()
    stale_days = (requested - latest).days
    if stale_days > max_stale_days:
        raise NoMarketDataError(
            symbol,
            canonical,
            f"latest row is {latest.date()}, {stale_days} days before the "
            f"requested {requested.date()} (stale) — refusing to use it",
        )


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV data with caching, filtered to prevent look-ahead bias."""
    canonical = normalize_symbol(symbol)
    safe_symbol = safe_ticker_component(canonical)

    config = get_config()
    curr_date_dt = pd.to_datetime(curr_date)
    os.makedirs(config["data_cache_dir"], exist_ok=True)

    extension = resolve_extension(symbol)
    if extension is not None:
        start_str, end_str = _history_window_for_symbol(curr_date_dt)
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{safe_symbol}-extension-data-{start_str}-{end_str}.csv",
        )
        data = None
        if os.path.exists(data_file):
            cached = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
            if not cached.empty and "Close" in cached.columns:
                data = cached
        if data is None:
            data = _load_extension_ohlcv(symbol, start_str, end_str)
            if data.empty or "Close" not in data.columns:
                raise NoMarketDataError(symbol, canonical, "market extension returned no rows")
            data.to_csv(data_file, index=False, encoding="utf-8")
    else:
        # Cache uses a fixed window (5y to today) so one file per symbol.
        today_date = pd.Timestamp.today()
        start_date = today_date - pd.DateOffset(years=5)
        start_str = start_date.strftime("%Y-%m-%d")
        # yfinance ``end`` is EXCLUSIVE; request tomorrow so today's row is included
        # when curr_date is the current day (#986). Look-ahead is still prevented by
        # the curr_date filter below.
        end_str = (today_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        data_file = os.path.join(
            config["data_cache_dir"],
            f"{safe_symbol}-YFin-data-{start_str}-{end_str}.csv",
        )

        # A cached file may be empty if a prior fetch failed (unknown symbol,
        # transient rate limit). Treat an empty/columnless cache as a miss and
        # re-fetch rather than serving the poisoned file forever.
        data = None
        if os.path.exists(data_file):
            cached = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
            if not cached.empty and "Close" in cached.columns:
                data = cached

        if data is None:
            downloaded = yf_retry(lambda: yf.download(
                canonical,
                start=start_str,
                end=end_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            ))
            downloaded = _ensure_date_column(downloaded.reset_index())
            # Only cache real data — never persist an empty frame.
            if downloaded.empty or "Close" not in downloaded.columns:
                raise NoMarketDataError(symbol, canonical, "Yahoo Finance returned no rows")
            downloaded.to_csv(data_file, index=False, encoding="utf-8")
            data = downloaded

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]

    # Reject a stale frame (latest row far older than curr_date) rather than
    # feeding year-old prices into indicators (#1021).
    _assert_ohlcv_not_stale(data, curr_date, symbol, canonical)
    return data


def filter_financials_by_date(data: pd.DataFrame, curr_date: str) -> pd.DataFrame:
    """Drop financial statement columns (fiscal period timestamps) after curr_date."""
    if not curr_date or data.empty:
        return data
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(data.columns, errors="coerce") <= cutoff
    return data.loc[:, mask]


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
    ):
        data = load_ohlcv(symbol, curr_date)
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        curr_date_str = pd.to_datetime(curr_date).strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date_str)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
