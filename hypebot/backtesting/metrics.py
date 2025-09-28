"""Performance metrics for backtests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


def _safe_annualize(period_returns: pd.Series, periods_per_year: int) -> float:
    return (1 + period_returns.mean()) ** periods_per_year - 1 if not period_returns.empty else 0.0


def compute_metrics(equity_curve: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252, dca_metrics: Dict = None) -> Dict[str, float]:
    if equity_curve is None:
        raise ValueError("Equity curve is required")

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

    metrics = {
        "pnl": float(total_return * equity.iloc[0]),
        "return_pct": float(total_return),
        "cagr": float(cagr),
        "vol_annual": float(vol_annual),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": float(max_drawdown),
    }

    # Add DCA metrics if available
    if dca_metrics:
        metrics.update(compute_dca_metrics(equity, dca_metrics))

    return metrics


def compute_dca_metrics(equity_curve: pd.Series, dca_metrics: Dict) -> Dict[str, float]:
    """Compute DCA-specific performance metrics.
    
    Args:
        equity_curve: Portfolio equity curve
        dca_metrics: DCA metrics from position manager
        
    Returns:
        Dictionary with DCA-specific metrics
    """
    if not dca_metrics:
        return {}

    total_dca_injected = dca_metrics.get("total_dca_injected", 0.0)
    initial_cash = dca_metrics.get("initial_cash", 0.0)
    dca_contribution_ratio = dca_metrics.get("dca_contribution_ratio", 0.0)
    
    # Calculate DCA-adjusted returns
    total_capital = initial_cash + total_dca_injected
    if total_capital > 0:
        dca_adjusted_return = (equity_curve.iloc[-1] / total_capital) - 1.0
    else:
        dca_adjusted_return = 0.0

    # Calculate return attribution
    initial_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0 if equity_curve.iloc[0] > 0 else 0.0
    dca_return_contribution = dca_adjusted_return - initial_return

    return {
        "total_dca_injected": float(total_dca_injected),
        "dca_injection_count": float(dca_metrics.get("dca_injection_count", 0)),
        "dca_contribution_ratio": float(dca_contribution_ratio),
        "dca_adjusted_return": float(dca_adjusted_return),
        "dca_return_contribution": float(dca_return_contribution),
        "initial_cash": float(initial_cash),
        "total_capital": float(total_capital),
    }


