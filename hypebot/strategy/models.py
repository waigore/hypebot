"""Strategy-specific models and enums."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime


@dataclass
class StrategyOrder:
    """Order intent produced by StrategyRunner from a TradingSignal."""

    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: float
    price: Optional[float]
    timestamp: datetime


