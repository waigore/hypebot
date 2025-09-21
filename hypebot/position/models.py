"""Position models for position management and sizing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Position:
    """Position model for tracking trading positions."""
    
    symbol: str
    side: Literal["LONG", "SHORT"]
    size: float
    entry_price: float
    current_price: float
    pnl: float
    kelly_size: float
    timestamp: datetime
    unrealized_pnl: Optional[float] = None
    realized_pnl: float = 0.0
    
    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.size * self.current_price
    
    @property
    def entry_value(self) -> float:
        """Entry value of the position."""
        return self.size * self.entry_price
    
    @property
    def pnl_percentage(self) -> float:
        """P&L as percentage of entry value."""
        if self.entry_value == 0:
            return 0.0
        return (self.pnl / self.entry_value) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "pnl": self.pnl,
            "kelly_size": self.kelly_size,
            "timestamp": self.timestamp,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl
        }


@dataclass
class PositionSize:
    """Position sizing model using Kelly criterion."""
    
    symbol: str
    timestamp: datetime
    recommended_size: float
    kelly_fraction: float
    max_position_size: float
    current_price: float
    confidence: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    
    @property
    def position_value(self) -> float:
        """Recommended position value in base currency."""
        return self.recommended_size * self.current_price
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "recommended_size": self.recommended_size,
            "kelly_fraction": self.kelly_fraction,
            "max_position_size": self.max_position_size,
            "current_price": self.current_price,
            "confidence": self.confidence,
            "risk_level": self.risk_level
        }
