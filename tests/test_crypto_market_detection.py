"""Tests for crypto market detection."""

import unittest
from unittest.mock import patch

import tradingagents.dataflows.interface as interface
from tradingagents.extensions import ashare, crypto
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.extensions.market_ext import get_extension, reset_extensions_for_test
from tradingagents.extensions.crypto.normalize import detect_market
from tradingagents.extensions.market_ext.types import Market


class CryptoMarketDetectionTests(unittest.TestCase):
    def test_known_bare_symbols_are_crypto(self):
        self.assertEqual(detect_market("BTC"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH"), Market.CRYPTO)

    def test_pair_inputs_are_crypto(self):
        self.assertEqual(detect_market("BTCUSDT"), Market.CRYPTO)
        self.assertEqual(detect_market("ETH-USD"), Market.CRYPTO)

    def test_equity_tickers_do_not_accidentally_route_to_crypto(self):
        self.assertEqual(detect_market("AAPL"), Market.UNKNOWN)
        self.assertEqual(detect_market("600519"), Market.UNKNOWN)


class CryptoExtensionRegistrationTests(unittest.TestCase):
    def tearDown(self):
        reset_extensions_for_test()
        ashare.ensure_registered()
        crypto.ensure_registered()

    def test_crypto_can_re_register_after_extension_reset(self):
        reset_extensions_for_test()
        self.assertIsNone(get_extension("crypto"))

        crypto.ensure_registered()

        extension = get_extension("crypto")
        self.assertIsNotNone(extension)
        self.assertEqual(extension.name, "crypto")


class CryptoNewsRoutingTests(unittest.TestCase):
    def test_route_to_vendor_skips_extension_for_unimplemented_crypto_news(self):
        with (
            patch("tradingagents.dataflows.interface.route_market_extension", side_effect=AssertionError("crypto news should skip extension routing")),
            patch.dict(interface.VENDOR_METHODS["get_news"], {"alpha_vantage": lambda *args, **kwargs: "UPSTREAM_NEWS"}, clear=True),
            patch("tradingagents.dataflows.interface.get_vendor", return_value="alpha_vantage"),
        ):
            out = route_to_vendor("get_news", "BTCUSDT", "2024-01-01", "2024-01-10")

        self.assertEqual(out, "UPSTREAM_NEWS")


if __name__ == "__main__":
    unittest.main()
