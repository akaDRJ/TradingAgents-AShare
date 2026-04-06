"""AKShare provider for A-share market data.

Requires: pip install akshare
"""

from typing import Any, Dict, Optional

from .base import BaseProvider


class AKShareProvider(BaseProvider):
    """AKShare-based A-share data provider.

    Fetches OHLCV data via AKShare (free, no API key required).
    Uses a fallback chain because the Eastmoney-backed endpoint can be unstable
    on some hosts:
    1. Eastmoney `stock_zh_a_hist`
    2. Sina `stock_zh_a_daily`
    3. Tencent `stock_zh_a_hist_tx`
    """

    name = "akshare"

    def __init__(self) -> None:
        self._available: bool = self._check_available()

    def _check_available(self) -> bool:
        """Check if akshare is installed and importable."""
        try:
            import akshare as ak  # noqa: F401
            return True
        except ImportError:
            return False

    def _parse_ticker(self, ticker: str) -> tuple[str, str]:
        parts = ticker.rsplit(".", 1)
        if len(parts) != 2:
            self._error(ticker, f"Invalid ticker format: {ticker}")
        return parts[0], parts[1].upper()

    def _to_prefixed_symbol(self, code: str, exchange: str) -> str:
        exchange_map = {
            "SS": "sh",
            "SZ": "sz",
            "BJ": "bj",
        }
        prefix = exchange_map.get(exchange)
        if prefix is None:
            self._error(code, f"Unsupported exchange suffix: {exchange}")
        return f"{prefix}{code}"

    def _normalize_frame(self, df, source: str, ticker: str) -> Dict[str, Any]:
        if df is None or (hasattr(df, "empty") and df.empty):
            return {
                "ticker": ticker,
                "data": [],
                "provider": self.name,
                "source": source,
            }

        rename_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
            "换手率": "turnover",
        }
        if hasattr(df, "rename"):
            df = df.rename(columns=rename_map)

        records = df.to_dict("records") if hasattr(df, "to_dict") else []
        return {
            "ticker": ticker,
            "data": records,
            "provider": self.name,
            "source": source,
        }

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Fetch OHLCV bar data via AKShare fallback chain."""
        if not self._available:
            self._error(
                ticker,
                "AKShare not available: install with 'pip install akshare'. "
                "No API key required."
            )

        import akshare as ak

        code, exchange = self._parse_ticker(ticker)
        prefixed = self._to_prefixed_symbol(code, exchange)
        start_compact = (start_date or "").replace("-", "")
        end_compact = (end_date or "").replace("-", "")
        adjust = kwargs.get("adjust", "qfq")

        last_error: Exception | None = None

        # 1) Eastmoney-backed endpoint
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "eastmoney", ticker)
        except Exception as exc:
            last_error = exc

        # 2) Sina fallback
        try:
            df = ak.stock_zh_a_daily(
                symbol=prefixed,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "sina", ticker)
        except Exception as exc:
            last_error = exc

        # 3) Tencent fallback
        try:
            df = ak.stock_zh_a_hist_tx(
                symbol=prefixed,
                start_date=start_compact,
                end_date=end_compact,
                adjust=adjust,
            )
            return self._normalize_frame(df, "tencent", ticker)
        except Exception as exc:
            last_error = exc

        self._error(ticker, f"AKShare fallback chain failed: {last_error}")


_provider_instance: Optional[AKShareProvider] = None


def get_provider() -> AKShareProvider:
    """Return the singleton AKShare provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AKShareProvider()
    return _provider_instance
