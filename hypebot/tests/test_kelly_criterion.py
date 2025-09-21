"""Tests for Kelly Criterion calculator."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from hypebot.position.kelly_criterion import KellyCriterion
from hypebot.config import TradingConfig


class TestKellyCriterion:
    """Test cases for Kelly Criterion calculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TradingConfig(
            max_position_size=0.1,
            min_position_size=0.001,
            kelly_lookback_period=30,
            risk_free_rate=0.02
        )
        self.kelly_criterion = KellyCriterion(self.config)
    
    def test_calculate_kelly_fraction_positive_returns(self):
        """Test Kelly fraction calculation with positive returns."""
        # Create positive returns data
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01, 0.02, -0.005, 0.015])
        
        kelly_fraction = self.kelly_criterion.calculate_kelly_fraction(returns)
        
        assert kelly_fraction > 0
        assert kelly_fraction <= self.config.max_position_size
    
    def test_calculate_kelly_fraction_negative_returns(self):
        """Test Kelly fraction calculation with negative returns."""
        # Create negative returns data
        returns = pd.Series([-0.01, -0.02, -0.01, -0.03, -0.01, -0.02, -0.005, -0.015])
        
        kelly_fraction = self.kelly_criterion.calculate_kelly_fraction(returns)
        
        assert kelly_fraction == 0.0  # Should be 0 for negative expected returns
    
    def test_calculate_kelly_fraction_zero_variance(self):
        """Test Kelly fraction calculation with zero variance."""
        # Create constant returns (zero variance)
        returns = pd.Series([0.01] * 10)
        
        kelly_fraction = self.kelly_criterion.calculate_kelly_fraction(returns)
        
        assert kelly_fraction == 0.0  # Should be 0 for zero variance
    
    def test_calculate_kelly_fraction_insufficient_data(self):
        """Test Kelly fraction calculation with insufficient data."""
        returns = pd.Series([0.01])  # Only one data point
        
        kelly_fraction = self.kelly_criterion.calculate_kelly_fraction(returns)
        
        assert kelly_fraction == 0.0
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        symbol = "BTC"
        current_price = 50000.0
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01, 0.02, -0.005, 0.015])
        signal_strength = 0.8
        confidence = 0.9
        
        position_size = self.kelly_criterion.calculate_position_size(
            symbol=symbol,
            current_price=current_price,
            historical_returns=returns,
            signal_strength=signal_strength,
            confidence=confidence
        )
        
        assert position_size.symbol == symbol
        assert position_size.current_price == current_price
        assert position_size.recommended_size >= 0
        assert position_size.recommended_size <= self.config.max_position_size
        assert position_size.confidence == confidence
        assert position_size.kelly_fraction >= 0
    
    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01, 0.02, -0.005, 0.015])
        position_size = 0.05
        
        risk_metrics = self.kelly_criterion.calculate_risk_metrics(returns, position_size)
        
        assert "volatility" in risk_metrics
        assert "sharpe_ratio" in risk_metrics
        assert "max_drawdown" in risk_metrics
        assert "var_95" in risk_metrics
        assert "expected_return" in risk_metrics
        
        assert risk_metrics["volatility"] >= 0
        assert risk_metrics["max_drawdown"] <= 0  # Drawdown should be negative or zero
    
    def test_determine_risk_level(self):
        """Test risk level determination."""
        # High risk
        risk_level = self.kelly_criterion._determine_risk_level(0.08, 0.9, 0.9)
        assert risk_level == "HIGH"
        
        # Medium risk
        risk_level = self.kelly_criterion._determine_risk_level(0.05, 0.7, 0.8)
        assert risk_level == "MEDIUM"
        
        # Low risk
        risk_level = self.kelly_criterion._determine_risk_level(0.02, 0.5, 0.6)
        assert risk_level == "LOW"
    
    def test_calculate_optimal_leverage(self):
        """Test optimal leverage calculation."""
        kelly_fraction = 0.05
        max_leverage = 10.0
        
        leverage = self.kelly_criterion.calculate_optimal_leverage(kelly_fraction, max_leverage)
        
        assert leverage >= 1.0
        assert leverage <= max_leverage
    
    def test_calculate_position_limits(self):
        """Test position limits calculation."""
        account_balance = 10000.0
        symbol = "BTC"
        current_price = 50000.0
        
        limits = self.kelly_criterion.calculate_position_limits(
            account_balance, symbol, current_price
        )
        
        assert "max_position_value" in limits
        assert "max_position_size" in limits
        assert "max_position_percentage" in limits
        
        assert limits["max_position_value"] == account_balance * self.config.max_position_size
        assert limits["max_position_size"] == limits["max_position_value"] / current_price
        assert limits["max_position_percentage"] == self.config.max_position_size * 100
    
    def test_validate_position_size(self):
        """Test position size validation."""
        account_balance = 10000.0
        current_price = 50000.0
        
        # Valid position size
        is_valid, message = self.kelly_criterion.validate_position_size(
            0.05, account_balance, current_price
        )
        assert is_valid
        assert "valid" in message.lower()
        
        # Position size too small
        is_valid, message = self.kelly_criterion.validate_position_size(
            0.0005, account_balance, current_price
        )
        assert not is_valid
        assert "below minimum" in message.lower()
        
        # Position size too large
        is_valid, message = self.kelly_criterion.validate_position_size(
            0.2, account_balance, current_price
        )
        assert not is_valid
        assert "exceeds maximum" in message.lower()
    
    def test_calculate_portfolio_kelly(self):
        """Test portfolio Kelly calculation."""
        symbols = ["BTC", "ETH"]
        returns_data = {
            "BTC": pd.Series([0.01, 0.02, -0.01, 0.03]),
            "ETH": pd.Series([0.015, 0.025, -0.005, 0.025])
        }
        
        kelly_fractions = self.kelly_criterion.calculate_portfolio_kelly(
            symbols, returns_data
        )
        
        assert len(kelly_fractions) == 2
        assert "BTC" in kelly_fractions
        assert "ETH" in kelly_fractions
        
        for symbol, fraction in kelly_fractions.items():
            assert 0 <= fraction <= self.config.max_position_size
