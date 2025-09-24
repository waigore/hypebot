"""Data storage using Pandas for local persistence."""

import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from .models import PriceData, MarketData, OHLCVData
from ..config import DatabaseConfig


logger = logging.getLogger(__name__)


class DataStorage:
    """Local data storage using Pandas DataFrames."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize data storage."""
        self.config = config
        self.data_dir = config.data_dir
        self._ensure_data_directory()
        # Historical OHLCV directory
        self.historical_dir = os.path.join(self.data_dir, getattr(self.config, "historical_data_dir", "historical"))
        os.makedirs(self.historical_dir, exist_ok=True)
    
    def _ensure_data_directory(self):
        """Ensure data directory exists."""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_file_path(self, filename: str) -> str:
        """Get full file path for a data file."""
        return os.path.join(self.data_dir, filename)
    
    def save_price_data(self, price_data: List[PriceData], append: bool = True) -> bool:
        """Save price data to CSV file."""
        try:
            if not price_data:
                return True
            
            # Convert to DataFrame
            df = pd.DataFrame([data.to_dict() for data in price_data])
            
            file_path = self._get_file_path(self.config.price_data_file)
            
            if append and os.path.exists(file_path):
                # Load existing data and append
                existing_df = pd.read_csv(file_path)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                # Remove duplicates based on symbol and timestamp
                combined_df = combined_df.drop_duplicates(subset=['symbol', 'timestamp'], keep='last')
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            logger.info(f"Saved {len(price_data)} price data records")
            return True
            
        except Exception as e:
            logger.error(f"Error saving price data: {e}")
            return False
    
    def load_price_data(
        self, 
        symbol: Optional[str] = None, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load price data from CSV file."""
        try:
            file_path = self._get_file_path(self.config.price_data_file)
            
            if not os.path.exists(file_path):
                logger.warning(f"Price data file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by symbol if provided
            if symbol:
                df = df[df['symbol'] == symbol.upper()]
            
            # Filter by date range if provided
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            logger.info(f"Loaded {len(df)} price data records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading price data: {e}")
            return pd.DataFrame()
    
    def save_market_data(self, market_data: List[MarketData], append: bool = True) -> bool:
        """Save market data to CSV file."""
        try:
            if not market_data:
                return True
            
            # Convert to DataFrame
            df = pd.DataFrame([data.to_dict() for data in market_data])
            
            file_path = self._get_file_path("market_data.csv")
            
            if append and os.path.exists(file_path):
                # Load existing data and append
                existing_df = pd.read_csv(file_path)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                # Remove duplicates based on symbol and timestamp
                combined_df = combined_df.drop_duplicates(subset=['symbol', 'timestamp'], keep='last')
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            logger.info(f"Saved {len(market_data)} market data records")
            return True
            
        except Exception as e:
            logger.error(f"Error saving market data: {e}")
            return False
    
    def load_market_data(
        self, 
        symbol: Optional[str] = None, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load market data from CSV file."""
        try:
            file_path = self._get_file_path("market_data.csv")
            
            if not os.path.exists(file_path):
                logger.warning(f"Market data file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by symbol if provided
            if symbol:
                df = df[df['symbol'] == symbol.upper()]
            
            # Filter by date range if provided
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            logger.info(f"Loaded {len(df)} market data records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            return pd.DataFrame()
    
    def save_positions(self, positions: List[Dict[str, Any]], append: bool = True) -> bool:
        """Save positions to CSV file."""
        try:
            if not positions:
                return True
            
            df = pd.DataFrame(positions)
            file_path = self._get_file_path(self.config.positions_file)
            
            if append and os.path.exists(file_path):
                existing_df = pd.read_csv(file_path)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            logger.info(f"Saved {len(positions)} position records")
            return True
            
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
            return False
    
    def load_positions(self) -> pd.DataFrame:
        """Load positions from CSV file."""
        try:
            file_path = self._get_file_path(self.config.positions_file)
            
            if not os.path.exists(file_path):
                logger.warning(f"Positions file not found: {file_path}")
                return pd.DataFrame()
            
            # Check if file is empty or only contains whitespace
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    logger.info("Positions file is empty")
                    return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            
            # Check if DataFrame is empty after reading
            if df.empty:
                logger.info("No position records found in file")
                return pd.DataFrame()
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"Loaded {len(df)} position records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            return pd.DataFrame()
    
    def save_trades(self, trades: List[Dict[str, Any]], append: bool = True) -> bool:
        """Save trades to CSV file."""
        try:
            if not trades:
                return True
            
            df = pd.DataFrame(trades)
            file_path = self._get_file_path(self.config.trades_file)
            
            if append and os.path.exists(file_path):
                existing_df = pd.read_csv(file_path)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            logger.info(f"Saved {len(trades)} trade records")
            return True
            
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
            return False
    
    def load_trades(self) -> pd.DataFrame:
        """Load trades from CSV file."""
        try:
            file_path = self._get_file_path(self.config.trades_file)
            
            if not os.path.exists(file_path):
                logger.warning(f"Trades file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"Loaded {len(df)} trade records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            return pd.DataFrame()
    
    def save_signals(self, signals: List[Dict[str, Any]], append: bool = True) -> bool:
        """Save trading signals to CSV file."""
        try:
            if not signals:
                return True
            
            df = pd.DataFrame(signals)
            file_path = self._get_file_path(self.config.signals_file)
            
            if append and os.path.exists(file_path):
                existing_df = pd.read_csv(file_path)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            logger.info(f"Saved {len(signals)} signal records")
            return True
            
        except Exception as e:
            logger.error(f"Error saving signals: {e}")
            return False
    
    def load_signals(self) -> pd.DataFrame:
        """Load trading signals from CSV file."""
        try:
            file_path = self._get_file_path(self.config.signals_file)
            
            if not os.path.exists(file_path):
                logger.warning(f"Signals file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            logger.info(f"Loaded {len(df)} signal records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading signals: {e}")
            return pd.DataFrame()
    
    def get_latest_price(self, symbol: str) -> Optional[PriceData]:
        """Get the latest price for a symbol."""
        try:
            df = self.load_price_data(symbol=symbol)
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            return PriceData(
                symbol=latest['symbol'],
                timestamp=latest['timestamp'],
                price=latest['price'],
                volume_24h=latest['volume_24h'],
                market_cap=latest['market_cap'],
                source=latest.get('source', 'provider')
            )
            
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def _historical_filename(self, symbol: str, year: int, granularity: str) -> str:
        symbol_upper = symbol.upper()
        return f"{symbol_upper}_{year}_{granularity}.csv"

    def _historical_filepath(self, symbol: str, year: int, granularity: str) -> str:
        return os.path.join(self.historical_dir, self._historical_filename(symbol, year, granularity))

    def _normalize_timestamp_series_utc(self, ts: pd.Series) -> pd.Series:
        s = pd.to_datetime(ts, utc=True)
        return s

    def _write_ohlcv_df(self, df: pd.DataFrame, filepath: str, append: bool) -> None:
        # Ensure column order per spec
        columns = ["symbol", "timestamp", "open", "high", "low", "close", "volume", "source"]
        # Drop unknown columns
        df = df[[c for c in columns if c in df.columns]]
        # Remove duplicates by symbol+timestamp (last write wins)
        df = df.drop_duplicates(subset=["symbol", "timestamp"], keep="last")
        # If appending, merge with existing
        if append and os.path.exists(filepath):
            existing = pd.read_csv(filepath)
            if not existing.empty:
                existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["symbol", "timestamp"], keep="last")
            # Sort by timestamp
            combined = combined.sort_values("timestamp")
            # Write
            combined.to_csv(filepath, index=False)
        else:
            df = df.sort_values("timestamp")
            df.to_csv(filepath, index=False)

    def save_ohlcv_data(self, ohlcv_data: List[OHLCVData], granularity: str, append: bool = True) -> bool:
        """Save OHLCV data to organized CSV files by symbol/year/granularity."""
        try:
            if not ohlcv_data:
                return True

            # Convert to DataFrame
            df = pd.DataFrame([data.to_dict() for data in ohlcv_data])
            if df.empty:
                return True
            # Normalize timestamps to UTC
            df["timestamp"] = self._normalize_timestamp_series_utc(df["timestamp"])

            # Group by symbol and year, write to corresponding files
            records_written = 0
            for (symbol, year), group in df.groupby(["symbol", df["timestamp"].dt.year]):
                filepath = self._historical_filepath(symbol, int(year), granularity)
                self._write_ohlcv_df(group, filepath, append=append)
                records_written += len(group)

            logger.info(f"Saved {records_written} OHLCV data records to historical storage for granularity {granularity}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving OHLCV data: {e}")
            return False
    
    def _list_symbol_year_files(self, symbol: str, granularity: str, year: Optional[int] = None) -> List[str]:
        symbol_upper = symbol.upper()
        files: List[str] = []
        if year is not None:
            candidate = self._historical_filepath(symbol_upper, int(year), granularity)
            if os.path.exists(candidate):
                files.append(candidate)
            return files
        # scan directory for matching files
        try:
            for fname in os.listdir(self.historical_dir):
                if not fname.endswith(".csv"):
                    continue
                # Expected: SYMBOL_YEAR_GRANULARITY.csv
                parts = fname[:-4].split("_")
                if len(parts) != 3:
                    continue
                f_symbol, f_year, f_gran = parts
                if f_symbol == symbol_upper and f_gran == granularity:
                    files.append(os.path.join(self.historical_dir, fname))
        except FileNotFoundError:
            pass
        return sorted(files)

    def load_ohlcv_data(
        self,
        symbol: Optional[str] = None,
        granularity: Optional[str] = None,
        year: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load OHLCV data from organized CSV files.

        If symbol and granularity are provided, loads corresponding files (optionally filtered by year).
        If symbol is None, loads all symbols for the provided granularity.
        """
        try:
            frames: List[pd.DataFrame] = []
            # Determine files to load
            if symbol and granularity:
                files = self._list_symbol_year_files(symbol, granularity, year)
            else:
                # load all files optionally filtered by granularity
                files = []
                try:
                    for fname in os.listdir(self.historical_dir):
                        if not fname.endswith('.csv'):
                            continue
                        if granularity:
                            if not fname.endswith(f"_{granularity}.csv"):
                                continue
                        files.append(os.path.join(self.historical_dir, fname))
                except FileNotFoundError:
                    files = []

            if not files:
                logger.warning("No OHLCV historical files found for criteria")
                return pd.DataFrame()

            for path in files:
                tmp = pd.read_csv(path)
                if tmp.empty:
                    continue
                tmp['timestamp'] = pd.to_datetime(tmp['timestamp'], utc=True)
                frames.append(tmp)

            if not frames:
                return pd.DataFrame()

            df = pd.concat(frames, ignore_index=True)
            # Filter by symbol if provided
            if symbol:
                df = df[df['symbol'] == symbol.upper()]
            # Filter by date range if provided
            if start_date is not None:
                df = df[df['timestamp'] >= pd.to_datetime(start_date, utc=True)]
            if end_date is not None:
                df = df[df['timestamp'] <= pd.to_datetime(end_date, utc=True)]

            # Sort by timestamp
            df = df.sort_values('timestamp')

            logger.info(f"Loaded {len(df)} OHLCV data records from historical storage")
            return df
            
        except Exception as e:
            logger.error(f"Error loading OHLCV data: {e}")
            return pd.DataFrame()
    
    def get_historical_ohlcv_data(
        self, 
        symbol: str,
        granularity: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get historical OHLCV data with standardized DataFrame shape and UTC timestamps."""
        try:
            # Determine year(s) to load based on date range
            year = None
            if start_date and end_date:
                start_year = start_date.year
                end_year = end_date.year
                # If date range spans multiple years, we'll load all years and filter later
                if start_year == end_year:
                    year = start_year
            
            # Load OHLCV data
            df = self.load_ohlcv_data(symbol=symbol, granularity=granularity, year=year, start_date=start_date, end_date=end_date)
            
            if df.empty:
                logger.warning(f"No OHLCV data found for symbol {symbol}")
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            
            # Create standardized DataFrame with timestamp as index
            ohlcv_df = df.set_index('timestamp')
            
            # Select only OHLCV columns
            ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
            if all(col in ohlcv_df.columns for col in ohlcv_columns):
                ohlcv_df = ohlcv_df[ohlcv_columns]
            else:
                logger.error(f"Missing required OHLCV columns: {ohlcv_columns}")
                return pd.DataFrame(columns=ohlcv_columns)
            
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
                "source": df.iloc[0].get('source', 'provider') if not df.empty else 'unknown',
                "data_type": "ohlcv",
                "total_records": len(ohlcv_df),
                "start_date": ohlcv_df.index.min() if not ohlcv_df.empty else None,
                "end_date": ohlcv_df.index.max() if not ohlcv_df.empty else None,
                "granularity": granularity
            }
            
            logger.info(f"Retrieved {len(ohlcv_df)} historical OHLCV records for {symbol} at {granularity}")
            return ohlcv_df
            
        except Exception as e:
            logger.error(f"Error getting historical OHLCV data for {symbol}: {e}")
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    
    def get_latest_ohlcv_data(self, symbol: str) -> Optional[OHLCVData]:
        """Get the latest OHLCV data for a symbol."""
        try:
            # Load across all granularities and pick latest overall
            df = self.load_ohlcv_data(symbol=symbol)
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            return OHLCVData(
                symbol=latest['symbol'],
                timestamp=latest['timestamp'],
                open=latest['open'],
                high=latest['high'],
                low=latest['low'],
                close=latest['close'],
                volume=latest['volume'],
                source=latest.get('source', 'provider')
            )
            
        except Exception as e:
            logger.error(f"Error getting latest OHLCV data for {symbol}: {e}")
            return None
