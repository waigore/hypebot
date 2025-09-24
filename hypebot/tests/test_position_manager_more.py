import pytest

from hypebot.config import Config
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager


def _make_pm(starting_cash: float = 1000.0) -> PositionManager:
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)
    return PositionManager(cfg.trading, storage, load_existing=False, starting_cash=starting_cash)


def test_update_position_price_and_summary_and_metrics():
    pm = _make_pm(1000.0)

    # Open LONG position
    assert pm.open_position(symbol="AAA-USD", side="LONG", size=2.0, entry_price=50.0, kelly_size=2.0)
    # Cash debited: 1000 - 100 = 900
    assert pm.cash_balance == pytest.approx(900.0)

    # Update price higher
    assert pm.update_position_price("AAA-USD", 60.0) is True
    pos = pm.get_position("AAA-USD")
    assert pos is not None
    assert pos.unrealized_pnl == pytest.approx((60.0 - 50.0) * 2.0)
    assert pos.pnl == pytest.approx(pos.unrealized_pnl + pos.realized_pnl)

    # Portfolio metrics should include cash + market value
    metrics = pm.calculate_portfolio_metrics()
    # Market value: 2 * 60 = 120; portfolio = cash 900 + 120 = 1020
    assert metrics["portfolio_value"] == pytest.approx(1020.0)
    assert metrics["total_positions"] == 1

    # Summary contains expected columns and values
    summary = pm.get_position_summary()
    assert not summary.empty
    row = summary.iloc[0]
    assert row["symbol"] == "AAA-USD"
    assert row["side"] == "LONG"
    assert row["size"] == 2.0
    assert row["current_price"] == 60.0


def test_open_position_invalid_inputs_and_missing_symbol_close():
    pm = _make_pm(100.0)
    # Invalid size
    assert pm.open_position(symbol="BBB-USD", side="LONG", size=0.0, entry_price=10.0, kelly_size=0.0) is False
    # Invalid price
    assert pm.open_position(symbol="BBB-USD", side="LONG", size=1.0, entry_price=0.0, kelly_size=1.0) is False
    # Close non-existent
    assert pm.close_position("UNKNOWN", 10.0) is None


