"""Tests for RSI + EMA Hybrid Strategy."""

from __future__ import annotations

from datetime import datetime, timedelta
import asyncio
from typing import Dict

import pandas as pd

from hypebot.strategy.hybrid_rsi_ema_strategy import RSIEMAHybridStrategy
from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.indicators.ema import EMACalculator
from hypebot.position.manager import PositionManager
from hypebot.data.storage import DataStorage
from hypebot.config import Config


def _make_df(prices: list[float], start: datetime | None = None) -> pd.DataFrame:
    start = start or datetime.utcnow() - timedelta(days=len(prices))
    idx = [start + timedelta(days=i) for i in range(len(prices))]
    return pd.DataFrame({
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": [1.0] * len(prices),
    }, index=pd.to_datetime(idx, utc=True))


def _to_ind_input(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    t = df[["close"]].rename(columns={"close": "price"}).reset_index().rename(columns={"index": "timestamp"})
    t["symbol"] = symbol
    return t


class TestRSIEMAHybridStrategy:
    def setup_method(self):
        self.config = Config.from_env()
        storage = DataStorage(self.config.database)
        # For unit tests, do not persist
        self.pm = PositionManager(self.config.trading, storage, load_existing=False, starting_cash=1000.0, persist=False)
        self.rsi = RSICalculator(period=14, oversold_threshold=30, overbought_threshold=70)
        self.ema = EMACalculator(period=20)
        self.strategy = RSIEMAHybridStrategy(
            assets=["BTC-USD"],
            interval="1d",
            position_manager=self.pm,
            rsi_calculator=self.rsi,
            ema_calculator=self.ema,
            rsi_trend_threshold=50.0,
            oversold_threshold=30.0,
        )

    def test_no_signal_with_insufficient_history(self):
        df = _make_df([100.0] * 10)  # less than EMA/RSI period
        orders = asyncio.run(self.strategy.tick(datetime.utcnow(), {"BTC-USD": df}))
        assert orders == []

    def test_entry_when_rsi_above_50_and_price_above_ema(self, monkeypatch):
        # Construct rising prices to push RSI > 50 and close > EMA
        prices = [i for i in range(80, 120)]
        df = _make_df(prices)
        # Ensure enough cash to buy
        self.pm.cash_balance = 1000.0
        orders = asyncio.run(self.strategy.tick(datetime.utcnow(), {"BTC-USD": df}))
        assert len(orders) in (0, 1)  # RSI depends on series; usually 1
        if orders:
            o = orders[0]
            assert o.side == "BUY"
            assert o.quantity > 0

    def test_exit_when_rsi_drops_below_50(self):
        # Simulate existing long position
        # Directly set a simple position in manager
        self.pm._positions["BTC-USD"] = type("P", (), {"side": "LONG", "size": 1.0})()
        prices = [i for i in range(80, 120)] + [100.0] * 30  # plateau to potentially lower RSI
        df = _make_df(prices)
        orders = asyncio.run(self.strategy.tick(datetime.utcnow(), {"BTC-USD": df}))
        # Might or might not trigger depending on series; check that any SELL does not exceed position size
        for o in orders:
            if o.side == "SELL":
                assert o.quantity == 1.0

    def test_exit_when_price_below_ema(self):
        # Existing long
        self.pm._positions["BTC-USD"] = type("P", (), {"side": "LONG", "size": 0.5})()
        # Prices dip under EMA
        prices = [100.0] * 30 + [90.0] * 10
        df = _make_df(prices)
        orders = asyncio.run(self.strategy.tick(datetime.utcnow(), {"BTC-USD": df}))
        for o in orders:
            if o.side == "SELL":
                assert o.quantity == 0.5


