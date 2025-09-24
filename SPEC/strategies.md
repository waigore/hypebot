# HypeBot Trading Strategies

This document contains detailed documentation for all trading strategies implemented in HypeBot.

## Buy-and-Hold Strategy

The Buy-and-Hold strategy serves as the control baseline for all backtesting comparisons in HypeBot.

### Overview

The Buy-and-Hold strategy:
- Implements the standard `Strategy` interface
- Purchases assets in full on the first tick using entire cash position
- Never sells or rebalances positions after initial purchase
- Distributes cash equally across multiple assets when specified
- Provides a simple baseline for strategy performance comparison

### Strategy Behavior

**Initial Purchase**:
- On the first tick of backtesting, the strategy uses 100% of available cash
- For single asset: purchases the entire position in that asset
- For multiple assets: distributes cash equally across all specified assets
- No position sizing calculations or risk management applied

**Position Management**:
- No selling or rebalancing after initial purchase
- Positions are held throughout the entire backtesting period
- No stop-losses, take-profits, or other exit conditions
- Pure buy-and-hold approach with no active management

### Strategy Parameters

The Buy-and-Hold strategy requires no configuration parameters beyond the standard strategy interface:

```env
# Standard Strategy Configuration
DEFAULT_SYMBOL=BTC
# No additional parameters needed for buy-and-hold
```

### Implementation

The Buy-and-Hold strategy is implemented in `hypebot/strategy/buy_and_hold_strategy.py` and follows the `Strategy` abstract base class interface:

- **assets**: List of symbols to trade (purchased equally on first tick)
- **interval**: Data granularity (1h, 4h, 1d, 1w, 1mo)
- **tick()**: Returns purchase orders only on first tick, empty list thereafter
- **on_start()/on_stop()**: Standard lifecycle hooks

Note: The strategy draws from the portfolio's cash position managed by `PositionManager`. If insufficient cash is available, order execution should fail with the appropriate error from the position management layer.

### Backtesting Integration

The Buy-and-Hold strategy serves as the control strategy in all backtesting scenarios:

- **Automatic Inclusion**: The `BackTester` automatically creates and runs a Buy-and-Hold instance alongside any specified strategies
- **Performance Comparison**: All backtesting results include Buy-and-Hold metrics for comparison
- **HTML Reports**: Generated reports show side-by-side comparison of all strategies including Buy-and-Hold
- **Equity Curves**: Visualization plots include Buy-and-Hold equity curve as baseline reference

### Use Cases

- **Baseline Performance**: Provides simple market performance benchmark
- **Strategy Validation**: Helps determine if active strategies outperform passive holding
- **Risk Assessment**: Shows performance without active risk management
- **Market Timing**: Demonstrates impact of timing decisions vs. simple holding

## RSI Strategy

The RSI (Relative Strength Index) strategy is the default trading strategy implemented in HypeBot.

### Overview

The RSI strategy:
- Calculates RSI values from historical data
- Generates BUY/SELL signals based on thresholds
- Uses KellyCriterion for position sizing
- Applies risk management and signal filtering

### Strategy Parameters

The RSI strategy can be configured using the following environment variables:

```env
# RSI Configuration
RSI_PERIOD=14
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
KELLY_LOOKBACK_PERIOD=30
MAX_POSITION_SIZE=0.1
MIN_POSITION_SIZE=0.001
RISK_FREE_RATE=0.02
```

### Signal Generation

- **BUY Signal**: Generated when RSI falls below the oversold threshold (default: 30)
- **SELL Signal**: Generated when RSI rises above the overbought threshold (default: 70)
- **Signal Strength**: Based on how far the RSI value is from the threshold
- **Risk Management**: Position sizing calculated using Kelly Criterion

### Position Sizing

The strategy uses Kelly Criterion for optimal position sizing:
- Analyzes historical performance over a configurable lookback period
- Calculates optimal position size based on win rate and average win/loss ratios
- Applies maximum and minimum position size limits
- Considers risk-free rate in calculations

### Implementation

The RSI strategy is implemented in `hypebot/strategy/rsi_strategy.py` and follows the `Strategy` abstract base class interface:

- **assets**: List of symbols to trade
- **interval**: Data granularity (1h, 4h, 1d, 1w, 1mo)
- **tick()**: Main strategy logic returning StrategyOrders
- **on_start()/on_stop()**: Lifecycle hooks

### Backtesting

The RSI strategy can be backtested using the HypeBot backtesting engine. See the main [specification](spec.md) for details on running backtests and analyzing performance metrics.

Both strategies’ equity outcomes reflect: mark-to-market value of open asset positions plus remaining cash in the portfolio at each step, as recorded by the backtester’s equity curve.
