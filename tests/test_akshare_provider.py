"""Focused tests for AKShare provider fallback behavior."""

import unittest
from unittest.mock import patch

from tradingagents.extensions.ashare.providers.akshare import AKShareProvider


class _FakeFrame:
    def __init__(self, records):
        self._records = records
        self.empty = len(records) == 0

    def rename(self, columns=None):
        return self

    def to_dict(self, orient):
        return self._records


class AKShareProviderTests(unittest.TestCase):
    @patch.object(AKShareProvider, "_check_available", return_value=True)
    def test_falls_back_to_sina_when_eastmoney_fails(self, _available):
        provider = AKShareProvider()

        with patch("akshare.stock_zh_a_hist", side_effect=RuntimeError("em down")), \
             patch("akshare.stock_zh_a_daily", return_value=_FakeFrame([{"date": "2024-01-02", "close": 1.0}])), \
             patch("akshare.stock_zh_a_hist_tx") as tx:
            result = provider.get_stock_data("600519.SS", "2024-01-01", "2024-01-10")

        self.assertEqual(result["provider"], "akshare")
        self.assertEqual(result["source"], "sina")
        self.assertEqual(result["ticker"], "600519.SS")
        self.assertEqual(len(result["data"]), 1)
        tx.assert_not_called()


if __name__ == "__main__":
    unittest.main()
