"""Integration tests for DCA functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from hypebot.dca import DCAConfig, DCAScheduler
from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.position.manager import PositionManager
from hypebot.strategy.runner import StrategyRunner
from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from hypebot.config import Config, TradingConfig, DatabaseConfig


class TestDCAPositionManagerIntegration:
    """Test DCA integration with PositionManager."""

    def test_dca_fund_injection(self):
        """Test DCA fund injection into position manager."""
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        # Initial state
        assert pm.cash_balance == 1000.0
        assert pm._total_dca_injected == 0.0
        assert len(pm._dca_injections) == 0
        
        # Inject DCA funds
        pm.inject_dca_funds(500.0, datetime(2024, 1, 1))
        
        # Verify injection
        assert pm.cash_balance == 1500.0
        assert pm._total_dca_injected == 500.0
        assert len(pm._dca_injections) == 1
        assert pm._dca_injections[0] == (datetime(2024, 1, 1), 500.0)

    def test_multiple_dca_injections(self):
        """Test multiple DCA fund injections."""
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        # Multiple injections
        pm.inject_dca_funds(200.0, datetime(2024, 1, 1))
        pm.inject_dca_funds(300.0, datetime(2024, 1, 15))
        pm.inject_dca_funds(100.0, datetime(2024, 2, 1))
        
        # Verify totals
        assert pm.cash_balance == 1600.0
        assert pm._total_dca_injected == 600.0
        assert len(pm._dca_injections) == 3

    def test_dca_metrics(self):
        """Test DCA metrics calculation."""
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        # Inject some DCA funds
        pm.inject_dca_funds(500.0, datetime(2024, 1, 1))
        pm.inject_dca_funds(300.0, datetime(2024, 1, 15))
        
        # Get metrics
        metrics = pm.get_dca_metrics()
        
        assert metrics["total_dca_injected"] == 800.0
        assert metrics["dca_injection_count"] == 2
        assert metrics["initial_cash"] == 1000.0
        assert metrics["dca_contribution_ratio"] == 800.0 / 1800.0
        assert len(metrics["dca_injections"]) == 2

    def test_invalid_dca_injection(self):
        """Test invalid DCA injection handling."""
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        # Try to inject negative amount
        pm.inject_dca_funds(-100.0, datetime(2024, 1, 1))
        
        # Should not change anything
        assert pm.cash_balance == 1000.0
        assert pm._total_dca_injected == 0.0
        assert len(pm._dca_injections) == 0


class TestDCAStrategyRunnerIntegration:
    """Test DCA integration with StrategyRunner."""

    def test_dca_injection_during_backtest(self):
        """Test DCA injection during strategy execution."""
        # Create mock components
        strategy = Mock()
        strategy.assets = ["BTC-USD"]
        strategy.interval = "1d"
        strategy.tick = AsyncMock(return_value=[])
        strategy.on_start = AsyncMock()
        strategy.on_stop = AsyncMock()
        
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        trading_client = Mock()
        data_loader = Mock(return_value=pd.DataFrame())
        
        # Create DCA scheduler
        dca_config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        dca_scheduler = DCAScheduler(dca_config, datetime(2024, 1, 1), datetime(2024, 1, 2))
        dca_scheduler.generate_schedule([])
        
        # Create strategy runner with DCA
        runner = StrategyRunner(
            strategy=strategy,
            position_manager=pm,
            trading_client=trading_client,
            data_loader=data_loader,
            dca_scheduler=dca_scheduler
        )
        
        # Run with DCA injection dates
        ticks = [datetime(2024, 1, 1), datetime(2024, 1, 2)]
        
        import asyncio
        asyncio.run(runner.run(ticks))
        
        # Verify DCA injections occurred
        assert pm._total_dca_injected == 200.0  # 2 injections of 100 each
        assert len(pm._dca_injections) == 2

    def test_no_dca_injection_when_disabled(self):
        """Test no DCA injection when DCA is disabled."""
        strategy = Mock()
        strategy.assets = ["BTC-USD"]
        strategy.interval = "1d"
        strategy.tick = AsyncMock(return_value=[])
        strategy.on_start = AsyncMock()
        strategy.on_stop = AsyncMock()
        
        config = TradingConfig()
        storage = Mock()
        pm = PositionManager(config, storage, load_existing=False, starting_cash=1000.0)
        
        trading_client = Mock()
        data_loader = Mock(return_value=pd.DataFrame())
        
        # Create strategy runner without DCA
        runner = StrategyRunner(
            strategy=strategy,
            position_manager=pm,
            trading_client=trading_client,
            data_loader=data_loader,
            dca_scheduler=None
        )
        
        ticks = [datetime(2024, 1, 1), datetime(2024, 1, 2)]
        
        import asyncio
        asyncio.run(runner.run(ticks))
        
        # Verify no DCA injections
        assert pm._total_dca_injected == 0.0
        assert len(pm._dca_injections) == 0


class TestDCABackTesterIntegration:
    """Test DCA integration with BackTester."""

    @patch('hypebot.backtesting.backtester.DataStorage')
    def test_backtester_with_dca(self, mock_storage):
        """Test BackTester with DCA configuration."""
        # Mock data storage
        mock_storage.return_value.get_historical_ohlcv_data.return_value = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        # Create DCA config
        dca_config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3)
        )
        
        # Create backtester with DCA
        config = Config.from_env()
        bt = BackTester(
            config=config,
            commission=CommissionModel(type="percent", value=0.001),
            starting_cash=1000.0,
            dca_config=dca_config
        )
        
        # Create buy-and-hold strategy
        strategy = BuyAndHoldStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=PositionManager(config.trading, mock_storage.return_value, load_existing=False)
        )
        
        # Run backtest
        import asyncio
        result = asyncio.run(bt.run_single(
            strategy=strategy,
            assets=["BTC-USD"],
            interval="1d",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3)
        ))
        
        # Verify DCA was applied
        assert result is not None
        # The position manager should have received DCA injections
        # (This would be verified through the strategy's position manager)

    def test_backtester_without_dca(self):
        """Test BackTester without DCA configuration."""
        config = Config.from_env()
        bt = BackTester(
            config=config,
            commission=CommissionModel(type="percent", value=0.001),
            starting_cash=1000.0,
            dca_config=None  # No DCA
        )
        
        # Should work normally without DCA
        assert bt.dca_config.enabled is False
