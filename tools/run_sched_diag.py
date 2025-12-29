from task_scheduler.loader import load_team
from task_scheduler.config import SchedulingConfig
from task_scheduler.scheduler import Scheduler
from datetime import date
from collections import defaultdict

if __name__ == '__main__':
    members = load_team('data/team.yaml')
    print('Loaded', len(members), 'members')
    config = SchedulingConfig()
    s = Scheduler(config)
    start = date(2026,1,5)
    end = date(2026,1,11)
    sched = s.generate_schedule(members, start, end)
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
