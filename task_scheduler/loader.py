"""Load team members and configuration from YAML files."""

from datetime import date
from typing import List
import yaml
from .models import TeamMember
from .config import SchedulingConfig


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return date.fromisoformat(date_str)


def load_team(file_path: str) -> List[TeamMember]:
    """Load team members from YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    members = []
    for member_data in data.get('members', []):
        name = member_data['name']
        member_id = member_data.get('id', name.lower().replace(' ', '_'))
        
        # Parse office days (default: Mon-Fri)
        office_days = set(member_data.get('office_days', [0, 1, 2, 3, 4]))
        
        # Parse unavailable dates
        unavailable_dates = set()
        if 'unavailable_dates' in member_data:
            for date_str in member_data['unavailable_dates']:
                unavailable_dates.add(parse_date(date_str))
        
        # Parse unavailable ranges
        unavailable_ranges = []
        if 'unavailable_ranges' in member_data:
            for range_data in member_data['unavailable_ranges']:
                start = parse_date(range_data['start'])
                end = parse_date(range_data['end'])
                unavailable_ranges.append((start, end))
        
        member = TeamMember(
            name=name,
            id=member_id,
            office_days=office_days,
            unavailable_dates=unavailable_dates,
            unavailable_ranges=unavailable_ranges
        )
        members.append(member)
    
    return members

