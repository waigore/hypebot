"""Base Strategy interface definition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from ..indicators.base_indicator import BaseIndicator
from ..position.manager import PositionManager
from .models import StrategyOrder


class Strategy(ABC):
    """Abstract, testable strategy interface.

    Concrete strategies should implement the tick method. All dependencies should be
    injected to allow unit testing with mocks.
    """

    assets: List[str]
    interval: str  # Literal["1h","4h","1d","1w","1mo"] in practice
    position_manager: PositionManager
    indicators: Dict[str, BaseIndicator]

    def __init__(
        self,
        assets: List[str],
        interval: str,
        position_manager: PositionManager,
        indicators: Optional[Dict[str, BaseIndicator]] = None,
    ) -> None:
        self.assets = assets
        self.interval = interval
        self.position_manager = position_manager
        self.indicators = indicators or {}

    async def on_start(self) -> None:  # noqa: D401
        """Optional initialization hook."""
        return None

    @abstractmethod
    async def tick(self, as_of: datetime, historical: Dict[str, pd.DataFrame]) -> List[StrategyOrder]:
        """Compute position-sized orders from historical data up to as_of.

        - historical: mapping from symbol -> OHLCV DataFrame (UTC index, cols: open,high,low,close,volume).
        Returns a list of StrategyOrder items with calculated position sizes (may be empty).
        """

    async def on_stop(self) -> None:  # noqa: D401
        """Optional finalization hook."""
        return None


