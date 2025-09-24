import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pandas as pd
import pytest

from hypebot.strategy.base import Strategy
from hypebot.strategy.runner import StrategyRunner, RunnerMode, ExecutionConfig
from hypebot.strategy.client import TradingClientInterface
from hypebot.strategy.models import StrategyOrder


class DummyStrategy(Strategy):
    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        orders: List[StrategyOrder] = []
        for sym, df in historical.items():
            if df.empty:
                continue
            close = float(df["close"].iloc[-1])
            # Emit BUY when close is even, SELL otherwise
            side = "BUY" if int(close) % 2 == 0 else "SELL"
            orders.append(
                StrategyOrder(
                    symbol=sym,
                    side=side,
                    order_type="MARKET",
                    quantity=0.02,  # Fixed position size for testing
                    price=close,
                    timestamp=as_of,
                )
            )
        return orders


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
    def __init__(self):
        self.positions = {}

    def get_position(self, symbol: str):
        return self.positions.get(symbol)

    def open_position(self, symbol: str, side: str, size: float, entry_price: float, kelly_size: float):
        self.positions[symbol] = type("Position", (), {
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "kelly_size": kelly_size
        })()

    def close_position(self, symbol: str, exit_price: float):
        return self.positions.pop(symbol, None)


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
async def test_runner_executes_orders_based_on_strategy_orders():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    hist = {"BTC-USD": make_df(start, 5)}

    def loader(symbol: str, interval: str, start_dt, end_dt):
        return hist[symbol]

    pm = DummyPositionManager()
    strat = DummyStrategy(assets=["BTC-USD"], interval="1d", position_manager=pm)
    client = DummyTradingClient()
    runner = StrategyRunner(
        strategy=strat,
        position_manager=pm,  # type: ignore
        trading_client=client,
        data_loader=loader,
        mode=RunnerMode.BACKTEST,
        execution_config=ExecutionConfig(),
    )

    ticks = [start + timedelta(days=i) for i in range(3)]
    orders = await runner.run(ticks)

    assert len(orders) == 3
    for o in orders:
        assert o.quantity == pytest.approx(0.02)
        assert o.order_type == "MARKET"


@pytest.mark.asyncio
async def test_runner_executes_all_strategy_orders():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    hist = {"ETH-USD": make_df(start, 3)}

    def loader(symbol: str, interval: str, start_dt, end_dt):
        return hist[symbol]

    class NoOrderStrategy(DummyStrategy):
        async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
            # Return no orders
            return []

    pm = DummyPositionManager()
    strat = NoOrderStrategy(assets=["ETH-USD"], interval="1d", position_manager=pm)
    client = DummyTradingClient()
    runner = StrategyRunner(
        strategy=strat,
        position_manager=pm,  # type: ignore
        trading_client=client,
        data_loader=loader,
        mode=RunnerMode.BACKTEST,
        execution_config=ExecutionConfig(),
    )

    ticks = [start + timedelta(days=i) for i in range(2)]
    orders = await runner.run(ticks)
    # No orders because strategy returns empty list
    assert len(orders) == 0


