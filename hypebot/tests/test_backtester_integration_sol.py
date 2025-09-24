import os
from datetime import datetime, timezone

import pytest

from hypebot.backtesting.backtester import BackTester, CommissionModel
from hypebot.config import Config
from hypebot.data.storage import DataStorage
from hypebot.indicators.rsi_calculator import RSICalculator
from hypebot.position.manager import PositionManager
from hypebot.position.kelly_criterion import KellyCriterion
from hypebot.strategy.rsi_strategy import RSIStrategy


@pytest.mark.asyncio
async def test_integration_backtest_sol_2mo():
    cfg = Config.from_env()
    storage = DataStorage(cfg.database)

    # Ensure historical daily SOL-USD data exists for 2020-2025
    # Files already exist in data/historical per repository snapshot
    pm = PositionManager(cfg.trading, storage)
    rsi = RSICalculator(period=14, oversold_threshold=40, overbought_threshold=60)
    kelly = KellyCriterion(cfg.trading)
    strat = RSIStrategy(assets=["SOL-USD"], interval="1d", position_manager=pm, rsi_calculator=rsi, kelly_criterion=kelly, config=cfg.trading)

    bt = BackTester(config=cfg, storage=storage, commission=CommissionModel(type="percent", value=0.001), starting_cash=10_000.0)
    start = datetime(2024, 10, 1, tzinfo=timezone.utc)
    end = datetime(2024, 12, 31, tzinfo=timezone.utc)
    result = await bt.run_single(strategy=strat, assets=["SOL-USD"], interval="1d", start=start, end=end)

    # Basic assertions to ensure backtest produced output
    assert result.equity_curve is not None
    assert len(result.equity_curve) > 0
    
    # Debug: Check if we have any orders at all
    print(f"Number of orders generated: {len(result.orders)}")
    
    # Verify that orders were generated and executed
    assert len(result.orders) > 0, "Strategy should have generated trading orders"
    
    # Verify that orders have proper structure
    for order in result.orders:
        assert order.symbol == "SOL-USD"
        assert order.side in ["BUY", "SELL"]
        assert order.status == "FILLED"
        assert order.quantity > 0
        assert order.price is not None
        assert order.filled_quantity == order.quantity
        assert order.average_fill_price == order.price
    
    # Verify that positions were tracked (at least some positions should have been opened/closed)
    # The position manager should have some position history
    all_positions = pm.get_all_positions()
    # Note: positions might be closed during backtest, so we check the order history instead
    buy_orders = [o for o in result.orders if o.side == "BUY"]
    sell_orders = [o for o in result.orders if o.side == "SELL"]
    
    # Should have trading activity (at least some orders)
    total_orders = len(buy_orders) + len(sell_orders)
    assert total_orders > 0, "Strategy should have generated some trading orders"
    
    # Print order distribution for debugging
    print(f"Order distribution: {len(buy_orders)} BUY, {len(sell_orders)} SELL")
    
    # Note: RSI strategy might generate only one type of signal depending on market conditions
    # This is acceptable as long as we have some trading activity



