"""Export schedules to various formats (CSV, ICS)."""

import csv
from datetime import datetime
from typing import List
import pytz
from ics import Calendar, Event
from .models import Schedule, Assignment, TaskType
from openpyxl import Workbook
from openpyxl.utils import get_column_letter


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
            # Sunday special: up to 09:00
            if assignment_date.weekday() == 6:
                start_time = datetime.combine(assignment_date, time_class(7, 30))
                end_time = datetime.combine(assignment_date, time_class(9, 0))
            else:
                start_time = datetime.combine(assignment_date, time_class(7, 30))
                end_time = datetime.combine(assignment_date, time_class(8, 30))
            title = f"ATM Morning Report - {assignee_names}"
        elif task_type == TaskType.ATM_MIDNIGHT:
            if assignment_date.weekday() == 6:
                # Sunday second slot 09:00 - 16:00
                start_time = datetime.combine(assignment_date, time_class(9, 0))
                end_time = datetime.combine(assignment_date, time_class(16, 0))
            else:
                start_time = datetime.combine(assignment_date, time_class(13, 0))
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


def export_to_xlsx(schedule: Schedule, file_path: str):
    """Export schedule to XLSX with vertical layout (dates as rows)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"

    # Columns: Date, ATM Morning, ATM Mid/Night, SysAid Maker, SysAid Checker
    headers = [
        "Date",
        "ATM Morning (07:30-08:30)",
        "ATM Mid/Night",
        "SysAid Maker",
        "SysAid Checker"
    ]
    ws.append(headers)

    # Group by date
    by_date = {}
    for a in schedule.assignments:
        d = a.date
        by_date.setdefault(d, []).append(a)

    for day in sorted(by_date.keys()):
        row = [day.isoformat(), "", "", "", ""]
        for a in by_date[day]:
            if a.task_type == TaskType.ATM_MORNING:
                row[1] = a.assignee.name
            elif a.task_type == TaskType.ATM_MIDNIGHT:
                row[2] = a.assignee.name
            elif a.task_type == TaskType.SYSAID_MAKER:
                row[3] = a.assignee.name
            elif a.task_type == TaskType.SYSAID_CHECKER:
                row[4] = a.assignee.name
        ws.append(row)

    # Autosize columns
    for col_idx in range(1, len(headers) + 1):
        max_len = 12
        for cell in ws[get_column_letter(col_idx)]:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

    wb.save(file_path)

