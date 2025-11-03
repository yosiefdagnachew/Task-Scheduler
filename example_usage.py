"""Example usage of the task scheduler system."""

from datetime import date, timedelta
from task_scheduler.loader import load_team
from task_scheduler.config import SchedulingConfig
from task_scheduler.scheduler import Scheduler
from task_scheduler.export import export_to_csv, export_to_ics, export_audit_log

# Load configuration
print("Loading team and configuration...")
members = load_team("data/team.yaml")
config = SchedulingConfig.from_yaml("data/config.yaml")

print(f"Loaded {len(members)} team members")

# Generate schedule for next week
start_date = date.today()
# Find next Monday
days_until_monday = (7 - start_date.weekday()) % 7
if days_until_monday == 0:
    days_until_monday = 7
start_date = start_date + timedelta(days=days_until_monday)
end_date = start_date + timedelta(days=6)  # Sunday

print(f"\nGenerating schedule from {start_date} to {end_date}...")

# Create scheduler and generate
scheduler = Scheduler(config)
schedule = scheduler.generate_schedule(members, start_date, end_date)

print(f"\nGenerated {len(schedule.assignments)} assignments")

# Export to files
export_to_csv(schedule, "out/schedule.csv")
export_to_ics(schedule, "out/schedule.ics", config.timezone)
export_audit_log(scheduler.audit.get_log(), "out/audit.log")

print("\nSchedule exported:")
print("  - CSV: out/schedule.csv")
print("  - ICS: out/schedule.ics")
print("  - Audit log: out/audit.log")

# Print summary
print("\n=== Schedule Summary ===")
for day_offset in range(7):
    check_date = start_date + timedelta(days=day_offset)
    day_assignments = schedule.get_assignments_for_date(check_date)
    print(f"\n{check_date.strftime('%A, %Y-%m-%d')}:")
    for assignment in day_assignments:
        print(f"  - {assignment.task_type.value}: {assignment.assignee.name}")

