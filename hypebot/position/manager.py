"""Position manager for tracking and managing trading positions."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd

from .models import Position, PositionSize
from .kelly_criterion import KellyCriterion
from ..config import TradingConfig
from ..data.storage import DataStorage


logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions and risk."""
    
    def __init__(self, config: TradingConfig, storage: DataStorage):
        """Initialize position manager."""
        self.config = config
        self.storage = storage
        self.kelly_criterion = KellyCriterion(config)
        self._positions: Dict[str, Position] = {}
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
            if symbol in self._positions:
                logger.warning(f"Position already exists for {symbol}")
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
            self._save_positions()
            
            logger.info(f"Opened {side} position for {symbol}: {size} @ {entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")
            return False
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[Position]:
        """Close an existing position."""
        try:
            if symbol not in self._positions:
                logger.warning(f"No position found for {symbol}")
                return None
            
            position = self._positions[symbol]
            
            # Calculate final P&L
            if position.side == "LONG":
                pnl = (exit_price - position.entry_price) * position.size
            else:  # SHORT
                pnl = (position.entry_price - exit_price) * position.size
            
            # Update position with final values
            position.current_price = exit_price
            position.pnl = pnl
            position.realized_pnl = pnl
            position.unrealized_pnl = 0.0
            
            # Remove from active positions
            closed_position = self._positions.pop(symbol)
            self._save_positions()
            
            logger.info(f"Closed {position.side} position for {symbol}: P&L = {pnl:.2f}")
            return closed_position
            
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
    
    def calculate_position_size(
        self, 
        symbol: str, 
        current_price: float, 
        signal_strength: float = 1.0,
        confidence: float = 1.0
    ) -> PositionSize:
        """Calculate optimal position size using Kelly Criterion."""
        try:
            # Get historical price data
            price_data = self.storage.load_price_data(symbol=symbol)
            if price_data.empty:
                logger.warning(f"No historical data for {symbol}")
                return PositionSize(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    recommended_size=0.0,
                    kelly_fraction=0.0,
                    max_position_size=self.config.max_position_size,
                    current_price=current_price,
                    confidence=0.0,
                    risk_level="HIGH"
                )
            
            # Calculate returns
            returns = price_data['price'].pct_change().dropna()
            
            # Calculate position size
            position_size = self.kelly_criterion.calculate_position_size(
                symbol=symbol,
                current_price=current_price,
                historical_returns=returns,
                signal_strength=signal_strength,
                confidence=confidence
            )
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return PositionSize(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                recommended_size=0.0,
                kelly_fraction=0.0,
                max_position_size=self.config.max_position_size,
                current_price=current_price,
                confidence=0.0,
                risk_level="HIGH"
            )
    
    def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio-level metrics."""
        try:
            if not self._positions:
                return {
                    "total_positions": 0,
                    "total_pnl": 0.0,
                    "total_unrealized_pnl": 0.0,
                    "total_realized_pnl": 0.0,
                    "portfolio_value": 0.0,
                    "win_rate": 0.0
                }
            
            total_pnl = sum(pos.pnl for pos in self._positions.values())
            total_unrealized_pnl = sum(pos.unrealized_pnl or 0 for pos in self._positions.values())
            total_realized_pnl = sum(pos.realized_pnl for pos in self._positions.values())
            portfolio_value = sum(pos.market_value for pos in self._positions.values())
            
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
    
    def check_risk_limits(self, symbol: str, position_size: float) -> Tuple[bool, str]:
        """Check if position size is within risk limits."""
        try:
            # Get current position if exists
            current_position = self.get_position(symbol)
            if current_position:
                total_size = current_position.size + position_size
            else:
                total_size = position_size
            
            # Check against maximum position size
            if total_size > self.config.max_position_size:
                return False, f"Position size {total_size} exceeds maximum {self.config.max_position_size}"
            
            # Check against minimum position size
            if position_size < self.config.min_position_size:
                return False, f"Position size {position_size} below minimum {self.config.min_position_size}"
            
            return True, "Position size is within limits"
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return False, f"Error checking risk limits: {e}"
    
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
    
    def cleanup_old_positions(self, days: int = 30):
        """Remove positions older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            positions_to_remove = []
            
            for symbol, position in self._positions.items():
                if position.timestamp < cutoff_date:
                    positions_to_remove.append(symbol)
            
            for symbol in positions_to_remove:
                del self._positions[symbol]
            
            if positions_to_remove:
                self._save_positions()
                logger.info(f"Cleaned up {len(positions_to_remove)} old positions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old positions: {e}")
