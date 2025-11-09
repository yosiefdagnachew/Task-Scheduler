"""Helper functions for calculating rest days based on company policy."""

from datetime import date, timedelta
from typing import Optional, List, Set


def calculate_rest_day(assignment_date: date) -> Optional[date]:
    """
    Calculate rest day based on company policy:
    - Monday assignment → rest Tuesday
    - Tuesday assignment → rest Wednesday
    - Wednesday assignment → rest Thursday
    - Thursday assignment → rest Friday
    - Friday assignment → rest Monday (not Saturday!)
    - Saturday assignment → no rest
    - Sunday assignment → no rest
    
    Args:
        assignment_date: The date when the assignment was made
        
    Returns:
        The rest day date, or None if no rest day applies
    """
    weekday = assignment_date.weekday()  # 0=Monday, 6=Sunday
    
    # Saturday (5) and Sunday (6) have no rest day
    if weekday == 5 or weekday == 6:
        return None
    
    # Friday (4) → rest Monday (next week)
    if weekday == 4:
        days_until_monday = 3  # Friday to Monday
        return assignment_date + timedelta(days=days_until_monday)
    
    # Monday (0) through Thursday (3) → rest next day
    return assignment_date + timedelta(days=1)


def is_rest_day(check_date: date, assignment_date: date) -> bool:
    """
    Check if a given date is a rest day for an assignment made on assignment_date.
    
    Args:
        check_date: The date to check
        assignment_date: The date when the assignment was made
        
    Returns:
        True if check_date is a rest day for the assignment
    """
    rest_day = calculate_rest_day(assignment_date)
    return rest_day is not None and rest_day == check_date


def get_rest_days_for_assignments(assignments: List[tuple[date, bool]]) -> Set[date]:
    """
    Get all rest days for a list of assignments.
    Each assignment is a tuple of (date, requires_rest).
    
    Args:
        assignments: List of (assignment_date, requires_rest) tuples
        
    Returns:
        Set of rest day dates
    """
    rest_days = set()
    for assignment_date, requires_rest in assignments:
        if requires_rest:
            rest_day = calculate_rest_day(assignment_date)
            if rest_day is not None:
                rest_days.add(rest_day)
    return rest_days

