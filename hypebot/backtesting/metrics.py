"""Performance metrics for backtests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


def _safe_annualize(period_returns: pd.Series, periods_per_year: int) -> float:
    return (1 + period_returns.mean()) ** periods_per_year - 1 if not period_returns.empty else 0.0


def compute_metrics(equity_curve: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> Dict[str, float]:
    if equity_curve is None or equity_curve.empty:
        return {"pnl": 0.0, "return_pct": 0.0, "cagr": 0.0, "vol_annual": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0}

    equity = equity_curve.dropna().astype(float)
    returns = equity.pct_change().dropna()

    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0

    num_years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / num_years) - 1

    vol_annual = returns.std() * np.sqrt(periods_per_year) if not returns.empty else 0.0
    excess = returns - (risk_free_rate / periods_per_year)
    sharpe = (excess.mean() / returns.std() * np.sqrt(periods_per_year)) if returns.std() > 0 else 0.0

    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(periods_per_year) if not downside.empty else 0.0
    sortino = (returns.mean() - risk_free_rate / periods_per_year) / downside_std if downside_std > 0 else 0.0

    # Max drawdown
    running_max = equity.cummax()
    drawdowns = equity / running_max - 1.0
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0.0

    return {
        "pnl": float(total_return * equity.iloc[0]),
        "return_pct": float(total_return),
        "cagr": float(cagr),
        "vol_annual": float(vol_annual),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": float(max_drawdown),
    }


