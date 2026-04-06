"""Tests for A-share routing seam behavior."""

import unittest

from tradingagents.extensions.ashare.registry import get_registry
from tradingagents.extensions.ashare.routing import route_extension, route_symbol
from tradingagents.extensions.ashare.types import Market


class RoutingSeamTests(unittest.TestCase):
    def test_route_extension_accepts_raw_ticker_shape_from_interface(self):
        calls = []

        def fake_get_stock_data(ticker, *args, **kwargs):
            calls.append((ticker, args, kwargs))
            return {"ticker": ticker, "args": args, "kwargs": kwargs}

        registry = get_registry()
        registry.register("tushare", "get_stock_data", fake_get_stock_data)

        result = route_extension("get_stock_data", "600519", "2024-01-01", limit=10)

        self.assertEqual(result["ticker"], "600519.SS")
        self.assertEqual(result["args"], ("2024-01-01",))
        self.assertEqual(result["kwargs"], {"limit": 10})
        self.assertEqual(calls[0][0], "600519.SS")

    def test_route_symbol_reports_normalized_ticker_and_market(self):
        normalized, market, result = route_symbol("get_insider_transactions", "000001")
        self.assertEqual(normalized, "000001.SZ")
        self.assertEqual(market, Market.A_SHARE)
        self.assertIn("not supported", result)


if __name__ == "__main__":
    unittest.main()
