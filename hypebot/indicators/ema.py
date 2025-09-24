"""EMA (Exponential Moving Average) calculator.

Provides rolling EMA values and simple accessors for the latest and previous
values. This indicator is used as a trend filter in hybrid strategies.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd

from .base_indicator import BaseIndicator
from .models import IndicatorResult, TradingSignal


class EMACalculator(BaseIndicator):
    """EMA calculator without intrinsic signal generation.

    The EMA is used as a filter; this class focuses on calculating values.
    """

    def __init__(self, period: int = 20) -> None:
        super().__init__("EMA", period)

    def calculate(self, data: pd.DataFrame) -> List[IndicatorResult]:  # pragma: no cover - not used directly
        self.validate_data(data, ["price"])  # Expect columns: [timestamp, price, symbol]
        if len(data) < self.period:
            return []
        prices = data["price"].astype(float)
        ema_series = prices.ewm(span=self.period, adjust=False).mean()
        # Return as generic results structure if needed by future consumers
        results: List[IndicatorResult] = []
        for idx in range(self.period - 1, len(data)):
            results.append(IndicatorResult())
        return results

    def generate_signal(self, current_value: float, previous_value: Optional[float] = None, metadata: Optional[dict] = None) -> Optional[TradingSignal]:  # pragma: no cover - EMA does not emit signals
        return None

    def calculate_last(self, data: pd.DataFrame) -> Optional[Tuple[float, Optional[float]]]:
        """Return (current_ema, previous_ema) for the provided price data.

        Expects columns: ['timestamp', 'price', 'symbol'] with at least `period` rows.
        """
        self.validate_data(data, ["price"])  # minimal validation
        if len(data) < self.period:
            return None
        prices = data["price"].astype(float)
        ema_series = prices.ewm(span=self.period, adjust=False).mean()
        current = float(ema_series.iloc[-1])
        prev = float(ema_series.iloc[-2]) if len(ema_series) >= 2 else None
        return current, prev


