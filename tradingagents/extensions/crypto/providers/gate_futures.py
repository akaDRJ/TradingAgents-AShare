from __future__ import annotations

from datetime import datetime, timedelta

import requests

from .base import format_gate_symbol


class GateFuturesProvider:
    name = "gate_futures"
    base_url = "https://api.gateio.ws/api/v4"

    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def _ensure_symbol(self, ticker: str) -> str:
        contract = format_gate_symbol(ticker)
        payload = self._get(f"/futures/usdt/contracts/{contract}")
        if payload.get("status") != "trading":
            raise RuntimeError(f"Gate futures symbol unavailable: {contract}")
        return contract

    def _window_params(self, contract: str, start_date: str | None, end_date: str | None) -> dict[str, str | int]:
        params: dict[str, str | int] = {"contract": contract, "interval": "1d"}
        if start_date:
            params["from"] = int(datetime.fromisoformat(start_date).timestamp())
        if end_date:
            end_ts = int((datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(seconds=1)).timestamp())
            params["to"] = end_ts
        return params

    def get_stock_data(self, ticker: str, start_date: str | None = None, end_date: str | None = None, **kwargs):
        contract = self._ensure_symbol(ticker)
        params = self._window_params(contract, start_date, end_date)
        rows = self._get("/futures/usdt/candlesticks", params)
        data = []
        for row in rows:
            row_date = datetime.fromtimestamp(int(row["t"])).strftime("%Y-%m-%d")
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            data.append(
                {
                    "date": row_date,
                    "open": float(row["o"]),
                    "high": float(row["h"]),
                    "low": float(row["l"]),
                    "close": float(row["c"]),
                    "volume": float(row["v"]),
                }
            )
        return {"ticker": ticker, "data": data, "provider": self.name, "source": "gate_futures"}
