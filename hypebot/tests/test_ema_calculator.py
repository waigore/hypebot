"""Tests for EMA calculator."""

from datetime import datetime, timedelta

import pandas as pd

from hypebot.indicators.ema import EMACalculator


class TestEMACalculator:
    def test_calculate_last_basic(self):
        ema = EMACalculator(period=5)
        base = datetime.utcnow()
        prices = [10, 11, 12, 13, 14, 15, 16]
        df = pd.DataFrame({
            "symbol": ["BTC"] * len(prices),
            "timestamp": [base + timedelta(days=i) for i in range(len(prices))],
            "price": prices,
        })

        last = ema.calculate_last(df)
        assert last is not None
        current, prev = last
        assert isinstance(current, float)
        assert prev is None or isinstance(prev, float)
        # EMA should be between min and max of prices
        assert min(prices) <= current <= max(prices)

    def test_insufficient_data(self):
        ema = EMACalculator(period=10)
        base = datetime.utcnow()
        prices = [10, 11, 12]  # fewer than period
        df = pd.DataFrame({
            "symbol": ["BTC"] * len(prices),
            "timestamp": [base + timedelta(days=i) for i in range(len(prices))],
            "price": prices,
        })
        assert ema.calculate_last(df) is None


