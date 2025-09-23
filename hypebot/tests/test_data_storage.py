"""Tests for data storage functionality."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile
import shutil

from hypebot.data.storage import DataStorage
from hypebot.data.models import PriceData, MarketData, OHLCVData
from hypebot.config import DatabaseConfig


class TestDataStorage:
    """Test cases for data storage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config = DatabaseConfig(
            data_dir=self.temp_dir,
            price_data_file="price_data.csv",
            positions_file="positions.csv",
            trades_file="trades.csv",
            signals_file="signals.csv"
        )
        self.storage = DataStorage(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_price_data(self):
        """Test saving and loading price data."""
        # Create test price data
        price_data = [
            PriceData(
                symbol="BTC",
                timestamp=datetime.utcnow(),
                price=50000.0,
                volume_24h=1000000.0,
                market_cap=1000000000.0,
                source="coingecko"
            ),
            PriceData(
                symbol="ETH",
                timestamp=datetime.utcnow(),
                price=3000.0,
                volume_24h=500000.0,
                market_cap=400000000.0,
                source="coingecko"
            )
        ]
        
        # Save data
        success = self.storage.save_price_data(price_data)
        assert success
        
        # Load data
        loaded_data = self.storage.load_price_data()
        assert len(loaded_data) == 2
        assert "BTC" in loaded_data["symbol"].values
        assert "ETH" in loaded_data["symbol"].values
    
    def test_save_and_load_price_data_with_symbol_filter(self):
        """Test loading price data with symbol filter."""
        # Create test data
        price_data = [
            PriceData("BTC", datetime.utcnow(), 50000.0, 1000000.0, 1000000000.0),
            PriceData("ETH", datetime.utcnow(), 3000.0, 500000.0, 400000000.0)
        ]
        
        self.storage.save_price_data(price_data)
        
        # Load only BTC data
        btc_data = self.storage.load_price_data(symbol="BTC")
        assert len(btc_data) == 1
        assert btc_data.iloc[0]["symbol"] == "BTC"
    
    def test_save_and_load_price_data_with_date_filter(self):
        """Test loading price data with date filter."""
        # Create test data with different timestamps
        now = datetime.utcnow()
        price_data = [
            PriceData("BTC", now - timedelta(days=2), 50000.0, 1000000.0, 1000000000.0),
            PriceData("BTC", now - timedelta(days=1), 51000.0, 1100000.0, 1100000000.0),
            PriceData("BTC", now, 52000.0, 1200000.0, 1200000000.0)
        ]
        
        self.storage.save_price_data(price_data)
        
        # Load data from last day only
        recent_data = self.storage.load_price_data(
            start_date=now - timedelta(days=1)
        )
        assert len(recent_data) == 2
    
    def test_save_and_load_market_data(self):
        """Test saving and loading market data."""
        market_data = [
            MarketData(
                symbol="BTC",
                timestamp=datetime.utcnow(),
                price=50000.0,
                volume_24h=1000000.0,
                market_cap=1000000000.0,
                price_change_24h=1000.0,
                price_change_percentage_24h=2.0,
                high_24h=51000.0,
                low_24h=49000.0,
                source="coingecko"
            )
        ]
        
        # Save data
        success = self.storage.save_market_data(market_data)
        assert success
        
        # Load data
        loaded_data = self.storage.load_market_data()
        assert len(loaded_data) == 1
        assert loaded_data.iloc[0]["symbol"] == "BTC"
        assert loaded_data.iloc[0]["price_change_24h"] == 1000.0
    
    def test_save_and_load_positions(self):
        """Test saving and loading positions."""
        positions = [
            {
                "symbol": "BTC",
                "side": "LONG",
                "size": 0.1,
                "entry_price": 50000.0,
                "current_price": 51000.0,
                "pnl": 100.0,
                "kelly_size": 0.05,
                "timestamp": datetime.utcnow()
            }
        ]
        
        # Save data
        success = self.storage.save_positions(positions)
        assert success
        
        # Load data
        loaded_data = self.storage.load_positions()
        assert len(loaded_data) == 1
        assert loaded_data.iloc[0]["symbol"] == "BTC"
        assert loaded_data.iloc[0]["side"] == "LONG"
    
    def test_save_and_load_trades(self):
        """Test saving and loading trades."""
        trades = [
            {
                "trade_id": "trade_1",
                "symbol": "BTC",
                "side": "BUY",
                "quantity": 0.1,
                "price": 50000.0,
                "timestamp": datetime.utcnow(),
                "order_id": "order_1",
                "commission": 5.0,
                "commission_asset": "USDC"
            }
        ]
        
        # Save data
        success = self.storage.save_trades(trades)
        assert success
        
        # Load data
        loaded_data = self.storage.load_trades()
        assert len(loaded_data) == 1
        assert loaded_data.iloc[0]["trade_id"] == "trade_1"
        assert loaded_data.iloc[0]["symbol"] == "BTC"
    
    def test_save_and_load_signals(self):
        """Test saving and loading signals."""
        signals = [
            {
                "symbol": "BTC",
                "timestamp": datetime.utcnow(),
                "signal_type": "BUY",
                "strength": 0.8,
                "rsi_value": 25.0,
                "indicator": "RSI",
                "price": 50000.0,
                "metadata": {"test": "data"}
            }
        ]
        
        # Save data
        success = self.storage.save_signals(signals)
        assert success
        
        # Load data
        loaded_data = self.storage.load_signals()
        assert len(loaded_data) == 1
        assert loaded_data.iloc[0]["symbol"] == "BTC"
        assert loaded_data.iloc[0]["signal_type"] == "BUY"
    
    def test_get_latest_price(self):
        """Test getting latest price for a symbol."""
        # Create test data
        now = datetime.utcnow()
        price_data = [
            PriceData("BTC", now - timedelta(hours=2), 50000.0, 1000000.0, 1000000000.0),
            PriceData("BTC", now - timedelta(hours=1), 51000.0, 1100000.0, 1100000000.0),
            PriceData("BTC", now, 52000.0, 1200000.0, 1200000000.0)
        ]
        
        self.storage.save_price_data(price_data)
        
        # Get latest price
        latest = self.storage.get_latest_price("BTC")
        assert latest is not None
        assert latest.price == 52000.0
        assert latest.symbol == "BTC"
    
    def test_get_latest_price_no_data(self):
        """Test getting latest price when no data exists."""
        latest = self.storage.get_latest_price("NONEXISTENT")
        assert latest is None
    
    def test_append_mode(self):
        """Test that data is appended correctly."""
        # Save initial data
        price_data_1 = [
            PriceData("BTC", datetime.utcnow(), 50000.0, 1000000.0, 1000000000.0)
        ]
        self.storage.save_price_data(price_data_1)
        
        # Save additional data
        price_data_2 = [
            PriceData("ETH", datetime.utcnow(), 3000.0, 500000.0, 400000000.0)
        ]
        self.storage.save_price_data(price_data_2)
        
        # Load all data
        all_data = self.storage.load_price_data()
        assert len(all_data) == 2
        assert "BTC" in all_data["symbol"].values
        assert "ETH" in all_data["symbol"].values
    
    def test_save_and_load_ohlcv_data(self):
        """Test saving and loading OHLCV data."""
        # Create test OHLCV data
        ohlcv_data = [
            OHLCVData(
                symbol="BTC",
                timestamp=datetime.utcnow(),
                open=49000.0,
                high=51000.0,
                low=48500.0,
                close=50000.0,
                volume=1000000.0,
                source="coingecko"
            ),
            OHLCVData(
                symbol="ETH",
                timestamp=datetime.utcnow(),
                open=2900.0,
                high=3100.0,
                low=2850.0,
                close=3000.0,
                volume=500000.0,
                source="coingecko"
            )
        ]
        
        # Save data
        success = self.storage.save_ohlcv_data(ohlcv_data, granularity="1d")
        assert success
        
        # Load data
        loaded_data = self.storage.load_ohlcv_data()
        assert len(loaded_data) == 2
        assert "BTC" in loaded_data["symbol"].values
        assert "ETH" in loaded_data["symbol"].values
        assert all(col in loaded_data.columns for col in ["open", "high", "low", "close", "volume"])
    
    def test_save_and_load_ohlcv_data_with_symbol_filter(self):
        """Test loading OHLCV data with symbol filter."""
        # Create test data
        ohlcv_data = [
            OHLCVData("BTC", datetime.utcnow(), 49000.0, 51000.0, 48500.0, 50000.0, 1000000.0),
            OHLCVData("ETH", datetime.utcnow(), 2900.0, 3100.0, 2850.0, 3000.0, 500000.0)
        ]
        
        self.storage.save_ohlcv_data(ohlcv_data, granularity="1h")
        
        # Load only BTC data
        btc_data = self.storage.load_ohlcv_data(symbol="BTC", granularity="1h")
        assert len(btc_data) == 1
        assert btc_data.iloc[0]["symbol"] == "BTC"
        assert btc_data.iloc[0]["open"] == 49000.0
    
    def test_save_and_load_ohlcv_data_with_date_filter(self):
        """Test loading OHLCV data with date filter."""
        # Create test data with different timestamps
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC", now - timedelta(days=2), 48000.0, 50000.0, 47500.0, 49000.0, 900000.0),
            OHLCVData("BTC", now - timedelta(days=1), 49000.0, 51000.0, 48500.0, 50000.0, 1000000.0),
            OHLCVData("BTC", now, 50000.0, 52000.0, 49500.0, 51000.0, 1100000.0)
        ]
        
        self.storage.save_ohlcv_data(ohlcv_data, granularity="1d")
        
        # Load data from last day only
        recent_data = self.storage.load_ohlcv_data(
            granularity="1d",
            start_date=now - timedelta(days=1)
        )
        assert len(recent_data) == 2
    
    def test_get_historical_ohlcv_data(self):
        """Test getting historical OHLCV data with standardized DataFrame format."""
        # Create test data
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC", now - timedelta(hours=2), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0),
            OHLCVData("BTC", now - timedelta(hours=1), 49500.0, 50500.0, 49000.0, 50000.0, 1100000.0),
            OHLCVData("BTC", now, 50000.0, 51000.0, 49500.0, 50500.0, 1200000.0)
        ]
        
        self.storage.save_ohlcv_data(ohlcv_data, granularity="1h")
        
        # Get historical data
        historical_df = self.storage.get_historical_ohlcv_data("BTC", "1h")
        
        # Check DataFrame structure
        assert not historical_df.empty
        assert list(historical_df.columns) == ["open", "high", "low", "close", "volume"]
        assert len(historical_df) == 3
        
        # Check index is timestamp and UTC
        assert historical_df.index.tz is not None
        assert str(historical_df.index.tz) == 'UTC'
        
        # Check metadata
        assert historical_df.attrs["symbol"] == "BTC"
        assert historical_df.attrs["data_type"] == "ohlcv"
        assert historical_df.attrs["total_records"] == 3
        assert historical_df.attrs["granularity"] == "1h"
    
    def test_get_historical_ohlcv_data_with_date_range(self):
        """Test getting historical OHLCV data with date range filtering."""
        # Create test data
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC", now - timedelta(days=3), 48000.0, 49000.0, 47500.0, 48500.0, 900000.0),
            OHLCVData("BTC", now - timedelta(days=2), 48500.0, 49500.0, 48000.0, 49000.0, 950000.0),
            OHLCVData("BTC", now - timedelta(days=1), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0),
            OHLCVData("BTC", now, 49500.0, 50500.0, 49000.0, 50000.0, 1050000.0)
        ]
        
        self.storage.save_ohlcv_data(ohlcv_data, granularity="1d")
        
        # Get data from last 2 days only (excluding today)
        historical_df = self.storage.get_historical_ohlcv_data(
            "BTC",
            "1d",
            start_date=now - timedelta(days=2),
            end_date=now - timedelta(days=1)
        )
        
        assert len(historical_df) == 2
        assert historical_df.attrs["total_records"] == 2
    
    def test_get_historical_ohlcv_data_no_data(self):
        """Test getting historical OHLCV data when no data exists."""
        historical_df = self.storage.get_historical_ohlcv_data("NONEXISTENT", "1h")
        
        assert historical_df.empty
        assert list(historical_df.columns) == ["open", "high", "low", "close", "volume"]
    
    def test_get_latest_ohlcv_data(self):
        """Test getting latest OHLCV data for a symbol."""
        # Create test data
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC", now - timedelta(hours=2), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0),
            OHLCVData("BTC", now - timedelta(hours=1), 49500.0, 50500.0, 49000.0, 50000.0, 1100000.0),
            OHLCVData("BTC", now, 50000.0, 51000.0, 49500.0, 50500.0, 1200000.0)
        ]
        
        self.storage.save_ohlcv_data(ohlcv_data, granularity="1h")
        
        # Get latest OHLCV data
        latest = self.storage.get_latest_ohlcv_data("BTC")
        assert latest is not None
        assert latest.symbol == "BTC"
        assert latest.close == 50500.0
        assert latest.volume == 1200000.0
    
    def test_get_latest_ohlcv_data_no_data(self):
        """Test getting latest OHLCV data when no data exists."""
        latest = self.storage.get_latest_ohlcv_data("NONEXISTENT")
        assert latest is None
    
    def test_ohlcv_append_mode(self):
        """Test that OHLCV data is appended correctly."""
        # Save initial data
        ohlcv_data_1 = [
            OHLCVData("BTC", datetime.utcnow(), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0)
        ]
        self.storage.save_ohlcv_data(ohlcv_data_1, granularity="1d")
        
        # Save additional data
        ohlcv_data_2 = [
            OHLCVData("ETH", datetime.utcnow(), 2900.0, 3000.0, 2850.0, 2950.0, 500000.0)
        ]
        self.storage.save_ohlcv_data(ohlcv_data_2, granularity="1d")
        
        # Load all data
        all_data = self.storage.load_ohlcv_data()
        assert len(all_data) == 2
        assert "BTC" in all_data["symbol"].values
        assert "ETH" in all_data["symbol"].values
    
    def test_ohlcv_data_model_serialization(self):
        """Test OHLCV data model serialization methods."""
        # Test to_dict
        ohlcv = OHLCVData("BTC", datetime.utcnow(), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0)
        data_dict = ohlcv.to_dict()
        
        assert data_dict["symbol"] == "BTC"
        assert data_dict["open"] == 49000.0
        assert data_dict["high"] == 50000.0
        assert data_dict["low"] == 48500.0
        assert data_dict["close"] == 49500.0
        assert data_dict["volume"] == 1000000.0
        
        # Test from_dict
        ohlcv_from_dict = OHLCVData.from_dict(data_dict)
        assert ohlcv_from_dict.symbol == ohlcv.symbol
        assert ohlcv_from_dict.open == ohlcv.open
        assert ohlcv_from_dict.close == ohlcv.close
    
    def test_ohlcv_standardized_dataframe(self):
        """Test OHLCV standardized DataFrame creation."""
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC", now - timedelta(hours=1), 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0),
            OHLCVData("BTC", now, 49500.0, 50500.0, 49000.0, 50000.0, 1100000.0)
        ]
        
        # Test single OHLCV to DataFrame
        df_single = ohlcv_data[0].to_standardized_dataframe()
        assert len(df_single) == 1
        assert list(df_single.columns) == ["open", "high", "low", "close", "volume"]
        assert df_single.attrs["symbol"] == "BTC"
        assert df_single.attrs["data_type"] == "ohlcv"
        
        # Test multiple OHLCV to DataFrame
        df_multiple = OHLCVData.create_standardized_dataframe(ohlcv_data)
        assert len(df_multiple) == 2
        assert list(df_multiple.columns) == ["open", "high", "low", "close", "volume"]
        assert df_multiple.attrs["symbol"] == "BTC"
        assert df_multiple.attrs["total_records"] == 2
        assert df_multiple.index.tz is not None
    
    def test_ohlcv_duplicate_handling(self):
        """Test that duplicate OHLCV records are handled correctly."""
        now = datetime.utcnow()
        # Create duplicate data (same symbol and timestamp)
        ohlcv_data_1 = [
            OHLCVData("BTC", now, 49000.0, 50000.0, 48500.0, 49500.0, 1000000.0)
        ]
        ohlcv_data_2 = [
            OHLCVData("BTC", now, 49500.0, 50500.0, 49000.0, 50000.0, 1100000.0)  # Same timestamp
        ]
        
        # Save first batch
        self.storage.save_ohlcv_data(ohlcv_data_1, granularity="1h")
        
        # Save second batch (should replace duplicate)
        self.storage.save_ohlcv_data(ohlcv_data_2, granularity="1h")
        
        # Load data - should only have one record with updated values
        loaded_data = self.storage.load_ohlcv_data(symbol="BTC", granularity="1h")
        assert len(loaded_data) == 1
        assert loaded_data.iloc[0]["close"] == 50000.0  # Should be the second value

    def test_historical_file_naming_and_directory(self):
        """Test that files are created under historical dir with correct names."""
        now = datetime.utcnow()
        ohlcv_data = [
            OHLCVData("BTC-USD", now, 45000.0, 45500.0, 44800.0, 45200.0, 1250000.0, source="coingecko")
        ]
        granularity = "1d"
        assert self.storage.save_ohlcv_data(ohlcv_data, granularity=granularity)
        year = now.year
        hist_dir = os.path.join(self.config.data_dir, getattr(self.config, "historical_data_dir", "historical"))
        expected_filename = f"BTC-USD_{year}_{granularity}.csv"
        expected_path = os.path.join(hist_dir, expected_filename)
        assert os.path.exists(expected_path)
        # Verify CSV header columns order
        df = pd.read_csv(expected_path)
        assert list(df.columns)[:7] == ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
