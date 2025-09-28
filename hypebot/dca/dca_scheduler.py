"""DCA (Dollar Cost Averaging) schedule calculation and management."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from .dca_models import DCAConfig, DCASchedule

logger = logging.getLogger(__name__)


class DCAScheduler:
    """Generates and manages DCA injection schedules."""

    def __init__(self, config: DCAConfig, backtest_start: datetime, backtest_end: datetime):
        """Initialize DCA scheduler.
        
        Args:
            config: DCA configuration
            backtest_start: Start date of backtest
            backtest_end: End date of backtest
        """
        self.config = config
        self.backtest_start = backtest_start
        self.backtest_end = backtest_end
        self._schedule: Optional[DCASchedule] = None

    def generate_schedule(self, trading_days: List[datetime]) -> DCASchedule:
        """Generate DCA injection schedule based on calendar days (24/7 trading).
        
        Args:
            trading_days: List of trading days (used for reference, but DCA works 24/7)
            
        Returns:
            DCASchedule with injection dates and amounts
        """
        if not self.config.enabled:
            return DCASchedule([], [], 0, 0.0)

        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"DCA configuration errors: {errors}")

        logger.info(f"Generating DCA schedule: {self.config.frequency} "
                   f"injections of ${self.config.amount}")

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

        injection_dates = calculate_func()
        
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
        logger.info(f"DCA schedule generated: {schedule.total_injections} "
                   f"injections totaling ${schedule.total_amount}")

        return schedule

    def get_injection_amount(self, timestamp: datetime) -> Optional[float]:
        """Check if timestamp requires DCA injection and return amount.
        
        Args:
            timestamp: Timestamp to check for DCA injection
            
        Returns:
            Injection amount if timestamp matches DCA schedule, None otherwise
        """
        if not self._schedule:
            return None

        return self._schedule.get_injection_amount(timestamp)

    def _calculate_daily_schedule(self) -> List[datetime]:
        """Generate daily injection schedule (every calendar day)."""
        start = self.config.start_date or self.backtest_start
        end = self.config.end_date or self.backtest_end

        injection_dates = []
        current_date = start.date()
        end_date = end.date()

        while current_date <= end_date:
            # Convert to datetime at start of day
            injection_dates.append(datetime.combine(current_date, datetime.min.time()))
            current_date += timedelta(days=1)

        return injection_dates

    def _calculate_weekly_schedule(self) -> List[datetime]:
        """Generate weekly injection schedule (every 7 calendar days)."""
        start = self.config.start_date or self.backtest_start
        end = self.config.end_date or self.backtest_end

        injection_dates = []
        current_date = start

        while current_date <= end:
            injection_dates.append(current_date)
            current_date += timedelta(days=7)

        return injection_dates

    def _calculate_biweekly_schedule(self) -> List[datetime]:
        """Generate bi-weekly injection schedule (every 14 calendar days)."""
        start = self.config.start_date or self.backtest_start
        end = self.config.end_date or self.backtest_end

        injection_dates = []
        current_date = start

        while current_date <= end:
            injection_dates.append(current_date)
            current_date += timedelta(days=14)

        return injection_dates

    def _calculate_monthly_schedule(self) -> List[datetime]:
        """Generate monthly injection schedule (first day of each month)."""
        start = self.config.start_date or self.backtest_start
        end = self.config.end_date or self.backtest_end

        injection_dates = []
        current_month = start.replace(day=1)

        while current_month <= end:
            # Use first day of month or start date if later
            injection_date = max(current_month, start)
            if injection_date <= end:
                injection_dates.append(injection_date)

            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        return injection_dates

    def _calculate_yearly_schedule(self) -> List[datetime]:
        """Generate yearly injection schedule (first day of each year)."""
        start = self.config.start_date or self.backtest_start
        end = self.config.end_date or self.backtest_end

        injection_dates = []
        current_year = start.year

        while current_year <= end.year:
            # Use first day of year or start date if later
            year_start = datetime(current_year, 1, 1)
            injection_date = max(year_start, start)
            if injection_date <= end:
                injection_dates.append(injection_date)

            current_year += 1

        return injection_dates
