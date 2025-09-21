"""Data storage using Pandas for local persistence."""

import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from .models import PriceData, MarketData
from ..config import DatabaseConfig


logger = logging.getLogger(__name__)


class DataStorage:
    """Local data storage using Pandas DataFrames."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize data storage."""
        self.config = config
        self.data_dir = config.data_dir
        self._ensure_data_directory()
    
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
            
            df = pd.read_csv(file_path)
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
                source=latest.get('source', 'coingecko')
            )
            
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
