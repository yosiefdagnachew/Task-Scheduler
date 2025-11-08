"""Export schedules to various formats (CSV, ICS, PDF, Excel)."""

import csv
from datetime import datetime
from typing import List
from pathlib import Path
import pytz
from ics import Calendar, Event
from .models import Schedule, Assignment, TaskType
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def export_to_csv(schedule: Schedule, file_path: str):
    """Export schedule to CSV file."""
    # Ensure output directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
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
            assignee_display = assignment.assignee.name
            if assignment.shift_label:
                assignee_display = f"{assignee_display} ({assignment.shift_label})"
            writer.writerow([
                assignment.date.isoformat(),
                assignment.task_type.value,
                assignee_display,
                week_start_str
            ])


def export_to_ics(schedule: Schedule, file_path: str, timezone: str = "Africa/Addis_Ababa"):
    """Export schedule to ICS calendar file."""
    tz = pytz.timezone(timezone)
    cal = Calendar()
    
    # Group assignments by date and task type for better calendar entries
    assignments_by_date = {}
    for assignment in schedule.assignments:
        key = (assignment.date, assignment.task_type, assignment.shift_label)
        if key not in assignments_by_date:
            assignments_by_date[key] = []
        assignments_by_date[key].append(assignment)
    
    # Create events
    for (assignment_date, task_type, shift_label), assignments in assignments_by_date.items():
        assignee_names = ", ".join(a.assignee.name for a in assignments)
        
        # Set times based on task type
        from datetime import time as time_class
        if task_type == TaskType.ATM_MORNING:
            # Sunday special: up to 09:00
            if shift_label and "09:00" in shift_label:
                start_time = datetime.combine(assignment_date, time_class(9, 0))
                end_time = datetime.combine(assignment_date, time_class(12, 0))
            else:
                start_time = datetime.combine(assignment_date, time_class(7, 30))
                end_time = datetime.combine(assignment_date, time_class(8, 30))
            title = f"ATM Morning Report - {assignee_names}" + (f" ({shift_label})" if shift_label else "")
        elif task_type == TaskType.ATM_MIDNIGHT:
            if shift_label and "06:00" in shift_label:
                start_time = datetime.combine(assignment_date, time_class(6, 0))
                end_time = datetime.combine(assignment_date, time_class(9, 0))
            elif shift_label and "11:00" in shift_label:
                start_time = datetime.combine(assignment_date, time_class(11, 0))
                end_time = datetime.combine(assignment_date, time_class(14, 0))
            elif shift_label and "16:00" in shift_label:
                start_time = datetime.combine(assignment_date, time_class(16, 0))
                end_time = datetime.combine(assignment_date, time_class(22, 0))
            elif shift_label and "09:00" in shift_label:
                start_time = datetime.combine(assignment_date, time_class(9, 0))
                end_time = datetime.combine(assignment_date, time_class(16, 0))
            else:
                start_time = datetime.combine(assignment_date, time_class(13, 0))
                end_time = datetime.combine(assignment_date, time_class(22, 0))
            title = f"ATM Mid-day/Night Report - {assignee_names}" + (f" ({shift_label})" if shift_label else "")
        elif task_type == TaskType.SYSAID_MAKER:
            start_time = datetime.combine(assignment_date, time_class(9, 0))
            end_time = datetime.combine(assignment_date, time_class(17, 0))
            title = f"SysAid Maker - {assignee_names}" + (f" ({shift_label})" if shift_label else "")
        elif task_type == TaskType.SYSAID_CHECKER:
            start_time = datetime.combine(assignment_date, time_class(9, 0))
            end_time = datetime.combine(assignment_date, time_class(17, 0))
            title = f"SysAid Checker - {assignee_names}" + (f" ({shift_label})" if shift_label else "")
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
    # Ensure output directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
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
        aggregates = {
            TaskType.ATM_MORNING: [],
            TaskType.ATM_MIDNIGHT: [],
            TaskType.SYSAID_MAKER: [],
            TaskType.SYSAID_CHECKER: []
        }
        for a in by_date[day]:
            display = a.assignee.name
            if a.shift_label:
                display = f"{display} ({a.shift_label})"
            aggregates.setdefault(a.task_type, []).append(display)

        row[1] = "\n".join(aggregates.get(TaskType.ATM_MORNING, []))
        row[2] = "\n".join(aggregates.get(TaskType.ATM_MIDNIGHT, []))
        row[3] = "\n".join(aggregates.get(TaskType.SYSAID_MAKER, []))
        row[4] = "\n".join(aggregates.get(TaskType.SYSAID_CHECKER, []))
        ws.append(row)

    # Autosize columns
    for col_idx in range(1, len(headers) + 1):
        max_len = 12
        for cell in ws[get_column_letter(col_idx)]:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

    wb.save(file_path)


def export_to_excel(schedule: Schedule, file_path: str):
    """Export schedule to Excel format (using openpyxl, same as XLSX)."""
    # Excel format is essentially XLSX, so reuse the XLSX export
    export_to_xlsx(schedule, file_path)


def export_to_pdf(schedule: Schedule, file_path: str):
    """Export schedule to PDF format."""
    # Ensure output directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph(f"Schedule: {schedule.start_date} to {schedule.end_date}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Group assignments by date
    by_date = {}
    for a in schedule.assignments:
        d = a.date
        by_date.setdefault(d, []).append(a)
    
    # Table data
    data = [['Date', 'ATM Morning', 'ATM Mid/Night', 'SysAid Maker', 'SysAid Checker']]
    
    for day in sorted(by_date.keys()):
        row = [day.strftime('%Y-%m-%d (%A)'), '', '', '', '']
        aggregates = {
            TaskType.ATM_MORNING: [],
            TaskType.ATM_MIDNIGHT: [],
            TaskType.SYSAID_MAKER: [],
            TaskType.SYSAID_CHECKER: []
        }
        for a in by_date[day]:
            display = a.assignee.name
            if a.shift_label:
                display = f"{display} ({a.shift_label})"
            aggregates.setdefault(a.task_type, []).append(display)
        
        row[1] = '\n'.join(aggregates.get(TaskType.ATM_MORNING, [])) or '-'
        row[2] = '\n'.join(aggregates.get(TaskType.ATM_MIDNIGHT, [])) or '-'
        row[3] = '\n'.join(aggregates.get(TaskType.SYSAID_MAKER, [])) or '-'
        row[4] = '\n'.join(aggregates.get(TaskType.SYSAID_CHECKER, [])) or '-'
        data.append(row)
    
    # Create table
    table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    
    elements.append(table)
    doc.build(elements)


def export_fairness_to_pdf(fairness_data: List[dict], file_path: str):
    """Export fairness tracking data to PDF."""
    # Ensure output directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph("Fairness Tracking Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Table data
    data = [['Member', 'ATM Morning', 'ATM Mid/Night', 'SysAid Maker', 'SysAid Checker', 'Total']]
    
    for member in fairness_data:
        row = [
            member.get('member_name', member.get('member_id', 'Unknown')),
            str(member.get('counts', {}).get('ATM_MORNING', 0)),
            str(member.get('counts', {}).get('ATM_MIDNIGHT', 0)),
            str(member.get('counts', {}).get('SYSAID_MAKER', 0)),
            str(member.get('counts', {}).get('SYSAID_CHECKER', 0)),
            str(member.get('total', 0))
        ]
        data.append(row)
    
    # Create table
    table = Table(data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    
    elements.append(table)
    doc.build(elements)

