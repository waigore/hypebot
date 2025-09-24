import numpy as np
import pandas as pd

from hypebot.config import Config
from hypebot.position.kelly_criterion import KellyCriterion


def test_kelly_validate_and_limits_and_leverage():
    cfg = Config.from_env()
    k = KellyCriterion(cfg.trading)

    ok, msg = k.validate_position_size(position_size=cfg.trading.min_position_size / 2, account_balance=1000, current_price=10)
    assert ok is False and "below minimum" in msg

    ok2, msg2 = k.validate_position_size(position_size=cfg.trading.max_position_size * 2, account_balance=1000, current_price=10)
    assert ok2 is False and "exceeds maximum" in msg2

    limits = k.calculate_position_limits(account_balance=1000.0, symbol="X", current_price=50.0)
    assert limits["max_position_size"] == (1000.0 * cfg.trading.max_position_size) / 50.0

    lev = k.calculate_optimal_leverage(kelly_fraction=0.1, max_leverage=3.0)
    assert 1.0 <= lev <= 3.0


def test_kelly_portfolio_and_risk_metrics():
    cfg = Config.from_env()
    k = KellyCriterion(cfg.trading)

    rng = np.random.default_rng(0)
    r1 = pd.Series(rng.normal(0.001, 0.01, size=252))
    r2 = pd.Series(rng.normal(0.0005, 0.008, size=252))
    returns = {"A": r1, "B": r2}

    indiv = k.calculate_portfolio_kelly(symbols=["A", "B"], returns_data=returns, correlation_matrix=None)
    assert set(indiv.keys()) == {"A", "B"}

    corr = pd.DataFrame(np.corrcoef(np.vstack([r1.values, r2.values])), index=["A", "B"], columns=["A", "B"])
    adj = k.calculate_portfolio_kelly(symbols=["A", "B"], returns_data=returns, correlation_matrix=corr)
    assert set(adj.keys()) == {"A", "B"}

    risk = k.calculate_risk_metrics(returns=r1, position_size=0.1)
    assert set(["volatility", "sharpe_ratio", "max_drawdown", "var_95", "expected_return"]).issubset(risk.keys())


