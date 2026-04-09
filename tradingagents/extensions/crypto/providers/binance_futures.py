from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from .base import chunk_date_range


class BinanceFuturesProvider:
    name = "binance_futures"
    base_url = "https://fapi.binance.com"
    max_points_per_request = 1500

    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_symbol(self, symbol: str) -> None:
        payload = self._get("/fapi/v1/exchangeInfo", {"symbol": symbol})
        symbols = payload.get("symbols", [])
        if not symbols or symbols[0].get("status") != "TRADING":
            raise RuntimeError(f"Binance futures symbol unavailable: {symbol}")

    def _window_params(self, start_date: str | None, end_date: str | None) -> dict[str, int]:
        params: dict[str, int] = {}
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC) if start_date else None
        end_dt = (
            datetime.fromisoformat(end_date).replace(tzinfo=UTC) + timedelta(days=1) - timedelta(milliseconds=1)
            if end_date
            else None
        )
        effective_end_dt = end_dt or datetime.now(UTC)

        if start_dt is not None:
            params["startTime"] = int(start_dt.timestamp() * 1000)
        if end_dt is not None:
            params["endTime"] = int(end_dt.timestamp() * 1000)

        if start_dt is not None:
            span_days = max(int(((effective_end_dt + timedelta(milliseconds=1)) - start_dt).days), 1)
            params["limit"] = min(span_days, self.max_points_per_request)
        elif params:
            params["limit"] = self.max_points_per_request

        return params

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        self._ensure_symbol(ticker)
        data = []
        windows = chunk_date_range(
            start_date,
            end_date,
            max_points=self.max_points_per_request,
        )
        if not windows:
            return {"ticker": ticker, "data": data, "provider": self.name, "source": "binance_futures"}

        for chunk_start, chunk_end in windows:
            params = {"symbol": ticker, "interval": "1d"}
            params.update(self._window_params(chunk_start, chunk_end))
            if "limit" not in params:
                params["limit"] = 365
            rows = self._get("/fapi/v1/klines", params)
            for row in rows:
                row_date = datetime.fromtimestamp(row[0] / 1000, UTC).strftime("%Y-%m-%d")
                if start_date and row_date < start_date:
                    continue
                if end_date and row_date > end_date:
                    continue
                data.append(
                    {
                        "date": row_date,
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "binance_futures"}
