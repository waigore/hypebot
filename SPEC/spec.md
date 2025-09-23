# Crypto Trading Bot - Feature Setup

## Overview
Set up a Python-based crypto trading bot called HypeBot that connects to Hyperliquid exchange, retrieves price data from a configurable data provider (CoinGecko or Yahoo Finance via yfinance), applies technical indicators (RSI), and manages positions using Kelly criterion for position sizing.

## 1. Requirements Definition

### Feature Scope and Goals
- **Primary Goal**: Automated crypto trading bot with RSI-based signals and Kelly criterion position sizing
- **Exchange Integration**: Hyperliquid using custom HTTP client
- **Data Source**: Configurable data provider (CoinGecko API or Yahoo Finance via yfinance) for price data
- **Storage**: Local CSV persistence for historical OHLCV data organized by symbol, year, and granularity
- **Technical Analysis**: RSI indicator with pandas calculations
- **Position Management**: Kelly criterion for position sizing

### User Stories
1. **As a trader**, I want the bot to automatically connect to Hyperliquid exchange so I can trade crypto assets
2. **As a trader**, I want real-time price data from CoinGecko API so I can make informed trading decisions
3. **As a trader**, I want RSI signals (long/short) so I can automate trading based on technical analysis
4. **As a trader**, I want Kelly criterion position sizing so I can optimize risk-adjusted returns
5. **As a trader**, I want organized historical OHLCV data storage so I can analyze performance and backtest strategies

### Acceptance Criteria
- [ ] Bot successfully connects to Hyperliquid exchange
- [ ] Historical OHLCV data is retrieved and stored in organized CSV files by symbol, year, and granularity
- [ ] RSI indicator calculates and emits buy/sell signals
- [ ] Kelly criterion calculates optimal position sizes
- [ ] Bot executes trades based on signals with proper position sizing
- [ ] All modules are separated and can work independently
- [ ] Error handling and logging are implemented
- [ ] Data provider is configurable (CoinGecko or Yahoo Finance) without caller code changes
- [ ] Historical OHLCV retrieval returns standardized DataFrame shape and UTC timestamps
- [ ] CSV storage supports bidirectional conversion between OHLCVData models and pandas DataFrames

## 2. Technical Approach

### Architecture Overview
The bot is built as 4 separate modules with async/await patterns:

```
hypebot/
├── main.py                  # Main bot orchestration
├── config.py                # Configuration settings
├── exchange/                # Hyperliquid integration
├── data/                    # Data providers (CoinGecko/yfinance) and storage
├── indicators/              # RSI calculation and signals
├── position/                # Position management and Kelly criterion
└── tests/                   # Unit and integration tests
```

### Key Technologies
- **Exchange**: Custom Hyperliquid HTTP client (httpx)
- **Price Data**: CoinGecko API (httpx) and Yahoo Finance via `yfinance`
- **Storage**: Organized CSV files with pandas DataFrame conversion for historical OHLCV data
- **Technical Analysis**: pandas, numpy for RSI calculations
- **Position Sizing**: Custom Kelly criterion implementation
- **Configuration**: python-dotenv for environment variables
- **Async Operations**: asyncio for concurrent operations

## 3. Dependencies Configuration

### Core Dependencies
```txt
# Exchange Integration
hyperliquid-python-sdk>=0.19.0

# Data Processing
pandas>=2.0.0
numpy>=1.24.0

# API Client
httpx>=0.24.0
yfinance>=0.2.50

# Configuration
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0

# Development
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

### Environment Variables
```env
# Hyperliquid Configuration
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET_KEY=your_secret_key_here
HYPERLIQUID_TESTNET=true

# CoinGecko Configuration
COINGECKO_API_KEY=your_coingecko_api_key
COINGECKO_BASE_URL=https://api.coingecko.com/api/v3
COINGECKO_RATE_LIMIT=50

# Data Provider Selection
DATA_PROVIDER=coingecko  # or yfinance

# Generic Data Settings
DATA_CACHE_TTL_S=0
DATA_DEFAULT_INTERVAL=1d
DATA_DEFAULT_LOOKBACK_DAYS=365

# Yahoo Finance Configuration
YF_RATE_LIMIT_RPS=5
YF_MAX_RETRIES=3
YF_TIMEOUT_S=30

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
CSV_FILE_PREFIX=ohlcv_

# Logging Configuration
LOG_LEVEL=INFO
DEBUG=false
```

## 4. Data Models Design

### Core Models

#### Price Data Model (data/models.py)
```python
@dataclass
class PriceData:
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    market_cap: float
    source: str = "provider"  # set by the selected data provider
```

#### Market Data Model (data/models.py)
```python
@dataclass
class MarketData:
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    market_cap: float
    price_change_24h: float
    price_change_percentage_24h: float
    high_24h: float
    low_24h: float
    source: str = "provider"  # set by the selected data provider
```

#### Trading Signal Model (indicators/models.py)
```python
@dataclass
class TradingSignal:
    symbol: str
    timestamp: datetime
    signal_type: Literal["BUY", "SELL", "HOLD"]
    strength: float  # 0-1 confidence level
    rsi_value: float
    indicator: str = "RSI"
    price: Optional[float] = None
    metadata: Optional[dict] = None
```

#### Position Model (position/models.py)
```python
@dataclass
class Position:
    symbol: str
    side: Literal["LONG", "SHORT"]
    size: float
    entry_price: float
    current_price: float
    pnl: float
    kelly_size: float
    timestamp: datetime
    unrealized_pnl: Optional[float] = None
    realized_pnl: float = 0.0
```

#### Position Size Model (position/models.py)
```python
@dataclass
class PositionSize:
    symbol: str
    timestamp: datetime
    recommended_size: float
    kelly_fraction: float
    max_position_size: float
    current_price: float
    confidence: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
```

## 5. Storage Specification

### Historical Data Storage

The storage system is designed specifically for historical OHLCV data with the following characteristics:

#### File Organization
- **Directory Structure**: `{DATA_DIR}/{HISTORICAL_DATA_DIR}/`
- **File Naming Convention**: `{SYMBOL}_{YEAR}_{GRANULARITY}.csv`
  - Example: `BTC-USD_2025_1d.csv` for daily BTC-USD price data for 2025
  - Example: `ETH-USD_2024_1h.csv` for hourly ETH-USD price data for 2024
- **Granularity Formats**: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`

#### CSV Format
CSV files match the OHLCVData model fields exactly:
```csv
symbol,timestamp,open,high,low,close,volume,source
BTC-USD,2025-01-01T00:00:00+00:00,45000.0,45500.0,44800.0,45200.0,1250000.0,coingecko
BTC-USD,2025-01-01T01:00:00+00:00,45200.0,45300.0,45100.0,45150.0,980000.0,coingecko
```

#### DataFrame Conversion
- **From CSV to DataFrame**: Load CSV with UTC timestamp index and OHLCV columns
- **From DataFrame to CSV**: Save with proper timestamp formatting and field ordering
- **Metadata Preservation**: Symbol, source, and data type metadata stored in DataFrame.attrs
- **Timezone Handling**: All timestamps normalized to UTC

#### Storage Operations
- **Write**: Append new OHLCV data to appropriate CSV file based on symbol, year, granularity
- **Read**: Load specific symbol/year/granularity combinations into pandas DataFrame
- **Update**: Handle duplicate records by timestamp (last write wins)
- **Query**: Support date range filtering and symbol filtering

## 6. Module Specifications

### Exchange Module (exchange/)
- **hyperliquid_client.py**: Custom HTTP client for Hyperliquid API with authentication, order placement, position queries
- **models.py**: Order, trade, and account balance models

### Data Module (data/)
- **client.py**: Provider-agnostic interface and factory for data clients
- **coingecko_client.py**: CoinGecko implementation of the data client with rate limiting
- **yfinance_client.py**: Yahoo Finance implementation via `yfinance` (thread-wrapped for async API)
- **storage.py**: Historical OHLCV data storage with organized CSV files and DataFrame conversion
- **models.py**: Price, market, and OHLCV models with CSV serialization and DataFrame conversion methods

### Indicators Module (indicators/)
- **rsi_calculator.py**: Calculate RSI using pandas with Wilder's smoothing, generate buy/sell signals with crossover detection
- **base_indicator.py**: Abstract base class for indicators with common functionality
- **models.py**: Indicator and signal models with comprehensive metadata

### Position Module (position/)
- **manager.py**: Track positions, calculate P&L, manage risk, portfolio metrics
- **kelly_criterion.py**: Calculate optimal position sizes using Kelly criterion with risk adjustments
- **models.py**: Position and sizing models with comprehensive properties and methods

## 6. Key Implementation Features

### Main Bot Features (main.py)
- **Trading cycle**: 60-second intervals with 30-second error recovery
- **Signal validation**: Minimum signal strength threshold (0.3) for trade execution
- **Signal cooldown**: 5-minute cooldown between signals to prevent overtrading
- **Async context managers**: Proper resource management for API clients
- **Graceful shutdown**: Signal handlers for SIGINT and SIGTERM

### RSI Calculator Features (indicators/rsi_calculator.py)
- **Crossover signals**: Moderate strength (0.7) for threshold crossover signals
- **RSI interpretation**: Human-readable interpretation of RSI levels
- **Signal strength calculation**: Distance-based strength calculation from thresholds
- **Divergence detection**: Basic bullish/bearish divergence detection

### Position Manager Features (position/manager.py)
- **P&L tracking**: Separate unrealized and realized P&L calculations
- **Risk validation**: Comprehensive validation before trade execution
- **Portfolio metrics**: Win rate, total P&L, portfolio value calculations
- **Position cleanup**: Automatic cleanup of old positions (30-day default)

### Kelly Criterion Features (position/kelly_criterion.py)
- **Risk metrics**: Volatility, Sharpe ratio, max drawdown, VaR (95% confidence)
- **Leverage calculation**: Optimal leverage calculation based on Kelly fraction (max 10x)
- **Position validation**: Comprehensive position size validation against min/max limits
- **Confidence adjustment**: Signal strength and confidence-based position size adjustments

### Data Storage Features (data/storage.py)
- **Organized CSV storage**: Historical OHLCV data stored in files organized by symbol, year, and granularity
- **File naming convention**: `{SYMBOL}_{YEAR}_{GRANULARITY}.csv` format for easy data management
- **DataFrame conversion**: Bidirectional conversion between OHLCVData models and pandas DataFrames
- **Duplicate handling**: Automatic removal of duplicate records based on symbol and timestamp
- **Data filtering**: Symbol, year, granularity, and date range filtering for historical data retrieval
- **Metadata preservation**: Symbol, source, and data type information preserved in DataFrame.attrs

### Data Client Features (data/client.py and providers/)
- **Provider selection**: `DATA_PROVIDER` config selects CoinGecko or Yahoo Finance
- **Unified async interface**: `authenticate`, `close`, `get_supported_symbols`, `get_spot_price`, `get_market_data`, `get_historical_prices`
- **Historical data**: Standardized OHLCV DataFrame with columns `open,high,low,close,volume`, UTC index, `attrs` metadata
- **Rate limiting and retries**: Token bucket RPS guard, exponential backoff with jitter, provider-specific handling
- **Error normalization**: Common exceptions (`DataNotFoundError`, `RateLimitError`, `ProviderAuthError`, `ProviderTemporaryError`, `ProviderPermanentError`, `InvalidSymbolError`, `TimeoutError`)
- **Caching (optional)**: TTL cache for spot/market endpoints, configurable via `DATA_CACHE_TTL_S`

### Exchange Client Features (exchange/hyperliquid_client.py)
- **Custom HTTP client**: Direct HTTP implementation for better control over API interactions
- **Authentication**: HMAC-SHA256 signature generation for API authentication
- **Order management**: Complete order lifecycle management (place, cancel, status)

## 7. Setup Commands

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd hypebot

# Create virtual environment (using pipenv)
pipenv install

# Or using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp hypebot/env.example .env
# Edit .env with your API keys

# Run the bot
python -m hypebot
# Or
hypebot
```

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
black .
flake8 .
mypy .

# Run tests
pytest hypebot/tests/
```

## 8. Testing Strategy

### Unit Tests
- Test each module independently with mocked dependencies
- Test RSI calculations with known datasets
- Test Kelly criterion with various return scenarios
- Test API clients with mock responses (both CoinGecko and Yahoo Finance providers)
- Test data client interface conformance and error normalization
- Test timezone normalization and interval mapping across providers

### Integration Tests
- Test data flow between modules
- Test end-to-end signal generation and position sizing
- Test error handling and recovery scenarios
- Test historical OHLCV retrieval from each provider (optional live tests behind `RUN_LIVE_DATA_TESTS=1`)

## Feature Setup Checklist
- [x] Requirements documented
- [x] User stories written
- [x] Technical approach planned
- [x] Architecture designed with 4 separate modules
- [x] Dependencies identified and configured
- [x] Data models designed and implemented
- [x] Testing strategy planned and implemented
- [x] Setup commands documented
- [x] Development environment ready
- [x] Initial module structure implemented
- [x] Basic functionality tested
- [x] Configuration management implemented
- [x] Logging and monitoring implemented
- [x] Package setup (setup.py) created
- [x] Environment template (env.example) created

## Next Steps
1. ✅ Create feature branch: `git checkout -b feature/hypebot`
2. ✅ Set up development environment with dependencies
3. ✅ Implement exchange module for Hyperliquid integration
4. ✅ Implement data module with provider-agnostic client (CoinGecko/yfinance) and Pandas storage
5. ✅ Implement indicators module with RSI calculator
6. ✅ Implement position module with Kelly criterion
7. ✅ Create main orchestration script
8. ✅ Add comprehensive testing
9. ✅ Add configuration management
10. ✅ Add logging and monitoring

## Additional Implementation Notes
- The bot is implemented as a complete package with proper Python packaging
- Uses async/await patterns for API calls and trading operations
- Includes comprehensive error handling and logging
- Supports both pipenv installation method only
- Has extensive configuration options through environment variables
- Includes signal cooldown and risk management features
- Implements proper position tracking with P&L calculations
- Uses organized CSV files for historical OHLCV data persistence with pandas DataFrame conversion
- Custom Hyperliquid client implementation for better API control
- Graceful shutdown handling with signal handlers
- Real-time position price updates
- Comprehensive portfolio metrics calculation
- Kelly criterion with correlation adjustments for portfolio optimization
- Signal strength calculation and validation
- Risk limit validation before trade execution