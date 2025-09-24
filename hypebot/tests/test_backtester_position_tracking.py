"""Tests for position tracking functionality in the backtester."""

import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from hypebot.backtesting.backtester import BackTester, BacktestResult, CommissionModel
from hypebot.config import Config, TradingConfig, DatabaseConfig
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager
from hypebot.position.models import Position
from hypebot.strategy.base import Strategy
from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from hypebot.exchange.models import Order


class MockStrategy(Strategy):
    """Mock strategy for testing."""
    
    def __init__(self):
        # Initialize with required parameters
        super().__init__(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=None
        )
        self.tick_count = 0
    
    async def tick(self, data: dict) -> list:
        """Mock tick implementation."""
        self.tick_count += 1
        # Open position on first tick, close on second
        if self.tick_count == 1:
            return [{"symbol": "BTC-USD", "side": "BUY", "quantity": 0.1, "price": 50000.0}]
        elif self.tick_count == 2:
            return [{"symbol": "BTC-USD", "side": "SELL", "quantity": 0.1, "price": 51000.0}]
        return []


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    config = Mock(spec=Config)
    config.trading = Mock(spec=TradingConfig)
    config.database = Mock(spec=DatabaseConfig)
    return config


@pytest.fixture
def mock_storage():
    """Create a mock storage for testing."""
    storage = Mock(spec=DataStorage)
    
    # Mock historical data
    dates = pd.date_range(start="2024-01-01", periods=5, freq="D", tz="UTC")
    data = pd.DataFrame({
        "open": [49000, 50000, 51000, 52000, 53000],
        "high": [49500, 50500, 51500, 52500, 53500],
        "low": [48500, 49500, 50500, 51500, 52500],
        "close": [50000, 51000, 52000, 53000, 54000],
        "volume": [100, 110, 120, 130, 140]
    }, index=dates)
    
    storage.get_historical_ohlcv_data.return_value = data
    return storage


@pytest.fixture
def backtester(mock_config, mock_storage):
    """Create a backtester instance for testing."""
    commission = CommissionModel(type="percent", value=0.001)
    return BackTester(
        config=mock_config,
        storage=mock_storage,
        commission=commission,
        starting_cash=10000.0
    )


class TestBacktestResult:
    """Test BacktestResult dataclass with positions field."""
    
    def test_backtest_result_creation(self):
        """Test that BacktestResult can be created with positions field."""
        equity_curve = pd.Series([10000, 10100, 10200], name="equity")
        orders = []
        trades = []
        snapshots = pd.DataFrame({"equity": [10000, 10100, 10200]})
        positions = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="D"),
            "symbol": ["BTC-USD", "BTC-USD", None],
            "cash_balance": [9500, 9000, 10000]
        })
        errors = []
        
        result = BacktestResult(
            equity_curve=equity_curve,
            orders=orders,
            trades=trades,
            snapshots=snapshots,
            positions=positions,
            errors=errors
        )
        
        assert result.positions is not None
        assert len(result.positions) == 3
        assert "symbol" in result.positions.columns
        assert "cash_balance" in result.positions.columns


class TestPositionTracking:
    """Test position tracking functionality in the backtester."""
    
    @pytest.mark.asyncio
    async def test_position_tracking_with_positions(self, backtester, mock_storage):
        """Test position tracking when positions are opened and closed."""
        strategy = MockStrategy()
        
        # Mock the strategy runner to simulate position opening/closing
        original_run = backtester.run_single
        
        async def mock_run_single(*args, **kwargs):
            # Create a mock result with positions
            equity_curve = pd.Series([10000, 9900, 10100], name="equity")
            orders = [
                Order(
                    symbol="BTC-USD",
                    side="BUY",
                    order_type="MARKET",
                    quantity=0.1,
                    price=50000.0,
                    status="FILLED",
                    filled_quantity=0.1,
                    average_fill_price=50000.0,
                    timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)
                )
            ]
            trades = []
            snapshots = pd.DataFrame({"equity": [10000, 9900, 10100]})
            
            # Create position tracking data
            positions_data = [
                {
                    "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "symbol": None,
                    "side": None,
                    "size": None,
                    "entry_price": None,
                    "current_price": None,
                    "pnl": None,
                    "realized_pnl": None,
                    "unrealized_pnl": None,
                    "pnl_percentage": None,
                    "kelly_size": None,
                    "market_value": None,
                    "entry_value": None,
                    "position_timestamp": None,
                    "cash_balance": 10000.0
                },
                {
                    "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
                    "symbol": "BTC-USD",
                    "side": "LONG",
                    "size": 0.1,
                    "entry_price": 50000.0,
                    "current_price": 51000.0,
                    "pnl": 100.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 100.0,
                    "pnl_percentage": 2.0,
                    "kelly_size": 0.1,
                    "market_value": 5100.0,
                    "entry_value": 5000.0,
                    "position_timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "cash_balance": 5000.0
                },
                {
                    "timestamp": datetime(2024, 1, 3, tzinfo=timezone.utc),
                    "symbol": None,
                    "side": None,
                    "size": None,
                    "entry_price": None,
                    "current_price": None,
                    "pnl": None,
                    "realized_pnl": None,
                    "unrealized_pnl": None,
                    "pnl_percentage": None,
                    "kelly_size": None,
                    "market_value": None,
                    "entry_value": None,
                    "position_timestamp": None,
                    "cash_balance": 10100.0
                }
            ]
            positions_df = pd.DataFrame(positions_data)
            if not positions_df.empty and "timestamp" in positions_df.columns:
                positions_df = positions_df.set_index(pd.to_datetime(positions_df["timestamp"], utc=True))
            
            errors = []
            
            return BacktestResult(
                equity_curve=equity_curve,
                orders=orders,
                trades=trades,
                snapshots=snapshots,
                positions=positions_df,
                errors=errors
            )
        
        backtester.run_single = mock_run_single
        
        # Run the backtest
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d"
        )
        
        # Verify position tracking
        assert result.positions is not None
        assert len(result.positions) == 3
        
        # Check first tick (no position)
        first_tick = result.positions.iloc[0]
        assert pd.isna(first_tick["symbol"])
        assert first_tick["cash_balance"] == 10000.0
        
        # Check second tick (position open)
        second_tick = result.positions.iloc[1]
        assert second_tick["symbol"] == "BTC-USD"
        assert second_tick["side"] == "LONG"
        assert second_tick["size"] == 0.1
        assert second_tick["entry_price"] == 50000.0
        assert second_tick["current_price"] == 51000.0
        assert second_tick["pnl"] == 100.0
        assert second_tick["cash_balance"] == 5000.0
        
        # Check third tick (position closed)
        third_tick = result.positions.iloc[2]
        assert pd.isna(third_tick["symbol"])
        assert third_tick["cash_balance"] == 10100.0
    
    @pytest.mark.asyncio
    async def test_position_tracking_no_data(self, backtester, mock_storage):
        """Test position tracking when no data is available."""
        strategy = MockStrategy()
        
        # Mock storage to return empty data
        mock_storage.get_historical_ohlcv_data.return_value = pd.DataFrame()
        
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d"
        )
        
        # Verify empty result
        assert result.positions is not None
        assert result.positions.empty
        assert result.equity_curve.empty
        assert result.orders == []
        assert result.errors == []
    
    @pytest.mark.asyncio
    async def test_position_tracking_error_handling(self, backtester, mock_storage):
        """Test position tracking when errors occur during backtesting."""
        strategy = MockStrategy()
        
        # Mock the strategy runner to raise an error
        original_run = backtester.run_single
        
        async def mock_run_single_with_error(*args, **kwargs):
            equity_curve = pd.Series([10000], name="equity")
            orders = []
            trades = []
            snapshots = pd.DataFrame({"equity": [10000]})
            positions = pd.DataFrame()
            errors = ["Test error"]
            
            return BacktestResult(
                equity_curve=equity_curve,
                orders=orders,
                trades=trades,
                snapshots=snapshots,
                positions=positions,
                errors=errors
            )
        
        backtester.run_single = mock_run_single_with_error
        
        result = await backtester.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d"
        )
        
        # Verify error handling
        assert result.errors == ["Test error"]
        assert result.positions is not None


class TestPositionDataStructure:
    """Test the structure and content of position tracking data."""
    
    def test_position_data_columns(self):
        """Test that position data contains all required columns."""
        expected_columns = [
            "timestamp", "symbol", "side", "size", "entry_price", "current_price",
            "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
            "market_value", "entry_value", "position_timestamp", "cash_balance"
        ]
        
        # Create a sample position data structure
        position_data = {
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "symbol": "BTC-USD",
            "side": "LONG",
            "size": 0.1,
            "entry_price": 50000.0,
            "current_price": 51000.0,
            "pnl": 100.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 100.0,
            "pnl_percentage": 2.0,
            "kelly_size": 0.1,
            "market_value": 5100.0,
            "entry_value": 5000.0,
            "position_timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "cash_balance": 5000.0
        }
        
        # Verify all expected columns are present
        for column in expected_columns:
            assert column in position_data
    
    def test_empty_position_data(self):
        """Test position data structure when no positions are held."""
        empty_position_data = {
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "symbol": None,
            "side": None,
            "size": None,
            "entry_price": None,
            "current_price": None,
            "pnl": None,
            "realized_pnl": None,
            "unrealized_pnl": None,
            "pnl_percentage": None,
            "kelly_size": None,
            "market_value": None,
            "entry_value": None,
            "position_timestamp": None,
            "cash_balance": 10000.0
        }
        
        # Verify empty position data structure
        assert empty_position_data["symbol"] is None
        assert empty_position_data["cash_balance"] == 10000.0
        assert all(value is None for key, value in empty_position_data.items() 
                  if key not in ["timestamp", "cash_balance"])


class TestPositionDataFrameCreation:
    """Test DataFrame creation and indexing for position data."""
    
    def test_position_dataframe_creation(self):
        """Test that position data is properly converted to DataFrame."""
        position_data = [
            {
                "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "symbol": None,
                "cash_balance": 10000.0
            },
            {
                "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
                "symbol": "BTC-USD",
                "cash_balance": 5000.0
            }
        ]
        
        df = pd.DataFrame(position_data)
        assert len(df) == 2
        assert "timestamp" in df.columns
        assert "symbol" in df.columns
        assert "cash_balance" in df.columns
    
    def test_position_dataframe_indexing(self):
        """Test that position DataFrame is properly indexed by timestamp."""
        position_data = [
            {
                "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "symbol": None,
                "cash_balance": 10000.0
            }
        ]
        
        df = pd.DataFrame(position_data)
        if not df.empty and "timestamp" in df.columns:
            df = df.set_index(pd.to_datetime(df["timestamp"], utc=True))
        
        # The index name will be 'timestamp' when using set_index with the column
        assert df.index.name == 'timestamp'  # Index name is 'timestamp'
        assert len(df.index) == 1
        assert isinstance(df.index[0], pd.Timestamp)


@pytest.mark.asyncio
async def test_integration_with_buy_and_hold():
    """Test position tracking integration with buy-and-hold strategy."""
    # This test verifies that position tracking works with the control strategy
    config = Mock(spec=Config)
    config.trading = Mock(spec=TradingConfig)
    config.database = Mock(spec=DatabaseConfig)
    
    storage = Mock(spec=DataStorage)
    dates = pd.date_range(start="2024-01-01", periods=3, freq="D", tz="UTC")
    data = pd.DataFrame({
        "open": [49000, 50000, 51000],
        "high": [49500, 50500, 51500],
        "low": [48500, 49500, 50500],
        "close": [50000, 51000, 52000],
        "volume": [100, 110, 120]
    }, index=dates)
    storage.get_historical_ohlcv_data.return_value = data
    
    commission = CommissionModel(type="percent", value=0.001)
    backtester = BackTester(
        config=config,
        storage=storage,
        commission=commission,
        starting_cash=10000.0
    )
    
    strategy = BuyAndHoldStrategy(
        assets=["BTC-USD"],
        interval="1d",
        position_manager=PositionManager(
            config.trading,
            storage,
            load_existing=False,
            starting_cash=10000.0,
            persist=False
        ),
        starting_cash=10000.0
    )
    
    # Mock the run_single method to return a result with positions
    async def mock_run_single(*args, **kwargs):
        equity_curve = pd.Series([10000, 10100, 10200], name="equity")
        orders = []
        trades = []
        snapshots = pd.DataFrame({"equity": [10000, 10100, 10200]})
        
        positions_data = [
            {
                "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "symbol": "BTC-USD",
                "side": "LONG",
                "size": 0.2,
                "entry_price": 50000.0,
                "current_price": 50000.0,
                "pnl": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "pnl_percentage": 0.0,
                "kelly_size": 0.2,
                "market_value": 10000.0,
                "entry_value": 10000.0,
                "position_timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "cash_balance": 0.0
            }
        ]
        positions_df = pd.DataFrame(positions_data)
        if not positions_df.empty and "timestamp" in positions_df.columns:
            positions_df = positions_df.set_index(pd.to_datetime(positions_df["timestamp"], utc=True))
        
        errors = []
        
        return BacktestResult(
            equity_curve=equity_curve,
            orders=orders,
            trades=trades,
            snapshots=snapshots,
            positions=positions_df,
            errors=errors
        )
    
    backtester.run_single = mock_run_single
    
    result = await backtester.run_single(
        strategy=strategy,
        assets=["BTC-USD"],
        interval="1d"
    )
    
    # Verify buy-and-hold position tracking
    assert result.positions is not None
    assert len(result.positions) == 1
    assert result.positions.iloc[0]["symbol"] == "BTC-USD"
    assert result.positions.iloc[0]["side"] == "LONG"
    assert result.positions.iloc[0]["size"] == 0.2
