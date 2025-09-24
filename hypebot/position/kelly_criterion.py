"""Kelly Criterion implementation for optimal position sizing."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

from .models import PositionSize
from ..config import TradingConfig


logger = logging.getLogger(__name__)


class KellyCriterion:
    """Kelly Criterion calculator for optimal position sizing."""
    
    def __init__(self, config: TradingConfig):
        """Initialize Kelly Criterion calculator."""
        self.config = config
        self.max_position_size = config.max_position_size
        self.min_position_size = config.min_position_size
        self.lookback_period = config.kelly_lookback_period
        self.risk_free_rate = config.risk_free_rate
    
    def calculate_kelly_fraction(
        self, 
        returns: pd.Series, 
        signal_strength: float = 1.0
    ) -> float:
        """Calculate Kelly fraction based on historical returns."""
        try:
            if len(returns) < 2:
                logger.warning("Insufficient data for Kelly calculation")
                return 0.0
            
            # Calculate basic statistics
            mean_return = returns.mean()
            variance = returns.var()
            
            # Check if expected return is negative or zero
            expected_return = mean_return - self.risk_free_rate / 252
            if expected_return <= 0:
                logger.debug("Expected return is negative or zero, Kelly fraction should be 0")
                return 0.0
            
            if variance < 1e-10:  # Very small variance (effectively zero)
                logger.warning("Zero variance in returns, cannot calculate Kelly fraction")
                return 0.0
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds received on the wager (1 for 1:1)
            # p = probability of winning
            # q = probability of losing (1 - p)
            
            # For trading, we use:
            # f = (mean_return - risk_free_rate) / variance
            
            kelly_fraction = expected_return / variance
            
            # Apply signal strength adjustment
            kelly_fraction *= signal_strength
            
            # Cap at maximum position size
            kelly_fraction = min(kelly_fraction, self.max_position_size)
            
            # Ensure minimum position size if signal is strong enough
            if signal_strength > 0.5 and kelly_fraction < self.min_position_size:
                kelly_fraction = self.min_position_size
            
            # Ensure non-negative
            kelly_fraction = max(0.0, kelly_fraction)
            
            logger.info(f"Calculated Kelly fraction: {kelly_fraction:.4f}")
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"Error calculating Kelly fraction: {e}")
            return 0.0
    
    def calculate_position_size(
        self, 
        symbol: str, 
        current_price: float, 
        historical_returns: pd.Series,
        signal_strength: float = 1.0,
        confidence: float = 1.0
    ) -> PositionSize:
        """Calculate optimal position size using Kelly Criterion."""
        try:
            # Calculate Kelly fraction
            kelly_fraction = self.calculate_kelly_fraction(historical_returns, signal_strength)
            
            # Apply confidence adjustment
            kelly_fraction *= confidence
            
            # Calculate recommended size
            recommended_size = kelly_fraction
            
            # Determine risk level
            risk_level = self._determine_risk_level(kelly_fraction, signal_strength, confidence)
            
            # Calculate position value
            position_value = recommended_size * current_price
            
            return PositionSize(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                recommended_size=recommended_size,
                kelly_fraction=kelly_fraction,
                max_position_size=self.max_position_size,
                current_price=current_price,
                confidence=confidence,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return PositionSize(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                recommended_size=0.0,
                kelly_fraction=0.0,
                max_position_size=self.max_position_size,
                current_price=current_price,
                confidence=0.0,
                risk_level="HIGH"
            )
    
    def calculate_risk_metrics(
        self, 
        returns: pd.Series, 
        position_size: float
    ) -> Dict[str, float]:
        """Calculate risk metrics for a position."""
        try:
            if len(returns) < 2:
                return {
                    "volatility": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "var_95": 0.0,
                    "expected_return": 0.0
                }
            
            # Calculate volatility (annualized)
            volatility = returns.std() * np.sqrt(252)
            
            # Calculate Sharpe ratio
            excess_returns = returns - (self.risk_free_rate / 252)
            sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
            
            # Calculate maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Calculate Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)
            
            # Expected return
            expected_return = returns.mean() * 252
            
            return {
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "var_95": var_95,
                "expected_return": expected_return
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "var_95": 0.0,
                "expected_return": 0.0
            }
    
    def calculate_portfolio_kelly(
        self, 
        symbols: List[str], 
        returns_data: Dict[str, pd.Series],
        correlation_matrix: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """Calculate Kelly fractions for a portfolio of assets."""
        try:
            if not symbols or not returns_data:
                return {}
            
            # Calculate individual Kelly fractions
            individual_kelly = {}
            for symbol in symbols:
                if symbol in returns_data:
                    returns = returns_data[symbol]
                    kelly_fraction = self.calculate_kelly_fraction(returns)
                    individual_kelly[symbol] = kelly_fraction
            
            # If no correlation matrix provided, return individual fractions
            if correlation_matrix is None:
                return individual_kelly
            
            # Adjust for correlation (simplified approach)
            # This is a basic implementation - more sophisticated methods exist
            adjusted_kelly = {}
            for symbol in symbols:
                if symbol in individual_kelly:
                    base_kelly = individual_kelly[symbol]
                    
                    # Reduce position size based on correlation with other assets
                    correlation_penalty = 0.0
                    for other_symbol in symbols:
                        if other_symbol != symbol and other_symbol in individual_kelly:
                            if symbol in correlation_matrix.columns and other_symbol in correlation_matrix.index:
                                correlation = abs(correlation_matrix.loc[other_symbol, symbol])
                                correlation_penalty += correlation * individual_kelly[other_symbol]
                    
                    # Apply penalty
                    adjusted_kelly[symbol] = base_kelly * (1 - correlation_penalty)
                    adjusted_kelly[symbol] = max(0.0, adjusted_kelly[symbol])
            
            return adjusted_kelly
            
        except Exception as e:
            logger.error(f"Error calculating portfolio Kelly: {e}")
            return individual_kelly
    
    def _determine_risk_level(
        self, 
        kelly_fraction: float, 
        signal_strength: float, 
        confidence: float
    ) -> str:
        """Determine risk level based on position size and confidence."""
        tolerance = 1e-10
        if kelly_fraction >= self.max_position_size * 0.8 - tolerance:
            return "HIGH"
        elif kelly_fraction >= self.max_position_size * 0.5 - tolerance:
            return "MEDIUM"
        else:
            return "LOW"
    
    def calculate_optimal_leverage(
        self, 
        kelly_fraction: float, 
        max_leverage: float = 10.0
    ) -> float:
        """Calculate optimal leverage based on Kelly fraction."""
        # Kelly fraction already accounts for optimal sizing
        # Leverage should be used carefully and typically not exceed Kelly fraction
        optimal_leverage = min(kelly_fraction * 2, max_leverage)
        return max(1.0, optimal_leverage)  # Minimum leverage of 1x
    
    def calculate_position_limits(
        self, 
        account_balance: float, 
        symbol: str, 
        current_price: float
    ) -> Dict[str, float]:
        """Calculate position limits based on account balance."""
        max_position_value = account_balance * self.max_position_size
        max_position_size = max_position_value / current_price
        
        return {
            "max_position_value": max_position_value,
            "max_position_size": max_position_size,
            "max_position_percentage": self.max_position_size * 100
        }
    
    def validate_position_size(
        self, 
        position_size: float, 
        account_balance: float, 
        current_price: float
    ) -> Tuple[bool, str]:
        """Validate if position size is within acceptable limits."""
        if position_size < self.min_position_size:
            return False, f"Position size {position_size} below minimum {self.min_position_size}"
        
        if position_size > self.max_position_size:
            return False, f"Position size {position_size} exceeds maximum {self.max_position_size}"
        
        return True, "Position size is valid"
