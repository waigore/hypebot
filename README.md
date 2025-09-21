# HypeBot - Crypto Trading Bot

A Python-based cryptocurrency trading bot that connects to Hyperliquid exchange, retrieves price data from CoinGecko API, applies technical indicators (RSI), and manages positions using Kelly criterion for position sizing.

## Features

- **Exchange Integration**: Connects to Hyperliquid exchange for trading operations
- **Price Data**: Retrieves real-time and historical price data from CoinGecko API
- **Technical Analysis**: Implements RSI (Relative Strength Index) indicator for signal generation
- **Position Management**: Uses Kelly Criterion for optimal position sizing
- **Data Storage**: Local data persistence using Pandas DataFrames
- **Risk Management**: Built-in risk controls and position limits
- **Modular Design**: Clean separation of concerns with independent modules

## Architecture

```
hypebot/
├── exchange/           # Hyperliquid exchange integration
│   ├── hyperliquid_client.py
│   └── models.py
├── data/              # Price data and storage
│   ├── coingecko_client.py
│   ├── storage.py
│   └── models.py
├── indicators/        # Technical analysis
│   ├── rsi_calculator.py
│   ├── base_indicator.py
│   └── models.py
├── position/          # Position management
│   ├── manager.py
│   ├── kelly_criterion.py
│   └── models.py
├── tests/             # Test suite
├── config.py          # Configuration management
├── main.py            # Main orchestration
└── __main__.py        # Module entry point
```

## Installation

### Prerequisites

- Python 3.10+
- pipenv (recommended) or pip

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd hypebot
   ```

2. **Install dependencies**:
   ```bash
   pipenv install
   # or
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp hypebot/env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Configure API keys**:
   Edit the `.env` file with your credentials:
   ```env
   # Hyperliquid Configuration
   HYPERLIQUID_API_KEY=your_api_key_here
   HYPERLIQUID_SECRET_KEY=your_secret_key_here
   HYPERLIQUID_TESTNET=true
   
   # CoinGecko Configuration
   COINGECKO_API_KEY=your_coingecko_api_key
   
   # Trading Configuration
   DEFAULT_SYMBOL=BTC
   RSI_PERIOD=14
   RSI_OVERSOLD=30
   RSI_OVERBOUGHT=70
   MAX_POSITION_SIZE=0.1
   ```

## Usage

### Running the Bot

```bash
# Using pipenv
pipenv run python -m hypebot

# Using python directly
python -m hypebot

# Or run the main script directly
python hypebot/main.py
```

### Configuration

The bot can be configured through environment variables or by modifying the `config.py` file. Key configuration options:

- **Trading Parameters**:
  - `DEFAULT_SYMBOL`: Default trading symbol (e.g., BTC, ETH)
  - `RSI_PERIOD`: RSI calculation period (default: 14)
  - `RSI_OVERSOLD`: RSI oversold threshold (default: 30)
  - `RSI_OVERBOUGHT`: RSI overbought threshold (default: 70)
  - `MAX_POSITION_SIZE`: Maximum position size as fraction of account (default: 0.1)

- **Risk Management**:
  - `KELLY_LOOKBACK_PERIOD`: Historical data period for Kelly calculation (default: 30)
  - `MIN_POSITION_SIZE`: Minimum position size (default: 0.001)
  - `RISK_FREE_RATE`: Risk-free rate for Kelly calculation (default: 0.02)

### Trading Strategy

The bot implements the following trading strategy:

1. **Data Collection**: Fetches price data from CoinGecko API
2. **Technical Analysis**: Calculates RSI indicator
3. **Signal Generation**: Generates BUY/SELL signals based on RSI levels
4. **Position Sizing**: Uses Kelly Criterion to determine optimal position size
5. **Risk Management**: Applies position limits and risk controls
6. **Order Execution**: Places orders on Hyperliquid exchange

### RSI Strategy

- **BUY Signal**: When RSI < 30 (oversold) and rising
- **SELL Signal**: When RSI > 70 (overbought) and falling
- **Signal Strength**: Based on how far RSI is from threshold levels
- **Cooldown**: 5-minute cooldown between signals to prevent overtrading

### Kelly Criterion

The bot uses Kelly Criterion for position sizing:

- Calculates optimal position size based on historical returns
- Considers signal strength and confidence levels
- Applies maximum position size limits
- Adjusts for correlation between assets (in portfolio mode)

## Testing

Run the test suite:

```bash
# Using pipenv
pipenv run pytest

# Using python directly
pytest hypebot/tests/
```

### Test Coverage

- **RSI Calculator**: Tests RSI calculation and signal generation
- **Kelly Criterion**: Tests position sizing calculations
- **Data Storage**: Tests data persistence and retrieval
- **Exchange Client**: Tests API integration (with mocks)

## Data Storage

The bot stores data locally in CSV format:

- `data/price_data.csv`: Historical price data
- `data/positions.csv`: Trading positions
- `data/trades.csv`: Executed trades
- `data/signals.csv`: Generated trading signals

## Logging

The bot provides comprehensive logging:

- **File Logging**: Logs saved to `hypebot.log`
- **Console Logging**: Real-time output to console
- **Log Levels**: INFO, WARNING, ERROR levels
- **Structured Logging**: Timestamped and categorized messages

## Risk Management

Built-in risk management features:

- **Position Limits**: Maximum position size per symbol
- **Signal Cooldown**: Prevents overtrading
- **Kelly Criterion**: Optimal position sizing
- **Stop Loss**: Automatic position closure on adverse moves
- **Portfolio Limits**: Maximum total exposure

## Development

### Code Structure

- **Modular Design**: Each component is independently testable
- **Type Hints**: Full type annotation for better code quality
- **Error Handling**: Comprehensive error handling and logging
- **Configuration**: Centralized configuration management

### Adding New Indicators

To add new technical indicators:

1. Create a new class inheriting from `BaseIndicator`
2. Implement `calculate()` and `generate_signal()` methods
3. Add to the indicators module
4. Update the main trading loop

### Adding New Exchanges

To add support for new exchanges:

1. Create a new client class similar to `HyperliquidClient`
2. Implement required methods (place_order, get_positions, etc.)
3. Add to the exchange module
4. Update configuration

## Disclaimer

**This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always do your own research and consider your risk tolerance before trading.**

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For questions and support:

- Create an issue on GitHub
- Check the documentation
- Review the test cases for usage examples

## Changelog

### v1.0.0
- Initial release
- Hyperliquid exchange integration
- CoinGecko API integration
- RSI indicator implementation
- Kelly Criterion position sizing
- Local data storage
- Comprehensive test suite
