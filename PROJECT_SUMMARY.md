# Task Scheduler System - Project Summary

## Overview

A comprehensive task scheduling system designed for fair, auditable, and repeatable assignment of operational tasks (ATM monitoring and SysAid monitoring) across team members.

## Architecture

### Core Components

1. **Models (`task_scheduler/models.py`)**

   - `TeamMember`: Represents team members with availability, office days, and unavailability windows
   - `Assignment`: Task assignments to members
   - `FairnessLedger`: Tracks assignment counts for fairness calculations
   - `Schedule`: Complete schedule with assignments
   - `TaskType`: Enum for task types (ATM_MORNING, ATM_MIDNIGHT, SYSAID_MAKER, SYSAID_CHECKER)

2. **Configuration (`task_scheduler/config.py`)**

   - `SchedulingConfig`: Centralized configuration management
   - Loads from YAML files
   - Configurable: timezone, rest rules, cooldowns, time windows

3. **Data Loading (`task_scheduler/loader.py`)**

   - `load_team()`: Loads team members from YAML
   - Parses office days, unavailable dates, and date ranges

4. **Scheduler (`task_scheduler/scheduler.py`)**

   - `Scheduler`: Main scheduling engine
   - `_schedule_atm()`: Daily ATM monitoring assignments
   - `_schedule_sysaid()`: Weekly SysAid assignments
   - `_get_eligible_members()`: Filters members based on constraints
   - `_select_assignee()`: Fairness-based selection with tie-breaking
   - `AuditLog`: Tracks all scheduling decisions

5. **Export (`task_scheduler/export.py`)**

   - `export_to_csv()`: Machine-readable schedule
   - `export_to_ics()`: Calendar file for import
   - `export_audit_log()`: Detailed decision log

6. **CLI (`task_scheduler/cli.py`)**
   - `generate`: Generate schedule for date range
   - `check`: Check member availability for specific date

## Key Features Implemented

### ✅ Fairness System

- Tracks assignment counts per task type per member
- Rolling window fairness (default 90 days)
- Primary: Equal task-specific counts
- Secondary: Equal total assignment counts
- Deterministic tie-breaking for reproducibility

### ✅ ATM Scheduling

- Daily assignments (A = Morning, B = Mid-day+Night)
- Rest rule: B-shift assignee gets next day off
- Cooldown: Minimum days between B-shift assignments
- No same-day double duty
- Distinct A and B assignees

### ✅ SysAid Scheduling

- Weekly assignments (Maker/Checker pair)
- Office presence validation: Must be in office for all days of week
- Rest day exclusion: Cannot be on rest from ATM B-shift
- Distinct maker and checker
- Weekly rotation with fairness

### ✅ Constraint Handling

- Unavailability dates and ranges
- Office days (weekday configuration)
- Rest days from B-shift
- Cooldown periods
- Hard constraints override fairness preferences

### ✅ Audit & Traceability

- Complete audit log of all decisions
- Tie-break explanations
- Warnings for insufficient members
- Assignment reasoning

### ✅ Configuration Flexibility

- YAML-based configuration
- Timezone support
- Configurable rest rules
- Adjustable time windows
- Customizable cooldown periods

## File Structure

```
task scheduler/
├── task_scheduler/
│   ├── __init__.py          # Package initialization
│   ├── models.py             # Data models
│   ├── config.py             # Configuration management
│   ├── loader.py             # Data loading
│   ├── scheduler.py          # Core scheduling logic
│   ├── export.py             # Export functionality
│   └── cli.py                # Command-line interface
├── data/
│   ├── config.yaml           # Scheduling configuration
│   └── team.yaml             # Team members data
├── out/                      # Output directory (generated)
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── README.md                 # User documentation
├── example_usage.py          # Example script
└── .gitignore                # Git ignore rules
```

## Usage Example

```python
from datetime import date, timedelta
from task_scheduler.loader import load_team
from task_scheduler.config import SchedulingConfig
from task_scheduler.scheduler import Scheduler
from task_scheduler.export import export_to_csv, export_to_ics

# Load data
members = load_team("data/team.yaml")
config = SchedulingConfig.from_yaml("data/config.yaml")

# Generate schedule
scheduler = Scheduler(config)
schedule = scheduler.generate_schedule(
    members,
    date(2025, 11, 3),  # Start date
    date(2025, 11, 9)   # End date
)

# Export
export_to_csv(schedule, "out/schedule.csv")
export_to_ics(schedule, "out/schedule.ics", config.timezone)
```

## CLI Commands

```bash
# Generate schedule
python -m task_scheduler.cli generate \
  --team data/team.yaml \
  --config data/config.yaml \
  --start 2025-11-03 \
  --out out/schedule.csv \
  --ics out/schedule.ics

# Check availability
python -m task_scheduler.cli check \
  --team data/team.yaml \
  --config data/config.yaml \
  --date 2025-11-15
```

## Operational Workflow Integration

1. **Thursday 12:00**: Team members report unavailability
2. **Thursday 14:00**: Scheduler generates draft schedule
3. **Thursday 16:00**: Manager reviews and approves
4. **Friday 09:00**: Final schedule published

## Error Handling

- Insufficient eligible members: Warning logged, day/week skipped
- Conflicts: Automatic resolution with distinct assignees
- Edge cases: Handled gracefully with audit log entries

## Future Enhancements (Potential)

1. Web interface for schedule management
2. Email notifications for assignments
3. Integration with calendar systems
4. Historical schedule analysis
5. Manual override capabilities
6. Schedule templates
7. Multi-team support
8. Advanced fairness metrics

## Testing Recommendations

1. Unit tests for each component
2. Integration tests for full scheduling flow
3. Edge case testing (small teams, many conflicts)
4. Fairness validation tests
5. Configuration validation tests

## Dependencies

- `pyyaml`: YAML configuration parsing
- `pytz`: Timezone handling
- `ics`: Calendar file generation
- `python-dateutil`: Date utilities
- `click`: CLI framework
