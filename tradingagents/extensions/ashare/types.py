"""Market and provider type definitions for A-share extension."""

from enum import Enum
from typing import Literal


class Market(Enum):
    """Supported markets."""
    A_SHARE = "a_share"      # China A-shares (SSE/SZSE)
    HK = "hk"                # Hong Kong
    US = "us"                # United States
    UNKNOWN = "unknown"

    def __repr__(self) -> str:
        return f"<Market.{self.name}>"


# Convenience aliases
A_SHARE = Market.A_SHARE
HK = Market.HK
US = Market.US
UNKNOWN = Market.UNKNOWN

MarketLiteral = Literal["a_share", "hk", "us", "unknown"]
TickerNormalized = str  # Fully normalized ticker with exchange suffix if needed
TickerRaw = str  # User-provided raw ticker input