from __future__ import annotations

from typing import Dict, Iterable, Optional

from .types import ExtensionRegistration


_EXTENSIONS: Dict[str, ExtensionRegistration] = {}


def register_extension(
    name: str,
    match_ticker,
    detect_market,
    route_extension,
) -> None:
    _EXTENSIONS[name] = ExtensionRegistration(
        name=name,
        match_ticker=match_ticker,
        detect_market=detect_market,
        route_extension=route_extension,
    )


def get_extension(name: str) -> Optional[ExtensionRegistration]:
    return _EXTENSIONS.get(name)


def list_extensions() -> Iterable[ExtensionRegistration]:
    return _EXTENSIONS.values()


def reset_extensions_for_test() -> None:
    _EXTENSIONS.clear()
