import pandas as pd
from datetime import datetime, timedelta, timezone

from unittest.mock import Mock

from hypebot.config import Config
from hypebot.position.manager import PositionManager


def _row(symbol: str, side: str, size: float, entry: float, current: float, pnl: float, kelly: float, ts: datetime):
    return {
        "symbol": symbol,
        "side": side,
        "size": size,
        "entry_price": entry,
        "current_price": current,
        "pnl": pnl,
        "kelly_size": kelly,
        "timestamp": ts,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
    }


def test_load_positions_and_cleanup(monkeypatch):
    cfg = Config.from_env()
    storage = Mock()
    old_ts = datetime.now(tz=timezone.utc) - timedelta(days=365)
    df = pd.DataFrame([
        _row("OLD-USD", "LONG", 1.0, 10.0, 10.0, 0.0, 1.0, old_ts),
    ])
    # Ensure timestamp is datetime dtype
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    storage.load_positions.return_value = df
    storage.save_positions.return_value = True

    pm = PositionManager(cfg.trading, storage, load_existing=True, starting_cash=0.0)
    assert pm.get_position("OLD-USD") is not None

    # Cleanup should remove the old position
    pm.cleanup_old_positions(days=30)
    assert pm.get_position("OLD-USD") is None
    # Save called at least once during cleanup
    assert storage.save_positions.call_count >= 1


def test_save_called_on_open_update_close():
    cfg = Config.from_env()
    storage = Mock()
    storage.load_positions.return_value = pd.DataFrame()
    storage.save_positions.return_value = True

    pm = PositionManager(cfg.trading, storage, load_existing=True, starting_cash=100.0)

    # Open
    assert pm.open_position("IO-USD", "LONG", 1.0, 10.0, 1.0) is True
    # Update
    assert pm.update_position_price("IO-USD", 11.0) is True
    # Close
    assert pm.close_position("IO-USD", 12.0) is not None

    # save_positions should have been called for open, update, and close
    assert storage.save_positions.call_count >= 3


def test_update_unknown_symbol_returns_false():
    cfg = Config.from_env()
    storage = Mock()
    storage.load_positions.return_value = pd.DataFrame()
    pm = PositionManager(cfg.trading, storage, load_existing=True, starting_cash=0.0)
    assert pm.update_position_price("MISSING", 1.0) is False


