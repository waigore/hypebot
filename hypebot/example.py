"""Example script demonstrating HypeBot usage."""

import asyncio
import logging
from datetime import datetime, timedelta

from hypebot.config import Config
from hypebot.data import DataClient, DataStorage
from hypebot.indicators import RSICalculator
from hypebot.position import PositionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_usage():
    """Example of how to use HypeBot components."""
    
    # Load configuration
    config = Config.from_env()
    
    # Initialize components
    data_client = DataClient(config)
    data_storage = DataStorage(config.database)
    rsi_calculator = RSICalculator(
        period=config.trading.rsi_period,
        oversold_threshold=config.trading.rsi_oversold,
        overbought_threshold=config.trading.rsi_overbought
    )
    position_manager = PositionManager(config.trading, data_storage)
    
    try:
        # Example 1: Get price data
        logger.info("=== Getting Price Data ===")
        async with data_client as client:
            price_data = await client.get_spot_price("BTC")
            if price_data:
                logger.info(f"BTC Price: ${price_data.price:,.2f}")
                logger.info(f"Volume 24h: ${price_data.volume_24h:,.2f}")
                logger.info(f"Market Cap: ${price_data.market_cap:,.2f}")
                
                # Save price data
                data_storage.save_price_data([price_data])
        
        # Example 2: Calculate RSI
        logger.info("\n=== Calculating RSI ===")
        
        # Get historical data
        historical_data = data_storage.load_price_data(
            symbol="BTC",
            start_date=datetime.utcnow() - timedelta(days=30)
        )
        
        if len(historical_data) >= rsi_calculator.period + 1:
            rsi_results = rsi_calculator.calculate(historical_data)
            if rsi_results:
                latest_rsi = rsi_results[-1]
                logger.info(f"Latest RSI: {latest_rsi.value:.2f}")
                logger.info(f"RSI Level: {rsi_calculator.get_rsi_interpretation(latest_rsi.value)}")
                
                # Generate signal
                signal = rsi_calculator.generate_signal(
                    current_value=latest_rsi.value,
                    previous_value=latest_rsi.metadata.get("previous_rsi") if latest_rsi.metadata else None,
                    metadata={"symbol": "BTC"}
                )
                
                if signal:
                    logger.info(f"Trading Signal: {signal.signal_type}")
                    logger.info(f"Signal Strength: {signal.strength:.2f}")
                else:
                    logger.info("No trading signal generated")
        
        # Example 3: Position sizing
        logger.info("\n=== Position Sizing ===")
        
        if not historical_data.empty:
            returns = historical_data['price'].pct_change().dropna()
            position_size = position_manager.calculate_position_size(
                symbol="BTC",
                current_price=price_data.price if price_data else 50000.0,
                signal_strength=0.8,
                confidence=0.9
            )
            
            logger.info(f"Recommended Position Size: {position_size.recommended_size:.4f}")
            logger.info(f"Kelly Fraction: {position_size.kelly_fraction:.4f}")
            logger.info(f"Risk Level: {position_size.risk_level}")
            logger.info(f"Position Value: ${position_size.position_value:,.2f}")
        
        # Example 4: Portfolio metrics
        logger.info("\n=== Portfolio Metrics ===")
        metrics = position_manager.calculate_portfolio_metrics()
        logger.info(f"Total Positions: {metrics['total_positions']}")
        logger.info(f"Total P&L: ${metrics['total_pnl']:,.2f}")
        logger.info(f"Portfolio Value: ${metrics['portfolio_value']:,.2f}")
        logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
        
    except Exception as e:
        logger.error(f"Error in example: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
