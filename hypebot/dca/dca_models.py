"""Data models for backtesting functionality."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class DCAConfig:
    """Configuration for DCA mode."""
    enabled: bool = False
    frequency: str = "monthly"  # daily, weekly, bi-weekly, monthly, yearly
    amount: float = 1000.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def validate(self) -> List[str]:
        """Validate DCA configuration and return any errors."""
        errors = []
        
        if not self.enabled:
            return errors  # No validation needed if disabled
        
        # Validate frequency
        valid_frequencies = ["daily", "weekly", "bi-weekly", "monthly", "yearly"]
        if self.frequency not in valid_frequencies:
            errors.append(f"Invalid DCA frequency: {self.frequency}")
        
        # Validate amount
        if self.amount <= 0:
            errors.append("DCA amount must be positive")
        
        # Validate date ranges
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors.append("DCA start_date must be before end_date")
        
        return errors


@dataclass
class DCASchedule:
    """Pre-calculated DCA injection schedule."""
    injection_dates: List[datetime]
    injection_amounts: List[float]
    total_injections: int
    total_amount: float

    def get_injection_amount(self, timestamp: datetime) -> Optional[float]:
        """Check if timestamp requires DCA injection and return amount."""
        # Normalize timestamps to compare dates only (ignore time and timezone)
        timestamp_date = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        if timestamp_date.tzinfo is not None:
            timestamp_date = timestamp_date.replace(tzinfo=None)
        
        for i, injection_date in enumerate(self.injection_dates):
            # Normalize injection date to compare dates only
            injection_date_normalized = injection_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if injection_date_normalized == timestamp_date:
                return self.injection_amounts[i]
        return None

    def get_injection_count(self) -> int:
        """Get total number of injections."""
        return self.total_injections

    def get_total_amount(self) -> float:
        """Get total amount to be injected."""
        return self.total_amount
