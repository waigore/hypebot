"""Hybrid RSI + EMA strategy implementing trend-filtered momentum.

Rules (long-only):
- Entry: (RSI > 50 or RSI crosses up from < oversold) AND Close > EMA(20)
- Exit:  (RSI < 50) OR (Close < EMA(20))

Sizing: all-in/all-out. Buy uses entire available cash for the asset; sell closes full position.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from .base import Strategy
from .models import StrategyOrder
from ..indicators.rsi_calculator import RSICalculator
from ..indicators.ema import EMACalculator
from ..indicators.base_indicator import BaseIndicator
from ..position.manager import PositionManager


class RSIEMAHybridStrategy(Strategy):
    """Trend-filtered RSI + EMA hybrid, all-in/all-out."""

    def __init__(
        self,
        assets: List[str],
        interval: str,
        position_manager: PositionManager,
        rsi_calculator: RSICalculator,
        ema_calculator: EMACalculator,
        rsi_trend_threshold: float = 50.0,
        oversold_threshold: float = 30.0,
        indicators: Optional[Dict[str, BaseIndicator]] = None,
    ) -> None:
        super().__init__(assets, interval, position_manager, indicators)
        if position_manager is None:
            raise ValueError("RSIEMAHybridStrategy requires a position_manager. Cannot be None.")
        self.rsi = rsi_calculator
        self.ema = ema_calculator
        self.rsi_trend_threshold = float(rsi_trend_threshold)
        self.oversold_threshold = float(oversold_threshold)

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        orders: List[StrategyOrder] = []

        for symbol, df in historical.items():
            if df is None or df.empty or "close" not in df.columns:
                continue

            current_price = float(df["close"].iloc[-1])

            # Compute indicator inputs on a rolling window
            rsi_window = max(getattr(self.rsi, "period", 14) + 2, 200)
            ema_window = max(getattr(self.ema, "period", 20) + 2, 200)
            window = max(rsi_window, ema_window)
            tail_df = df.tail(window)

            tmp = (
                tail_df[["close"]]
                .rename(columns={"close": "price"})
                .reset_index()
                .rename(columns={"index": "timestamp"})
            )
            tmp["symbol"] = symbol

            # Calculate RSI last and previous
            rsi_last = self.rsi.calculate_last(tmp)
            if rsi_last is None:
                continue
            rsi_current, rsi_prev = rsi_last

            # Calculate EMA last
            ema_last = self.ema.calculate_last(tmp)
            if ema_last is None:
                continue
            ema_current, _ = ema_last

            # Determine RSI conditions
            rsi_above_trend = rsi_current > self.rsi_trend_threshold
            crossed_up_from_oversold = False
            if rsi_prev is not None:
                crossed_up_from_oversold = rsi_prev < self.oversold_threshold and rsi_current >= self.oversold_threshold

            price_above_ema = current_price > ema_current
            price_below_ema = current_price < ema_current

            # Check existing position
            pos = self.position_manager.get_position(symbol)

            # Entry conditions: long-only
            should_buy = (rsi_above_trend or crossed_up_from_oversold) and price_above_ema
            # Exit conditions
            should_sell = (pos is not None and pos.side == "LONG") and (rsi_current < self.rsi_trend_threshold or price_below_ema)

            if pos is None and should_buy:
                # Use entire available cash
                cash = float(self.position_manager.cash_balance)
                if cash <= 0:
                    continue
                quantity = cash / current_price
                if quantity <= 0:
                    continue
                orders.append(
                    StrategyOrder(
                        symbol=symbol,
                        side="BUY",
                        order_type="MARKET",
                        quantity=quantity,
                        price=current_price,
                        timestamp=as_of,
                    )
                )
            elif should_sell:
                # Close entire position
                quantity = float(pos.size) if pos is not None else 0.0
                if quantity > 0:
                    orders.append(
                        StrategyOrder(
                            symbol=symbol,
                            side="SELL",
                            order_type="MARKET",
                            quantity=quantity,
                            price=current_price,
                            timestamp=as_of,
                        )
                    )

        return orders


