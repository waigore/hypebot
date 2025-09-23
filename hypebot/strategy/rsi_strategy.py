"""Concrete RSI-based strategy implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from .base import Strategy
from ..indicators.rsi_calculator import RSICalculator
from ..indicators.models import TradingSignal


class RSIStrategy(Strategy):
    """Strategy that emits signals based on RSI on the close price."""

    def __init__(self, *args, rsi_calculator: RSICalculator, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rsi = rsi_calculator

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        signals: List[TradingSignal] = []
        for symbol, df in historical.items():
            if df is None or df.empty or "close" not in df.columns:
                continue
            # Prepare DataFrame expected by RSICalculator: columns ['timestamp','price','symbol']
            tmp = (
                df[["close"]]
                .rename(columns={"close": "price"})
                .reset_index()
                .rename(columns={"index": "timestamp"})
            )
            tmp["symbol"] = symbol
            results = self.rsi.calculate(tmp)
            if not results:
                continue
            latest = results[-1]
            prev = results[-2].value if len(results) > 1 else None
            sig = self.rsi.generate_signal(
                current_value=latest.value,
                previous_value=prev,
                metadata={"symbol": symbol},
            )
            if sig is None:
                continue
            # Attach current price
            sig.price = float(df["close"].iloc[-1])
            sig.timestamp = as_of
            signals.append(sig)
        return signals


