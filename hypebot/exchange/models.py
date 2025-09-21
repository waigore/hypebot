"""Exchange models for orders, trades, and account data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
from decimal import Decimal


@dataclass
class Order:
    """Order model for trading operations."""
    
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"]
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    order_id: Optional[str] = None
    status: Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"] = "PENDING"
    timestamp: Optional[datetime] = None
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "order_id": self.order_id,
            "status": self.status,
            "timestamp": self.timestamp,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price
        }


@dataclass
class Trade:
    """Trade model for executed trades."""
    
    trade_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: float
    timestamp: datetime
    order_id: str
    commission: float = 0.0
    commission_asset: str = "USDC"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp,
            "order_id": self.order_id,
            "commission": self.commission,
            "commission_asset": self.commission_asset
        }


@dataclass
class AccountBalance:
    """Account balance model."""
    
    asset: str
    free: float
    locked: float
    total: float
    timestamp: datetime
    
    @property
    def available(self) -> float:
        """Available balance (free - locked)."""
        return self.free - self.locked
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "asset": self.asset,
            "free": self.free,
            "locked": self.locked,
            "total": self.total,
            "timestamp": self.timestamp
        }
