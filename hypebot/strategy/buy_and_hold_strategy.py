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
    """Strategy that purchases assets in full on first tick and holds them.

    This strategy:
    - Uses 100% of available cash on the first tick
    - For single asset: purchases entire position in that asset
    - For multiple assets: distributes cash equally across all assets
    - Never sells or rebalances after initial purchase
    - Provides simple baseline for strategy performance comparison
    """

    def __init__(self, *args, starting_cash: float = 10000.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._has_purchased = False
        self.starting_cash = starting_cash

    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        """Generate buy orders only on the first tick, empty list thereafter."""
        orders: List[StrategyOrder] = []
        
        # Only purchase on the first tick
        if self._has_purchased:
            return orders
            
        # Check if we have valid data for all assets
        valid_assets = []
        for symbol in self.assets:
            df = historical.get(symbol)
            if df is not None and not df.empty and "close" in df.columns:
                valid_assets.append(symbol)
        
        if not valid_assets:
            return orders
            
        # Use starting cash amount
        cash = self.starting_cash
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
        
        # Mark that we've made our initial purchase
        self._has_purchased = True
        
        return orders

    async def on_start(self) -> None:
        """Reset purchase flag when strategy starts."""
        self._has_purchased = False
        await super().on_start()

    async def on_stop(self) -> None:
        """Reset purchase flag when strategy stops."""
        self._has_purchased = False
        await super().on_stop()
