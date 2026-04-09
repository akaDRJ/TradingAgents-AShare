"""Tests for additional crypto exchange market-data providers."""

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.binance_futures import BinanceFuturesProvider
from tradingagents.extensions.crypto.providers.gate_futures import GateFuturesProvider
from tradingagents.extensions.crypto.providers.gate_spot import GateSpotProvider


class BinanceFuturesProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.binance_futures.requests.Session.get")
    def test_get_stock_data_formats_futures_klines(self, mock_get):
        exchange_info = Mock()
        exchange_info.raise_for_status.return_value = None
        exchange_info.json.return_value = {"symbols": [{"symbol": "KASUSDT", "status": "TRADING"}]}

        klines = Mock()
        klines.raise_for_status.return_value = None
        klines.json.return_value = [
            [1704067200000, "0.10", "0.12", "0.09", "0.11", "5000", 1704153599999, "0", 0, "0", "0", "0"]
        ]

        mock_get.side_effect = [exchange_info, klines]

        provider = BinanceFuturesProvider()
        result = provider.get_stock_data("KASUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["provider"], "binance_futures")
        self.assertEqual(result["data"][0]["close"], 0.11)
        self.assertEqual(
            mock_get.call_args_list[1].kwargs["params"]["endTime"],
            int(datetime(2024, 1, 2, 23, 59, 59, 999000, tzinfo=UTC).timestamp() * 1000),
        )


class GateSpotProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.gate_spot.requests.Session.get")
    def test_get_stock_data_formats_gate_spot_candles(self, mock_get):
        pair = Mock()
        pair.raise_for_status.return_value = None
        pair.json.return_value = {"id": "KAS_USDT", "trade_status": "tradable"}

        candles = Mock()
        candles.raise_for_status.return_value = None
        candles.json.return_value = [
            ["1704067200", "1000", "0.11", "0.12", "0.09", "0.10", "110", "true"]
        ]

        mock_get.side_effect = [pair, candles]

        provider = GateSpotProvider()
        result = provider.get_stock_data("KASUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["provider"], "gate_spot")
        self.assertEqual(result["data"][0]["open"], 0.10)
        self.assertEqual(mock_get.call_args_list[1].kwargs["params"]["currency_pair"], "KAS_USDT")

    @patch("tradingagents.extensions.crypto.providers.gate_spot.requests.Session.get")
    def test_get_stock_data_chunks_gate_spot_requests_beyond_thousand_days(self, mock_get):
        pair = Mock()
        pair.raise_for_status.return_value = None
        pair.json.return_value = {"id": "BTC_USDT", "trade_status": "tradable"}

        first_chunk = Mock()
        first_chunk.raise_for_status.return_value = None
        first_chunk.json.return_value = [
            ["1609459200", "1000", "29300", "29500", "28800", "29000", "0", "true"]
        ]

        second_chunk = Mock()
        second_chunk.raise_for_status.return_value = None
        second_chunk.json.return_value = [
            ["1695859200", "1000", "27200", "27500", "26800", "27000", "0", "true"]
        ]

        mock_get.side_effect = [pair, first_chunk, second_chunk]

        provider = GateSpotProvider()
        result = provider.get_stock_data("BTCUSDT", "2021-01-01", "2023-12-31")

        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(mock_get.call_count, 3)
        first_params = mock_get.call_args_list[1].kwargs["params"]
        second_params = mock_get.call_args_list[2].kwargs["params"]
        self.assertLess(int(first_params["from"]), int(second_params["from"]))


class GateFuturesProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.gate_futures.requests.Session.get")
    def test_get_stock_data_formats_gate_futures_candles(self, mock_get):
        contract = Mock()
        contract.raise_for_status.return_value = None
        contract.json.return_value = {"name": "KAS_USDT", "status": "trading"}

        candles = Mock()
        candles.raise_for_status.return_value = None
        candles.json.return_value = [
            {"t": 1704067200, "o": "0.10", "h": "0.12", "l": "0.09", "c": "0.11", "v": 5000, "sum": "550"}
        ]

        mock_get.side_effect = [contract, candles]

        provider = GateFuturesProvider()
        result = provider.get_stock_data("KASUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["provider"], "gate_futures")
        self.assertEqual(result["data"][0]["volume"], 5000.0)
        self.assertEqual(mock_get.call_args_list[1].kwargs["params"]["contract"], "KAS_USDT")


if __name__ == "__main__":
    unittest.main()
