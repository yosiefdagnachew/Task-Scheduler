"""Data models for team members, assignments, and scheduling state."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Set
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks in the system."""
    ATM_MORNING = "ATM_MORNING"  # Morning reporter (A)
    ATM_MIDNIGHT = "ATM_MIDNIGHT"  # Mid-day+Night reporter (B)
    SYSAID_MAKER = "SYSAID_MAKER"
    SYSAID_CHECKER = "SYSAID_CHECKER"


@dataclass
class TeamMember:
    """Represents a team member with their availability and office schedule."""
    name: str
    id: str  # Unique identifier
    office_days: Set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})  # Mon-Fri by default (0=Mon, 6=Sun)
    unavailable_dates: Set[date] = field(default_factory=set)
    unavailable_ranges: List[tuple[date, date]] = field(default_factory=list)  # (start, end) inclusive
    
    def is_available_on(self, check_date: date) -> bool:
        """Check if member is available on a specific date."""
        # Check if date is in unavailable set
        if check_date in self.unavailable_dates:
            return False
        
        # Check if date falls in any unavailable range
        for start, end in self.unavailable_ranges:
            if start <= check_date <= end:
                return False
        
        # Check if it's an office day
        weekday = check_date.weekday()  # 0=Monday, 6=Sunday
        return weekday in self.office_days
    
    def is_unavailable_range(self, start_date: date, end_date: date) -> bool:
        """Check if member is unavailable for any day in the range."""
        from datetime import timedelta
        current = start_date
        while current <= end_date:
            if not self.is_available_on(current):
                return True
            current = current + timedelta(days=1)
        return False


@dataclass
class Assignment:
    """Represents a task assignment to a team member."""
    task_type: TaskType
    assignee: TeamMember
    date: date
    week_start: Optional[date] = None  # For SysAid weekly assignments
    
    def __str__(self) -> str:
        return f"{self.assignee.name} -> {self.task_type.value} on {self.date}"


@dataclass
class FairnessLedger:
    """Tracks assignment counts for fairness calculations."""
    member_counts: dict[str, dict[TaskType, int]] = field(default_factory=dict)
    fairness_window_days: int = 90  # Rolling window
    
    def get_count(self, member_id: str, task_type: TaskType) -> int:
        """Get assignment count for a member and task type."""
        return self.member_counts.get(member_id, {}).get(task_type, 0)
    
    def increment(self, member_id: str, task_type: TaskType):
        """Increment count for a member and task type."""
        if member_id not in self.member_counts:
            self.member_counts[member_id] = {}
        if task_type not in self.member_counts[member_id]:
            self.member_counts[member_id][task_type] = 0
        self.member_counts[member_id][task_type] += 1
    
    def get_total_count(self, member_id: str) -> int:
        """Get total assignment count across all task types."""
        return sum(self.member_counts.get(member_id, {}).values())


@dataclass
class Schedule:
    """Complete schedule for a time period."""
    assignments: List[Assignment] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    def get_assignments_for_date(self, check_date: date) -> List[Assignment]:
        """Get all assignments for a specific date."""
        return [a for a in self.assignments if a.date == check_date]
    
    def get_assignments_for_member(self, member_id: str) -> List[Assignment]:
        """Get all assignments for a specific member."""
        return [a for a in self.assignments if a.assignee.id == member_id]
    
    def get_rest_days(self) -> Set[date]:
        """Get all rest days (days following ATM_MIDNIGHT assignments)."""
        rest_days = set()
        for assignment in self.assignments:
            if assignment.task_type == TaskType.ATM_MIDNIGHT:
                from datetime import timedelta
                rest_day = assignment.date + timedelta(days=1)
                rest_days.add(rest_day)
        return rest_days

