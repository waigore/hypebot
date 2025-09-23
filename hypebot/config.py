"""Configuration management for HypeBot."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class HyperliquidConfig:
    """Hyperliquid exchange configuration."""
    
    api_key: str
    secret_key: str
    testnet: bool = True
    base_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "HyperliquidConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("HYPERLIQUID_API_KEY", ""),
            secret_key=os.getenv("HYPERLIQUID_SECRET_KEY", ""),
            testnet=os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true",
            base_url=os.getenv("HYPERLIQUID_BASE_URL")
        )


@dataclass
class CoinGeckoConfig:
    """CoinGecko API configuration."""
    
    api_key: Optional[str] = None
    base_url: str = "https://api.coingecko.com/api/v3"
    rate_limit: int = 50  # requests per minute
    
    @classmethod
    def from_env(cls) -> "CoinGeckoConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("COINGECKO_API_KEY"),
            base_url=os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3"),
            rate_limit=int(os.getenv("COINGECKO_RATE_LIMIT", "50"))
        )


@dataclass
class YahooFinanceConfig:
    """Yahoo Finance API configuration."""
    
    rate_limit_rps: int = 5  # requests per second
    max_retries: int = 3
    timeout_s: int = 30
    
    @classmethod
    def from_env(cls) -> "YahooFinanceConfig":
        """Create config from environment variables."""
        return cls(
            rate_limit_rps=int(os.getenv("YF_RATE_LIMIT_RPS", "5")),
            max_retries=int(os.getenv("YF_MAX_RETRIES", "3")),
            timeout_s=int(os.getenv("YF_TIMEOUT_S", "30"))
        )


@dataclass
class DataConfig:
    """Data provider configuration."""
    
    provider: str = "yfinance"  # Default to yfinance as per spec
    cache_ttl_s: int = 0
    default_interval: str = "1d"
    default_lookback_days: int = 365
    
    @classmethod
    def from_env(cls) -> "DataConfig":
        """Create config from environment variables."""
        return cls(
            provider=os.getenv("DATA_PROVIDER", "yfinance"),
            cache_ttl_s=int(os.getenv("DATA_CACHE_TTL_S", "0")),
            default_interval=os.getenv("DATA_DEFAULT_INTERVAL", "1d"),
            default_lookback_days=int(os.getenv("DATA_DEFAULT_LOOKBACK_DAYS", "365"))
        )


@dataclass
class TradingConfig:
    """Trading configuration."""
    
    default_symbol: str = "BTC"
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    kelly_lookback_period: int = 30
    max_position_size: float = 0.1
    min_position_size: float = 0.001
    risk_free_rate: float = 0.02  # 2% annual risk-free rate
    
    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Create config from environment variables."""
        return cls(
            default_symbol=os.getenv("DEFAULT_SYMBOL", "BTC"),
            rsi_period=int(os.getenv("RSI_PERIOD", "14")),
            rsi_oversold=float(os.getenv("RSI_OVERSOLD", "30")),
            rsi_overbought=float(os.getenv("RSI_OVERBOUGHT", "70")),
            kelly_lookback_period=int(os.getenv("KELLY_LOOKBACK_PERIOD", "30")),
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", "0.1")),
            min_position_size=float(os.getenv("MIN_POSITION_SIZE", "0.001")),
            risk_free_rate=float(os.getenv("RISK_FREE_RATE", "0.02"))
        )


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    data_dir: str = "data"
    price_data_file: str = "price_data.csv"
    positions_file: str = "positions.csv"
    trades_file: str = "trades.csv"
    signals_file: str = "signals.csv"
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables."""
        return cls(
            data_dir=os.getenv("DATA_DIR", "data"),
            price_data_file=os.getenv("PRICE_DATA_FILE", "price_data.csv"),
            positions_file=os.getenv("POSITIONS_FILE", "positions.csv"),
            trades_file=os.getenv("TRADES_FILE", "trades.csv"),
            signals_file=os.getenv("SIGNALS_FILE", "signals.csv")
        )


@dataclass
class Config:
    """Main configuration class."""
    
    hyperliquid: HyperliquidConfig
    coingecko: CoinGeckoConfig
    yahoo_finance: YahooFinanceConfig
    data: DataConfig
    trading: TradingConfig
    database: DatabaseConfig
    log_level: str = "INFO"
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            hyperliquid=HyperliquidConfig.from_env(),
            coingecko=CoinGeckoConfig.from_env(),
            yahoo_finance=YahooFinanceConfig.from_env(),
            data=DataConfig.from_env(),
            trading=TradingConfig.from_env(),
            database=DatabaseConfig.from_env(),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.hyperliquid.api_key or not self.hyperliquid.secret_key:
            raise ValueError("Hyperliquid API credentials are required")
        
        if not self.trading.default_symbol:
            raise ValueError("Default symbol is required")
        
        return True
