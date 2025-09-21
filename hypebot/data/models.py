"""Data models for price and market data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PriceData:
    """Price data model for storing cryptocurrency price information."""
    
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    market_cap: float
    source: str = "coingecko"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "price": self.price,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PriceData":
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=data["timestamp"],
            price=data["price"],
            volume_24h=data["volume_24h"],
            market_cap=data["market_cap"],
            source=data.get("source", "coingecko")
        )


@dataclass
class MarketData:
    """Market data model for storing comprehensive market information."""
    
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    market_cap: float
    price_change_24h: float
    price_change_percentage_24h: float
    high_24h: float
    low_24h: float
    source: str = "coingecko"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "price": self.price,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "price_change_24h": self.price_change_24h,
            "price_change_percentage_24h": self.price_change_percentage_24h,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MarketData":
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=data["timestamp"],
            price=data["price"],
            volume_24h=data["volume_24h"],
            market_cap=data["market_cap"],
            price_change_24h=data["price_change_24h"],
            price_change_percentage_24h=data["price_change_percentage_24h"],
            high_24h=data["high_24h"],
            low_24h=data["low_24h"],
            source=data.get("source", "coingecko")
        )
