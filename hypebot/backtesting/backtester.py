"""Backtesting harness that runs strategies on historical data and reports results."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config import Config, TradingConfig, DatabaseConfig
from ..data.storage import DataStorage
from ..position.manager import PositionManager
from ..strategy.base import Strategy
from ..strategy.runner import StrategyRunner, RunnerMode, ExecutionConfig
from ..strategy.client import TradingClientInterface
from ..exchange.models import Order


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


class DummyTradingClient(TradingClientInterface):
    """Simulated execution client with simple commission model."""

    def __init__(self, commission: CommissionModel):
        self._orders: List[Order] = []
        self._commission = commission

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
            timestamp=datetime.utcnow(),
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
    ) -> None:
        self.config = config
        self.storage = storage or DataStorage(config.database)
        self.commission = commission or CommissionModel(type="percent", value=0.001)
        self.starting_cash = starting_cash

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
        pm = PositionManager(self.config.trading, self.storage)
        client = DummyTradingClient(self.commission)

        # Strategy should already be created with pm; ensure assets/interval
        strategy.assets = assets
        strategy.interval = interval
        strategy.position_manager = pm

        # Preload historical OHLCV per asset once
        preloaded: Dict[str, pd.DataFrame] = {}
        for a in assets:
            df = self.storage.get_historical_ohlcv_data(symbol=a, granularity=interval, start_date=start, end_date=end)
            preloaded[a] = df if isinstance(df, pd.DataFrame) else pd.DataFrame()

        def mem_loader(sym: str, _interval: str, _start: Optional[datetime], _end: Optional[datetime]) -> pd.DataFrame:
            return preloaded.get(sym, pd.DataFrame())

        runner = StrategyRunner(
            strategy=strategy,
            position_manager=pm,
            trading_client=client,
            data_loader=mem_loader,
            mode=RunnerMode.BACKTEST,
            execution_config=execution_config or ExecutionConfig(),
        )

        # Establish ticks based on available data across assets
        frames = [preloaded[a] for a in assets]
        frames = [f for f in frames if isinstance(f, pd.DataFrame) and not f.empty]
        if not frames:
            return BacktestResult(equity_curve=pd.Series(dtype=float), orders=[], trades=[], snapshots=pd.DataFrame())
        all_index = frames[0].index
        for f in frames[1:]:
            all_index = all_index.union(f.index)
        all_index = all_index.sort_values()
        ticks: List[datetime] = [ts.to_pydatetime() for ts in all_index]

        # Cash/equity tracking (simplified: track portfolio as sum of position values; here, we emulate by marking to close)
        equity_points: List[Tuple[datetime, float]] = []
        snapshots: List[Dict[str, float]] = []

        orders = await runner.run(ticks)
        # expose simple profiling info on the result via snapshots attrs
        profile_info = getattr(runner, "profile", {})

        # Build equity curve by marking to last close per asset and summing; PositionManager holds positions but we keep it simple
        cash = self.starting_cash
        for t in ticks:
            total_value = cash
            for a in assets:
                df = preloaded.get(a)
                if df is not None and not df.empty:
                    # locate last price at or before t
                    sub = df[df.index <= pd.to_datetime(t, utc=True)]
                    if not sub.empty:
                        price = float(sub["close"].iloc[-1])
                        pos = pm.get_position(a)
                        if pos is not None:
                            pm.update_position_price(a, price)
                            total_value += pos.unrealized_pnl + pos.entry_value
            equity_points.append((t, total_value))
            snapshots.append({"timestamp": t, "equity": total_value})

        equity_curve = pd.Series(
            data=[v for _, v in equity_points], index=pd.to_datetime([t for t, _ in equity_points], utc=True)
        )
        snapshots_df = pd.DataFrame(snapshots).set_index(pd.to_datetime(pd.Series([s["timestamp"] for s in snapshots]), utc=True))
        snapshots_df.attrs["profile"] = profile_info
        return BacktestResult(equity_curve=equity_curve, orders=orders, trades=[], snapshots=snapshots_df)


