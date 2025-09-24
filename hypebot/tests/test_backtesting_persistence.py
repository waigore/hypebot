import pandas as pd
import pytest
from datetime import datetime
from typing import Dict

from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.config import Config
from hypebot.data.storage import DataStorage
from hypebot.strategy.base import Strategy
from hypebot.strategy.models import StrategyOrder
from hypebot.position.manager import PositionManager


def _seed_simple_ohlcv(storage: DataStorage, symbol: str):
    # Create simple OHLCV over 5 days
    idx = pd.date_range(start=pd.Timestamp("2024-01-01", tz="UTC"), periods=5, freq="1D")
    df = pd.DataFrame(
        {
            "symbol": symbol,
            "timestamp": idx,
            "open": [100 + i for i in range(5)],
            "high": [101 + i for i in range(5)],
            "low": [99 + i for i in range(5)],
            "close": [100 + i for i in range(5)],
            "volume": [1000 for _ in range(5)],
            "source": "test",
        }
    )
    from hypebot.data.models import OHLCVData

    records = [
        OHLCVData(
            symbol=symbol,
            timestamp=ts.to_pydatetime(),
            open=float(df.loc[i, "open"]),
            high=float(df.loc[i, "high"]),
            low=float(df.loc[i, "low"]),
            close=float(df.loc[i, "close"]),
            volume=float(df.loc[i, "volume"]),
            source="test",
        )
        for i, ts in enumerate(idx)
    ]
    storage.save_ohlcv_data(records, granularity="1d", append=False)


class _BuyThenSell(Strategy):
    """Test strategy: BUY on first tick with price, SELL on second tick."""

    def __init__(self, assets, interval, position_manager):
        super().__init__(assets, interval, position_manager, indicators=None)
        self._did_buy: bool = False
        self._did_sell: bool = False

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]):
        orders: list[StrategyOrder] = []
        if not self.assets:
            return orders
        sym = self.assets[0]
        df = historical.get(sym)
        if df is None or df.empty or "close" not in df.columns:
            return orders
        price = float(df["close"].iloc[-1])
        if not self._did_buy:
            orders.append(StrategyOrder(symbol=sym, side="BUY", order_type="MARKET", quantity=1.0, price=price, timestamp=as_of))
            self._did_buy = True
        elif not self._did_sell:
            orders.append(StrategyOrder(symbol=sym, side="SELL", order_type="MARKET", quantity=1.0, price=price, timestamp=as_of))
            self._did_sell = True
        return orders


@pytest.mark.asyncio
async def test_backtesting_does_not_write_positions_csv(tmp_path):
    cfg = Config.from_env()
    cfg.database.data_dir = str(tmp_path)
    storage = DataStorage(cfg.database)
    _seed_simple_ohlcv(storage, "BTC-USD")

    # Ensure positions file does not exist before run
    positions_path = tmp_path / cfg.database.positions_file
    assert positions_path.exists() is False

    # Create a placeholder PM; BackTester will replace with a non-persisting PM
    pm = PositionManager(cfg.trading, storage)
    strat = _BuyThenSell(assets=["BTC-USD"], interval="1d", position_manager=pm)

    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.0), starting_cash=1000.0)
    await bt.run_single(strategy=strat, assets=["BTC-USD"], interval="1d")

    # No positions.csv should be written during backtesting
    assert positions_path.exists() is False

