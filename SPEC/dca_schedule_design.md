# DCA Schedule Calculation Design

This document outlines the detailed design for DCA (Dollar Cost Averaging) schedule calculation in HypeBot's backtesting system.

## Overview

The DCA scheduler is responsible for:
1. Generating injection dates based on frequency and date ranges
2. Aligning injections with actual trading days
3. Providing efficient lookup for the strategy runner
4. Handling edge cases and validation

## DCA Scheduler Class Design

### DCAScheduler Class

```python
@dataclass
class DCAConfig:
    """Configuration for DCA mode."""
    enabled: bool = False
    frequency: str = "monthly"  # daily, weekly, bi-weekly, monthly, yearly
    amount: float = 1000.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@dataclass
class DCASchedule:
    """Pre-calculated DCA injection schedule."""
    injection_dates: List[datetime]
    injection_amounts: List[float]
    total_injections: int
    total_amount: float

class DCAScheduler:
    """Generates and manages DCA injection schedules."""
    
    def __init__(self, config: DCAConfig, backtest_start: datetime, backtest_end: datetime):
        self.config = config
        self.backtest_start = backtest_start
        self.backtest_end = backtest_end
        self._schedule: Optional[DCASchedule] = None
    
    def generate_schedule(self, trading_days: List[datetime]) -> DCASchedule:
        """Generate DCA injection schedule based on trading days."""
        
    def get_injection_amount(self, timestamp: datetime) -> Optional[float]:
        """Check if timestamp requires DCA injection and return amount."""
        
    def validate_config(self) -> List[str]:
        """Validate DCA configuration and return any errors."""
```

## Frequency Mapping Logic

### Daily Frequency
```python
def _calculate_daily_schedule(self, trading_days: List[datetime]) -> List[datetime]:
    """Generate daily injection schedule."""
    start = self.config.start_date or self.backtest_start
    end = self.config.end_date or self.backtest_end
    
    # Filter trading days within date range
    eligible_days = [day for day in trading_days if start <= day <= end]
    return eligible_days
```

### Weekly Frequency
```python
def _calculate_weekly_schedule(self, trading_days: List[datetime]) -> List[datetime]:
    """Generate weekly injection schedule (every 7 days)."""
    start = self.config.start_date or self.backtest_start
    end = self.config.end_date or self.backtest_end
    
    # Find first eligible trading day
    first_day = next((day for day in trading_days if day >= start), None)
    if not first_day:
        return []
    
    # Generate weekly schedule
    injection_dates = []
    current_date = first_day
    
    while current_date <= end:
        # Find closest trading day to current_date
        closest_day = min(trading_days, 
                         key=lambda x: abs((x - current_date).days))
        if closest_day <= end:
            injection_dates.append(closest_day)
        current_date += timedelta(days=7)
    
    return sorted(injection_dates)
```

### Bi-Weekly Frequency
```python
def _calculate_biweekly_schedule(self, trading_days: List[datetime]) -> List[datetime]:
    """Generate bi-weekly injection schedule (every 14 days)."""
    # Similar to weekly but with 14-day intervals
    # Implementation follows same pattern as weekly
```

### Monthly Frequency (Default)
```python
def _calculate_monthly_schedule(self, trading_days: List[datetime]) -> List[datetime]:
    """Generate monthly injection schedule (first trading day of each month)."""
    start = self.config.start_date or self.backtest_start
    end = self.config.end_date or self.backtest_end
    
    injection_dates = []
    current_month = start.replace(day=1)
    
    while current_month <= end:
        # Find first trading day of the month
        month_start = current_month.replace(day=1)
        first_trading_day = next(
            (day for day in trading_days 
             if day >= month_start and day.month == current_month.month),
            None
        )
        
        if first_trading_day and start <= first_trading_day <= end:
            injection_dates.append(first_trading_day)
        
        # Move to next month
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)
    
    return sorted(injection_dates)
```

### Yearly Frequency
```python
def _calculate_yearly_schedule(self, trading_days: List[datetime]) -> List[datetime]:
    """Generate yearly injection schedule (first trading day of each year)."""
    start = self.config.start_date or self.backtest_start
    end = self.config.end_date or self.backtest_end
    
    injection_dates = []
    current_year = start.year
    
    while current_year <= end.year:
        # Find first trading day of the year
        year_start = datetime(current_year, 1, 1)
        first_trading_day = next(
            (day for day in trading_days 
             if day >= year_start and day.year == current_year),
            None
        )
        
        if first_trading_day and start <= first_trading_day <= end:
            injection_dates.append(first_trading_day)
        
        current_year += 1
    
    return sorted(injection_dates)
```

## Schedule Generation Algorithm

### Main Generation Logic
```python
def generate_schedule(self, trading_days: List[datetime]) -> DCASchedule:
    """Generate complete DCA injection schedule."""
    if not self.config.enabled:
        return DCASchedule([], [], 0, 0.0)
    
    # Validate configuration
    errors = self.validate_config()
    if errors:
        raise ValueError(f"DCA configuration errors: {errors}")
    
    # Generate injection dates based on frequency
    frequency_map = {
        "daily": self._calculate_daily_schedule,
        "weekly": self._calculate_weekly_schedule,
        "bi-weekly": self._calculate_biweekly_schedule,
        "monthly": self._calculate_monthly_schedule,
        "yearly": self._calculate_yearly_schedule,
    }
    
    calculate_func = frequency_map.get(self.config.frequency)
    if not calculate_func:
        raise ValueError(f"Unsupported DCA frequency: {self.config.frequency}")
    
    injection_dates = calculate_func(trading_days)
    
    # Generate injection amounts (all same amount for now)
    injection_amounts = [self.config.amount] * len(injection_dates)
    
    # Create schedule
    schedule = DCASchedule(
        injection_dates=injection_dates,
        injection_amounts=injection_amounts,
        total_injections=len(injection_dates),
        total_amount=sum(injection_amounts)
    )
    
    self._schedule = schedule
    return schedule
```

### Efficient Lookup
```python
def get_injection_amount(self, timestamp: datetime) -> Optional[float]:
    """Check if timestamp requires DCA injection and return amount."""
    if not self._schedule:
        return None
    
    # Binary search for efficient lookup
    dates = self._schedule.injection_dates
    amounts = self._schedule.injection_amounts
    
    # Find exact match or closest injection
    for i, injection_date in enumerate(dates):
        if injection_date == timestamp:
            return amounts[i]
    
    return None
```

## Configuration Validation

### Validation Rules
```python
def validate_config(self) -> List[str]:
    """Validate DCA configuration and return any errors."""
    errors = []
    
    if not self.config.enabled:
        return errors  # No validation needed if disabled
    
    # Validate frequency
    valid_frequencies = ["daily", "weekly", "bi-weekly", "monthly", "yearly"]
    if self.config.frequency not in valid_frequencies:
        errors.append(f"Invalid DCA frequency: {self.config.frequency}")
    
    # Validate amount
    if self.config.amount <= 0:
        errors.append("DCA amount must be positive")
    
    # Validate date ranges
    if self.config.start_date and self.config.end_date:
        if self.config.start_date >= self.config.end_date:
            errors.append("DCA start_date must be before end_date")
    
    if self.config.start_date and self.config.start_date < self.backtest_start:
        errors.append("DCA start_date cannot be before backtest start_date")
    
    if self.config.end_date and self.config.end_date > self.backtest_end:
        errors.append("DCA end_date cannot be after backtest end_date")
    
    return errors
```

## Integration Points

### BackTester Integration
```python
class BackTester:
    def __init__(self, ..., dca_config: Optional[DCAConfig] = None):
        self.dca_config = dca_config or DCAConfig()
    
    async def run_single(self, ...):
        # Generate DCA schedule
        if self.dca_config.enabled:
            dca_scheduler = DCAScheduler(
                self.dca_config, 
                start or datetime.min, 
                end or datetime.max
            )
            dca_schedule = dca_scheduler.generate_schedule(ticks)
        else:
            dca_schedule = None
        
        # Pass schedule to strategy runner
        runner = StrategyRunner(
            ..., 
            dca_scheduler=dca_scheduler
        )
```

### StrategyRunner Integration
```python
class StrategyRunner:
    def __init__(self, ..., dca_scheduler: Optional[DCAScheduler] = None):
        self.dca_scheduler = dca_scheduler
    
    async def run(self, ticks: Iterable[datetime], ...):
        for tick in sorted_ticks:
            # Check for DCA injection before strategy tick
            if self.dca_scheduler:
                injection_amount = self.dca_scheduler.get_injection_amount(tick)
                if injection_amount:
                    self.position_manager.inject_dca_funds(injection_amount, tick)
            
            # Run strategy tick
            strategy_orders = await self.strategy.tick(as_of=tick, historical=historical)
            # ... rest of execution
```

## Error Handling

### Edge Cases
1. **No Trading Days**: Return empty schedule if no trading days in range
2. **Invalid Date Ranges**: Validate and provide clear error messages
3. **Frequency Validation**: Check for supported frequencies only
4. **Amount Validation**: Ensure positive amounts
5. **Date Alignment**: Handle cases where injection dates fall outside trading days

### Logging
```python
import logging
logger = logging.getLogger(__name__)

def generate_schedule(self, trading_days: List[datetime]) -> DCASchedule:
    logger.info(f"Generating DCA schedule: {self.config.frequency} "
                f"injections of ${self.config.amount}")
    
    # ... generation logic ...
    
    logger.info(f"DCA schedule generated: {schedule.total_injections} "
                f"injections totaling ${schedule.total_amount}")
    
    return schedule
```

## Performance Considerations

### Optimization Strategies
1. **Pre-calculation**: Generate entire schedule upfront
2. **Binary Search**: Efficient timestamp lookup
3. **Sorted Storage**: Keep injection dates sorted for quick access
4. **Memory Efficiency**: Store only necessary data in schedule

### Complexity Analysis
- **Schedule Generation**: O(n) where n is number of trading days
- **Lookup**: O(log n) using binary search
- **Memory**: O(m) where m is number of injection dates

This design provides a robust, efficient, and extensible foundation for DCA schedule calculation in the HypeBot backtesting system.
