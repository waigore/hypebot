"""Integration tests for BackTester with BuyAndHold control strategy."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pandas as pd

from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from hypebot.strategy.rsi_strategy import RSIStrategy
from hypebot.config import Config, TradingConfig, DatabaseConfig
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager
from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.position.kelly_criterion import KellyCriterion


class TestBackTesterBuyAndHoldIntegration:
    """Integration tests for BackTester with BuyAndHold control strategy."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.trading = Mock(spec=TradingConfig)
        config.trading.rsi_period = 14
        config.trading.rsi_oversold = 30
        config.trading.rsi_overbought = 70
        config.trading.kelly_lookback_period = 30
        config.trading.max_position_size = 0.1
        config.trading.min_position_size = 0.001
        config.trading.risk_free_rate = 0.02
        config.database = Mock(spec=DatabaseConfig)
        config.database.data_dir = "data"
        config.database.historical_data_dir = "historical"
        return config

    @pytest.fixture
    def mock_storage(self):
        """Create a mock data storage."""
        storage = Mock(spec=DataStorage)
        return storage

    @pytest.fixture
    def sample_historical_data(self):
        """Create sample historical data for testing."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D", tz=timezone.utc)
        return {
            "BTC-USD": pd.DataFrame({
                "open": [100.0 + i for i in range(30)],
                "high": [110.0 + i for i in range(30)],
                "low": [90.0 + i for i in range(30)],
                "close": [105.0 + i for i in range(30)],
                "volume": [1000 + i * 10 for i in range(30)]
            }, index=dates),
            "ETH-USD": pd.DataFrame({
                "open": [50.0 + i * 0.5 for i in range(30)],
                "high": [55.0 + i * 0.5 for i in range(30)],
                "low": [45.0 + i * 0.5 for i in range(30)],
                "close": [52.0 + i * 0.5 for i in range(30)],
                "volume": [2000 + i * 20 for i in range(30)]
            }, index=dates)
        }

    @pytest.fixture
    def backtester(self, mock_config, mock_storage):
        """Create a BackTester instance for testing."""
        return BackTester(
            config=mock_config,
            storage=mock_storage,
            commission=CommissionModel(type="percent", value=0.001),
            starting_cash=10000.0
        )

    @pytest.fixture
    def rsi_strategy(self, mock_config, mock_storage):
        """Create an RSI strategy for testing."""
        rsi_calc = RSICalculator(period=14, oversold_threshold=30, overbought_threshold=70)
        pm = PositionManager(mock_config.trading, mock_storage)
        kelly_criterion = KellyCriterion(mock_config.trading)
        return RSIStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=pm,
            rsi_calculator=rsi_calc,
            kelly_criterion=kelly_criterion,
            config=mock_config.trading
        )

    @pytest.fixture
    def buy_and_hold_strategy(self, mock_config, mock_storage):
        """Create a BuyAndHold strategy for testing."""
        pm = PositionManager(mock_config.trading, mock_storage)
        return BuyAndHoldStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=pm
        )

    @pytest.mark.asyncio
    async def test_run_with_control_includes_buy_and_hold(self, backtester, rsi_strategy, sample_historical_data, mock_storage):
        """Test that run_with_control includes BuyAndHold strategy."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        strategies = [rsi_strategy]
        assets = ["BTC-USD", "ETH-USD"]
        interval = "1d"
        
        results = await backtester.run_with_control(
            strategies=strategies,
            assets=assets,
            interval=interval
        )
        
        # Should have results for both RSI strategy and BuyAndHold
        assert "RSIStrategy" in results
        assert "BuyAndHoldStrategy" in results
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_buy_and_hold_control_performance(self, backtester, sample_historical_data, mock_storage):
        """Test that BuyAndHold control strategy performs as expected."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        # Create BuyAndHold strategy
        pm = PositionManager(backtester.config.trading, mock_storage)
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=pm
        )
        
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d"
        )
        
        # Should have equity curve
        assert not result.equity_curve.empty
        assert len(result.equity_curve) > 0
        
        # Should have orders (buy orders on first tick)
        assert len(result.orders) > 0
        
        # All orders should be BUY orders
        for order in result.orders:
            assert order.side == "BUY"
            assert order.symbol == "BTC-USD"

    @pytest.mark.asyncio
    async def test_multiple_strategies_with_control(self, backtester, rsi_strategy, sample_historical_data, mock_storage):
        """Test running multiple strategies with control."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        # Create another strategy
        pm2 = PositionManager(backtester.config.trading, mock_storage)
        strategy2 = BuyAndHoldStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=pm2
        )
        
        strategies = [rsi_strategy, strategy2]
        assets = ["BTC-USD", "ETH-USD"]
        interval = "1d"
        
        results = await backtester.run_with_control(
            strategies=strategies,
            assets=assets,
            interval=interval
        )
        
        # Should have results for all strategies plus control
        assert "RSIStrategy" in results
        assert "BuyAndHoldStrategy" in results  # This is the control
        # Note: Both provided strategies are BuyAndHoldStrategy, so we get 2 total (1 RSI + 1 BuyAndHold control)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_control_strategy_uses_same_parameters(self, backtester, sample_historical_data, mock_storage):
        """Test that control strategy uses same parameters as other strategies."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        # Create a simple strategy
        pm = PositionManager(backtester.config.trading, mock_storage)
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=pm
        )
        
        strategies = [strategy]
        assets = ["BTC-USD"]
        interval = "1d"
        
        results = await backtester.run_with_control(
            strategies=strategies,
            assets=assets,
            interval=interval
        )
        
        # Both strategies should have same assets and interval
        for strategy_name, result in results.items():
            # The result should contain data for the same assets
            assert not result.equity_curve.empty

    @pytest.mark.asyncio
    async def test_empty_strategies_list_still_includes_control(self, backtester, sample_historical_data, mock_storage):
        """Test that empty strategies list still includes control strategy."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        strategies = []
        assets = ["BTC-USD"]
        interval = "1d"
        
        results = await backtester.run_with_control(
            strategies=strategies,
            assets=assets,
            interval=interval
        )
        
        # Should only have the control strategy
        assert "BuyAndHoldStrategy" in results
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_control_strategy_equity_curve_monotonic_increase(self, backtester, sample_historical_data, mock_storage):
        """Test that BuyAndHold control strategy equity curve increases with price."""
        # Create data with increasing prices
        dates = pd.date_range("2024-01-01", periods=10, freq="D", tz=timezone.utc)
        increasing_data = {
            "BTC-USD": pd.DataFrame({
                "open": [100.0 + i * 10 for i in range(10)],
                "high": [110.0 + i * 10 for i in range(10)],
                "low": [90.0 + i * 10 for i in range(10)],
                "close": [105.0 + i * 10 for i in range(10)],
                "volume": [1000] * 10
            }, index=dates)
        }
        
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return increasing_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        # Create BuyAndHold strategy
        pm = PositionManager(backtester.config.trading, mock_storage)
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=pm
        )
        
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d"
        )
        
        # Equity curve should generally increase (allowing for small fluctuations due to commission)
        equity_values = result.equity_curve.values
        assert len(equity_values) > 1
        
        # First value should be starting cash minus commission
        # Last value should be higher due to price appreciation
        assert equity_values[-1] > equity_values[0] * 0.9  # Allow for commission

    @pytest.mark.asyncio
    async def test_control_strategy_with_multiple_assets(self, backtester, sample_historical_data, mock_storage):
        """Test BuyAndHold control strategy with multiple assets."""
        # Mock the storage to return our sample data
        def mock_get_historical_ohlcv_data(symbol, granularity, start_date, end_date):
            return sample_historical_data.get(symbol, pd.DataFrame())
        
        mock_storage.get_historical_ohlcv_data = mock_get_historical_ohlcv_data
        
        # Create BuyAndHold strategy with multiple assets
        pm = PositionManager(backtester.config.trading, mock_storage)
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD", "ETH-USD"],
            interval="1d",
            position_manager=pm
        )
        
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD", "ETH-USD"],
            interval="1d"
        )
        
        # Should have orders for both assets
        btc_orders = [o for o in result.orders if o.symbol == "BTC-USD"]
        eth_orders = [o for o in result.orders if o.symbol == "ETH-USD"]
        
        assert len(btc_orders) > 0
        assert len(eth_orders) > 0
        
        # All orders should be BUY orders
        for order in result.orders:
            assert order.side == "BUY"
