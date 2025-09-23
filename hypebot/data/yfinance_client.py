"""Yahoo Finance API client for price data retrieval."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import yfinance as yf
import pandas as pd

from .models import PriceData, MarketData, OHLCVData
from ..config import YahooFinanceConfig


logger = logging.getLogger(__name__)


class YahooFinanceClient:
    """Client for interacting with Yahoo Finance API via yfinance."""
    
    def __init__(self, config: YahooFinanceConfig):
        """Initialize Yahoo Finance client."""
        self.config = config
        self._last_request_time = 0.0
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    async def _rate_limit_delay(self):
        """Implement rate limiting."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        min_interval = 1.0 / self.config.rate_limit_rps  # Convert to seconds between requests
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, func, *args, **kwargs)
    
    async def authenticate(self) -> bool:
        """Authenticate with Yahoo Finance (no auth required)."""
        return True
    
    async def close(self):
        """Close client (no cleanup needed)."""
        pass
    
    async def get_supported_symbols(self) -> List[str]:
        """Get list of supported cryptocurrency symbols."""
        # Common crypto symbols supported by Yahoo Finance
        return [
            "BTC-USD", "ETH-USD", "BNB-USD", "ADA-USD", "SOL-USD",
            "DOT-USD", "DOGE-USD", "AVAX-USD", "MATIC-USD", "LINK-USD",
            "UNI-USD", "LTC-USD", "ATOM-USD", "XRP-USD", "BCH-USD",
            "ALGO-USD", "VET-USD", "FIL-USD", "TRX-USD", "XLM-USD"
        ]
    
    async def get_spot_price(self, symbol: str) -> Optional[PriceData]:
        """Get current spot price for a symbol."""
        try:
            await self._rate_limit_delay()
            
            # Convert symbol to Yahoo Finance format if needed
            yf_symbol = self._map_symbol_to_yf_format(symbol)
            
            def _get_price():
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                return PriceData(
                    symbol=symbol.upper(),
                    timestamp=datetime.utcnow(),
                    price=info.get('currentPrice', 0.0) or info.get('regularMarketPrice', 0.0),
                    volume_24h=info.get('volume24Hr', 0.0) or info.get('volume', 0.0),
                    market_cap=info.get('marketCap', 0.0),
                    source="yfinance"
                )
            
            return await self._run_in_thread(_get_price)
            
        except Exception as e:
            logger.error(f"Error fetching spot price for {symbol}: {e}")
            return None
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get comprehensive market data for a symbol."""
        try:
            await self._rate_limit_delay()
            
            yf_symbol = self._map_symbol_to_yf_format(symbol)
            
            def _get_market_data():
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                current_price = info.get('currentPrice', 0.0) or info.get('regularMarketPrice', 0.0)
                prev_close = info.get('previousClose', current_price)
                price_change_24h = current_price - prev_close
                price_change_percentage_24h = (price_change_24h / prev_close * 100) if prev_close else 0.0
                
                return MarketData(
                    symbol=symbol.upper(),
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    volume_24h=info.get('volume24Hr', 0.0) or info.get('volume', 0.0),
                    market_cap=info.get('marketCap', 0.0),
                    price_change_24h=price_change_24h,
                    price_change_percentage_24h=price_change_percentage_24h,
                    high_24h=info.get('dayHigh', current_price),
                    low_24h=info.get('dayLow', current_price),
                    source="yfinance"
                )
            
            return await self._run_in_thread(_get_market_data)
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    async def get_historical_prices(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> List[PriceData]:
        """Get historical price data for a symbol."""
        try:
            await self._rate_limit_delay()
            
            yf_symbol = self._map_symbol_to_yf_format(symbol)
            
            def _get_historical():
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period, interval=interval)
                
                price_data = []
                for timestamp, row in hist.iterrows():
                    price_data.append(PriceData(
                        symbol=symbol.upper(),
                        timestamp=timestamp.to_pydatetime(),
                        price=float(row['Close']),
                        volume_24h=float(row['Volume']),
                        market_cap=0.0,  # Not available in historical data
                        source="yfinance"
                    ))
                
                return price_data
            
            return await self._run_in_thread(_get_historical)
            
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {e}")
            return []
    
    async def get_historical_ohlcv(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data with standardized DataFrame shape and UTC timestamps."""
        try:
            await self._rate_limit_delay()
            
            yf_symbol = self._map_symbol_to_yf_format(symbol)
            
            def _get_ohlcv():
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period, interval=interval)
                
                if hist.empty:
                    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
                
                # Select only OHLCV columns
                ohlcv_df = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                ohlcv_df.columns = ['open', 'high', 'low', 'close', 'volume']
                
                # Ensure UTC timezone
                if ohlcv_df.index.tz is None:
                    ohlcv_df.index = ohlcv_df.index.tz_localize('UTC')
                else:
                    ohlcv_df.index = ohlcv_df.index.tz_convert('UTC')
                
                # Sort by timestamp
                ohlcv_df = ohlcv_df.sort_index()
                
                # Add metadata
                ohlcv_df.attrs = {
                    "symbol": symbol.upper(),
                    "source": "yfinance",
                    "data_type": "ohlcv",
                    "total_records": len(ohlcv_df),
                    "start_date": ohlcv_df.index.min() if not ohlcv_df.empty else None,
                    "end_date": ohlcv_df.index.max() if not ohlcv_df.empty else None
                }
                
                return ohlcv_df
            
            return await self._run_in_thread(_get_ohlcv)
            
        except Exception as e:
            logger.error(f"Error fetching historical OHLCV for {symbol}: {e}")
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    
    def _map_symbol_to_yf_format(self, symbol: str) -> str:
        """Map trading symbol to Yahoo Finance format."""
        symbol_map = {
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "BNB": "BNB-USD",
            "ADA": "ADA-USD",
            "SOL": "SOL-USD",
            "DOT": "DOT-USD",
            "DOGE": "DOGE-USD",
            "AVAX": "AVAX-USD",
            "MATIC": "MATIC-USD",
            "LINK": "LINK-USD",
            "UNI": "UNI-USD",
            "LTC": "LTC-USD",
            "ATOM": "ATOM-USD",
            "XRP": "XRP-USD",
            "BCH": "BCH-USD",
            "ALGO": "ALGO-USD",
            "VET": "VET-USD",
            "FIL": "FIL-USD",
            "TRX": "TRX-USD",
            "XLM": "XLM-USD"
        }
        
        # If symbol already has -USD suffix, return as is
        if symbol.endswith('-USD'):
            return symbol.upper()
        
        # Map common symbols
        return symbol_map.get(symbol.upper(), f"{symbol.upper()}-USD")

