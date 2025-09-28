"""Tests for DCA scheduler functionality."""

import pytest
from datetime import datetime, timedelta
from hypebot.dca import DCAConfig, DCASchedule, DCAScheduler


class TestDCAConfig:
    """Test DCA configuration validation."""

    def test_valid_config(self):
        """Test valid DCA configuration."""
        config = DCAConfig(
            enabled=True,
            frequency="monthly",
            amount=1000.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_disabled_config(self):
        """Test disabled DCA configuration."""
        config = DCAConfig(enabled=False)
        errors = config.validate()
        assert len(errors) == 0

    def test_invalid_frequency(self):
        """Test invalid frequency validation."""
        config = DCAConfig(
            enabled=True,
            frequency="invalid",
            amount=1000.0
        )
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid DCA frequency" in errors[0]

    def test_negative_amount(self):
        """Test negative amount validation."""
        config = DCAConfig(
            enabled=True,
            frequency="monthly",
            amount=-100.0
        )
        errors = config.validate()
        assert len(errors) == 1
        assert "DCA amount must be positive" in errors[0]

    def test_invalid_date_range(self):
        """Test invalid date range validation."""
        config = DCAConfig(
            enabled=True,
            frequency="monthly",
            amount=1000.0,
            start_date=datetime(2024, 12, 31),
            end_date=datetime(2024, 1, 1)
        )
        errors = config.validate()
        assert len(errors) == 1
        assert "start_date must be before end_date" in errors[0]


class TestDCAScheduler:
    """Test DCA scheduler functionality."""

    def test_daily_schedule(self):
        """Test daily DCA schedule generation."""
        config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 3)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 1, 3))
        schedule = scheduler.generate_schedule([])
        
        assert schedule.total_injections == 3
        assert schedule.total_amount == 300.0
        assert len(schedule.injection_dates) == 3
        assert all(amount == 100.0 for amount in schedule.injection_amounts)

    def test_weekly_schedule(self):
        """Test weekly DCA schedule generation."""
        config = DCAConfig(
            enabled=True,
            frequency="weekly",
            amount=500.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 15)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 1, 15))
        schedule = scheduler.generate_schedule([])
        
        # Should have 3 injections: Jan 1, Jan 8, Jan 15
        assert schedule.total_injections == 3
        assert schedule.total_amount == 1500.0
        assert len(schedule.injection_dates) == 3

    def test_monthly_schedule(self):
        """Test monthly DCA schedule generation."""
        config = DCAConfig(
            enabled=True,
            frequency="monthly",
            amount=1000.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 3, 31))
        schedule = scheduler.generate_schedule([])
        
        # Should have 3 injections: Jan 1, Feb 1, Mar 1
        assert schedule.total_injections == 3
        assert schedule.total_amount == 3000.0
        assert len(schedule.injection_dates) == 3

    def test_yearly_schedule(self):
        """Test yearly DCA schedule generation."""
        config = DCAConfig(
            enabled=True,
            frequency="yearly",
            amount=5000.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2026, 12, 31)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2026, 12, 31))
        schedule = scheduler.generate_schedule([])
        
        # Should have 3 injections: 2024, 2025, 2026
        assert schedule.total_injections == 3
        assert schedule.total_amount == 15000.0
        assert len(schedule.injection_dates) == 3

    def test_disabled_schedule(self):
        """Test disabled DCA schedule generation."""
        config = DCAConfig(enabled=False)
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 12, 31))
        schedule = scheduler.generate_schedule([])
        
        assert schedule.total_injections == 0
        assert schedule.total_amount == 0.0
        assert len(schedule.injection_dates) == 0

    def test_injection_lookup(self):
        """Test DCA injection lookup functionality."""
        config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 1, 2))
        schedule = scheduler.generate_schedule([])
        
        # Test exact match
        injection_amount = scheduler.get_injection_amount(datetime(2024, 1, 1))
        assert injection_amount == 100.0
        
        # Test no match
        injection_amount = scheduler.get_injection_amount(datetime(2024, 1, 3))
        assert injection_amount is None

    def test_weekend_injections(self):
        """Test that DCA works on weekends (24/7 trading)."""
        config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 6),  # Saturday
            end_date=datetime(2024, 1, 8)     # Monday
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 6), datetime(2024, 1, 8))
        schedule = scheduler.generate_schedule([])
        
        # Should include weekend days
        assert schedule.total_injections == 3
        assert datetime(2024, 1, 6) in schedule.injection_dates  # Saturday
        assert datetime(2024, 1, 7) in schedule.injection_dates  # Sunday
        assert datetime(2024, 1, 8) in schedule.injection_dates  # Monday

    def test_edge_case_empty_range(self):
        """Test edge case with empty date range."""
        config = DCAConfig(
            enabled=True,
            frequency="daily",
            amount=100.0,
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 1)  # End before start
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 1, 1))
        
        with pytest.raises(ValueError, match="DCA configuration errors"):
            scheduler.generate_schedule([])

    def test_biweekly_schedule(self):
        """Test bi-weekly DCA schedule generation."""
        config = DCAConfig(
            enabled=True,
            frequency="bi-weekly",
            amount=200.0,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 29)
        )
        scheduler = DCAScheduler(config, datetime(2024, 1, 1), datetime(2024, 1, 29))
        schedule = scheduler.generate_schedule([])
        
        # Should have 3 injections: Jan 1, Jan 15, Jan 29
        assert schedule.total_injections == 3
        assert schedule.total_amount == 600.0
        assert len(schedule.injection_dates) == 3
