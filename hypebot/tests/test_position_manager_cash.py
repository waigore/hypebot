import pytest

from hypebot.config import Config
from hypebot.data.storage import DataStorage
from hypebot.position.manager import PositionManager


def test_position_manager_cash_open_close_long():
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)

    starting_cash = 1000.0
    pm = PositionManager(cfg.trading, storage, load_existing=False, starting_cash=starting_cash)

    # Open LONG within cash
    ok = pm.open_position(symbol="TEST-USD", side="LONG", size=1.0, entry_price=100.0, kelly_size=1.0)
    assert ok is True
    assert pm.cash_balance == pytest.approx(starting_cash - 100.0)

    # Attempt to open another LONG exceeding cash
    ok2 = pm.open_position(symbol="FAIL-USD", side="LONG", size=1000.0, entry_price=100.0, kelly_size=1.0)
    assert ok2 is False
    # Cash unchanged on failure
    assert pm.cash_balance == pytest.approx(starting_cash - 100.0)

    # Close the first position and verify cash credited
    closed = pm.close_position(symbol="TEST-USD", exit_price=110.0)
    assert closed is not None
    # Cash should increase by proceeds (1 * 110)
    assert pm.cash_balance == pytest.approx(starting_cash + 10.0)


