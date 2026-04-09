"""Tests for Binance spot crypto provider."""

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.binance_spot import BinanceSpotProvider


class BinanceSpotProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.binance_spot.requests.Session.get")
    def test_get_stock_data_formats_klines_into_extension_shape(self, mock_get):
        exchange_info = Mock()
        exchange_info.raise_for_status.return_value = None
        exchange_info.json.return_value = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}]}

        klines = Mock()
        klines.raise_for_status.return_value = None
        klines.json.return_value = [
            [1704067200000, "42000.0", "42500.0", "41800.0", "42300.0", "100.0", 1704153599999, "0", 0, "0", "0", "0"]
        ]

        mock_get.side_effect = [exchange_info, klines]

        provider = BinanceSpotProvider()
        result = provider.get_stock_data("BTCUSDT", "2024-01-01", "2024-01-02")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(result["provider"], "binance_spot")
        self.assertEqual(result["data"][0]["close"], 42300.0)
        klines_params = mock_get.call_args_list[1].kwargs["params"]
        self.assertEqual(
            klines_params["startTime"],
            int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000),
        )
        self.assertEqual(
            klines_params["endTime"],
            int(datetime(2024, 1, 2, 23, 59, 59, 999000, tzinfo=UTC).timestamp() * 1000),
        )

    @patch("tradingagents.extensions.crypto.providers.binance_spot.requests.Session.get")
    def test_get_stock_data_chunks_windows_that_exceed_single_request_capacity(self, mock_get):
        exchange_info = Mock()
        exchange_info.raise_for_status.return_value = None
        exchange_info.json.return_value = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}]}

        first_chunk = Mock()
        first_chunk.raise_for_status.return_value = None
        first_chunk.json.return_value = [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "100.0", 1609545599999, "0", 0, "0", "0", "0"]
        ]

        second_chunk = Mock()
        second_chunk.raise_for_status.return_value = None
        second_chunk.json.return_value = [
            [1695859200000, "27000.0", "27500.0", "26800.0", "27200.0", "200.0", 1695945599999, "0", 0, "0", "0", "0"]
        ]

        mock_get.side_effect = [exchange_info, first_chunk, second_chunk]

        provider = BinanceSpotProvider()
        result = provider.get_stock_data("BTCUSDT", "2021-01-01", "2023-12-31")

        self.assertEqual(result["ticker"], "BTCUSDT")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(mock_get.call_count, 3)
        first_params = mock_get.call_args_list[1].kwargs["params"]
        second_params = mock_get.call_args_list[2].kwargs["params"]
        self.assertEqual(first_params["limit"], 1000)
        self.assertGreater(second_params["startTime"], first_params["startTime"])


if __name__ == "__main__":
    unittest.main()
