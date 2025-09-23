"""Trading client interface used by StrategyRunner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..exchange.models import Order


class TradingClientInterface(ABC):
    """Abstract trading client used by the runner (mockable)."""

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,  # Literal["BUY","SELL"]
        order_type: str,  # Literal["MARKET","LIMIT"]
        quantity: float,
        price: Optional[float] = None,
    ) -> Order:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self):  # return list[Position] but avoid import cycle
        raise NotImplementedError


