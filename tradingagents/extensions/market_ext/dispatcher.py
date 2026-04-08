from __future__ import annotations

from typing import Any, Optional

from .registry import list_extensions
from .types import ExtensionRegistration, Market


def resolve_extension(ticker: str) -> Optional[ExtensionRegistration]:
    if not ticker:
        return None

    raw = str(ticker).strip()
    if not raw:
        return None

    for extension in list_extensions():
        if extension.match_ticker(raw):
            return extension
    return None


def detect_market_for_ticker(ticker: str) -> Market:
    extension = resolve_extension(ticker)
    if extension is None:
        return Market.UNKNOWN
    return extension.detect_market(ticker)


def route_market_extension(method: str, *args, **kwargs) -> Any | None:
    ticker = None
    if args:
        ticker = str(args[0])
    else:
        ticker = kwargs.get("ticker") or kwargs.get("symbol")

    extension = resolve_extension(ticker or "")
    if extension is None:
        return None

    return extension.route_extension(method, *args, **kwargs)
