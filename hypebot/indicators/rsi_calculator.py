"""RSI (Relative Strength Index) calculator and signal generator."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from .base_indicator import BaseIndicator
from .models import IndicatorResult, TradingSignal


logger = logging.getLogger(__name__)


class RSICalculator(BaseIndicator):
    """RSI calculator with signal generation."""
    
    def __init__(
        self, 
        period: int = 14, 
        oversold_threshold: float = 30.0, 
        overbought_threshold: float = 70.0
    ):
        """Initialize RSI calculator."""
        super().__init__("RSI", period)
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self._last_rsi_value: Optional[float] = None
    
    def calculate(self, data: pd.DataFrame) -> List[IndicatorResult]:
        """Calculate RSI values for the given price data."""
        try:
            self.validate_data(data, ['price'])
            
            if len(data) < self.period + 1:
                logger.warning(f"Insufficient data for RSI calculation. Need at least {self.period + 1} data points")
                return []
            
            prices = data['price']
            rsi_values = self._calculate_rsi(prices)
            
            results = []
            for i, (timestamp, rsi_value) in enumerate(zip(data['timestamp'], rsi_values)):
                if pd.isna(rsi_value):
                    continue
                
                # Generate signal
                signal = self.generate_signal(rsi_value, self._last_rsi_value)
                
                # Calculate signal strength
                strength = self.calculate_signal_strength(
                    rsi_value, 
                    self.oversold_threshold, 
                    self.overbought_threshold
                )
                
                # Detect divergence
                divergence = self.detect_divergence(
                    prices.iloc[:i+1], 
                    pd.Series(rsi_values[:i+1])
                )
                
                metadata = {
                    "rsi_value": rsi_value,
                    "oversold_threshold": self.oversold_threshold,
                    "overbought_threshold": self.overbought_threshold,
                    "signal_strength": strength,
                    "divergence": divergence,
                    "period": self.period
                }
                
                result = IndicatorResult(
                    symbol=data.iloc[i]['symbol'] if 'symbol' in data.columns else "UNKNOWN",
                    timestamp=timestamp,
                    indicator_name=self.name,
                    value=rsi_value,
                    signal=signal.signal_type if signal else None,
                    strength=strength,
                    metadata=metadata
                )
                
                results.append(result)
                self._last_rsi_value = rsi_value
            
            self._last_calculation_time = datetime.utcnow()
            logger.info(f"Calculated RSI for {len(results)} data points")
            return results
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return []
    
    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI using the standard formula."""
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate initial average gain and loss
        avg_gains = gains.rolling(window=self.period).mean()
        avg_losses = losses.rolling(window=self.period).mean()
        
        # Calculate subsequent average gains and losses using Wilder's smoothing
        for i in range(self.period, len(prices)):
            if i == self.period:
                continue
            
            avg_gains.iloc[i] = (avg_gains.iloc[i-1] * (self.period - 1) + gains.iloc[i]) / self.period
            avg_losses.iloc[i] = (avg_losses.iloc[i-1] * (self.period - 1) + losses.iloc[i]) / self.period
        
        # Calculate relative strength
        rs = avg_gains / avg_losses
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signal(
        self, 
        current_value: float, 
        previous_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal based on RSI value."""
        try:
            if pd.isna(current_value):
                return None
            
            # Determine signal type
            signal_type = "HOLD"
            strength = 0.0
            
            if current_value <= self.oversold_threshold:
                signal_type = "BUY"
                strength = self.calculate_signal_strength(
                    current_value, 
                    self.oversold_threshold, 
                    self.overbought_threshold
                )
            elif current_value >= self.overbought_threshold:
                signal_type = "SELL"
                strength = self.calculate_signal_strength(
                    current_value, 
                    self.oversold_threshold, 
                    self.overbought_threshold
                )
            
            # Check for signal confirmation with previous value
            if previous_value is not None and not pd.isna(previous_value):
                # Look for crossover signals
                if (previous_value <= self.oversold_threshold and 
                    current_value > self.oversold_threshold and 
                    signal_type == "HOLD"):
                    signal_type = "BUY"
                    strength = 0.7  # Moderate strength for crossover
                elif (previous_value >= self.overbought_threshold and 
                      current_value < self.overbought_threshold and 
                      signal_type == "HOLD"):
                    signal_type = "SELL"
                    strength = 0.7  # Moderate strength for crossover
            
            # Only return signal if it's not HOLD
            if signal_type == "HOLD":
                return None
            
            return TradingSignal(
                symbol=metadata.get('symbol', 'UNKNOWN') if metadata else 'UNKNOWN',
                timestamp=datetime.utcnow(),
                signal_type=signal_type,
                strength=strength,
                rsi_value=current_value,
                indicator=self.name,
                metadata={
                    "rsi_value": current_value,
                    "previous_rsi": previous_value,
                    "oversold_threshold": self.oversold_threshold,
                    "overbought_threshold": self.overbought_threshold,
                    "signal_strength": strength
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating RSI signal: {e}")
            return None
    
    def calculate_signal_strength(
        self, 
        current_value: float, 
        threshold_low: float, 
        threshold_high: float
    ) -> float:
        """Calculate signal strength based on RSI value."""
        if current_value <= threshold_low:
            # Oversold - strength based on how far below threshold
            return min(1.0, (threshold_low - current_value) / threshold_low)
        elif current_value >= threshold_high:
            # Overbought - strength based on how far above threshold
            return min(1.0, (current_value - threshold_high) / (100 - threshold_high))
        else:
            # Neutral zone
            return 0.0
    
    def get_rsi_levels(self) -> Dict[str, float]:
        """Get RSI threshold levels."""
        return {
            "oversold": self.oversold_threshold,
            "overbought": self.overbought_threshold,
            "neutral_low": 40.0,
            "neutral_high": 60.0
        }
    
    def is_oversold(self, rsi_value: float) -> bool:
        """Check if RSI indicates oversold condition."""
        return rsi_value <= self.oversold_threshold
    
    def is_overbought(self, rsi_value: float) -> bool:
        """Check if RSI indicates overbought condition."""
        return rsi_value >= self.overbought_threshold
    
    def is_neutral(self, rsi_value: float) -> bool:
        """Check if RSI is in neutral zone."""
        return self.oversold_threshold < rsi_value < self.overbought_threshold
    
    def get_rsi_interpretation(self, rsi_value: float) -> str:
        """Get human-readable interpretation of RSI value."""
        if self.is_oversold(rsi_value):
            return f"Oversold ({rsi_value:.2f}) - Potential buying opportunity"
        elif self.is_overbought(rsi_value):
            return f"Overbought ({rsi_value:.2f}) - Potential selling opportunity"
        else:
            return f"Neutral ({rsi_value:.2f}) - No clear signal"
