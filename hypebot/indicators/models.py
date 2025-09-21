"""Indicator models for technical analysis signals."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class TradingSignal:
    """Trading signal model for buy/sell/hold signals."""
    
    symbol: str
    timestamp: datetime
    signal_type: Literal["BUY", "SELL", "HOLD"]
    strength: float  # 0-1 confidence level
    rsi_value: float
    indicator: str = "RSI"
    price: Optional[float] = None
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "rsi_value": self.rsi_value,
            "indicator": self.indicator,
            "price": self.price,
            "metadata": self.metadata or {}
        }


@dataclass
class IndicatorResult:
    """Generic indicator result model."""
    
    symbol: str
    timestamp: datetime
    indicator_name: str
    value: float
    signal: Optional[Literal["BUY", "SELL", "HOLD"]] = None
    strength: Optional[float] = None
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "indicator_name": self.indicator_name,
            "value": self.value,
            "signal": self.signal,
            "strength": self.strength,
            "metadata": self.metadata or {}
        }
