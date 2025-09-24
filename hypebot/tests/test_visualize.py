import os
import tempfile
import pandas as pd

from hypebot.backtesting.visualize import plot_equity_curves


def test_plot_equity_curves_creates_file():
    s = pd.Series([100, 105, 110], index=pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC"))
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "eq.png")
        out = plot_equity_curves({"A": s, "B": s * 0.9}, title="Test", filepath=path)
        assert os.path.exists(out)
        assert out == path


