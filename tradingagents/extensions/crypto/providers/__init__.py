from tradingagents.extensions.crypto.registry import register_provider

from .base import ProviderError
from .binance_futures import BinanceFuturesProvider
from .binance_spot import BinanceSpotProvider
from .coingecko import CoinGeckoProvider
from .gate_futures import GateFuturesProvider
from .gate_spot import GateSpotProvider
from .public_news import PublicNewsProvider

__all__ = [
    "ProviderError",
    "BinanceFuturesProvider",
    "BinanceSpotProvider",
    "CoinGeckoProvider",
    "GateFuturesProvider",
    "GateSpotProvider",
    "PublicNewsProvider",
]


def _register_providers() -> None:
    binance = BinanceSpotProvider()
    binance_futures = BinanceFuturesProvider()
    coingecko = CoinGeckoProvider()
    gate_spot = GateSpotProvider()
    gate_futures = GateFuturesProvider()
    public_news = PublicNewsProvider()

    register_provider("binance_spot", "get_stock_data", binance.get_stock_data)
    register_provider("binance_futures", "get_stock_data", binance_futures.get_stock_data)
    register_provider("gate_spot", "get_stock_data", gate_spot.get_stock_data)
    register_provider("gate_futures", "get_stock_data", gate_futures.get_stock_data)
    register_provider("coingecko", "get_stock_data", coingecko.get_stock_data)
    register_provider("coingecko", "get_fundamentals", coingecko.get_fundamentals)
    register_provider("public_news", "get_news", public_news.get_news)
    register_provider("public_news", "get_global_news", public_news.get_global_news)


_register_providers()
