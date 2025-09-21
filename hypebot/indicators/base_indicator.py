"""Base indicator class for technical analysis."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from .models import IndicatorResult, TradingSignal


class BaseIndicator(ABC):
    """Abstract base class for technical indicators."""
    
    def __init__(self, name: str, period: int = 14):
        """Initialize base indicator."""
        self.name = name
        self.period = period
        self._last_calculation_time: Optional[datetime] = None
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> List[IndicatorResult]:
        """Calculate indicator values for the given data."""
        pass
    
    @abstractmethod
    def generate_signal(
        self, 
        current_value: float, 
        previous_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal based on indicator value."""
        pass
    
    def validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """Validate that data contains required columns."""
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        return True
    
    def get_latest_value(self, data: pd.DataFrame) -> Optional[float]:
        """Get the latest indicator value from data."""
        if data.empty:
            return None
        return data.iloc[-1].get('value', None)
    
    def get_previous_value(self, data: pd.DataFrame) -> Optional[float]:
        """Get the previous indicator value from data."""
        if len(data) < 2:
            return None
        return data.iloc[-2].get('value', None)
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate price returns."""
        return prices.pct_change().dropna()
    
    def calculate_volatility(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """Calculate rolling volatility."""
        return returns.rolling(window=window).std() * (252 ** 0.5)  # Annualized
    
    def smooth_data(self, data: pd.Series, window: int = 3) -> pd.Series:
        """Apply simple moving average smoothing."""
        return data.rolling(window=window, center=True).mean()
    
    def detect_divergence(
        self, 
        price_data: pd.Series, 
        indicator_data: pd.Series,
        lookback: int = 5
    ) -> Dict[str, bool]:
        """Detect bullish/bearish divergence between price and indicator."""
        if len(price_data) < lookback or len(indicator_data) < lookback:
            return {"bullish": False, "bearish": False}
        
        # Get recent data
        recent_prices = price_data.tail(lookback)
        recent_indicators = indicator_data.tail(lookback)
        
        # Check for bullish divergence (price lower low, indicator higher low)
        price_trend = recent_prices.iloc[-1] - recent_prices.iloc[0]
        indicator_trend = recent_indicators.iloc[-1] - recent_indicators.iloc[0]
        
        bullish_divergence = price_trend < 0 and indicator_trend > 0
        bearish_divergence = price_trend > 0 and indicator_trend < 0
        
        return {
            "bullish": bullish_divergence,
            "bearish": bearish_divergence
        }
    
    def calculate_signal_strength(
        self, 
        current_value: float, 
        threshold_low: float, 
        threshold_high: float
    ) -> float:
        """Calculate signal strength based on how far the value is from thresholds."""
        if current_value <= threshold_low:
            # Oversold - strength based on how far below threshold
            return min(1.0, (threshold_low - current_value) / threshold_low)
        elif current_value >= threshold_high:
            # Overbought - strength based on how far above threshold
            return min(1.0, (current_value - threshold_high) / (100 - threshold_high))
        else:
            # Neutral zone
            return 0.0
    
    def get_metadata(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get metadata about the calculation."""
        return {
            "indicator_name": self.name,
            "period": self.period,
            "data_points": len(data),
            "calculation_time": datetime.utcnow(),
            "last_update": self._last_calculation_time
        }
