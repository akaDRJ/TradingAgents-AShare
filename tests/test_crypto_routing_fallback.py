"""Tests for crypto provider fallback order."""

import unittest
from unittest.mock import patch

from tradingagents.extensions.crypto.routing import route_extension


class _Registry:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, provider, method):
        return self.mapping.get((provider, method))


class CryptoRoutingFallbackTests(unittest.TestCase):
    def test_route_extension_uses_binance_futures_after_spot_failure(self):
        calls = []

        def spot_fail(*args, **kwargs):
            calls.append(("binance_spot", args[0]))
            raise RuntimeError("spot missing")

        def futures_ok(*args, **kwargs):
            calls.append(("binance_futures", args[0]))
            return {"ticker": args[0], "provider": "binance_futures", "data": []}

        registry = _Registry(
            {
                ("binance_spot", "get_stock_data"): spot_fail,
                ("binance_futures", "get_stock_data"): futures_ok,
            }
        )

        with (
            patch(
                "tradingagents.extensions.crypto.routing.get_provider_chain",
                return_value=["binance_spot", "binance_futures", "gate_spot"],
            ),
            patch(
                "tradingagents.extensions.crypto.routing.get_registry",
                return_value=registry,
            ),
        ):
            result = route_extension("get_stock_data", "KASUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["provider"], "binance_futures")
        self.assertEqual(
            calls,
            [("binance_spot", "KASUSDT"), ("binance_futures", "KASUSDT")],
        )


if __name__ == "__main__":
    unittest.main()
