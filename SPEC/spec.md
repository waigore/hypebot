# HypeBot - Crypto Trading Bot Specification

## Overview

HypeBot is a Python-based cryptocurrency trading bot that connects to Hyperliquid exchange, retrieves price data from configurable data providers (CoinGecko or Yahoo Finance), applies technical indicators (RSI), and manages positions using Kelly criterion for position sizing.

## Features

- **Exchange Integration**: Hyperliquid exchange via custom HTTP client
- **Data Sources**: Configurable providers (CoinGecko API, Yahoo Finance via yfinance)
- **Technical Analysis**: RSI indicator with signal generation
- **Position Management**: Kelly criterion for optimal position sizing
- **Backtesting**: Historical strategy testing with comprehensive reporting
- **Data Storage**: Organized CSV storage for historical OHLCV data
- **Utility Programs**: Command-line tools for data retrieval and backtesting

## Architecture

```
hypebot/
├── main.py                  # Main bot orchestration
├── config.py                # Configuration management
├── exchange/                # Hyperliquid integration
├── data/                    # Data providers and storage
├── indicators/              # Technical analysis (RSI)
├── position/                # Position management and Kelly criterion
├── strategy/                # Strategy interfaces and execution
├── backtesting/             # Backtesting engine and visualization
├── tests/                   # Test suite
├── histprices.py            # Historical data utility
└── backtest.py              # Backtesting utility
```

## Core Modules

### Exchange Module (`exchange/`)
- **hyperliquid_client.py**: Custom HTTP client for Hyperliquid API
- **models.py**: Order, trade, and account balance models

### Data Module (`data/`)
- **client.py**: Provider-agnostic data client interface
- **coingecko_client.py**: CoinGecko API implementation
- **yfinance_client.py**: Yahoo Finance implementation via yfinance
- **storage.py**: Historical OHLCV data storage with organized CSV files
- **models.py**: Price, market, and OHLCV data models

### Indicators Module (`indicators/`)
- **rsi_calculator.py**: RSI calculation with signal generation
- **base_indicator.py**: Abstract base class for indicators
- **models.py**: Indicator and signal models

### Position Module (`position/`)
- **manager.py**: Portfolio tracking and P&L calculation
- **kelly_criterion.py**: Kelly criterion for position sizing
- **models.py**: Position and sizing models

### Strategy Module (`strategy/`)
- **base.py**: Strategy abstract base class
- **runner.py**: Strategy execution runner
- **client.py**: Trading client interface
- **rsi_strategy.py**: RSI-based trading strategy
- **models.py**: Strategy-specific models

### Backtesting Module (`backtesting/`)
- **backtester.py**: Backtesting engine
- **metrics.py**: Performance metrics calculation
- **visualize.py**: Equity curve visualization

## Configuration

### Environment Variables

```env
# Hyperliquid Configuration
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET_KEY=your_secret_key_here
HYPERLIQUID_TESTNET=true

# Data Provider Selection
DATA_PROVIDER=yfinance  # or coingecko

# Trading Configuration
DEFAULT_SYMBOL=BTC
RSI_PERIOD=14
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
KELLY_LOOKBACK_PERIOD=30
MAX_POSITION_SIZE=0.1
MIN_POSITION_SIZE=0.001
RISK_FREE_RATE=0.02

# Storage Configuration
DATA_DIR=data
HISTORICAL_DATA_DIR=historical
```

### Dependencies

```txt
# Core Dependencies
pandas>=2.0.0
numpy>=1.24.0
httpx>=0.24.0
yfinance>=0.2.50
python-dotenv>=1.0.0
PyYAML>=6.0.0

# Exchange Integration
hyperliquid-python-sdk>=0.19.0

# Visualization
matplotlib>=3.8.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

## Data Models

### Core Models

- **OHLCVData**: Historical price data with symbol, timestamp, OHLCV values
- **TradingSignal**: RSI-based buy/sell signals with strength and metadata
- **Position**: Portfolio position with P&L tracking
- **StrategyOrder**: Position-sized orders from strategies
- **BacktestResult**: Comprehensive backtesting results with metrics

### Storage Format

Historical data is stored in organized CSV files:
- **File naming**: `{SYMBOL}_{YEAR}_{GRANULARITY}.csv`
- **Example**: `BTC-USD_2025_1d.csv`
- **Format**: Standardized OHLCV columns with UTC timestamps

## Strategy System

### Strategy Interface

Strategies implement the `Strategy` abstract base class:
- **assets**: List of symbols to trade
- **interval**: Data granularity (1h, 4h, 1d, 1w, 1mo)
- **tick()**: Main strategy logic returning StrategyOrders
- **on_start()/on_stop()**: Lifecycle hooks

### Strategy Runner

The `StrategyRunner` orchestrates strategy execution:
- Feeds time-sliced historical data to strategies
- Executes StrategyOrders via TradingClientInterface
- Updates PositionManager with executed trades
- Supports both backtest and live modes

### RSI Strategy

The default RSI strategy:
- Calculates RSI values from historical data
- Generates BUY/SELL signals based on thresholds
- Uses KellyCriterion for position sizing
- Applies risk management and signal filtering

## Backtesting

### Backtesting Engine

The `BackTester` class provides:
- Multi-strategy backtesting on historical data
- Configurable commission models (fixed fee or percentage)
- Comprehensive performance metrics
- Equity curve visualization
- Buy-and-hold baseline comparison

### Performance Metrics

- Total return (absolute and percentage)
- CAGR (Compound Annual Growth Rate)
- Sharpe ratio and Sortino ratio
- Maximum drawdown and duration
- Win rate and trade statistics
- Kelly criterion analysis

## Utility Programs

HypeBot includes two standalone utility programs:

- **Historical Data Utility** (`histprices.py`): Retrieve and persist historical price data
- **Backtesting Utility** (`backtest.py`): Run backtests on historical data

For detailed utility documentation, see [utilities.md](utilities.md).

## Installation and Setup

### Prerequisites

- Python 3.10+
- pipenv (recommended) or pip

### Setup

1. **Clone and install**:
   ```bash
   git clone <repository-url>
   cd hypebot
   pipenv install
   ```

2. **Configure environment**:
   ```bash
   cp hypebot/env.example .env
   # Edit .env with your API keys
   ```

3. **Run the bot**:
   ```bash
   python -m hypebot
   ```

### Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest hypebot/tests/

# Run linting
black .
flake8 .
mypy .
```

## Testing Strategy

### Unit Tests
- Module-specific tests with mocked dependencies
- RSI calculation validation
- Kelly criterion testing
- API client conformance testing

### Integration Tests
- End-to-end data flow testing
- Strategy execution testing
- Backtesting validation
- Error handling scenarios

## Key Design Principles

### Separation of Concerns
- **Strategies**: Handle trading logic and position sizing
- **StrategyRunner**: Executes orders and manages data flow
- **PositionManager**: Tracks portfolio state only
- **Data Clients**: Provide unified interface to data sources

### Configuration Management
- Environment variable-based configuration
- Provider-agnostic data access
- Flexible strategy parameters

### Error Handling
- Comprehensive exception hierarchy
- Graceful degradation
- Detailed logging and monitoring

## Implementation Status

✅ **Completed**:
- Core module structure
- Data providers (CoinGecko, Yahoo Finance)
- RSI indicator implementation
- Kelly criterion position sizing
- Strategy system with RSI strategy
- Backtesting engine
- Utility programs
- Comprehensive testing

🔄 **In Progress**:
- Live trading integration
- Advanced strategy implementations
- Performance optimizations

## Next Steps

1. Complete live trading integration
2. Add more technical indicators
3. Implement additional strategies
4. Enhance risk management features
5. Add real-time monitoring dashboard
