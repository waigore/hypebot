"""Strategy runner that orchestrates ticking and order execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd
import time

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
    """Configuration for strategy execution."""
    pass  # Simplified - strategies handle their own filtering


class StrategyRunner:
    """Feeds time-sliced historical data per tick and executes StrategyOrders."""

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
        self.profile: Dict[str, float] = {"slice_s": 0.0, "tick_s": 0.0, "execute_s": 0.0}
        # Accumulate executed orders so callers can recover partial progress on errors
        self._orders: List[Order] = []

    async def run(self, ticks: Iterable[datetime]) -> List[Order]:
        # Reset accumulated orders each run
        self._orders = []
        await self.strategy.on_start()
        try:
            sorted_ticks = sorted(ticks)
            total = len(sorted_ticks)
            for i, t in enumerate(sorted_ticks):
                if i % 100 == 0:
                    logger.debug(f"StrategyRunner tick {i}/{total} at {t.isoformat()}")
                t0 = time.perf_counter()
                historical = self._slice_historical(as_of=t)
                self.profile["slice_s"] += time.perf_counter() - t0

                t1 = time.perf_counter()
                strategy_orders = await self.strategy.tick(as_of=t, historical=historical)
                self.profile["tick_s"] += time.perf_counter() - t1
                
                t2 = time.perf_counter()
                placed = await self._execute(strategy_orders)
                self.profile["execute_s"] += time.perf_counter() - t2
                self._orders.extend(placed)
        finally:
            await self.strategy.on_stop()
        return self._orders

    def _slice_historical(self, as_of: datetime) -> Dict[str, pd.DataFrame]:
        result: Dict[str, pd.DataFrame] = {}
        for symbol in self.strategy.assets:
            df = self.data_loader(symbol, self.strategy.interval, None, as_of)
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Slice up to as_of inclusive using index position for speed
                idx = df.index
                if idx.tz is None:
                    idx = pd.to_datetime(idx, utc=True)
                cutoff = pd.to_datetime(as_of, utc=True)
                pos = idx.searchsorted(cutoff, side="right")
                result[symbol] = df.iloc[:pos]
            else:
                result[symbol] = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])  # empty
        return result

    async def _execute(self, strategy_orders: List[StrategyOrder]) -> List[Order]:
        executed: List[Order] = []
        for strategy_order in strategy_orders:
            # Set the current backtest timestamp on the trading client
            if hasattr(self.trading_client, 'set_timestamp'):
                self.trading_client.set_timestamp(strategy_order.timestamp)
            order = await self.trading_client.place_order(
                symbol=strategy_order.symbol,
                side=strategy_order.side,
                order_type=strategy_order.order_type,
                quantity=strategy_order.quantity,
                price=strategy_order.price,
            )
            executed.append(order)
            
            # Update positions for backtest mode with simple open/close rules
            try:
                price = float(strategy_order.price) if strategy_order.price is not None else None
            except Exception:
                price = None
                
            if self.mode == RunnerMode.BACKTEST and price is not None:
                # Be tolerant of simplified PositionManager implementations used in tests
                position_manager = self.position_manager
                get_position = getattr(position_manager, "get_position", None)
                open_position = getattr(position_manager, "open_position", None)
                close_position = getattr(position_manager, "close_position", None)

                existing = get_position(strategy_order.symbol) if callable(get_position) else None

                if strategy_order.side == "BUY":
                    if existing is None:
                        if callable(open_position):
                            ok = open_position(
                                symbol=strategy_order.symbol,
                                side="LONG",
                                size=float(strategy_order.quantity),
                                entry_price=price,
                                kelly_size=float(strategy_order.quantity),
                            )
                            if ok is False:
                                raise RuntimeError(f"Illegal order: insufficient cash to open LONG {strategy_order.symbol}")
                    elif getattr(existing, "side", None) == "SHORT":
                        if callable(close_position):
                            close_position(strategy_order.symbol, exit_price=price)
                elif strategy_order.side == "SELL":
                    if existing is not None and getattr(existing, "side", None) == "LONG":
                        # Validate available size against sell quantity
                        try:
                            sell_qty = float(strategy_order.quantity)
                        except Exception:
                            sell_qty = None  # treat as None -> full close
                        if sell_qty is not None:
                            if sell_qty > float(getattr(existing, "size", 0.0)) + 1e-12:
                                raise RuntimeError(
                                    f"Illegal order: SELL qty {sell_qty} exceeds LONG size {getattr(existing, 'size', 0.0)} for {strategy_order.symbol}"
                                )
                        if callable(close_position):
                            # Support partial close when quantity is provided; tolerate PMs without quantity param
                            try:
                                import inspect  # local import to avoid top-level dependency in hot path
                                sig = inspect.signature(close_position)  # type: ignore[arg-type]
                                supports_qty = "quantity" in sig.parameters
                            except Exception:
                                supports_qty = False
                            if sell_qty is not None and supports_qty:
                                close_position(strategy_order.symbol, exit_price=price, quantity=sell_qty)
                            else:
                                # If PM doesn't support partials and sell is partial, raise
                                if sell_qty is not None and not supports_qty and sell_qty < float(getattr(existing, "size", 0.0)) - 1e-12:
                                    raise RuntimeError(
                                        f"Illegal order: partial SELL not supported by PositionManager for {strategy_order.symbol}"
                                    )
                                close_position(strategy_order.symbol, exit_price=price)
                    else:
                        # Illegal: attempting to sell without a LONG position
                        raise RuntimeError(f"Illegal order: SELL without LONG for {strategy_order.symbol}")
        if executed:
            logger.debug("\n".join([f"{e.symbol} {e.side} {e.quantity} {e.price}" for e in executed]))
        return executed


