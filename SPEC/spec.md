# HypeBot - Crypto Trading Bot Specification

## Overview

HypeBot is a Python-based cryptocurrency trading bot that connects to Hyperliquid exchange, retrieves price data from configurable data providers (CoinGecko or Yahoo Finance), applies technical indicators (RSI), and manages positions using Kelly criterion for position sizing.

## Features

- **Exchange Integration**: Hyperliquid exchange via custom HTTP client
- **Data Sources**: Configurable providers (CoinGecko API, Yahoo Finance via yfinance)
- **Technical Analysis**: RSI indicator with signal generation
- **Position Management**: Kelly criterion for optimal position sizing
- **Backtesting**: Historical strategy testing with comprehensive reporting
- **DCA Support**: Dollar Cost Averaging mode with configurable frequencies and amounts
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
- **ema (planned/added)**: EMA calculation used by hybrid strategies

### Position Module (`position/`)
- **manager.py**: Portfolio tracking and P&L calculation
  - Maintains a dedicated cash position when initialized with starting cash
  - Updates cash when asset positions are opened/closed (debits on buys, credits on sells)
  - Prevents opening positions without sufficient cash; raises an error
  - Prevents closing more than the held asset amount; raises an error
- **kelly_criterion.py**: Kelly criterion for position sizing
- **models.py**: Position and sizing models

### Strategy Module (`strategy/`)
- **base.py**: Strategy abstract base class
- **runner.py**: Strategy execution runner
- **client.py**: Trading client interface
- **rsi_strategy.py**: RSI-based trading strategy
- **hybrid_rsi_ema (spec)**: Trend-filtered RSI+EMA hybrid strategy (all-in/all-out)
- **models.py**: Strategy-specific models

### Backtesting Module (`backtesting/`)
- **backtester.py**: Backtesting engine with DCA support
- **metrics.py**: Performance metrics calculation
- **visualize.py**: Equity curve visualization with control strategy comparison
- **dca_scheduler.py**: DCA schedule calculation and management

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
- **BacktestResult**: Comprehensive backtesting results with metrics and position history
- **DCAConfig**: DCA configuration with frequency, amount, and date ranges
- **DCASchedule**: Pre-calculated DCA injection dates and amounts

### Storage Format

Historical data is stored in organized CSV files:
- **File naming**: `{SYMBOL}_{YEAR}_{GRANULARITY}.csv`
- **Example**: `BTC-USD_2025_1d.csv`
- **Format**: Standardized OHLCV columns with UTC timestamps

### Position Data Format

Position tracking data is exported as CSV files with the following structure:
- **File naming**: `positions_{strategy_name}.csv`
- **Example**: `positions_RSIStrategy.csv`
- **Format**: One row per tick, containing:
  - `timestamp`: UTC timestamp of the tick
  - `symbol`: Asset symbol (e.g., "SOL-USD")
  - `side`: Position side ("LONG" or "SHORT")
  - `size`: Position size in units
  - `entry_price`: Price at which position was opened
  - `current_price`: Current market price at this tick
  - `pnl`: Total P&L (realized + unrealized)
  - `realized_pnl`: P&L from closed portions
  - `unrealized_pnl`: P&L from open position
  - `pnl_percentage`: P&L as percentage of entry value
  - `kelly_size`: Kelly criterion recommended size
  - `market_value`: Current market value (size × current_price)
  - `entry_value`: Entry value (size × entry_price)
  - `position_timestamp`: When position was originally opened
  - `cash_balance`: Current cash balance
- **Empty rows**: When no positions are held, only timestamp and cash_balance are populated

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

### Trading Strategies

All implemented trading strategies are documented in [strategies.md](strategies.md).

Included strategies:
- RSI Strategy: RSI-based momentum with Kelly position sizing
- RSI + EMA Hybrid: Trend-filtered momentum using RSI(14) and EMA(20), all-in entries and full exits per rules

## Backtesting

### Backtesting Engine

The `BackTester` class provides:
- Multi-strategy backtesting on historical data
- Configurable commission models (fixed fee or percentage)
- DCA mode with periodic cash injections
- Comprehensive performance metrics
- Equity curve visualization
- Buy-and-hold baseline comparison
- Detailed position tracking with CSV export per tick

#### Equity Calculation
- Equity at each tick is the sum of:
  - Mark-to-market value of all open asset positions, and
  - Current cash position balance
- The backtester records this equity on every step to produce the equity curve.

#### Position Tracking
- The backtester captures detailed position data for each strategy at every tick
- Position data includes all available information from the position manager:
  - Symbol, side (LONG/SHORT), size, entry price, current price
  - P&L (total, realized, unrealized), P&L percentage
  - Kelly size, market value, entry value
  - Timestamp of position creation and last update
  - Current cash balance
- This position data is exported as CSV files with one row per tick per strategy
- File naming: `positions_{strategy_name}.csv`
- Enables detailed analysis of position evolution throughout the backtest period

#### DCA Mode Integration

When DCA mode is enabled, the backtesting system:

**DCA Schedule Generation**:
- Calculates injection dates based on frequency and date ranges
- Aligns injections with actual trading days (no weekends/holidays)
- Stores schedule as sorted list of timestamps for efficient lookup

**Cash Injection Process**:
- Before each tick, checks if current timestamp matches DCA schedule
- Injects specified DCA amount into position manager's cash balance
- Logs DCA injections for tracking and debugging
- Makes funds immediately available to strategies

**Strategy Integration**:
- All strategies access current cash balance through position manager
- No assumptions about "starting cash" - always use current balance
- DCA funds become part of total available capital for position sizing
- Buy-and-Hold strategy automatically purchases with new DCA funds

**DCA Reporting**:
- Tracks total DCA injections vs. initial capital
- Calculates DCA contribution ratios in performance metrics
- Shows DCA injection timeline in backtest results
- Includes DCA parameters in saved configuration

### Backtest Output Files

The backtesting system generates the following files for each strategy:
- **Equity Curve**: `equity_{strategy_name}.csv` - Portfolio value over time
- **Position History**: `positions_{strategy_name}.csv` - Detailed position data per tick
- **Trade Log**: `trades_{strategy_name}.csv` - Individual trade executions
- **Performance Metrics**: `metrics_{strategy_name}.json` - Calculated performance statistics
- **Visualization**: `equity_{strategy_name}.png` - Equity curve plot

#### Validity of trading strategy orders
- If the strategy being backtested issues orders that are incompatible with their overall portfolio positions (e.g. opening asset positions without sufficient cash, closing asset positions without sufficient asset sizes), such actions are marked as errors and the backtesting stopped immediately
- The errors are accessible as part of the backtesting result

### Control Strategy Integration

The backtesting system automatically includes a Buy-and-Hold control strategy:

- **Automatic Creation**: The `BackTester` creates and runs a Buy-and-Hold strategy instance alongside any specified strategies
- **Equal Treatment**: The control strategy uses the same starting cash, commission model, and data as other strategies
- **Performance Baseline**: Provides a simple market performance benchmark for comparison
- **Multi-Asset Support**: When multiple assets are specified, the control strategy distributes cash equally across all assets

### Performance Metrics

- Total return (absolute and percentage)
- CAGR (Compound Annual Growth Rate)
- Sharpe ratio and Sortino ratio
- Maximum drawdown and duration
- Win rate and trade statistics
- Kelly criterion analysis
- DCA metrics (when DCA enabled):
  - Total DCA injections
  - DCA contribution ratio (DCA vs. initial capital)
  - DCA injection count and timeline

### HTML Report Generation

The backtesting system generates comprehensive HTML reports that include:

- **Side-by-Side Comparison**: All strategies (including Buy-and-Hold control) displayed in comparison tables
- **Performance Metrics Table**: Key metrics for each strategy in tabular format for easy comparison
- **Strategy Rankings**: Performance rankings across different metrics (return, Sharpe ratio, etc.)
- **Trade Analysis**: Detailed trade statistics and win/loss analysis per strategy
- **Configuration Summary**: Complete backtest configuration and parameters used
- **Interactive Elements**: Sortable tables and expandable sections for detailed analysis

### Equity Curve Visualization

The backtesting system generates comprehensive equity curve plots that include:

- **Multi-Strategy Lines**: All backtested strategies displayed as separate lines on the same plot
- **Buy-and-Hold Baseline**: Control strategy line always included for performance comparison
- **Color-Coded Legend**: Distinct colors and styles for each strategy with clear labeling
- **Interactive Features**: Hover tooltips showing exact values and dates
- **Performance Annotations**: Key performance milestones and drawdown periods highlighted
- **Export Formats**: High-resolution PNG and SVG formats for reports and presentations

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

📋 **Planned**:
- DCA mode implementation
- Enhanced DCA reporting and analytics

## Next Steps

1. Implement DCA mode with schedule calculation and cash injection
2. Complete live trading integration
3. Add more technical indicators
4. Implement additional strategies
5. Enhance risk management features
6. Add real-time monitoring dashboard
