"""Tests for data storage functionality."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile
import shutil

from hypebot.data.storage import DataStorage
from hypebot.data.models import PriceData, MarketData
from hypebot.config import DatabaseConfig


class TestDataStorage:
    """Test cases for data storage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config = DatabaseConfig(data_dir=self.temp_dir)
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
