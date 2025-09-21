"""Tests for RSI calculator."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.indicators.models import TradingSignal


class TestRSICalculator:
    """Test cases for RSI calculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rsi_calculator = RSICalculator(period=14, oversold_threshold=30, overbought_threshold=70)
        
        # Create test data with known RSI values
        self.test_data = self._create_test_data()
    
    def _create_test_data(self):
        """Create test data with known price movements."""
        dates = [datetime.utcnow() - timedelta(days=i) for i in range(30, 0, -1)]
        
        # Create price data that will generate known RSI values
        prices = [100.0]
        for i in range(1, 30):
            # Create alternating up/down pattern for testing
            if i % 2 == 0:
                prices.append(prices[-1] * 1.02)  # 2% up
            else:
                prices.append(prices[-1] * 0.98)  # 2% down
        
        return pd.DataFrame({
            'symbol': ['BTC'] * 30,
            'timestamp': dates,
            'price': prices
        })
    
    def test_rsi_calculation(self):
        """Test RSI calculation with known data."""
        results = self.rsi_calculator.calculate(self.test_data)
        
        assert len(results) > 0
        assert all(0 <= result.value <= 100 for result in results)
        assert all(result.indicator_name == "RSI" for result in results)
    
    def test_oversold_signal(self):
        """Test oversold signal generation."""
        # Create data that will generate low RSI
        low_rsi_data = self._create_declining_data()
        results = self.rsi_calculator.calculate(low_rsi_data)
        
        # Check for oversold signals
        buy_signals = [r for r in results if r.signal == "BUY"]
        assert len(buy_signals) > 0
    
    def test_overbought_signal(self):
        """Test overbought signal generation."""
        # Create data that will generate high RSI
        high_rsi_data = self._create_rising_data()
        results = self.rsi_calculator.calculate(high_rsi_data)
        
        # Check for overbought signals
        sell_signals = [r for r in results if r.signal == "SELL"]
        assert len(sell_signals) > 0
    
    def _create_declining_data(self):
        """Create data with declining prices for oversold test."""
        dates = [datetime.utcnow() - timedelta(days=i) for i in range(20, 0, -1)]
        prices = [100.0]
        
        # Create declining trend
        for i in range(1, 20):
            prices.append(prices[-1] * 0.95)  # 5% down each day
        
        return pd.DataFrame({
            'symbol': ['BTC'] * 20,
            'timestamp': dates,
            'price': prices
        })
    
    def _create_rising_data(self):
        """Create data with rising prices for overbought test."""
        dates = [datetime.utcnow() - timedelta(days=i) for i in range(20, 0, -1)]
        prices = [100.0]
        
        # Create rising trend
        for i in range(1, 20):
            prices.append(prices[-1] * 1.05)  # 5% up each day
        
        return pd.DataFrame({
            'symbol': ['BTC'] * 20,
            'timestamp': dates,
            'price': prices
        })
    
    def test_signal_generation(self):
        """Test signal generation logic."""
        # Test oversold signal
        signal = self.rsi_calculator.generate_signal(25.0, 35.0)
        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.strength > 0
        
        # Test overbought signal
        signal = self.rsi_calculator.generate_signal(75.0, 65.0)
        assert signal is not None
        assert signal.signal_type == "SELL"
        assert signal.strength > 0
        
        # Test neutral signal
        signal = self.rsi_calculator.generate_signal(50.0, 45.0)
        assert signal is None
    
    def test_signal_strength_calculation(self):
        """Test signal strength calculation."""
        # Test oversold strength
        strength = self.rsi_calculator.calculate_signal_strength(20.0, 30.0, 70.0)
        assert 0 < strength <= 1.0
        
        # Test overbought strength
        strength = self.rsi_calculator.calculate_signal_strength(80.0, 30.0, 70.0)
        assert 0 < strength <= 1.0
        
        # Test neutral strength
        strength = self.rsi_calculator.calculate_signal_strength(50.0, 30.0, 70.0)
        assert strength == 0.0
    
    def test_rsi_levels(self):
        """Test RSI level checks."""
        assert self.rsi_calculator.is_oversold(25.0)
        assert not self.rsi_calculator.is_oversold(35.0)
        
        assert self.rsi_calculator.is_overbought(75.0)
        assert not self.rsi_calculator.is_overbought(65.0)
        
        assert self.rsi_calculator.is_neutral(50.0)
        assert not self.rsi_calculator.is_neutral(25.0)
        assert not self.rsi_calculator.is_neutral(75.0)
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        small_data = self.test_data.head(5)  # Less than required period
        results = self.rsi_calculator.calculate(small_data)
        assert len(results) == 0
    
    def test_empty_data(self):
        """Test behavior with empty data."""
        empty_data = pd.DataFrame(columns=['symbol', 'timestamp', 'price'])
        results = self.rsi_calculator.calculate(empty_data)
        assert len(results) == 0
