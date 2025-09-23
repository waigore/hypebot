"""Provider-agnostic data client interface and factory."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import pandas as pd

from .models import PriceData, MarketData, OHLCVData
from .coingecko_client import CoinGeckoClient
from .yfinance_client import YahooFinanceClient
from ..config import Config, CoinGeckoConfig, YahooFinanceConfig


logger = logging.getLogger(__name__)


class DataClientError(Exception):
    """Base exception for data client errors."""
    pass


class DataNotFoundError(DataClientError):
    """Data not found error."""
    pass


class RateLimitError(DataClientError):
    """Rate limit exceeded error."""
    pass


class ProviderAuthError(DataClientError):
    """Provider authentication error."""
    pass


class ProviderTemporaryError(DataClientError):
    """Temporary provider error."""
    pass


class ProviderPermanentError(DataClientError):
    """Permanent provider error."""
    pass


class InvalidSymbolError(DataClientError):
    """Invalid symbol error."""
    pass


class TimeoutError(DataClientError):
    """Timeout error."""
    pass


class DataClientInterface(ABC):
    """Abstract base class for data clients."""
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the data provider."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the client connection."""
        pass
    
    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols."""
        pass
    
    @abstractmethod
    async def get_spot_price(self, symbol: str) -> Optional[PriceData]:
        """Get current spot price for a symbol."""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get comprehensive market data for a symbol."""
        pass
    
    @abstractmethod
    async def get_historical_prices(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> List[PriceData]:
        """Get historical price data for a symbol."""
        pass
    
    @abstractmethod
    async def get_historical_ohlcv(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data with standardized DataFrame shape and UTC timestamps."""
        pass


class DataClientFactory:
    """Factory for creating data clients."""
    
    @staticmethod
    def create_client(config: Config) -> DataClientInterface:
        """Create a data client based on configuration."""
        provider = config.data.provider.lower()
        
        if provider == "yfinance":
            return YahooFinanceClient(config.yahoo_finance)
        elif provider == "coingecko":
            return CoinGeckoClient(config.coingecko)
        else:
            raise ValueError(f"Unsupported data provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available data providers."""
        return ["yfinance", "coingecko"]


class DataClient:
    """Provider-agnostic data client wrapper."""
    
    def __init__(self, config: Config):
        """Initialize data client."""
        self.config = config
        self._client: Optional[DataClientInterface] = None
        self._provider = config.data.provider.lower()
        
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = DataClientFactory.create_client(self.config)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def authenticate(self) -> bool:
        """Authenticate with the data provider."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.authenticate()
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
    
    async def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.get_supported_symbols()
    
    async def get_spot_price(self, symbol: str) -> Optional[PriceData]:
        """Get current spot price for a symbol."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            return await self._client.get_spot_price(symbol)
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {e}")
            raise ProviderTemporaryError(f"Failed to get spot price: {e}")
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get comprehensive market data for a symbol."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            return await self._client.get_market_data(symbol)
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            raise ProviderTemporaryError(f"Failed to get market data: {e}")
    
    async def get_historical_prices(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> List[PriceData]:
        """Get historical price data for a symbol."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            return await self._client.get_historical_prices(symbol, period, interval)
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            raise ProviderTemporaryError(f"Failed to get historical prices: {e}")
    
    async def get_historical_ohlcv(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data with standardized DataFrame shape and UTC timestamps."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            return await self._client.get_historical_ohlcv(symbol, period, interval)
        except Exception as e:
            logger.error(f"Error getting historical OHLCV for {symbol}: {e}")
            raise ProviderTemporaryError(f"Failed to get historical OHLCV: {e}")
    
    @property
    def provider(self) -> str:
        """Get current provider name."""
        return self._provider
    
    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._client is not None

