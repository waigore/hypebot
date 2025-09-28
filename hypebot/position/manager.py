"""Position manager for tracking and managing trading positions."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd

from .models import Position
from ..config import TradingConfig
from ..data.storage import DataStorage


logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions, cash, and portfolio tracking (no position sizing)."""
    
    def __init__(self, config: TradingConfig, storage: DataStorage, load_existing: bool = True, starting_cash: float = 0.0, persist: bool = True):
        """Initialize position manager.
        
        Args:
            config: Trading configuration
            storage: Data storage instance
            load_existing: Whether to load existing positions from storage (default: True)
                         Set to False for backtesting where positions should be memory-only
            starting_cash: Initial cash balance for portfolio tracking (default: 0.0)
        """
        self.config = config
        self.storage = storage
        self._positions: Dict[str, Position] = {}
        # Control whether changes are persisted to storage
        self._persist: bool = bool(persist)
        # Maintain dedicated cash balance per spec
        self.cash_balance: float = float(starting_cash)
        # DCA tracking attributes
        self._dca_injections: List[Tuple[datetime, float]] = []
        self._total_dca_injected: float = 0.0
        if load_existing:
            self._load_positions()
    
    def _load_positions(self):
        """Load existing positions from storage."""
        try:
            positions_df = self.storage.load_positions()
            if positions_df.empty:
                return
            
            for _, row in positions_df.iterrows():
                position = Position(
                    symbol=row['symbol'],
                    side=row['side'],
                    size=row['size'],
                    entry_price=row['entry_price'],
                    current_price=row['current_price'],
                    pnl=row['pnl'],
                    kelly_size=row['kelly_size'],
                    timestamp=row['timestamp'],
                    unrealized_pnl=row.get('unrealized_pnl'),
                    realized_pnl=row.get('realized_pnl', 0.0)
                )
                self._positions[row['symbol']] = position
            
            logger.info(f"Loaded {len(self._positions)} positions")
            
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
    
    def _save_positions(self):
        """Save positions to storage."""
        try:
            # Skip persistence when disabled (e.g., during backtesting)
            if not self._persist:
                return True
            positions_data = [pos.to_dict() for pos in self._positions.values()]
            self.storage.save_positions(positions_data)
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
    
    def open_position(
        self, 
        symbol: str, 
        side: str, 
        size: float, 
        entry_price: float,
        kelly_size: float
    ) -> bool:
        """Open a new position."""
        try:
            if size <= 0:
                raise ValueError("Position size must be positive")
            if entry_price <= 0:
                raise ValueError("Entry price must be positive")
            if symbol in self._positions:
                logger.warning(f"Position already exists for {symbol}")
                return False
            # Sufficient cash check for buys (opening new positions consumes cash)
            if side.upper() == "LONG":
                # Use Decimal for precise comparison with small tolerance for floating point precision
                cash_dec = Decimal(str(self.cash_balance))
                cost_dec = Decimal(str(size)) * Decimal(str(entry_price))
                tolerance = Decimal('0.01')  # Allow 1 cent tolerance for floating point precision
                if cash_dec < cost_dec - tolerance:
                    logger.warning(f"Insufficient cash to open position: need {cost_dec}, have {cash_dec}")
                    return False

            position = Position(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=entry_price,
                pnl=0.0,
                kelly_size=kelly_size,
                timestamp=datetime.utcnow()
            )
            
            self._positions[symbol] = position
            # Debit cash for LONG entry
            if side.upper() == "LONG":
                self.cash_balance = float(cash_dec - cost_dec)
            self._save_positions()
            
            logger.debug(f"Opened {side} position for {symbol}: {size} @ {entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")
            return False
    
    def close_position(self, symbol: str, exit_price: float, quantity: Optional[float] = None) -> Optional[Position]:
        """Close an existing position (fully or partially).

        Args:
            symbol: Symbol of the position to close
            exit_price: Execution price used to close
            quantity: Optional quantity to close. If None, closes full size.

        Returns:
            The updated Position if still open after a partial close, or the closed Position if fully closed.
            Returns None if validation fails.
        """
        try:
            if symbol not in self._positions:
                logger.warning(f"No position found for {symbol}")
                return None
            
            position = self._positions[symbol]
            
            # Determine close quantity
            close_qty = float(position.size) if quantity is None else float(quantity)
            if close_qty <= 0:
                logger.error("Close quantity must be positive")
                return None
            if close_qty > float(position.size) + 1e-12:
                logger.error(
                    f"Attempted to close {close_qty} which exceeds open size {position.size} for {symbol}"
                )
                return None

            # Calculate realized P&L for the portion being closed
            if position.side == "LONG":
                pnl_portion = (float(exit_price) - float(position.entry_price)) * close_qty
            else:  # SHORT (not actively used)
                pnl_portion = (float(position.entry_price) - float(exit_price)) * close_qty

            # Update cash for the closed portion (LONG credit proceeds)
            if position.side == "LONG":
                proceeds = close_qty * float(exit_price)
                self.cash_balance += proceeds

            # Reduce position size by the closed quantity
            remaining = float(position.size) - close_qty

            # Update current price
            position.current_price = float(exit_price)

            if remaining <= 1e-12:
                # Fully closed
                position.realized_pnl += pnl_portion
                position.unrealized_pnl = 0.0
                position.pnl = position.realized_pnl
                closed_position = self._positions.pop(symbol)
                self._save_positions()
                logger.debug(f"Closed {position.side} position for {symbol}: P&L = {position.pnl:.2f}")
                return closed_position
            else:
                # Partial close: update realized P&L and remaining metrics
                position.size = remaining
                position.realized_pnl += pnl_portion
                # Recompute unrealized on remaining using current price
                if position.side == "LONG":
                    position.unrealized_pnl = (float(position.current_price) - float(position.entry_price)) * position.size
                else:
                    position.unrealized_pnl = (float(position.entry_price) - float(position.current_price)) * position.size
                position.pnl = position.realized_pnl + (position.unrealized_pnl or 0.0)
                self._save_positions()
                logger.debug(
                    f"Partially closed {symbol}: closed {close_qty}, remaining {position.size}, realized {position.realized_pnl:.2f}"
                )
                return position
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None
    
    def update_position_price(self, symbol: str, current_price: float) -> bool:
        """Update current price for a position."""
        try:
            if symbol not in self._positions:
                return False
            
            position = self._positions[symbol]
            position.current_price = current_price
            
            # Calculate unrealized P&L
            if position.side == "LONG":
                position.unrealized_pnl = (current_price - position.entry_price) * position.size
            else:  # SHORT
                position.unrealized_pnl = (position.entry_price - current_price) * position.size
            
            position.pnl = position.realized_pnl + position.unrealized_pnl
            
            self._save_positions()
            return True
            
        except Exception as e:
            logger.error(f"Error updating position price for {symbol}: {e}")
            return False
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self._positions.get(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """Get all active positions."""
        return list(self._positions.values())
    
    
    def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio-level metrics."""
        try:
            if not self._positions:
                return {
                    "total_positions": 0,
                    "total_pnl": 0.0,
                    "total_unrealized_pnl": 0.0,
                    "total_realized_pnl": 0.0,
                    "portfolio_value": self.cash_balance,
                    "win_rate": 0.0
                }
            
            total_pnl = sum(pos.pnl for pos in self._positions.values())
            total_unrealized_pnl = sum(pos.unrealized_pnl or 0 for pos in self._positions.values())
            total_realized_pnl = sum(pos.realized_pnl for pos in self._positions.values())
            portfolio_value = self.cash_balance + sum(pos.market_value for pos in self._positions.values())
            
            # Calculate win rate (simplified)
            winning_positions = sum(1 for pos in self._positions.values() if pos.pnl > 0)
            win_rate = winning_positions / len(self._positions) if self._positions else 0.0
            
            return {
                "total_positions": len(self._positions),
                "total_pnl": total_pnl,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_realized_pnl": total_realized_pnl,
                "portfolio_value": portfolio_value,
                "win_rate": win_rate
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {
                "total_positions": 0,
                "total_pnl": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_realized_pnl": 0.0,
                "portfolio_value": 0.0,
                "win_rate": 0.0
            }
    
    
    def get_position_summary(self) -> pd.DataFrame:
        """Get summary of all positions."""
        try:
            if not self._positions:
                return pd.DataFrame()
            
            data = []
            for position in self._positions.values():
                data.append({
                    "symbol": position.symbol,
                    "side": position.side,
                    "size": position.size,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "pnl": position.pnl,
                    "pnl_percentage": position.pnl_percentage,
                    "kelly_size": position.kelly_size,
                    "timestamp": position.timestamp
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error creating position summary: {e}")
            return pd.DataFrame()
    
    def inject_dca_funds(self, amount: float, timestamp: datetime) -> None:
        """Inject DCA funds into cash balance.
        
        Args:
            amount: Amount to inject
            timestamp: Timestamp of injection
        """
        try:
            if amount <= 0:
                logger.warning(f"Invalid DCA injection amount: {amount}")
                return
            
            self.cash_balance += amount
            self._dca_injections.append((timestamp, amount))
            self._total_dca_injected += amount
            
            logger.debug(f"DCA injection: ${amount:.2f} at {timestamp.isoformat()}, "
                       f"total DCA: ${self._total_dca_injected:.2f}")
            
        except Exception as e:
            logger.error(f"Error injecting DCA funds: {e}")

    def get_dca_metrics(self) -> Dict[str, Any]:
        """Get DCA-related metrics.
        
        Returns:
            Dictionary with DCA metrics
        """
        return {
            "total_dca_injected": self._total_dca_injected,
            "dca_injection_count": len(self._dca_injections),
            "dca_injections": self._dca_injections.copy(),
            "initial_cash": self.cash_balance - self._total_dca_injected,
            "dca_contribution_ratio": self._total_dca_injected / max(self.cash_balance, 1e-12)
        }

    def cleanup_old_positions(self, days: int = 30):
        """Remove positions older than specified days."""
        try:
            # Use timezone-aware UTC timestamps for safe comparison with pandas Timestamps
            import pandas as pd
            cutoff_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days)
            positions_to_remove = []
            
            for symbol, position in self._positions.items():
                ts = pd.to_datetime(position.timestamp, utc=True)
                if ts < cutoff_date:
                    positions_to_remove.append(symbol)
            
            for symbol in positions_to_remove:
                del self._positions[symbol]
            
            if positions_to_remove:
                self._save_positions()
                logger.debug(f"Cleaned up {len(positions_to_remove)} old positions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old positions: {e}")
