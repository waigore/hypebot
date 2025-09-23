"""Main orchestration script for HypeBot trading bot."""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd

from .config import Config
from .data import DataClient, DataStorage
from .indicators import RSICalculator
from .position import PositionManager
from .exchange import HyperliquidClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hypebot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class HypeBot:
    """Main trading bot class."""
    
    def __init__(self, config: Config):
        """Initialize HypeBot."""
        self.config = config
        self.running = False
        
        # Initialize components
        self.data_client = DataClient(config)
        self.data_storage = DataStorage(config.database)
        self.rsi_calculator = RSICalculator(
            period=config.trading.rsi_period,
            oversold_threshold=config.trading.rsi_oversold,
            overbought_threshold=config.trading.rsi_overbought
        )
        self.position_manager = PositionManager(config.trading, self.data_storage)
        self.hyperliquid_client = HyperliquidClient(config.hyperliquid)
        
        # Trading state
        self.current_symbol = config.trading.default_symbol
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown = timedelta(minutes=5)  # 5-minute cooldown between signals
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize the bot and test connections."""
        try:
            logger.info("Initializing HypeBot...")
            
            # Test CoinGecko connection
            async with self.data_client as client:
                price_data = await client.get_price(self.current_symbol)
                if not price_data:
                    logger.error("Failed to connect to CoinGecko API")
                    return False
                logger.info(f"CoinGecko connection successful. {self.current_symbol} price: ${price_data.price}")
            
            # Test Hyperliquid connection
            async with self.hyperliquid_client as client:
                if not await client.test_connection():
                    logger.error("Failed to connect to Hyperliquid API")
                    return False
                logger.info("Hyperliquid connection successful")
            
            # Load existing positions
            positions = self.position_manager.get_all_positions()
            logger.info(f"Loaded {len(positions)} existing positions")
            
            logger.info("HypeBot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing HypeBot: {e}")
            return False
    
    async def run(self):
        """Main trading loop."""
        try:
            if not await self.initialize():
                logger.error("Failed to initialize HypeBot")
                return
            
            self.running = True
            logger.info("Starting HypeBot trading loop...")
            
            while self.running:
                try:
                    await self._trading_cycle()
                    await asyncio.sleep(60)  # Wait 1 minute between cycles
                    
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    await asyncio.sleep(30)  # Wait 30 seconds before retrying
            
            logger.info("HypeBot stopped")
            
        except Exception as e:
            logger.error(f"Fatal error in HypeBot: {e}")
        finally:
            await self._cleanup()
    
    async def _trading_cycle(self):
        """Execute one trading cycle."""
        try:
            # Get current price data
            async with self.data_client as client:
                price_data = await client.get_price(self.current_symbol)
                if not price_data:
                    logger.warning(f"Failed to get price data for {self.current_symbol}")
                    return
                
                # Save price data
                self.data_storage.save_price_data([price_data])
            
            # Get historical data for RSI calculation
            historical_data = self.data_storage.load_price_data(
                symbol=self.current_symbol,
                start_date=datetime.utcnow() - timedelta(days=30)
            )
            
            if len(historical_data) < self.config.trading.rsi_period + 1:
                logger.warning(f"Insufficient historical data for {self.current_symbol}")
                return
            
            # Calculate RSI and generate signals
            rsi_results = self.rsi_calculator.calculate(historical_data)
            if not rsi_results:
                logger.warning("No RSI results generated")
                return
            
            latest_rsi = rsi_results[-1]
            logger.info(f"Latest RSI for {self.current_symbol}: {latest_rsi.value:.2f}")
            
            # Generate trading signal
            signal = self.rsi_calculator.generate_signal(
                current_value=latest_rsi.value,
                previous_value=latest_rsi.metadata.get("previous_rsi") if latest_rsi.metadata else None,
                metadata={"symbol": self.current_symbol}
            )
            
            if signal and self._should_process_signal(signal):
                await self._process_signal(signal, price_data.price)
            
            # Update existing positions
            await self._update_positions()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def _should_process_signal(self, signal) -> bool:
        """Check if signal should be processed based on cooldown and other criteria."""
        if not signal:
            return False
        
        # Check cooldown
        if (self.last_signal_time and 
            datetime.utcnow() - self.last_signal_time < self.signal_cooldown):
            logger.info(f"Signal cooldown active, ignoring {signal.signal_type} signal")
            return False
        
        # Check signal strength
        if signal.strength < 0.3:  # Minimum signal strength
            logger.info(f"Signal strength too low: {signal.strength}")
            return False
        
        return True
    
    async def _process_signal(self, signal, current_price: float):
        """Process a trading signal."""
        try:
            logger.info(f"Processing {signal.signal_type} signal for {signal.symbol} (strength: {signal.strength:.2f})")
            
            # Calculate position size
            position_size = self.position_manager.calculate_position_size(
                symbol=signal.symbol,
                current_price=current_price,
                signal_strength=signal.strength,
                confidence=signal.strength
            )
            
            if position_size.recommended_size <= 0:
                logger.info("Position size too small, skipping trade")
                return
            
            # Check risk limits
            is_valid, message = self.position_manager.check_risk_limits(
                signal.symbol, 
                position_size.recommended_size
            )
            
            if not is_valid:
                logger.warning(f"Position size validation failed: {message}")
                return
            
            # Execute trade
            if signal.signal_type == "BUY":
                await self._execute_buy(signal.symbol, position_size, current_price)
            elif signal.signal_type == "SELL":
                await self._execute_sell(signal.symbol, position_size, current_price)
            
            # Save signal
            self.data_storage.save_signals([signal.to_dict()])
            self.last_signal_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _execute_buy(self, symbol: str, position_size, current_price: float):
        """Execute a buy order."""
        try:
            # Check if we already have a position
            existing_position = self.position_manager.get_position(symbol)
            if existing_position and existing_position.side == "LONG":
                logger.info(f"Already have LONG position for {symbol}, skipping buy")
                return
            
            # Close existing short position if any
            if existing_position and existing_position.side == "SHORT":
                logger.info(f"Closing existing SHORT position for {symbol}")
                closed_position = self.position_manager.close_position(symbol, current_price)
                if closed_position:
                    logger.info(f"Closed SHORT position: P&L = {closed_position.pnl:.2f}")
            
            # Place buy order
            async with self.hyperliquid_client as client:
                order = await client.place_order(
                    symbol=symbol,
                    side="BUY",
                    order_type="MARKET",
                    quantity=position_size.recommended_size,
                    price=current_price
                )
                
                if order:
                    # Open new position
                    self.position_manager.open_position(
                        symbol=symbol,
                        side="LONG",
                        size=position_size.recommended_size,
                        entry_price=current_price,
                        kelly_size=position_size.kelly_fraction
                    )
                    logger.info(f"Buy order executed: {position_size.recommended_size} {symbol} @ ${current_price}")
                else:
                    logger.error(f"Failed to execute buy order for {symbol}")
            
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
    
    async def _execute_sell(self, symbol: str, position_size, current_price: float):
        """Execute a sell order."""
        try:
            # Check if we have a position to sell
            existing_position = self.position_manager.get_position(symbol)
            if not existing_position or existing_position.side != "LONG":
                logger.info(f"No LONG position to sell for {symbol}")
                return
            
            # Place sell order
            async with self.hyperliquid_client as client:
                order = await client.place_order(
                    symbol=symbol,
                    side="SELL",
                    order_type="MARKET",
                    quantity=existing_position.size,
                    price=current_price
                )
                
                if order:
                    # Close position
                    closed_position = self.position_manager.close_position(symbol, current_price)
                    if closed_position:
                        logger.info(f"Sell order executed: P&L = {closed_position.pnl:.2f}")
                else:
                    logger.error(f"Failed to execute sell order for {symbol}")
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
    
    async def _update_positions(self):
        """Update current prices for all positions."""
        try:
            positions = self.position_manager.get_all_positions()
            
            for position in positions:
                # Get current price
                async with self.data_client as client:
                    price_data = await client.get_price(position.symbol)
                    if price_data:
                        self.position_manager.update_position_price(
                            position.symbol, 
                            price_data.price
                        )
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    async def _cleanup(self):
        """Cleanup resources."""
        try:
            # Save final state
            self.position_manager._save_positions()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point."""
    try:
        # Load configuration
        config = Config.from_env()
        config.validate()
        
        # Create and run bot
        bot = HypeBot(config)
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
