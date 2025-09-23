"""Strategy runner that orchestrates ticking and order execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd

from ..indicators.models import TradingSignal
from ..position.manager import PositionManager
from ..exchange.models import Order
from .client import TradingClientInterface
from .models import StrategyOrder
from .base import Strategy


logger = logging.getLogger(__name__)


class RunnerMode:
    BACKTEST = "backtest"
    LIVE = "live"


@dataclass
class ExecutionConfig:
    strength_threshold: float = 0.3
    cooldown_seconds: int = 300  # 5 minutes


class StrategyRunner:
    """Feeds time-sliced historical data per tick and executes orders."""

    def __init__(
        self,
        strategy: Strategy,
        position_manager: PositionManager,
        trading_client: TradingClientInterface,
        data_loader,  # callable (symbol, interval, start, end) -> DataFrame
        mode: str = RunnerMode.BACKTEST,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> None:
        self.strategy = strategy
        self.position_manager = position_manager
        self.trading_client = trading_client
        self.data_loader = data_loader
        self.mode = mode
        self.config = execution_config or ExecutionConfig()
        self._last_signal_time: Dict[str, datetime] = {}

    async def run(self, ticks: Iterable[datetime]) -> List[Order]:
        orders: List[Order] = []
        await self.strategy.on_start()
        try:
            for t in sorted(ticks):
                historical = self._slice_historical(as_of=t)
                signals = await self.strategy.tick(as_of=t, historical=historical)
                filtered = self._filter_signals(signals, as_of=t)
                intents = self._size_orders(filtered, historical)
                placed = await self._execute(intents)
                orders.extend(placed)
        finally:
            await self.strategy.on_stop()
        return orders

    def _slice_historical(self, as_of: datetime) -> Dict[str, pd.DataFrame]:
        result: Dict[str, pd.DataFrame] = {}
        for symbol in self.strategy.assets:
            df = self.data_loader(symbol, self.strategy.interval, None, as_of)
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Slice up to as_of inclusive
                if df.index.tz is None:
                    df.index = pd.to_datetime(df.index, utc=True)
                result[symbol] = df[df.index <= pd.to_datetime(as_of, utc=True)]
            else:
                result[symbol] = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # empty
        return result

    def _filter_signals(self, signals: List[TradingSignal], as_of: datetime) -> List[TradingSignal]:
        accepted: List[TradingSignal] = []
        for s in signals:
            if s.strength < self.config.strength_threshold:
                continue
            last = self._last_signal_time.get(s.symbol)
            if last is not None:
                elapsed = (as_of - last).total_seconds()
                if elapsed < self.config.cooldown_seconds:
                    continue
            self._last_signal_time[s.symbol] = as_of
            accepted.append(s)
        return accepted

    def _size_orders(self, signals: List[TradingSignal], historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        intents: List[StrategyOrder] = []
        for s in signals:
            # Determine current price from historical
            price = s.price
            if price is None:
                df = historical.get(s.symbol)
                if df is not None and not df.empty:
                    price = float(df["close"].iloc[-1])
            if price is None:
                # Cannot size without price
                continue
            size_info = self.position_manager.calculate_position_size(
                symbol=s.symbol,
                current_price=price,
                signal_strength=s.strength,
                confidence=s.strength,
            )
            ok, _ = self.position_manager.check_risk_limits(s.symbol, size_info.recommended_size)
            if not ok or size_info.recommended_size <= 0:
                continue
            side = "BUY" if s.signal_type == "BUY" else "SELL"
            intents.append(
                StrategyOrder(
                    symbol=s.symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=size_info.recommended_size,
                    price=None,
                    timestamp=datetime.utcnow(),
                )
            )
        return intents

    async def _execute(self, intents: List[StrategyOrder]) -> List[Order]:
        executed: List[Order] = []
        for intent in intents:
            order = await self.trading_client.place_order(
                symbol=intent.symbol,
                side=intent.side,
                order_type=intent.order_type,
                quantity=intent.quantity,
                price=intent.price,
            )
            executed.append(order)
        return executed


