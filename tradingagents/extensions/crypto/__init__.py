from tradingagents.extensions.market_ext import get_extension, register_extension

from . import providers  # noqa: F401
from .normalize import detect_market, normalize_ticker
from .policy import DEFERRED_UPSTREAM_METHODS, get_provider_chain, get_unsupported_message, is_method_supported
from .registry import get_registry, register_provider
from .routing import route_extension

__all__ = [
    "detect_market",
    "normalize_ticker",
    "get_provider_chain",
    "get_unsupported_message",
    "is_method_supported",
    "get_registry",
    "register_provider",
    "route_extension",
    "ensure_registered",
    "providers",
]


def ensure_registered() -> None:
    if get_extension("crypto") is not None:
        return

    register_extension(
        name="crypto",
        match_ticker=lambda ticker: detect_market(ticker).value == "crypto",
        detect_market=detect_market,
        supports_method=lambda method: method not in DEFERRED_UPSTREAM_METHODS,
        route_extension=route_extension,
    )


ensure_registered()
