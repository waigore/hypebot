"""Buy-and-Hold strategy implementation.

This strategy serves as the control baseline for all backtesting comparisons.
It purchases assets in full on the first tick and never sells or rebalances.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from .base import Strategy
from .models import StrategyOrder


class BuyAndHoldStrategy(Strategy):
    """Strategy that purchases assets using all available cash and holds them.

    This strategy:
    - Uses 100% of available cash on every tick (including DCA injections)
    - For single asset: purchases entire position in that asset
    - For multiple assets: distributes cash equally across all assets
    - Never sells or rebalances after purchase
    - Provides simple baseline for strategy performance comparison
    - Automatically accounts for DCA injections by using current cash balance
    """

    def __init__(self, *args, starting_cash: float = 10000.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.starting_cash = starting_cash

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        """Generate buy orders using all available cash (including DCA injections)."""
        orders: List[StrategyOrder] = []
        
        # Check if we have valid data for all assets
        valid_assets = []
        for symbol in self.assets:
            df = historical.get(symbol)
            if df is not None and not df.empty and "close" in df.columns:
                valid_assets.append(symbol)
        
        if not valid_assets:
            return orders
            
        # Use current available cash (includes DCA injections)
        cash = self.position_manager.cash_balance
        if cash <= 0:
            return orders
            
        # Distribute cash equally across all valid assets
        cash_per_asset = cash / len(valid_assets)
        
        for symbol in valid_assets:
            df = historical[symbol]
            current_price = float(df["close"].iloc[-1])
            
            # Calculate quantity to purchase
            quantity = cash_per_asset / current_price
            
            # Create buy order
            order = StrategyOrder(
                symbol=symbol,
                side="BUY",
                order_type="MARKET",
                quantity=quantity,
                price=current_price,
                timestamp=as_of,
            )
            orders.append(order)
        
        return orders

    async def on_start(self) -> None:
        """Initialize strategy."""
        await super().on_start()

    async def on_stop(self) -> None:
        """Clean up strategy."""
        await super().on_stop()
