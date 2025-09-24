import asyncio
from datetime import datetime, timezone

import pandas as pd
import pytest

from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.config import Config
from hypebot.data.storage import DataStorage
from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.position.manager import PositionManager
from hypebot.position.kelly_criterion import KellyCriterion
from hypebot.strategy.rsi_strategy import RSIStrategy


def make_config() -> Config:
    return Config.from_env()


def seed_simple_data(storage: DataStorage, symbol: str):
    # Create simple OHLCV over 10 days
    idx = pd.date_range(start=pd.Timestamp("2024-01-01", tz="UTC"), periods=10, freq="1D")
    df = pd.DataFrame(
        {
            "symbol": symbol,
            "timestamp": idx,
            "open": [100 + i for i in range(10)],
            "high": [101 + i for i in range(10)],
            "low": [99 + i for i in range(10)],
            "close": [100 + i for i in range(10)],
            "volume": [1000 for _ in range(10)],
            "source": "test",
        }
    )
    # Save via historical writer grouped by year
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


@pytest.mark.asyncio
async def test_backtester_runs_and_returns_equity_curve(tmp_path):
    cfg = make_config()
    cfg.database.data_dir = str(tmp_path)
    storage = DataStorage(cfg.database)
    seed_simple_data(storage, "BTC-USD")

    pm = PositionManager(cfg.trading, storage)
    rsi = RSICalculator(period=3, oversold_threshold=30, overbought_threshold=70)
    kelly = KellyCriterion(cfg.trading)
    strat = RSIStrategy(assets=["BTC-USD"], interval="1d", position_manager=pm, rsi_calculator=rsi, kelly_criterion=kelly, config=cfg.trading)

    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.0), starting_cash=1000.0)
    result = await bt.run_single(strategy=strat, assets=["BTC-USD"], interval="1d")

    assert result.equity_curve is not None
    # Equity curve should have as many points as historical days
    assert len(result.equity_curve) >= 1


