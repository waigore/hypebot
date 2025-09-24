"""Backtesting utilities for strategies."""

from .backtester import BackTester, BacktestResult, CommissionModel
from .metrics import compute_metrics
from .visualize import plot_equity_curves

__all__ = [
    "BackTester",
    "BacktestResult",
    "CommissionModel",
    "compute_metrics",
    "plot_equity_curves",
]


