"""Unit tests for BuyAndHoldStrategy."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
import pandas as pd

from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from hypebot.strategy.models import StrategyOrder
from hypebot.position.manager import PositionManager
from hypebot.config import TradingConfig, DatabaseConfig


class TestBuyAndHoldStrategy:
    """Test cases for BuyAndHoldStrategy."""

    @pytest.fixture
    def mock_position_manager(self):
        """Create a mock position manager."""
        pm = Mock(spec=PositionManager)
        pm.get_position.return_value = None
        return pm

    @pytest.fixture
    def strategy(self, mock_position_manager):
        """Create a BuyAndHoldStrategy instance for testing."""
        return BuyAndHoldStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=mock_position_manager,
            starting_cash=10000.0
        )

    @pytest.fixture
    def sample_historical_data(self):
        """Create sample historical data for testing."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D", tz=timezone.utc)
        return {
            "BTC-USD": pd.DataFrame({
                "open": [100.0] * 10,
                "high": [110.0] * 10,
                "low": [90.0] * 10,
                "close": [105.0] * 10,
                "volume": [1000] * 10
            }, index=dates),
            "ETH-USD": pd.DataFrame({
                "open": [50.0] * 10,
                "high": [55.0] * 10,
                "low": [45.0] * 10,
                "close": [52.0] * 10,
                "volume": [2000] * 10
            }, index=dates)
        }

    def test_initialization(self, strategy):
        """Test strategy initialization."""
        assert strategy.assets == ["BTC-USD", "ETH-USD"]
        assert strategy.interval == "1d"
        assert not strategy._has_purchased

    @pytest.mark.asyncio
    async def test_first_tick_generates_orders(self, strategy, sample_historical_data, mock_position_manager):
        """Test that first tick generates buy orders for all assets."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        orders = await strategy.tick(as_of, sample_historical_data)
        
        # Should generate 2 orders (one for each asset)
        assert len(orders) == 2
        
        # Check BTC-USD order
        btc_order = next((o for o in orders if o.symbol == "BTC-USD"), None)
        assert btc_order is not None
        assert btc_order.side == "BUY"
        assert btc_order.order_type == "MARKET"
        assert btc_order.price == 105.0
        assert btc_order.quantity == 5000.0 / 105.0  # Half of 10000 / price
        assert btc_order.timestamp == as_of
        
        # Check ETH-USD order
        eth_order = next((o for o in orders if o.symbol == "ETH-USD"), None)
        assert eth_order is not None
        assert eth_order.side == "BUY"
        assert eth_order.order_type == "MARKET"
        assert eth_order.price == 52.0
        assert eth_order.quantity == 5000.0 / 52.0  # Half of 10000 / price
        assert eth_order.timestamp == as_of
        
        # Should mark as purchased
        assert strategy._has_purchased

    @pytest.mark.asyncio
    async def test_subsequent_ticks_generate_no_orders(self, strategy, sample_historical_data):
        """Test that subsequent ticks generate no orders."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        # First tick
        orders1 = await strategy.tick(as_of, sample_historical_data)
        assert len(orders1) == 2
        assert strategy._has_purchased
        
        # Second tick
        as_of2 = datetime(2024, 1, 2, tzinfo=timezone.utc)
        orders2 = await strategy.tick(as_of2, sample_historical_data)
        assert len(orders2) == 0

    @pytest.mark.asyncio
    async def test_no_cash_generates_no_orders(self, sample_historical_data, mock_position_manager):
        """Test that no cash generates no orders."""
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=mock_position_manager,
            starting_cash=0.0
        )
        
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        orders = await strategy.tick(as_of, sample_historical_data)
        
        assert len(orders) == 0
        assert not strategy._has_purchased

    @pytest.mark.asyncio
    async def test_no_valid_data_generates_no_orders(self, strategy, mock_position_manager):
        """Test that no valid data generates no orders."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        empty_data = {
            "BTC-USD": pd.DataFrame(),  # Empty DataFrame
            "ETH-USD": None  # None data
        }
        
        orders = await strategy.tick(as_of, empty_data)
        
        assert len(orders) == 0
        assert not strategy._has_purchased

    @pytest.mark.asyncio
    async def test_partial_valid_data(self, strategy, sample_historical_data, mock_position_manager):
        """Test behavior with only some assets having valid data."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        partial_data = {
            "BTC-USD": sample_historical_data["BTC-USD"],
            "ETH-USD": pd.DataFrame(),  # Empty DataFrame
            "INVALID-USD": None  # None data
        }
        
        orders = await strategy.tick(as_of, partial_data)
        
        # Should only generate order for BTC-USD
        assert len(orders) == 1
        assert orders[0].symbol == "BTC-USD"
        assert orders[0].quantity == 10000.0 / 105.0  # All cash goes to single asset
        assert strategy._has_purchased

    @pytest.mark.asyncio
    async def test_single_asset_strategy(self, mock_position_manager):
        """Test strategy with single asset."""
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=mock_position_manager,
            starting_cash=10000.0
        )
        
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        single_asset_data = {
            "BTC-USD": pd.DataFrame({
                "open": [100.0],
                "high": [110.0],
                "low": [90.0],
                "close": [105.0],
                "volume": [1000]
            }, index=[as_of])
        }
        
        orders = await strategy.tick(as_of, single_asset_data)
        
        assert len(orders) == 1
        assert orders[0].symbol == "BTC-USD"
        assert orders[0].quantity == 10000.0 / 105.0  # All cash goes to single asset

    @pytest.mark.asyncio
    async def test_on_start_resets_purchase_flag(self, strategy):
        """Test that on_start resets the purchase flag."""
        strategy._has_purchased = True
        
        await strategy.on_start()
        
        assert not strategy._has_purchased

    @pytest.mark.asyncio
    async def test_on_stop_resets_purchase_flag(self, strategy):
        """Test that on_stop resets the purchase flag."""
        strategy._has_purchased = True
        
        await strategy.on_stop()
        
        assert not strategy._has_purchased

    @pytest.mark.asyncio
    async def test_cash_distribution_equal(self, strategy, sample_historical_data, mock_position_manager):
        """Test that cash is distributed equally among assets."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        orders = await strategy.tick(as_of, sample_historical_data)
        
        # Each order should use half the cash
        btc_order = next(o for o in orders if o.symbol == "BTC-USD")
        eth_order = next(o for o in orders if o.symbol == "ETH-USD")
        
        btc_value = btc_order.quantity * btc_order.price
        eth_value = eth_order.quantity * eth_order.price
        
        # Values should be equal (within floating point precision)
        assert abs(btc_value - eth_value) < 0.01
        assert abs(btc_value - 5000.0) < 0.01

    def test_strategy_implements_interface(self, strategy):
        """Test that strategy properly implements the Strategy interface."""
        from hypebot.strategy.base import Strategy
        
        assert isinstance(strategy, Strategy)
        assert hasattr(strategy, 'assets')
        assert hasattr(strategy, 'interval')
        assert hasattr(strategy, 'position_manager')
        assert hasattr(strategy, 'tick')
        assert hasattr(strategy, 'on_start')
        assert hasattr(strategy, 'on_stop')

    @pytest.mark.asyncio
    async def test_missing_close_column_skipped(self, strategy, mock_position_manager):
        """Test that assets without close column are skipped."""
        as_of = datetime(2024, 1, 1, tzinfo=timezone.utc)
        invalid_data = {
            "BTC-USD": pd.DataFrame({
                "open": [100.0],
                "high": [110.0],
                "low": [90.0],
                # Missing close column
                "volume": [1000]
            }, index=[as_of])
        }
        
        orders = await strategy.tick(as_of, invalid_data)
        
        assert len(orders) == 0
        assert not strategy._has_purchased
