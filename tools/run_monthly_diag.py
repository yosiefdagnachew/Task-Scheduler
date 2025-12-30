from task_scheduler.loader import load_team
from task_scheduler.config import SchedulingConfig
from task_scheduler.scheduler import Scheduler
from task_scheduler.task_type_model import DynamicTaskType, TaskTypeShift
from datetime import date
from collections import defaultdict

if __name__ == '__main__':
    members = load_team('data/team.yaml')
    print('Loaded', len(members), 'members')
    # select first 6 members if available
    selected = members[:6]
    print('Using', len(selected), 'members for custom task')

    config = SchedulingConfig()
    s = Scheduler(config)

    # Define an EOM monthly custom task with one shift
    shifts = [TaskTypeShift(label='Shift', start_time='00:00', end_time='23:59', required_count=1, requires_rest=False)]
    # Allow scheduling on any day (including weekends) unless task type rules require office days
    # Use default requires_office_days (True) to simulate typical task creation; scheduler will apply weekend fallback
    task = DynamicTaskType(id=1, name='EOM', recurrence='monthly', required_count=1, role_labels=['Primary'], rules_json={'day_of_month': 'EOM'}, shifts=shifts)

    start = date(2026,1,5)
    end = date(2026,6,11)

    sched = s.generate_schedule(selected, start, end, task_types=[task], task_members={'EOM':[m.id for m in selected]})
    print('Assignments generated:', len(sched.assignments))
    print('\nAudit log:\n')
    print(s.audit.get_log())
    by_date = defaultdict(list)
    for a in sched.assignments:
        by_date[a.date].append((a.task_type, a.assignee.name, a.shift_label))
    print('\nAssignments by date:')
    for d in sorted(by_date):
        print(d)
        for entry in by_date[d]:
            print(' ', entry)
