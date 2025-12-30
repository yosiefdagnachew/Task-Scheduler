from task_scheduler.loader import load_team
from task_scheduler.config import SchedulingConfig
from task_scheduler.scheduler import Scheduler
from task_scheduler.task_type_model import DynamicTaskType, TaskTypeShift
from task_scheduler.database import db, TeamMemberDB, ScheduleDB, AssignmentDB
from task_scheduler.api import db_member_to_model
from datetime import date
import yaml

# This script will ensure team members exist in DB, generate a monthly EOM schedule,
# save it to the DB, and print the resulting schedule ID and assignments.

if __name__ == '__main__':
    # Load team models from data/team.yaml
    models = load_team('data/team.yaml')
    session = db.get_session()

    # Ensure team members exist in DB
    for m in models:
        existing = session.query(TeamMemberDB).filter(TeamMemberDB.id == m.id).first()
        if not existing:
            dbm = TeamMemberDB(id=m.id, name=m.name, office_days=set(m.office_days), email=m.email)
            session.add(dbm)
    session.commit()

    # Build selected members (use first 6)
    db_members = session.query(TeamMemberDB).order_by(TeamMemberDB.id).all()
    selected_db_members = db_members[:6]
    selected_ids = [m.id for m in selected_db_members]
    print('Using member ids:', selected_ids)

    # Convert DB members to domain models expected by Scheduler
    selected_models = [db_member_to_model(m, session) for m in selected_db_members]

    # Build DynamicTaskType for EOM monthly
    shifts = [TaskTypeShift(label='Shift', start_time='00:00', end_time='23:59', required_count=1, requires_rest=False)]
    task = DynamicTaskType(id=1, name='EOM', recurrence='monthly', required_count=1, role_labels=['Primary'], rules_json={'day_of_month': 'EOM'}, shifts=shifts)

    # Generate schedule
    config = SchedulingConfig()
    s = Scheduler(config)
    start = date(2026,1,5)
    end = date(2026,6,11)
    sched = s.generate_schedule(selected_models, start, end, task_types=[task], task_members={'EOM': selected_ids})

    # Save schedule to DB
    db_schedule = ScheduleDB(start_date=start, end_date=end, status='draft')
    session.add(db_schedule)
    session.flush()

    for a in sched.assignments:
        db_assignment = AssignmentDB(
            task_type=str(a.task_type),
            schedule_id=db_schedule.id,
            member_id=a.assignee.id,
            assignment_date=a.date,
            week_start=a.week_start,
            shift_label=a.shift_label,
            custom_task_name=a.custom_task_name,
            custom_task_shift=a.custom_task_shift,
            recurrence=a.recurrence
        )
        session.add(db_assignment)
    session.commit()

    print('Saved schedule id:', db_schedule.id)
    assignments = session.query(AssignmentDB).filter(AssignmentDB.schedule_id == db_schedule.id).order_by(AssignmentDB.assignment_date).all()
    print('Assignments saved:', len(assignments))
    for a in assignments:
        print(a.assignment_date, a.task_type, a.member_id, a.shift_label)

    session.close()
