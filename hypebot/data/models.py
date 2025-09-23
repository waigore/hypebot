"""Data models for price and market data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class PriceData:
    """Price data model for storing cryptocurrency price information."""
    
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    market_cap: float
    source: str = "provider"
    
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
            source=data.get("source", "provider")
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
    source: str = "provider"
    
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
            source=data.get("source", "provider")
        )


@dataclass
class OHLCVData:
    """OHLCV (Open, High, Low, Close, Volume) data model for historical price information."""
    
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str = "provider"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHLCVData":
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=data["timestamp"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"],
            source=data.get("source", "provider")
        )
    
    @classmethod
    def from_dataframe_row(cls, row: Dict[str, Any], symbol: str, source: str = "provider") -> "OHLCVData":
        """Create OHLCV data from a pandas DataFrame row."""
        return cls(
            symbol=symbol,
            timestamp=row["timestamp"] if isinstance(row["timestamp"], datetime) else datetime.fromisoformat(str(row["timestamp"])),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            source=source
        )
    
    def to_standardized_dataframe(self) -> pd.DataFrame:
        """Convert to standardized DataFrame format with UTC index."""
        
        df = pd.DataFrame([{
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }], index=[self.timestamp])
        
        # Ensure UTC timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        # Add metadata
        df.attrs = {
            "symbol": self.symbol,
            "source": self.source,
            "data_type": "ohlcv"
        }
        
        return df
    
    @classmethod
    def create_standardized_dataframe(cls, ohlcv_data: list["OHLCVData"]) -> pd.DataFrame:
        """Create standardized DataFrame from list of OHLCV data."""
        
        if not ohlcv_data:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        
        # Create DataFrame with timestamp as index
        data = []
        timestamps = []
        symbol = ohlcv_data[0].symbol
        source = ohlcv_data[0].source
        
        for item in ohlcv_data:
            data.append({
                "open": item.open,
                "high": item.high,
                "low": item.low,
                "close": item.close,
                "volume": item.volume
            })
            timestamps.append(item.timestamp)
        
        df = pd.DataFrame(data, index=timestamps)
        
        # Ensure UTC timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        # Sort by timestamp
        df = df.sort_index()
        
        # Add metadata
        df.attrs = {
            "symbol": symbol,
            "source": source,
            "data_type": "ohlcv",
            "total_records": len(ohlcv_data)
        }
        
        return df
