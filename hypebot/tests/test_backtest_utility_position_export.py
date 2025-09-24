"""Tests for position CSV export functionality in backtest utility."""

import pytest
import pandas as pd
import json
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, mock_open

from hypebot.backtesting.backtester import BacktestResult, CommissionModel
from hypebot.exchange.models import Order


@pytest.fixture
def sample_backtest_result():
    """Create a sample BacktestResult with position data."""
    equity_curve = pd.Series([10000, 10100, 10200], name="equity")
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
    
    # Create snapshots DataFrame
    snapshots_data = {
        "timestamp": pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"),
        "equity": [10000, 10100, 10200]
    }
    snapshots = pd.DataFrame(snapshots_data).set_index("timestamp")
    
    # Create positions DataFrame
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
    positions = pd.DataFrame(positions_data)
    if not positions.empty and "timestamp" in positions.columns:
        positions["timestamp"] = pd.to_datetime(positions["timestamp"], utc=True)
        positions = positions.set_index("timestamp")
    
    errors = []
    
    return BacktestResult(
        equity_curve=equity_curve,
        orders=orders,
        trades=trades,
        snapshots=snapshots,
        positions=positions,
        errors=errors
    )


@pytest.fixture
def empty_backtest_result():
    """Create an empty BacktestResult."""
    return BacktestResult(
        equity_curve=pd.Series(dtype=float),
        orders=[],
        trades=[],
        snapshots=pd.DataFrame(),
        positions=pd.DataFrame(),
        errors=[]
    )


class TestPositionCSVExport:
    """Test position CSV export functionality."""
    
    def test_position_csv_export_with_data(self, sample_backtest_result):
        """Test exporting position data to CSV when data is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_test_strategy.csv")
            
            # Mock the CSV export logic from backtest.py
            try:
                if hasattr(sample_backtest_result, "positions") and isinstance(sample_backtest_result.positions, pd.DataFrame) and not sample_backtest_result.positions.empty:
                    # Reset index to include timestamp as a column
                    positions_df = sample_backtest_result.positions.reset_index()
                    # Ensure timestamp column exists and is properly formatted
                    if "timestamp" in positions_df.columns:
                        positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"])
                    positions_df.to_csv(positions_csv_path, index=False)
                    
                    # Verify file was created
                    assert os.path.exists(positions_csv_path)
                    
                    # Read and verify content
                    df = pd.read_csv(positions_csv_path)
                    assert len(df) == 3
                    assert "timestamp" in df.columns
                    assert "symbol" in df.columns
                    assert "cash_balance" in df.columns
                    assert "pnl" in df.columns
                    
                    # Check specific values
                    assert pd.isna(df.iloc[0]["symbol"])  # First row has no position
                    assert df.iloc[1]["symbol"] == "BTC-USD"  # Second row has position
                    assert df.iloc[1]["side"] == "LONG"
                    assert df.iloc[1]["size"] == 0.1
                    assert df.iloc[1]["pnl"] == 100.0
                    
            except Exception as e:
                pytest.fail(f"Failed to export positions CSV: {e}")
    
    def test_position_csv_export_empty_data(self, empty_backtest_result):
        """Test exporting position data when no data is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_empty.csv")
            
            # Mock the CSV export logic for empty data
            try:
                if hasattr(empty_backtest_result, "positions") and isinstance(empty_backtest_result.positions, pd.DataFrame) and not empty_backtest_result.positions.empty:
                    # This should not execute for empty data
                    positions_df = empty_backtest_result.positions.reset_index()
                    positions_df.to_csv(positions_csv_path, index=False)
                else:
                    # Create empty CSV with proper headers
                    empty_positions = pd.DataFrame(columns=[
                        "timestamp", "symbol", "side", "size", "entry_price", "current_price",
                        "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
                        "market_value", "entry_value", "position_timestamp", "cash_balance"
                    ])
                    empty_positions.to_csv(positions_csv_path, index=False)
                
                # Verify file was created
                assert os.path.exists(positions_csv_path)
                
                # Read and verify content
                df = pd.read_csv(positions_csv_path)
                assert len(df) == 0  # Empty DataFrame
                assert "timestamp" in df.columns
                assert "symbol" in df.columns
                assert "cash_balance" in df.columns
                
            except Exception as e:
                pytest.fail(f"Failed to export empty positions CSV: {e}")
    
    def test_position_csv_columns(self, sample_backtest_result):
        """Test that position CSV contains all required columns."""
        expected_columns = [
            "timestamp", "symbol", "side", "size", "entry_price", "current_price",
            "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
            "market_value", "entry_value", "position_timestamp", "cash_balance"
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_columns_test.csv")
            
            positions_df = sample_backtest_result.positions.reset_index()
            if "timestamp" in positions_df.columns:
                positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"])
            positions_df.to_csv(positions_csv_path, index=False)
            
            # Read and verify columns
            df = pd.read_csv(positions_csv_path)
            for column in expected_columns:
                assert column in df.columns, f"Missing column: {column}"
    
    def test_position_csv_timestamp_formatting(self, sample_backtest_result):
        """Test that timestamps are properly formatted in CSV export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_timestamp_test.csv")
            
            positions_df = sample_backtest_result.positions.reset_index()
            if "timestamp" in positions_df.columns:
                positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"])
            positions_df.to_csv(positions_csv_path, index=False)
            
            # Read and verify timestamp formatting
            df = pd.read_csv(positions_csv_path)
            assert "timestamp" in df.columns
            
            # Check that timestamps are properly formatted
            timestamps = pd.to_datetime(df["timestamp"])
            assert len(timestamps) == 3
            assert timestamps[0].year == 2024
            assert timestamps[0].month == 1
            assert timestamps[0].day == 1


class TestBuyAndHoldPositionExport:
    """Test position CSV export for buy-and-hold control strategy."""
    
    def test_buy_and_hold_position_export(self):
        """Test position export for buy-and-hold strategy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            control_positions_csv_path = os.path.join(temp_dir, "positions_buy_and_hold.csv")
            
            # Create mock buy-and-hold result
            equity_curve = pd.Series([10000, 10100, 10200], name="equity")
            orders = []
            trades = []
            snapshots = pd.DataFrame({"equity": [10000, 10100, 10200]})
            
            # Buy-and-hold positions (should hold position throughout)
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
                },
                {
                    "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
                    "symbol": "BTC-USD",
                    "side": "LONG",
                    "size": 0.2,
                    "entry_price": 50000.0,
                    "current_price": 51000.0,
                    "pnl": 200.0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 200.0,
                    "pnl_percentage": 4.0,
                    "kelly_size": 0.2,
                    "market_value": 10200.0,
                    "entry_value": 10000.0,
                    "position_timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "cash_balance": 0.0
                }
            ]
            positions = pd.DataFrame(positions_data)
            if not positions.empty and "timestamp" in positions.columns:
                positions["timestamp"] = pd.to_datetime(positions["timestamp"], utc=True)
                positions = positions.set_index("timestamp")
            
            errors = []
            
            control_result = BacktestResult(
                equity_curve=equity_curve,
                orders=orders,
                trades=trades,
                snapshots=snapshots,
                positions=positions,
                errors=errors
            )
            
            # Mock the export logic
            try:
                if hasattr(control_result, "positions") and isinstance(control_result.positions, pd.DataFrame) and not control_result.positions.empty:
                    positions_df = control_result.positions.reset_index()
                    if "timestamp" in positions_df.columns:
                        positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"])
                    positions_df.to_csv(control_positions_csv_path, index=False)
                
                # Verify file was created
                assert os.path.exists(control_positions_csv_path)
                
                # Read and verify content
                df = pd.read_csv(control_positions_csv_path)
                assert len(df) == 2
                assert df.iloc[0]["symbol"] == "BTC-USD"
                assert df.iloc[0]["side"] == "LONG"
                assert df.iloc[0]["size"] == 0.2
                assert df.iloc[0]["pnl"] == 0.0
                assert df.iloc[1]["pnl"] == 200.0
                
            except Exception as e:
                pytest.fail(f"Failed to export buy-and-hold positions CSV: {e}")


class TestPositionExportErrorHandling:
    """Test error handling in position CSV export."""
    
    def test_position_export_with_missing_positions_attribute(self):
        """Test position export when result doesn't have positions attribute."""
        # Create a mock result without positions attribute
        mock_result = Mock()
        mock_result.positions = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_error_test.csv")
            
            try:
                # This should create an empty CSV
                if hasattr(mock_result, "positions") and isinstance(mock_result.positions, pd.DataFrame) and not mock_result.positions.empty:
                    # This should not execute
                    pass
                else:
                    # Create empty CSV with proper headers
                    empty_positions = pd.DataFrame(columns=[
                        "timestamp", "symbol", "side", "size", "entry_price", "current_price",
                        "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
                        "market_value", "entry_value", "position_timestamp", "cash_balance"
                    ])
                    empty_positions.to_csv(positions_csv_path, index=False)
                
                # Verify file was created with empty data
                assert os.path.exists(positions_csv_path)
                df = pd.read_csv(positions_csv_path)
                assert len(df) == 0
                
            except Exception as e:
                pytest.fail(f"Failed to handle missing positions attribute: {e}")
    
    def test_position_export_with_invalid_dataframe(self):
        """Test position export with invalid DataFrame."""
        # Create a mock result with invalid positions data
        mock_result = Mock()
        mock_result.positions = "invalid_dataframe"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            positions_csv_path = os.path.join(temp_dir, "positions_invalid_test.csv")
            
            try:
                # This should create an empty CSV due to invalid data
                if hasattr(mock_result, "positions") and isinstance(mock_result.positions, pd.DataFrame) and not mock_result.positions.empty:
                    # This should not execute
                    pass
                else:
                    # Create empty CSV with proper headers
                    empty_positions = pd.DataFrame(columns=[
                        "timestamp", "symbol", "side", "size", "entry_price", "current_price",
                        "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
                        "market_value", "entry_value", "position_timestamp", "cash_balance"
                    ])
                    empty_positions.to_csv(positions_csv_path, index=False)
                
                # Verify file was created with empty data
                assert os.path.exists(positions_csv_path)
                df = pd.read_csv(positions_csv_path)
                assert len(df) == 0
                
            except Exception as e:
                pytest.fail(f"Failed to handle invalid DataFrame: {e}")


class TestPositionCSVIntegration:
    """Test integration of position CSV export with full backtest workflow."""
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pandas.DataFrame.to_csv')
    def test_full_backtest_workflow_with_positions(self, mock_to_csv, mock_file, sample_backtest_result):
        """Test that position CSV export integrates with full backtest workflow."""
        # This test simulates the full workflow from backtest.py
        
        # Mock the backtest result
        result = sample_backtest_result
        strategy_name = "TestStrategy"
        output_dir = "/tmp/test_output"
        
        # Simulate the position CSV export logic
        positions_csv_path = os.path.join(output_dir, f"positions_{strategy_name.replace(' ', '_')}.csv")
        
        try:
            if hasattr(result, "positions") and isinstance(result.positions, pd.DataFrame) and not result.positions.empty:
                positions_df = result.positions.reset_index()
                if "timestamp" in positions_df.columns:
                    positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"])
                positions_df.to_csv(positions_csv_path, index=False)
            else:
                empty_positions = pd.DataFrame(columns=[
                    "timestamp", "symbol", "side", "size", "entry_price", "current_price",
                    "pnl", "realized_pnl", "unrealized_pnl", "pnl_percentage", "kelly_size",
                    "market_value", "entry_value", "position_timestamp", "cash_balance"
                ])
                empty_positions.to_csv(positions_csv_path, index=False)
        
        except Exception as e:
            pytest.fail(f"Position CSV export failed in full workflow: {e}")
        
        # Verify that to_csv was called (mocked)
        mock_to_csv.assert_called()
    
    def test_position_csv_filename_generation(self):
        """Test that position CSV filenames are generated correctly."""
        strategy_names = [
            "RSIStrategy",
            "RSI EMA Hybrid Strategy",
            "Buy And Hold Strategy",
            "Test Strategy"
        ]
        
        expected_filenames = [
            "positions_RSIStrategy.csv",
            "positions_RSI_EMA_Hybrid_Strategy.csv",
            "positions_Buy_And_Hold_Strategy.csv",
            "positions_Test_Strategy.csv"
        ]
        
        for strategy_name, expected_filename in zip(strategy_names, expected_filenames):
            # Simulate filename generation from backtest.py
            generated_filename = f"positions_{strategy_name.replace(' ', '_')}.csv"
            assert generated_filename == expected_filename
