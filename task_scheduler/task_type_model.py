"""Models for database-driven task types."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import date


@dataclass
class TaskTypeShift:
    """Represents a shift definition for a task type."""
    label: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    required_count: int = 1
    requires_rest: bool = False  # Whether this shift requires a rest day after


@dataclass
class DynamicTaskType:
    """Represents a task type from the database that can be used for scheduling."""
    id: int
    name: str
    recurrence: str  # "daily", "weekly", "monthly"
    required_count: int = 1
    role_labels: List[str] = None
    rules_json: Optional[Dict[str, Any]] = None
    shifts: List[TaskTypeShift] = None
    
    def __post_init__(self):
        if self.role_labels is None:
            self.role_labels = []
        if self.shifts is None:
            self.shifts = []
    
    def get_shifts_for_weekday(self, weekday: int) -> List[TaskTypeShift]:
        """
        Get shifts that should be scheduled for a given weekday.
        For now, returns all shifts, but can be customized based on rules_json.
        
        Args:
            weekday: 0=Monday, 6=Sunday
            
        Returns:
            List of shifts to schedule for this weekday
        """
        # For now, return all shifts. Can be customized based on rules_json
        return self.shifts
    
    def should_schedule_on_date(self, check_date: date) -> bool:
        """
        Determine if this task type should be scheduled on a given date
        based on its recurrence pattern.
        
        Args:
            check_date: The date to check
            
        Returns:
            True if task should be scheduled on this date
        """
        if self.recurrence == "daily":
            return True
        elif self.recurrence == "weekly":
            # Weekly tasks typically start on a specific day (e.g., Monday)
            # For now, schedule on the week start day
            weekday = check_date.weekday()
            # Default to Monday (0), but can be customized via rules_json
            week_start_day = self.rules_json.get("week_start_day", 0) if self.rules_json else 0
            return weekday == week_start_day
        elif self.recurrence == "monthly":
            # Monthly tasks on a specific day of month
            day_of_month = self.rules_json.get("day_of_month", 1) if self.rules_json else 1
            return check_date.day == day_of_month
        return False

