from __future__ import annotations

from datetime import datetime, timedelta

import requests

from .base import chunk_date_range, format_gate_symbol


class GateSpotProvider:
    name = "gate_spot"
    base_url = "https://api.gateio.ws/api/v4"
    max_points_per_request = 1000

    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_symbol(self, ticker: str) -> str:
        pair = format_gate_symbol(ticker)
        payload = self._get(f"/spot/currency_pairs/{pair}")
        if payload.get("trade_status") != "tradable":
            raise RuntimeError(f"Gate spot symbol unavailable: {pair}")
        return pair

    def _window_params(self, pair: str, start_date: str | None, end_date: str | None) -> dict[str, str | int]:
        params: dict[str, str | int] = {"currency_pair": pair, "interval": "1d"}
        if start_date:
            params["from"] = int(datetime.fromisoformat(start_date).timestamp())
        if end_date:
            end_ts = int((datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            params["to"] = end_ts
        return params

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        pair = self._ensure_symbol(ticker)
        data = []
        windows = chunk_date_range(
            start_date,
            end_date,
            max_points=self.max_points_per_request,
        )
        if not windows:
            return {"ticker": ticker, "data": data, "provider": self.name, "source": "gate_spot"}

        for chunk_start, chunk_end in windows:
            params = self._window_params(pair, chunk_start, chunk_end)
            rows = self._get("/spot/candlesticks", params)
            for row in rows:
                row_date = datetime.fromtimestamp(int(row[0])).strftime("%Y-%m-%d")
                if start_date and row_date < start_date:
                    continue
                if end_date and row_date > end_date:
                    continue
                data.append(
                    {
                        "date": row_date,
                        "open": float(row[5]),
                        "high": float(row[3]),
                        "low": float(row[4]),
                        "close": float(row[2]),
                        "volume": float(row[6]),
                    }
                )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "gate_spot"}
