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

**DCA Integration** (when DCA mode is enabled):
- Automatically purchases additional assets when DCA funds are injected
- Uses new DCA funds to proportionally increase position sizes
- Maintains equal distribution across all specified assets
- Continues purchasing throughout the backtesting period as funds become available

**Position Management**:
- No selling or rebalancing after initial purchase
- Positions are held throughout the entire backtesting period
- No stop-losses, take-profits, or other exit conditions
- Pure buy-and-hold approach with no active management
- Accumulates additional positions when DCA funds are available

### Strategy Parameters

The Buy-and-Hold strategy requires no configuration parameters beyond the standard strategy interface:

```env
# Standard Strategy Configuration
DEFAULT_SYMBOL=BTC
# No additional parameters needed for buy-and-hold
```

### Implementation

The Buy-and-Hold strategy is implemented in `hypebot/strategy/buy_and_hold_strategy.py` and follows the `Strategy` abstract base class interface:

- **assets**: List of symbols to trade (purchased equally on first tick and with DCA funds)
- **interval**: Data granularity (1h, 4h, 1d, 1w, 1mo)
- **tick()**: Returns purchase orders when cash is available (first tick and DCA injection ticks)
- **on_start()/on_stop()**: Standard lifecycle hooks
- **position_manager**: Access to current cash balance for dynamic purchasing

**DCA-Aware Implementation**:
- Removes dependency on `starting_cash` parameter
- Uses `position_manager.cash_balance` for all purchase decisions
- Purchases assets whenever available cash exceeds zero
- Supports continuous accumulation with DCA fund injections

Note: The strategy draws from the portfolio's cash position managed by `PositionManager`. DCA funds are automatically injected into the position manager's cash balance, making them immediately available to the strategy for purchasing additional assets.

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

Both strategies' equity outcomes reflect: mark-to-market value of open asset positions plus remaining cash in the portfolio at each step, as recorded by the backtester's equity curve.

### DCA Strategy Requirements

All custom strategies should be designed to work with DCA mode:

**Cash Balance Awareness**:
- Strategies must access cash balance through `position_manager.cash_balance`
- No assumptions about "starting cash" - always use current available balance
- Position sizing should consider entire available capital (initial + DCA injections)

**Dynamic Cash Handling**:
- Strategies should handle dynamic cash balance changes gracefully
- DCA funds become part of total available capital for position sizing
- Kelly criterion and other sizing methods should work with changing cash amounts

**Best Practices**:
- Access cash via `self.position_manager.cash_balance` in strategy implementations
- Calculate position sizes based on current available funds, not fixed starting amounts
- Handle cases where cash balance changes between ticks due to DCA injections

## RSI + EMA Hybrid Strategy (Trend-Filtered Momentum)

A hybrid, momentum-with-trend filter strategy combining RSI with the 20-period Exponential Moving Average (EMA).

### Overview

The RSI + EMA Hybrid strategy seeks long entries only when momentum aligns with an established uptrend. It uses RSI to gauge momentum and a 20-period EMA as a trend filter and support confirmation. Position sizing for this strategy is all-in/all-out per signal as specified below.

### Strategy Parameters

```env
# RSI + EMA Hybrid Configuration
RSI_PERIOD=14            # RSI lookback for momentum
RSI_OVERSOLD=30          # Oversold threshold used for cross-out detection
RSI_TREND_THRESHOLD=50   # Momentum confirmation threshold for long bias
EMA_PERIOD=20            # EMA lookback for trend filter
```

Notes:
- The strategy ignores Kelly-based sizing and instead uses full available cash on entries and fully exits on sells.
- Thresholds may be overridden per backtest via strategy parameters.

### Signal Generation

Long-only strategy. A strong LONG signal is triggered when BOTH conditions are true on the current bar:
- RSI momentum confirmation:
  - RSI(14) > 50; OR
  - RSI crosses up from below the oversold threshold (default: 30) this bar
- Trend filter and support confirmation:
  - Close price > EMA(20)

Exit (close the long) when ANY of the following occurs:
- RSI falls below 50; OR
- Close price < EMA(20)

### Order Sizing and Execution

- On a buy signal, the strategy places a market buy using the entire available cash balance for the asset (subject to commission and lot constraints).
- On an exit signal, the strategy closes the entire position in the asset.
- No pyramiding or partial scaling is performed.
- Only one position per asset is maintained at a time.

### Risk Management and Filters

- Trend filter via EMA(20) is required for entries and acts as a trailing support for exits.
- No stop-loss or take-profit is enforced by this spec; exits occur per RSI/EMA rules above.
- No Kelly Criterion sizing is applied in this strategy by design.

### Multi-Asset Behavior

- For multiple assets, signals are evaluated independently per asset.
- Each asset uses its own available cash derived from the global cash balance; purchases use all currently available cash (i.e., the full remaining cash at the time of signal). There is no enforced equal-weighting rebalance.

### Implementation

The strategy should implement the standard `Strategy` interface with:
- `assets`: List of symbols to trade
- `interval`: Data granularity
- `tick()`: Generates orders per above rules (all-in buy or full exit)
- `on_start()/on_stop()`: Lifecycle hooks

Indicator computations required:
- RSI with configurable period (default 14)
- EMA with configurable period (default 20)

### Backtesting

- Evaluate against Buy-and-Hold as comparator.
- Key performance metrics include hit rate, average trade return, maximum drawdown, and time in market—often lower than simple RSI due to trend filter.