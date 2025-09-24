# HypeBot Utility Programs

This document describes the standalone utility programs that complement the main HypeBot trading system.

## Historical Price Data Utility (histprices.py)

A standalone command-line utility for retrieving and persisting historical price data using the hypebot data infrastructure.

### Purpose
- Retrieve historical OHLCV data for specified symbols
- Persist data locally using the organized CSV storage system
- Support multiple data providers (yfinance default, CoinGecko)
- Provide flexible time period and interval configuration

### Command Line Interface
```bash
python histprices.py <symbol> [--period PERIOD] [--interval INTERVAL] [--provider PROVIDER] [--output-dir OUTPUT_DIR]
```

### Arguments and Options
- **symbol** (required): Trading symbol (e.g., "BTC-USD", "ETH-USD", "AAPL")
- **--period, -p** (optional): Time period for data retrieval (default: "1y")
  - Valid values: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
- **--interval, -i** (optional): Data granularity/interval (default: "1d")
  - Valid values: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
- **--provider, -pr** (optional): Data provider selection (default: "yfinance")
  - Valid values: "yfinance", "coingecko"
- **--output-dir, -o** (optional): Custom output directory (default: uses DATA_DIR from config)
- **--help, -h**: Display help message

### Usage Examples
```bash
# Basic usage - get 1 year of daily BTC-USD data
python histprices.py BTC-USD

# Get 6 months of hourly ETH data
python histprices.py ETH-USD --period 6mo --interval 1h

# Use CoinGecko provider for crypto data
python histprices.py BTC-USD --provider coingecko --period 2y

# Custom output directory
python histprices.py AAPL --output-dir ./my_data --period 1mo --interval 1d
```

### Implementation Details
- **Data Provider Integration**: Uses the existing `DataClientInterface` and factory pattern
- **Storage Integration**: Leverages `DataStorage` class for organized CSV persistence
- **Configuration**: Reads from environment variables and config files (same as main bot)
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Progress Indication**: Shows progress for long-running operations
- **Data Validation**: Validates symbol format and parameter combinations

### File Organization
- **Input Validation**: Validates symbol format and parameter combinations
- **Provider Selection**: Uses `DataClientFactory` to create appropriate client
- **Data Retrieval**: Calls `get_historical_ohlcv()` method with specified parameters
- **Storage**: Uses `DataStorage.save_historical_ohlcv()` for organized CSV storage
- **Output**: Provides summary of retrieved data (records count, date range, file location)

### Error Handling
- **Invalid Symbol**: Clear error message for unsupported symbols
- **Provider Errors**: Handles rate limiting, authentication, and temporary failures
- **Parameter Validation**: Validates period/interval combinations
- **Storage Errors**: Handles file system and permission issues
- **Network Issues**: Provides retry logic and timeout handling

### Output Format
- **Console Output**: Progress indicators and summary statistics
- **File Storage**: Organized CSV files following existing naming convention
- **Logging**: Configurable logging to file and console
- **Summary**: Final report with data retrieval statistics

### Integration with Existing Modules
- **Data Client**: Uses existing `DataClientInterface` implementations
- **Storage**: Leverages `DataStorage` for consistent file organization
- **Configuration**: Uses shared `Config` classes and environment variables
- **Models**: Utilizes `OHLCVData` models for data consistency
- **Logging**: Integrates with existing logging infrastructure

## Backtesting Utility (backtest.py)

A standalone command-line utility for running backtests on historical data using the hypebot strategy and backtesting infrastructure.

### Purpose
- Run backtests on historical data using configurable strategies
- Support multiple assets and time periods
- Generate comprehensive performance reports and visualizations
- Provide flexible configuration through command-line arguments or config files
- Enable debugging and profiling information for strategy analysis

### Command Line Interface
```bash
python backtest.py [OPTIONS] [--config CONFIG_FILE]
```

### Arguments and Options
- **--assets, -a** (required): Comma-separated list of trading symbols (e.g., "BTC-USD,ETH-USD")
- **--strategy, -s** (required): Strategy name to use for backtesting
  - Valid values: "rsi", "buy_and_hold" (extensible for future strategies)
  - Note: Buy-and-hold control strategy is automatically included in all backtests
  - Planned/added: "rsi_ema_hybrid" for trend-filtered momentum
- **--interval, -i** (optional): Data granularity/interval (default: "1d")
  - Valid values: "1h", "4h", "1d", "1w", "1mo"
- **--start-date, --start** (optional): Start date for backtest (default: earliest available data)
  - Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
- **--end-date, --end** (optional): End date for backtest (default: latest available data)
  - Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
- **--starting-cash, --cash** (optional): Starting cash balance (default: 10000.0)
- **--commission** (optional): Commission model (default: "percent:0.001")
  - Format: "fixed:0.5" or "percent:0.001"
- **--config, -c** (optional): Path to configuration file with backtest parameters
- **--no-plot** (optional): Suppress equity curve plot generation
- **--debug** (optional): Show profiling and debugging information
- **--output-dir, -o** (optional): Output directory for results and plots (default: "./backtest_results")
- **--help, -h**: Display help message

### Configuration File Format
The utility supports YAML configuration files for complex backtest setups:

```yaml
# backtest_config.yaml
backtest:
  assets: ["BTC-USD", "ETH-USD", "SOL-USD"]
  strategy: "rsi"
  interval: "1d"
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  starting_cash: 50000.0
  commission:
    type: "percent"
    value: 0.001
  output_dir: "./my_backtest_results"
  show_plot: true
  debug: false

# Strategy-specific parameters
strategy_params:
  rsi:
    period: 14
    oversold: 30
    overbought: 70
  buy_and_hold:
    # No parameters required - uses equal distribution across assets
  rsi_ema_hybrid:
    rsi_period: 14
    rsi_oversold: 30
    rsi_trend_threshold: 50
    ema_period: 20
```

### Usage Examples
```bash
# Basic RSI strategy backtest on BTC-USD
python backtest.py --assets BTC-USD --strategy rsi

# Multi-asset backtest with custom date range
python backtest.py --assets "BTC-USD,ETH-USD" --strategy rsi --start-date "2024-01-01" --end-date "2024-06-30"

# Backtest with custom parameters and debugging
python backtest.py --assets SOL-USD --strategy rsi --interval 1h --starting-cash 25000 --debug

# Use configuration file
python backtest.py --config my_backtest.yaml

# Suppress plot generation
python backtest.py --assets BTC-USD --strategy rsi --no-plot

# Custom commission and output directory
python backtest.py --assets "BTC-USD,ETH-USD" --strategy rsi --commission "fixed:1.0" --output-dir "./results"
```

### Implementation Details
- **Strategy Integration**: Uses existing `Strategy` interface and `StrategyRunner` for execution
- **Backtesting Engine**: Leverages `BackTester` class for historical data processing
- **Data Loading**: Uses `DataStorage` for historical OHLCV data retrieval
- **Configuration Management**: Supports both command-line arguments and YAML config files
- **Error Handling**: Comprehensive validation of parameters and data availability. Errors in the backtested strategy are reported in the console
- **Progress Indication**: Shows progress for long-running backtests
- **Result Generation**: Produces detailed performance reports and visualizations

### Output Format
- **Console Output**: 
  - Progress indicators during backtest execution
  - Summary statistics and performance metrics
  - Debug information (when --debug flag is used)
- **File Output**:
  - Equity curve plot (PNG format) saved to output directory
  - Detailed performance report (JSON format) with all metrics
  - Trade log (CSV format) with individual trade details
  - Configuration snapshot (YAML format) for reproducibility
- **Performance Metrics**:
  - Total return (absolute and percentage)
  - CAGR (Compound Annual Growth Rate)
  - Annualized volatility and return
  - Sharpe ratio and Sortino ratio
  - Maximum drawdown and duration
  - Win rate and average trade duration
  - Kelly criterion statistics

### Debug and Profiling Information
When the `--debug` flag is used, the utility provides:
- **Execution Timing**: Strategy execution time per tick
- **Memory Usage**: Peak memory consumption during backtest
- **Data Loading Statistics**: Time spent loading historical data
- **Signal Generation**: Count and timing of trading signals
- **Order Execution**: Simulated order fill statistics
- **Performance Bottlenecks**: Identification of slow operations

### Error Handling
- **Invalid Assets**: Clear error messages for unsupported symbols
- **Data Availability**: Validation of data availability for specified date ranges
- **Strategy Validation**: Verification of strategy parameters and compatibility
- **Configuration Errors**: Detailed error messages for malformed config files
- **File System Issues**: Proper handling of output directory creation and permissions
- **Memory Management**: Graceful handling of large datasets and memory constraints

### Integration with Existing Modules
- **Backtesting Module**: Uses `BackTester` and `DummyTradingClient` for simulation
- **Strategy Module**: Integrates with `Strategy` interface and concrete implementations
- **Data Module**: Leverages `DataStorage` for historical data access
- **Position Module**: Uses `PositionManager` for portfolio tracking
  - Maintains a dedicated cash position when starting cash is provided
  - Debits cash on buys and credits cash on sells
  - Prevents opening positions without sufficient cash; raises an error
  - Prevents closing more than held asset quantity; raises an error
- **Configuration**: Extends existing `Config` classes for backtest-specific settings
- **Visualization**: Utilizes `matplotlib` for equity curve generation
- **Logging**: Integrates with existing logging infrastructure for debug output
