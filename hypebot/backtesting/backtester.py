"""Backtesting harness that runs strategies on historical data and reports results."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from ..config import Config, TradingConfig, DatabaseConfig
from ..data.storage import DataStorage
from ..position.manager import PositionManager
from ..strategy.base import Strategy
from ..strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from ..strategy.runner import StrategyRunner, RunnerMode, ExecutionConfig
from ..strategy.client import TradingClientInterface
from ..exchange.models import Order
from ..dca import DCAConfig, DCAScheduler


@dataclass
class CommissionModel:
    type: str  # "fixed" | "percent"
    value: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    orders: List[Order]
    trades: List[Dict[str, float]]
    snapshots: pd.DataFrame
    positions: pd.DataFrame  # Position data for each tick
    errors: List[str]


class DummyTradingClient(TradingClientInterface):
    """Simulated execution client with simple commission model."""

    def __init__(self, commission: CommissionModel):
        self._orders: List[Order] = []
        self._commission = commission
        self._current_timestamp: Optional[datetime] = None

    def set_timestamp(self, timestamp: datetime) -> None:
        """Set the current backtest timestamp for order generation."""
        self._current_timestamp = timestamp

    async def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> Order:
        executed_price = float(price) if price is not None else None
        order = Order(
            symbol=symbol,
            side=side,  # type: ignore
            order_type=order_type,  # type: ignore
            quantity=quantity,
            price=executed_price,
            status="FILLED",
            filled_quantity=quantity,
            average_fill_price=executed_price,
            timestamp=self._current_timestamp or datetime.utcnow(),
        )
        self._orders.append(order)
        return order

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self):
        return []


class BackTester:
    """Run one or more strategies in parallel over the same historical data."""

    def __init__(
        self,
        config: Config,
        storage: Optional[DataStorage] = None,
        commission: Optional[CommissionModel] = None,
        starting_cash: float = 10_000.0,
        dca_config: Optional[DCAConfig] = None,
    ) -> None:
        self.config = config
        self.storage = storage or DataStorage(config.database)
        self.commission = commission or CommissionModel(type="percent", value=0.001)
        self.starting_cash = starting_cash
        self.dca_config = dca_config or DCAConfig()

    def _data_loader(self, symbol: str, interval: str, start: Optional[datetime], end: Optional[datetime]) -> pd.DataFrame:
        # This default loader reads from storage; overridden in run_single with preloaded data
        granularity = interval
        return self.storage.get_historical_ohlcv_data(
            symbol=symbol, granularity=granularity, start_date=start, end_date=end
        )

    async def run_single(
        self,
        strategy: Strategy,
        assets: List[str],
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> BacktestResult:
        # Build dedicated position manager and client per strategy
        # For backtesting, don't load existing positions - keep everything in memory
        pm = PositionManager(
            self.config.trading,
            self.storage,
            load_existing=False,
            starting_cash=self.starting_cash,
            persist=False,
        )
        client = DummyTradingClient(self.commission)

        # Strategy should already be created with pm; ensure assets/interval
        strategy.assets = assets
        strategy.interval = interval
        # Use the same position manager instance for consistency
        strategy.position_manager = pm

        # Preload historical OHLCV per asset once
        preloaded: Dict[str, pd.DataFrame] = {}
        for a in assets:
            df = self.storage.get_historical_ohlcv_data(symbol=a, granularity=interval, start_date=start, end_date=end)
            preloaded[a] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()

        def mem_loader(sym: str, _interval: str, _start: Optional[datetime], _end: Optional[datetime]) -> pd.DataFrame:
            return preloaded.get(sym, pd.DataFrame())

        # Establish ticks based on available data across assets
        frames = [preloaded[a] for a in assets]
        frames = [f for f in frames if isinstance(f, pd.DataFrame) and not f.empty]
        if not frames:
            return BacktestResult(
                equity_curve=pd.Series(dtype=float),
                orders=[],
                trades=[],
                snapshots=pd.DataFrame(),
                positions=pd.DataFrame(),
                errors=[],
            )
        all_index = frames[0].index
        for f in frames[1:]:
            all_index = all_index.union(f.index)
        all_index = all_index.sort_values()
        ticks: List[datetime] = [ts.to_pydatetime() for ts in all_index]

        # Generate DCA schedule if enabled
        dca_scheduler = None
        if self.dca_config.enabled:
            dca_scheduler = DCAScheduler(
                self.dca_config,
                start or datetime.min,
                end or datetime.max
            )
            dca_schedule = dca_scheduler.generate_schedule(ticks)
            logger.info(f"DCA schedule generated: {dca_schedule.total_injections} injections totaling ${dca_schedule.total_amount}")

        runner = StrategyRunner(
            strategy=strategy,
            position_manager=pm,
            trading_client=client,
            data_loader=mem_loader,
            mode=RunnerMode.BACKTEST,
            execution_config=execution_config or ExecutionConfig(),
            dca_scheduler=dca_scheduler,
        )

        # Cash/equity tracking (simplified: track portfolio as sum of position values; here, we emulate by marking to close)
        equity_points: List[Tuple[datetime, float]] = []
        snapshots: List[Dict[str, float]] = []
        position_snapshots: List[Dict[str, Any]] = []

        errors: List[str] = []
        # Define a per-tick callback to snapshot cash/positions after each tick execution
        position_snapshots: List[Dict[str, Any]] = []
        snapshots: List[Dict[str, float]] = []

        def _after_tick(as_of: datetime) -> None:
            total_value = pm.cash_balance
            tick_position_data: Dict[str, Any] = {
                "timestamp": as_of,
                "symbol": None,
                "side": None,
                "size": None,
                "entry_price": None,
                "current_price": None,
                "pnl": None,
                "realized_pnl": None,
                "unrealized_pnl": None,
                "pnl_percentage": None,
                "kelly_size": None,
                "market_value": None,
                "entry_value": None,
                "position_timestamp": None,
                "cash_balance": pm.cash_balance,
            }

            for a in assets:
                df = preloaded.get(a)
                if df is not None and not df.empty:
                    sub = df[df.index <= pd.to_datetime(as_of, utc=True)]
                    if not sub.empty:
                        price = float(sub["close"].iloc[-1])
                        pos = pm.get_position(a)
                        if pos is not None:
                            pm.update_position_price(a, price)
                            total_value += pos.size * price
                            tick_position_data.update({
                                "symbol": pos.symbol,
                                "side": pos.side,
                                "size": pos.size,
                                "entry_price": pos.entry_price,
                                "current_price": pos.current_price,
                                "pnl": pos.pnl,
                                "realized_pnl": pos.realized_pnl,
                                "unrealized_pnl": pos.unrealized_pnl,
                                "pnl_percentage": pos.pnl_percentage,
                                "kelly_size": pos.kelly_size,
                                "market_value": pos.market_value,
                                "entry_value": pos.entry_value,
                                "position_timestamp": pos.timestamp,
                            })

            equity_points.append((as_of, total_value))
            snapshots.append({"timestamp": as_of, "equity": total_value})
            position_snapshots.append(tick_position_data)

        try:
            orders = await runner.run(ticks, on_after_tick=_after_tick)
        except RuntimeError as e:
            # Illegal order encountered; stop immediately and report error
            # Preserve any orders placed before the error
            try:
                orders = list(getattr(runner, "_orders", []))
            except Exception:
                orders = []
            errors.append(str(e))
            # Build minimal snapshots/equity until the failure point if possible (left empty for simplicity)
        # expose simple profiling info on the result via snapshots attrs
        profile_info = getattr(runner, "profile", {})

        # If no snapshots were collected (e.g., no ticks), fall back to initial point
        if not snapshots and ticks:
            t0 = ticks[0]
            snapshots.append({"timestamp": t0, "equity": self.starting_cash})
            equity_points.append((t0, self.starting_cash))
            position_snapshots.append({
                "timestamp": t0,
                "symbol": None,
                "side": None,
                "size": None,
                "entry_price": None,
                "current_price": None,
                "pnl": None,
                "realized_pnl": None,
                "unrealized_pnl": None,
                "pnl_percentage": None,
                "kelly_size": None,
                "market_value": None,
                "entry_value": None,
                "position_timestamp": None,
                "cash_balance": pm.cash_balance,
            })

        equity_curve = pd.Series(
            data=[v for _, v in equity_points], index=pd.to_datetime([t for t, _ in equity_points], utc=True)
        )
        snapshots_df = pd.DataFrame(snapshots).set_index(pd.to_datetime(pd.Series([s["timestamp"] for s in snapshots]), utc=True))
        snapshots_df.attrs["profile"] = profile_info
        
        # Create positions DataFrame
        positions_df = pd.DataFrame(position_snapshots)
        if not positions_df.empty and "timestamp" in positions_df.columns:
            # Convert timestamp to datetime and set as index
            positions_df["timestamp"] = pd.to_datetime(positions_df["timestamp"], utc=True)
            positions_df = positions_df.set_index("timestamp")
        
        return BacktestResult(equity_curve=equity_curve, orders=orders, trades=[], snapshots=snapshots_df, positions=positions_df, errors=errors)

    async def run_with_control(
        self,
        strategies: List[Strategy],
        assets: List[str],
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> Dict[str, BacktestResult]:
        """Run multiple strategies including a Buy-and-Hold control strategy.
        
        Args:
            strategies: List of strategies to test
            assets: List of asset symbols to trade
            interval: Data granularity
            start: Start date for backtest
            end: End date for backtest
            execution_config: Execution configuration
            
        Returns:
            Dictionary mapping strategy names to BacktestResult objects
        """
        results = {}
        
        # Run each provided strategy
        for strategy in strategies:
            strategy_name = strategy.__class__.__name__
            result = await self.run_single(
                strategy=strategy,
                assets=assets,
                interval=interval,
                start=start,
                end=end,
                execution_config=execution_config
            )
            results[strategy_name] = result
        
        # Always include Buy-and-Hold control strategy
        control_strategy = BuyAndHoldStrategy(
            assets=assets,
            interval=interval,
            position_manager=PositionManager(
                self.config.trading,
                self.storage,
                load_existing=False,
                starting_cash=self.starting_cash,
                persist=False,
            ),
            starting_cash=self.starting_cash
        )
        control_result = await self.run_single(
            strategy=control_strategy,
            assets=assets,
            interval=interval,
            start=start,
            end=end,
            execution_config=execution_config
        )
        results["BuyAndHoldStrategy"] = control_result
        
        return results


