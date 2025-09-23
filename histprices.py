#!/usr/bin/env python3
"""
Historical Price Data Utility

A standalone command-line utility for retrieving and persisting historical price data
using the hypebot data infrastructure.

Usage:
    python histprices.py <symbol> [--period PERIOD] [--interval INTERVAL] [--provider PROVIDER] [--output-dir OUTPUT_DIR]

Examples:
    # Basic usage - get 1 year of daily BTC-USD data
    python histprices.py BTC-USD

    # Get 6 months of hourly ETH data
    python histprices.py ETH-USD --period 6mo --interval 1h

    # Use CoinGecko provider for crypto data
    python histprices.py BTC-USD --provider coingecko --period 2y

    # Custom output directory
    python histprices.py AAPL --output-dir ./my_data --period 1mo --interval 1d
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Add the hypebot package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hypebot'))

from hypebot.config import Config
from hypebot.data import DataClient, DataClientFactory, DataStorage
from hypebot.data.models import OHLCVData
from hypebot.data.client import (
    DataNotFoundError,
    RateLimitError,
    ProviderAuthError,
    ProviderTemporaryError,
    ProviderPermanentError,
    InvalidSymbolError,
    TimeoutError as DataTimeoutError
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistPricesError(Exception):
    """Base exception for histprices utility errors."""
    pass


def validate_period_interval_combination(period: str, interval: str) -> None:
    """Validate that the period and interval combination is reasonable."""
    
    # Period mappings to approximate days
    period_days = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "ytd": 365,  # Approximate
        "max": 3650  # Approximate
    }
    
    # Interval mappings to approximate minutes
    interval_minutes = {
        "1m": 1,
        "2m": 2,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "60m": 60,
        "90m": 90,
        "1h": 60,
        "1d": 1440,
        "5d": 7200,
        "1wk": 10080,
        "1mo": 43200,
        "3mo": 129600
    }
    
    period_days_val = period_days.get(period, 365)
    interval_minutes_val = interval_minutes.get(interval, 1440)
    
    # Calculate approximate number of data points
    total_minutes = period_days_val * 24 * 60
    data_points = total_minutes / interval_minutes_val
    
    # Warn if too many data points (over 10000)
    if data_points > 10000:
        logger.warning(
            f"Warning: Requesting {data_points:.0f} data points. "
            f"This may take a while and could hit rate limits."
        )


def validate_symbol_format(symbol: str) -> None:
    """Validate symbol format."""
    if not symbol or not symbol.strip():
        raise HistPricesError("Symbol cannot be empty")
    
    # Basic validation - should contain alphanumeric characters and common separators
    import re
    if not re.match(r'^[A-Za-z0-9\-\.]+$', symbol.strip()):
        raise HistPricesError(f"Invalid symbol format: {symbol}")


async def retrieve_historical_data(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    provider: str = "yfinance",
    output_dir: Optional[str] = None
) -> bool:
    """
    Retrieve and save historical OHLCV data for the specified symbol.
    
    Args:
        symbol: Trading symbol (e.g., "BTC-USD", "ETH-USD", "AAPL")
        period: Time period for data retrieval
        interval: Data granularity/interval
        provider: Data provider selection ("yfinance" or "coingecko")
        output_dir: Custom output directory (optional)
    
    Returns:
        True if successful, False otherwise
    """
    
    # Validate inputs
    validate_symbol_format(symbol)
    validate_period_interval_combination(period, interval)
    
    logger.info(f"Starting historical data retrieval for {symbol}")
    logger.info(f"Parameters: period={period}, interval={interval}, provider={provider}")
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Override data provider if specified
        if provider != config.data.provider:
            config.data.provider = provider
            logger.info(f"Using provider: {provider}")
        
        # Override output directory if specified
        if output_dir:
            config.database.data_dir = output_dir
            logger.info(f"Using custom output directory: {output_dir}")
        
        # Initialize storage
        storage = DataStorage(config.database)
        
        # Create data client
        async with DataClient(config) as client:
            logger.info("Authenticating with data provider...")
            auth_success = await client.authenticate()
            if not auth_success:
                logger.error("Failed to authenticate with data provider")
                return False
            
            logger.info("Retrieving historical OHLCV data...")
            
            # Get historical OHLCV data
            ohlcv_data = await client.get_historical_ohlcv(
                symbol=symbol,
                period=period,
                interval=interval
            )
            
            if ohlcv_data is None or (hasattr(ohlcv_data, 'empty') and ohlcv_data.empty):
                logger.error(f"No historical data found for symbol: {symbol}")
                return False
            
            # Convert DataFrame to OHLCVData objects if needed
            if hasattr(ohlcv_data, 'iterrows'):
                # It's a DataFrame, convert to OHLCVData objects
                ohlcv_records = []
                for timestamp, row in ohlcv_data.iterrows():
                    # Get source from DataFrame attrs if available
                    source = ohlcv_data.attrs.get('source', provider) if hasattr(ohlcv_data, 'attrs') else provider
                    
                    ohlcv_records.append(OHLCVData(
                        symbol=symbol.upper(),
                        timestamp=timestamp,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume']),
                        source=source
                    ))
                
                ohlcv_data = ohlcv_records
            
            # Save data using storage module
            logger.info(f"Saving {len(ohlcv_data)} records to storage...")
            success = storage.save_ohlcv_data(ohlcv_data, granularity=interval, append=True)
            
            if success:
                logger.info("✅ Data successfully saved!")
                
                # Print summary
                if ohlcv_data:
                    start_date = min(record.timestamp for record in ohlcv_data)
                    end_date = max(record.timestamp for record in ohlcv_data)
                    
                    print(f"\n📊 Data Retrieval Summary:")
                    print(f"   Symbol: {symbol.upper()}")
                    print(f"   Records: {len(ohlcv_data)}")
                    print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                    print(f"   Interval: {interval}")
                    print(f"   Provider: {provider}")
                    print(f"   Storage: {config.database.data_dir}/{config.database.historical_data_dir}/")
                
                return True
            else:
                logger.error("Failed to save data to storage")
                return False
                
    except InvalidSymbolError as e:
        logger.error(f"Invalid symbol: {e}")
        return False
    except DataNotFoundError as e:
        logger.error(f"Data not found: {e}")
        return False
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        return False
    except ProviderAuthError as e:
        logger.error(f"Authentication error: {e}")
        return False
    except ProviderTemporaryError as e:
        logger.error(f"Temporary provider error: {e}")
        return False
    except ProviderPermanentError as e:
        logger.error(f"Permanent provider error: {e}")
        return False
    except DataTimeoutError as e:
        logger.error(f"Timeout error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def main():
    """Main entry point for the histprices utility."""
    
    parser = argparse.ArgumentParser(
        description="Retrieve and persist historical price data using hypebot infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s BTC-USD
  %(prog)s ETH-USD --period 6mo --interval 1h
  %(prog)s BTC-USD --provider coingecko --period 2y
  %(prog)s AAPL --output-dir ./my_data --period 1mo --interval 1d
        """
    )
    
    # Required arguments
    parser.add_argument(
        "symbol",
        help="Trading symbol (e.g., BTC-USD, ETH-USD, AAPL)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--period", "-p",
        default="1y",
        choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
        help="Time period for data retrieval (default: 1y)"
    )
    
    parser.add_argument(
        "--interval", "-i",
        default="1d",
        choices=["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
        help="Data granularity/interval (default: 1d)"
    )
    
    parser.add_argument(
        "--provider", "-pr",
        default="yfinance",
        choices=["yfinance", "coingecko"],
        help="Data provider selection (default: yfinance)"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Custom output directory (default: uses DATA_DIR from config)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('hypebot').setLevel(logging.DEBUG)
    
    # Validate provider availability
    available_providers = DataClientFactory.get_available_providers()
    if args.provider not in available_providers:
        logger.error(f"Provider '{args.provider}' not available. Available providers: {available_providers}")
        sys.exit(1)
    
    # Run the async main function
    try:
        success = asyncio.run(retrieve_historical_data(
            symbol=args.symbol,
            period=args.period,
            interval=args.interval,
            provider=args.provider,
            output_dir=args.output_dir
        ))
        
        if success:
            logger.info("✅ Historical data retrieval completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Historical data retrieval failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
