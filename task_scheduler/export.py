"""Export schedules to various formats (CSV, ICS)."""

import csv
from datetime import datetime
from typing import List
import pytz
from ics import Calendar, Event
from .models import Schedule, Assignment, TaskType


def export_to_csv(schedule: Schedule, file_path: str):
    """Export schedule to CSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Task Type', 'Assignee', 'Week Start (SysAid)'])
        
        # Sort by date, then by task type
        sorted_assignments = sorted(
            schedule.assignments,
            key=lambda a: (a.date, a.task_type.value)
        )
        
        for assignment in sorted_assignments:
            week_start_str = assignment.week_start.isoformat() if assignment.week_start else ""
            writer.writerow([
                assignment.date.isoformat(),
                assignment.task_type.value,
                assignment.assignee.name,
                week_start_str
            ])


def export_to_ics(schedule: Schedule, file_path: str, timezone: str = "Africa/Addis_Ababa"):
    """Export schedule to ICS calendar file."""
    tz = pytz.timezone(timezone)
    cal = Calendar()
    
    # Group assignments by date and task type for better calendar entries
    assignments_by_date = {}
    for assignment in schedule.assignments:
        key = (assignment.date, assignment.task_type)
        if key not in assignments_by_date:
            assignments_by_date[key] = []
        assignments_by_date[key].append(assignment)
    
    # Create events
    for (assignment_date, task_type), assignments in assignments_by_date.items():
        assignee_names = ", ".join(a.assignee.name for a in assignments)
        
        # Set times based on task type
        from datetime import time as time_class
        if task_type == TaskType.ATM_MORNING:
            start_time = datetime.combine(assignment_date, time_class(6, 0))
            end_time = datetime.combine(assignment_date, time_class(8, 30))
            title = f"ATM Morning Report - {assignee_names}"
        elif task_type == TaskType.ATM_MIDNIGHT:
            start_time = datetime.combine(assignment_date, time_class(8, 30))
            end_time = datetime.combine(assignment_date, time_class(22, 0))
            title = f"ATM Mid-day/Night Report - {assignee_names}"
        elif task_type == TaskType.SYSAID_MAKER:
            start_time = datetime.combine(assignment_date, time_class(9, 0))
            end_time = datetime.combine(assignment_date, time_class(17, 0))
            title = f"SysAid Maker - {assignee_names}"
        elif task_type == TaskType.SYSAID_CHECKER:
            start_time = datetime.combine(assignment_date, time_class(9, 0))
            end_time = datetime.combine(assignment_date, time_class(17, 0))
            title = f"SysAid Checker - {assignee_names}"
        else:
            start_time = datetime.combine(assignment_date, time_class(9, 0))
            end_time = datetime.combine(assignment_date, time_class(17, 0))
            title = f"{task_type.value} - {assignee_names}"
        
        # Localize to timezone
        start_time = tz.localize(start_time)
        end_time = tz.localize(end_time)
        
        event = Event()
        event.name = title
        event.begin = start_time
        event.end = end_time
        event.description = f"Assignee(s): {assignee_names}\nTask: {task_type.value}"
        
        cal.events.add(event)
    
    # Write to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(cal)


def export_audit_log(audit_log: str, file_path: str):
    """Export audit log to text file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("SCHEDULING AUDIT LOG\n")
        f.write("=" * 50 + "\n\n")
        f.write(audit_log)

