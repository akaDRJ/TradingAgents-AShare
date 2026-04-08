"""Tests for crypto public news provider date-window filtering."""

import unittest
from unittest.mock import Mock, patch

from tradingagents.extensions.crypto.providers.public_news import PublicNewsProvider


class PublicNewsProviderTests(unittest.TestCase):
    @patch("tradingagents.extensions.crypto.providers.public_news.requests.get")
    def test_get_news_filters_items_to_requested_date_window(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = b"""
<rss><channel>
<item><title>Too Early</title><link>https://example.com/early</link><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>In Window</title><link>https://example.com/in-window</link><pubDate>Fri, 05 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>Too Late</title><link>https://example.com/late</link><pubDate>Thu, 01 Feb 2024 10:00:00 GMT</pubDate></item>
</channel></rss>
"""
        mock_get.return_value = response

        provider = PublicNewsProvider()
        out = provider.get_news("BTCUSDT", "2024-01-03", "2024-01-31")

        self.assertIn("In Window", out)
        self.assertNotIn("Too Early", out)
        self.assertNotIn("Too Late", out)

    @patch("tradingagents.extensions.crypto.providers.public_news.requests.get")
    def test_get_global_news_filters_items_to_look_back_window(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = b"""
<rss><channel>
<item><title>Before Window</title><link>https://example.com/before</link><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>Inside Window</title><link>https://example.com/inside</link><pubDate>Tue, 09 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>Future Leak</title><link>https://example.com/future</link><pubDate>Fri, 12 Jan 2024 10:00:00 GMT</pubDate></item>
</channel></rss>
"""
        mock_get.return_value = response

        provider = PublicNewsProvider()
        out = provider.get_global_news("2024-01-10", look_back_days=3, limit=5)

        self.assertIn("Inside Window", out)
        self.assertNotIn("Before Window", out)
        self.assertNotIn("Future Leak", out)


if __name__ == "__main__":
    unittest.main()
