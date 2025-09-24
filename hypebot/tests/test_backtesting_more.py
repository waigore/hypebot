import pandas as pd
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from hypebot.config import Config
from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.backtesting.metrics import compute_metrics
from hypebot.data.storage import DataStorage
from hypebot.strategy.base import Strategy


class EmptyStrategy(Strategy):
    async def on_start(self):
        return None

    async def on_stop(self):
        return None

    async def tick(self, as_of, historical):
        # No orders ever
        return []


@pytest.mark.asyncio
async def test_backtester_no_data_returns_empty_result(monkeypatch):
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)
    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.0), starting_cash=100.0)

    # Strategy with no orders
    strat = EmptyStrategy(assets=["XYZ-USD"], interval="1d", position_manager=None)

    # Monkeypatch storage to return empty data
    monkeypatch.setattr(storage, "get_historical_ohlcv_data", lambda **kwargs: pd.DataFrame())

    result = await bt.run_single(strategy=strat, assets=["XYZ-USD"], interval="1d")
    assert result.equity_curve.empty
    assert result.orders == []
    assert result.errors == []


def test_compute_metrics_raises_on_none_equity():
    with pytest.raises(ValueError):
        compute_metrics(None)  # type: ignore


def test_backtester_data_loader_calls_storage(mocker):
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)
    bt = BackTester(config=cfg, storage=storage)

    spy = mocker.spy(storage, "get_historical_ohlcv_data")
    # Call private loader directly
    bt._data_loader(symbol="ABC-USD", interval="1d", start=None, end=None)
    spy.assert_called_once()


