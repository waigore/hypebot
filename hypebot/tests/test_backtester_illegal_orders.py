import pytest
from datetime import datetime, timezone

from hypebot.config import Config
from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager
from hypebot.strategy.base import Strategy
from hypebot.strategy.models import StrategyOrder


class DummyIllegalSellStrategy(Strategy):
    async def on_start(self):
        return None

    async def on_stop(self):
        return None

    async def tick(self, as_of, historical):
        # Always SELL without a LONG position
        return [
            StrategyOrder(
                symbol=self.assets[0],
                side="SELL",
                order_type="MARKET",
                quantity=1.0,
                price=historical[self.assets[0]].iloc[-1]["close"] if not historical[self.assets[0]].empty else 1.0,
                timestamp=as_of,
            )
        ]


@pytest.mark.asyncio
async def test_backtester_halts_on_illegal_sell():
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)
    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.0), starting_cash=100.0)

    # Use available historical for SOL-USD daily (exists in repo)
    strat = DummyIllegalSellStrategy(assets=["SOL-USD"], interval="1d", position_manager=PositionManager(cfg.trading, storage, load_existing=False, starting_cash=100.0))

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 31, tzinfo=timezone.utc)
    result = await bt.run_single(strategy=strat, assets=["SOL-USD"], interval="1d", start=start, end=end)

    # Should record an error about illegal sell
    assert isinstance(result.errors, list)
    assert any("Illegal order" in e for e in result.errors)


class DummyOversellStrategy(Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._did_buy = False

    async def tick(self, as_of, historical):
        sym = self.assets[0]
        df = historical[sym]
        price = df.iloc[-1]["close"] if not df.empty else 1.0
        if not self._did_buy:
            self._did_buy = True
            return [
                StrategyOrder(symbol=sym, side="BUY", order_type="MARKET", quantity=1.0, price=price, timestamp=as_of)
            ]
        # Attempt to SELL more than we own
        return [
            StrategyOrder(symbol=sym, side="SELL", order_type="MARKET", quantity=2.0, price=price, timestamp=as_of)
        ]


@pytest.mark.asyncio
async def test_backtester_rejects_oversell_quantity():
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)
    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.0), starting_cash=1000.0)

    strat = DummyOversellStrategy(assets=["SOL-USD"], interval="1d", position_manager=PositionManager(cfg.trading, storage, load_existing=False, starting_cash=1000.0))
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 2, 1, tzinfo=timezone.utc)
    result = await bt.run_single(strategy=strat, assets=["SOL-USD"], interval="1d", start=start, end=end)

    assert isinstance(result.errors, list)
    assert any("exceeds LONG size" in e for e in result.errors)


