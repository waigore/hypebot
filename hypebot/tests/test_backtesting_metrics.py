import pandas as pd
from datetime import datetime, timedelta, timezone

from hypebot.backtesting.metrics import compute_metrics


def test_compute_metrics_basic():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    idx = pd.date_range(start=start, periods=6, freq="1D", tz=timezone.utc)
    equity = pd.Series([100, 101, 102, 103, 104, 105], index=idx)
    m = compute_metrics(equity, risk_free_rate=0.0, periods_per_year=252)
    assert m["return_pct"] > 0
    assert -1.0 <= m["max_drawdown"] <= 0.0


