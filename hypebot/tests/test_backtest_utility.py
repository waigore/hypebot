"""Tests for backtest.py utility."""

import pytest
import tempfile
import os
import json
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Import the backtest utility functions
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from backtest import (
    _parse_datetime,
    _parse_commission,
    _load_yaml_config,
    _resolve_args_with_config,
    _build_strategy,
    _print_metrics,
    main
)


class TestBacktestUtility:
    """Test cases for backtest.py utility functions."""

    def test_parse_datetime_valid_formats(self):
        """Test parsing valid datetime formats."""
        # Test YYYY-MM-DD format
        dt1 = _parse_datetime("2024-01-01")
        assert dt1 == datetime(2024, 1, 1)
        
        # Test YYYY-MM-DD HH:MM:SS format
        dt2 = _parse_datetime("2024-01-01 12:30:45")
        assert dt2 == datetime(2024, 1, 1, 12, 30, 45)
        
        # Test None input
        dt3 = _parse_datetime(None)
        assert dt3 is None

    def test_parse_datetime_invalid_format(self):
        """Test parsing invalid datetime formats."""
        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_datetime("invalid-date")

    def test_parse_commission_valid_formats(self):
        """Test parsing valid commission formats."""
        # Test fixed commission
        comm1 = _parse_commission("fixed:0.5")
        assert comm1.type == "fixed"
        assert comm1.value == 0.5
        
        # Test percent commission
        comm2 = _parse_commission("percent:0.001")
        assert comm2.type == "percent"
        assert comm2.value == 0.001
        
        # Test default
        comm3 = _parse_commission(None)
        assert comm3.type == "percent"
        assert comm3.value == 0.001

    def test_parse_commission_invalid_format(self):
        """Test parsing invalid commission formats."""
        with pytest.raises(ValueError, match="--commission must be like"):
            _parse_commission("invalid:format")

    def test_load_yaml_config_valid(self):
        """Test loading valid YAML config."""
        config_data = {
            "backtest": {
                "assets": ["BTC-USD"],
                "strategy": "rsi",
                "interval": "1d"
            },
            "strategy_params": {
                "rsi": {
                    "period": 14,
                    "oversold": 30
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            result = _load_yaml_config(temp_path)
            assert result == config_data
        finally:
            os.unlink(temp_path)

    def test_load_yaml_config_missing_pyyaml(self):
        """Test loading YAML config when PyYAML is not available."""
        with patch('backtest.yaml', None):
            with pytest.raises(RuntimeError, match="PyYAML is required"):
                _load_yaml_config("test.yaml")

    def test_resolve_args_with_config(self):
        """Test resolving CLI args with YAML config."""
        # Mock argparse.Namespace
        args = Mock()
        args.assets = None
        args.strategy = None
        args.interval = "1d"
        args.start_date = None
        args.end_date = None
        args.starting_cash = 10000.0
        args.commission = None
        args.output_dir = "./backtest_results"
        args.no_plot = False
        args.debug = False
        
        config = {
            "backtest": {
                "assets": ["BTC-USD", "ETH-USD"],
                "strategy": "rsi",
                "interval": "4h",
                "starting_cash": 20000.0
            },
            "strategy_params": {
                "rsi": {"period": 21}
            }
        }
        
        backtest_cfg, strategy_params = _resolve_args_with_config(args, config)
        
        # Should merge CLI args with config
        assert backtest_cfg["assets"] == ["BTC-USD", "ETH-USD"]
        assert backtest_cfg["strategy"] == "rsi"
        assert backtest_cfg["interval"] == "1d"  # CLI takes precedence
        assert backtest_cfg["starting_cash"] == 10000.0  # CLI value used (not overridden by config)
        assert strategy_params == {"rsi": {"period": 21}}

    @patch('backtest.DataStorage')
    @patch('backtest.PositionManager')
    @patch('backtest.RSICalculator')
    @patch('backtest.KellyCriterion')
    @patch('backtest.Config')
    def test_build_strategy_rsi(self, mock_config_class, mock_kelly, mock_rsi, mock_pm, mock_storage):
        """Test building RSI strategy."""
        mock_config = Mock()
        mock_config.trading.rsi_period = 14
        mock_config.trading.rsi_oversold = 30
        mock_config.trading.rsi_overbought = 70
        mock_config_class.from_env.return_value = mock_config
        
        strategy = _build_strategy("rsi", mock_config, {}, ["BTC-USD"], "1d")
        
        from hypebot.strategy.rsi_strategy import RSIStrategy
        assert isinstance(strategy, RSIStrategy)
        mock_rsi.assert_called_once()
        mock_pm.assert_called_once()

    @patch('backtest.DataStorage')
    @patch('backtest.PositionManager')
    @patch('backtest.Config')
    def test_build_strategy_buy_and_hold(self, mock_config_class, mock_pm, mock_storage):
        """Test building BuyAndHold strategy."""
        mock_config = Mock()
        mock_config_class.from_env.return_value = mock_config
        
        strategy = _build_strategy("buy_and_hold", mock_config, {}, ["BTC-USD"], "1d")
        
        from hypebot.strategy.buy_and_hold_strategy import BuyAndHoldStrategy
        assert isinstance(strategy, BuyAndHoldStrategy)

    def test_build_strategy_unsupported(self):
        """Test building unsupported strategy."""
        mock_config = Mock()
        
        with pytest.raises(ValueError, match="Unsupported strategy"):
            _build_strategy("unsupported", mock_config, {}, ["BTC-USD"], "1d")

    def test_print_metrics(self, capsys):
        """Test printing metrics."""
        metrics = {
            "return_pct": 0.15,
            "cagr": 0.12,
            "vol_annual": 0.25,
            "sharpe": 1.5,
            "sortino": 1.8,
            "max_drawdown": 0.08
        }
        
        _print_metrics("Test Strategy", metrics)
        
        captured = capsys.readouterr()
        assert "Test Strategy" in captured.out
        assert "15.00%" in captured.out
        assert "12.00%" in captured.out
        assert "1.50" in captured.out

    @patch('backtest.plot_equity_curves')
    @patch('backtest.compute_metrics')
    @patch('backtest.BackTester')
    @patch('backtest.Config')
    @patch('backtest.DataStorage')
    @patch('backtest.PositionManager')
    @patch('backtest.RSICalculator')
    @patch('backtest.KellyCriterion')
    def test_main_rsi_strategy(self, mock_kelly, mock_rsi, mock_pm, mock_storage, mock_config_class, mock_backtester_class, mock_metrics, mock_plot):
        """Test main function with RSI strategy."""
        # Mock configuration
        mock_config = Mock()
        mock_config.trading.risk_free_rate = 0.02
        mock_config.trading.rsi_period = 14
        mock_config.trading.rsi_oversold = 30
        mock_config.trading.rsi_overbought = 70
        mock_config.trading.kelly_lookback_period = 30
        mock_config.trading.max_position_size = 0.1
        mock_config.trading.min_position_size = 0.001
        mock_config.database = Mock()
        mock_config.database.data_dir = "data"
        mock_config.database.historical_data_dir = "historical"
        mock_config_class.from_env.return_value = mock_config
        
        # Mock backtester
        mock_backtester = Mock()
        mock_backtester_class.return_value = mock_backtester
        
        # Mock backtest result
        mock_result = Mock()
        mock_result.equity_curve = pd.Series([10000, 10500, 11000], 
                                           index=pd.date_range("2024-01-01", periods=3, freq="D"))
        mock_result.orders = []
        mock_result.snapshots = Mock()
        mock_result.snapshots.attrs = {}
        
        # Mock async run_with_control
        async def mock_run_with_control():
            return {"RSIStrategy": mock_result}

        mock_backtester.run_with_control = Mock(return_value=mock_run_with_control())
        
        # Mock metrics
        mock_metrics.return_value = {"return_pct": 0.1, "cagr": 0.08}
        
        # Mock plot
        mock_plot.return_value = None
        
        # Test with RSI strategy
        with tempfile.TemporaryDirectory() as temp_dir:
            result = main([
                "--assets", "BTC-USD",
                "--strategy", "rsi",
                "--interval", "1d",
                "--output-dir", temp_dir,
                "--no-plot"
            ])
        
        assert result == 0
        mock_backtester.run_with_control.assert_called_once()

    @patch('backtest.plot_equity_curves')
    @patch('backtest.compute_metrics')
    @patch('backtest.BackTester')
    @patch('backtest.Config')
    @patch('backtest.DataStorage')
    @patch('backtest.PositionManager')
    def test_main_buy_and_hold_strategy(self, mock_pm, mock_storage, mock_config_class, mock_backtester_class, mock_metrics, mock_plot):
        """Test main function with BuyAndHold strategy."""
        # Mock configuration
        mock_config = Mock()
        mock_config.trading.risk_free_rate = 0.02
        mock_config.database = Mock()
        mock_config.database.data_dir = "data"
        mock_config.database.historical_data_dir = "historical"
        mock_config_class.from_env.return_value = mock_config
        
        # Mock backtester
        mock_backtester = Mock()
        mock_backtester_class.return_value = mock_backtester
        
        # Mock backtest result
        mock_result = Mock()
        mock_result.equity_curve = pd.Series([10000, 10500, 11000], 
                                           index=pd.date_range("2024-01-01", periods=3, freq="D"))
        mock_result.orders = []
        mock_result.snapshots = Mock()
        mock_result.snapshots.attrs = {}
        
        # Mock async run_with_control
        async def mock_run_with_control():
            return {"BuyAndHoldStrategy": mock_result}

        mock_backtester.run_with_control = Mock(return_value=mock_run_with_control())
        
        # Mock metrics
        mock_metrics.return_value = {"return_pct": 0.1, "cagr": 0.08}
        
        # Mock plot
        mock_plot.return_value = None
        
        # Test with BuyAndHold strategy
        with tempfile.TemporaryDirectory() as temp_dir:
            result = main([
                "--assets", "BTC-USD",
                "--strategy", "buy_and_hold",
                "--interval", "1d",
                "--output-dir", temp_dir,
                "--no-plot"
            ])
        
        assert result == 0
        mock_backtester.run_with_control.assert_called_once()

    def test_main_missing_required_args(self):
        """Test main function with missing required arguments."""
        result = main([])
        assert result == 2  # Error exit code

    def test_main_invalid_date_format(self):
        """Test main function with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            main([
                "--assets", "BTC-USD",
                "--strategy", "rsi",
                "--start-date", "invalid-date"
            ])

    def test_main_invalid_commission_format(self):
        """Test main function with invalid commission format."""
        with pytest.raises(ValueError, match="--commission must be like"):
            main([
                "--assets", "BTC-USD",
                "--strategy", "rsi",
                "--commission", "invalid:format"
            ])

    @patch('backtest.plot_equity_curves')
    @patch('backtest.compute_metrics')
    @patch('backtest.BackTester')
    @patch('backtest.Config')
    @patch('backtest.DataStorage')
    @patch('backtest.PositionManager')
    def test_main_with_yaml_config(self, mock_pm, mock_storage, mock_config_class, mock_backtester_class, mock_metrics, mock_plot):
        """Test main function with YAML config file."""
        # Create temporary YAML config
        config_data = {
            "backtest": {
                "assets": ["BTC-USD", "ETH-USD"],
                "strategy": "buy_and_hold",
                "interval": "1d",
                "starting_cash": 20000.0
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # Mock configuration
            mock_config = Mock()
            mock_config.trading.risk_free_rate = 0.02
            mock_config.database = Mock()
            mock_config.database.data_dir = "data"
            mock_config.database.historical_data_dir = "historical"
            mock_config_class.from_env.return_value = mock_config
            
            # Mock backtester
            mock_backtester = Mock()
            mock_backtester_class.return_value = mock_backtester
            
            # Mock backtest result
            mock_result = Mock()
            mock_result.equity_curve = pd.Series([20000, 21000], 
                                               index=pd.date_range("2024-01-01", periods=2, freq="D"))
            mock_result.orders = []
            mock_result.snapshots = Mock()
            mock_result.snapshots.attrs = {}
            
            # Mock async run_with_control
            async def mock_run_with_control():
                return {"BuyAndHoldStrategy": mock_result}

            mock_backtester.run_with_control = Mock(return_value=mock_run_with_control())
            
            # Mock metrics
            mock_metrics.return_value = {"return_pct": 0.1, "cagr": 0.08}
            
            # Mock plot
            mock_plot.return_value = None
            
            # Test with config file
            with tempfile.TemporaryDirectory() as temp_dir:
                result = main([
                    "--config", temp_path,
                    "--output-dir", temp_dir,
                    "--no-plot"
                ])
            
            assert result == 0
        finally:
            os.unlink(temp_path)
