"""CoinGecko API client for price data retrieval."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import httpx
import pandas as pd

from .models import PriceData, MarketData
from ..config import CoinGeckoConfig


logger = logging.getLogger(__name__)


class CoinGeckoClient:
    """Client for interacting with CoinGecko API."""
    
    def __init__(self, config: CoinGeckoConfig):
        """Initialize CoinGecko client."""
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.rate_limit = config.rate_limit
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time = 0.0
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["x-cg-demo-api-key"] = self.api_key
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0
            )
    
    async def _rate_limit_delay(self):
        """Implement rate limiting."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        min_interval = 60.0 / self.rate_limit  # Convert to seconds between requests
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def get_price(self, symbol: str, vs_currency: str = "usd") -> Optional[PriceData]:
        """Get current price for a symbol."""
        try:
            await self._rate_limit_delay()
            await self._ensure_client()
            
            # Map common symbols to CoinGecko IDs
            coin_id = self._map_symbol_to_coin_id(symbol)
            
            url = f"/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": vs_currency,
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if coin_id not in data:
                logger.warning(f"No data found for symbol {symbol} (coin_id: {coin_id})")
                return None
            
            coin_data = data[coin_id]
            price = coin_data.get(f"{vs_currency}", 0.0)
            volume_24h = coin_data.get(f"{vs_currency}_24h_vol", 0.0)
            market_cap = coin_data.get(f"{vs_currency}_market_cap", 0.0)
            
            return PriceData(
                symbol=symbol.upper(),
                timestamp=datetime.utcnow(),
                price=price,
                volume_24h=volume_24h,
                market_cap=market_cap,
                source="coingecko"
            )
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    async def get_market_data(self, symbol: str, vs_currency: str = "usd") -> Optional[MarketData]:
        """Get comprehensive market data for a symbol."""
        try:
            await self._rate_limit_delay()
            await self._ensure_client()
            
            coin_id = self._map_symbol_to_coin_id(symbol)
            
            url = f"/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            }
            
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            market_data = data.get("market_data", {})
            
            price = market_data.get("current_price", {}).get(vs_currency, 0.0)
            volume_24h = market_data.get("total_volume", {}).get(vs_currency, 0.0)
            market_cap = market_data.get("market_cap", {}).get(vs_currency, 0.0)
            price_change_24h = market_data.get("price_change_24h", 0.0)
            price_change_percentage_24h = market_data.get("price_change_percentage_24h", 0.0)
            high_24h = market_data.get("high_24h", {}).get(vs_currency, 0.0)
            low_24h = market_data.get("low_24h", {}).get(vs_currency, 0.0)
            
            return MarketData(
                symbol=symbol.upper(),
                timestamp=datetime.utcnow(),
                price=price,
                volume_24h=volume_24h,
                market_cap=market_cap,
                price_change_24h=price_change_24h,
                price_change_percentage_24h=price_change_percentage_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                source="coingecko"
            )
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    async def get_historical_prices(
        self, 
        symbol: str, 
        days: int = 30, 
        vs_currency: str = "usd"
    ) -> List[PriceData]:
        """Get historical price data for a symbol."""
        try:
            await self._rate_limit_delay()
            await self._ensure_client()
            
            coin_id = self._map_symbol_to_coin_id(symbol)
            
            url = f"/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": vs_currency,
                "days": days,
                "interval": "daily" if days > 90 else "hourly"
            }
            
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])
            market_caps = data.get("market_caps", [])
            
            price_data = []
            for i, (timestamp_ms, price) in enumerate(prices):
                volume_24h = volumes[i][1] if i < len(volumes) else 0.0
                market_cap = market_caps[i][1] if i < len(market_caps) else 0.0
                
                price_data.append(PriceData(
                    symbol=symbol.upper(),
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                    price=price,
                    volume_24h=volume_24h,
                    market_cap=market_cap,
                    source="coingecko"
                ))
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {e}")
            return []
    
    def _map_symbol_to_coin_id(self, symbol: str) -> str:
        """Map trading symbol to CoinGecko coin ID."""
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "ADA": "cardano",
            "SOL": "solana",
            "DOT": "polkadot",
            "DOGE": "dogecoin",
            "AVAX": "avalanche-2",
            "MATIC": "matic-network",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "LTC": "litecoin",
            "ATOM": "cosmos",
            "XRP": "ripple",
            "BCH": "bitcoin-cash",
            "ALGO": "algorand",
            "VET": "vechain",
            "FIL": "filecoin",
            "TRX": "tron",
            "XLM": "stellar"
        }
        
        return symbol_map.get(symbol.upper(), symbol.lower())
