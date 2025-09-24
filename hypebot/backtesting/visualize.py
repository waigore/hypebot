"""Visualization helpers for backtest results."""

from __future__ import annotations

from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curves(curves: Dict[str, pd.Series], title: str, filepath: str) -> str:
    plt.figure(figsize=(10, 6))
    for name, series in curves.items():
        if series is None or series.empty:
            continue
        series = series.sort_index()
        plt.plot(series.index, series.values, label=name)
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()
    return filepath


