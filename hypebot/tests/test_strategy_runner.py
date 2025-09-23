import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pandas as pd
import pytest

from hypebot.strategy.base import Strategy
from hypebot.strategy.runner import StrategyRunner, RunnerMode, ExecutionConfig
from hypebot.strategy.client import TradingClientInterface
from hypebot.indicators.models import TradingSignal


class DummyStrategy(Strategy):
    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        signals: List[TradingSignal] = []
        for sym, df in historical.items():
            if df.empty:
                continue
            close = float(df["close"].iloc[-1])
            # Emit BUY when close is even, SELL otherwise with strength 0.8
            sig_type = "BUY" if int(close) % 2 == 0 else "SELL"
            signals.append(
                TradingSignal(
                    symbol=sym,
                    timestamp=as_of,
                    signal_type=sig_type,
                    strength=0.8,
                    rsi_value=50.0,
                    price=close,
                )
            )
        return signals


class DummyTradingClient(TradingClientInterface):
    def __init__(self):
        self.placed = []

    async def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price=None):
        order = type("Order", (), {})()
        order.symbol = symbol
        order.side = side
        order.order_type = order_type
        order.quantity = quantity
        order.price = price
        order.status = "FILLED"
        self.placed.append(order)
        return order

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self):
        return []


class DummyPositionManager:
    def __init__(self, size: float = 0.01):
        self.size = size

    def calculate_position_size(self, symbol: str, current_price: float, signal_strength: float = 1.0, confidence: float = 1.0):
        return type(
            "PositionSize",
            (),
            {
                "recommended_size": self.size,
                "kelly_fraction": 0.5,
                "max_position_size": 1.0,
                "current_price": current_price,
                "confidence": confidence,
                "risk_level": "LOW",
            },
        )()

    def check_risk_limits(self, symbol: str, position_size: float):
        return True, "ok"


def make_df(start: datetime, n: int) -> pd.DataFrame:
    idx = pd.date_range(start=start, periods=n, freq="1D", tz=timezone.utc)
    df = pd.DataFrame(
        {
            "open": [100 + i for i in range(n)],
            "high": [101 + i for i in range(n)],
            "low": [99 + i for i in range(n)],
            "close": [100 + i for i in range(n)],
            "volume": [1000 for _ in range(n)],
        },
        index=idx,
    )
    return df


@pytest.mark.asyncio
async def test_runner_executes_orders_based_on_signals():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    hist = {"BTC-USD": make_df(start, 5)}

    def loader(symbol: str, interval: str, start_dt, end_dt):
        return hist[symbol]

    pm = DummyPositionManager(size=0.02)
    strat = DummyStrategy(assets=["BTC-USD"], interval="1d", position_manager=pm)
    client = DummyTradingClient()
    runner = StrategyRunner(
        strategy=strat,
        position_manager=pm,  # type: ignore
        trading_client=client,
        data_loader=loader,
        mode=RunnerMode.BACKTEST,
        execution_config=ExecutionConfig(strength_threshold=0.3, cooldown_seconds=0),
    )

    ticks = [start + timedelta(days=i) for i in range(3)]
    orders = await runner.run(ticks)

    assert len(orders) == 3
    for o in orders:
        assert o.quantity == pytest.approx(0.02)
        assert o.order_type == "MARKET"


@pytest.mark.asyncio
async def test_runner_applies_strength_threshold_and_cooldown():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    hist = {"ETH-USD": make_df(start, 3)}

    def loader(symbol: str, interval: str, start_dt, end_dt):
        return hist[symbol]

    class WeakSignalStrategy(DummyStrategy):
        async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
            sigs = await super().tick(as_of, historical)
            for s in sigs:
                s.strength = 0.2  # below threshold
            return sigs

    pm = DummyPositionManager(size=0.01)
    strat = WeakSignalStrategy(assets=["ETH-USD"], interval="1d", position_manager=pm)
    client = DummyTradingClient()
    runner = StrategyRunner(
        strategy=strat,
        position_manager=pm,  # type: ignore
        trading_client=client,
        data_loader=loader,
        mode=RunnerMode.BACKTEST,
        execution_config=ExecutionConfig(strength_threshold=0.3, cooldown_seconds=600),
    )

    ticks = [start + timedelta(days=i) for i in range(2)]
    orders = await runner.run(ticks)
    # No orders because strength below threshold
    assert len(orders) == 0


