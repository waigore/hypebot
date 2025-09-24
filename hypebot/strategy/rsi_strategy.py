"""Concrete RSI-based strategy implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from .base import Strategy
from .models import StrategyOrder
from ..indicators.rsi_calculator import RSICalculator
from ..indicators.models import TradingSignal
from ..indicators.base_indicator import BaseIndicator
from ..position.kelly_criterion import KellyCriterion
from ..position.manager import PositionManager
from ..config import TradingConfig


class RSIStrategy(Strategy):
    """Strategy that emits position-sized orders based on RSI signals and Kelly criterion."""

    def __init__(
        self, 
        assets: List[str],
        interval: str,
        position_manager: PositionManager,
        rsi_calculator: RSICalculator, 
        kelly_criterion: KellyCriterion,
        config: TradingConfig,
        indicators: Optional[Dict[str, BaseIndicator]] = None,
    ) -> None:
        super().__init__(assets, interval, position_manager, indicators)
        if position_manager is None:
            raise ValueError("RSIStrategy requires a position_manager. Cannot be None.")
        self.rsi = rsi_calculator
        self.kelly_criterion = kelly_criterion
        self.config = config

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        orders: List[StrategyOrder] = []
        
        for symbol, df in historical.items():
            if df is None or df.empty or "close" not in df.columns:
                continue
                
            current_price = float(df["close"].iloc[-1])
            
            # Prepare DataFrame expected by RSICalculator: columns ['timestamp','price','symbol']
            # Use trailing window to avoid O(N^2) recomputation per tick
            window = max(getattr(self.rsi, "period", 14) + 2, 200)
            tail_df = df.tail(window)
            tmp = (
                tail_df[["close"]]
                .rename(columns={"close": "price"})
                .reset_index()
                .rename(columns={"index": "timestamp"})
            )
            tmp["symbol"] = symbol
            
            # Calculate RSI
            last = self.rsi.calculate_last(tmp)
            if last is None:
                continue
            current_val, prev = last
            
            # Generate signal
            signal = self.rsi.generate_signal(
                current_value=current_val,
                previous_value=prev,
                metadata={"symbol": symbol},
            )
            if signal is None:
                continue
                
            # Apply signal filtering and risk management
            if not self._should_trade(symbol, signal, as_of):
                continue
                
            # Calculate position size using Kelly criterion
            position_size = self._calculate_position_size(symbol, current_price, signal, df)
            if position_size <= 0:
                continue
                
            # Create strategy order
            side = "BUY" if signal.signal_type == "BUY" else "SELL"
            order = StrategyOrder(
                symbol=symbol,
                side=side,
                order_type="MARKET",
                quantity=position_size,
                price=current_price,
                timestamp=as_of,
            )
            orders.append(order)
            
        return orders
    
    def _should_trade(self, symbol: str, signal: TradingSignal, as_of: datetime) -> bool:
        """Apply signal filtering and risk management logic."""
        # Check signal strength threshold
        if signal.strength < 0.5:  # Configurable threshold
            return False
            
        # Check if we already have a position for this symbol
        existing_position = self.position_manager.get_position(symbol)
        
        if signal.signal_type == "BUY":
            # For BUY signals, only allow if we don't have a LONG position already
            if existing_position is not None and existing_position.side == "LONG":
                return False
            return True
            
        elif signal.signal_type == "SELL":
            # For SELL signals, only allow if we have a LONG position to sell
            # This prevents short selling
            if existing_position is None or existing_position.side != "LONG":
                return False
            return True
            
        return False
    
    def _calculate_position_size(self, symbol: str, current_price: float, signal: TradingSignal, df: pd.DataFrame) -> float:
        """Calculate position size using Kelly criterion."""
        try:
            # Get historical returns for Kelly calculation
            returns = df['close'].astype(float).pct_change().dropna()
            if returns.empty:
                return 0.0
                
            # Calculate position size using Kelly criterion
            position_size_info = self.kelly_criterion.calculate_position_size(
                symbol=symbol,
                current_price=current_price,
                historical_returns=returns,
                signal_strength=signal.strength,
                confidence=signal.strength
            )
            
            # Apply signal strength adjustment
            adjusted_size = position_size_info.recommended_size * signal.strength
            
            # Apply risk limits
            adjusted_size = min(adjusted_size, self.config.max_position_size)
            adjusted_size = max(adjusted_size, self.config.min_position_size)
            
            return adjusted_size
            
        except Exception as e:
            # Log error and return 0 to skip this trade
            return 0.0


