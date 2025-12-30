"""Backfill script to assign schedule_id for assignments missing it.

Rules:
- For each AssignmentDB with schedule_id NULL or 0, find schedules that include the assignment_date.
- If exactly one schedule matches, set `schedule_id` to that schedule's id and persist.
- If multiple schedules match, log to console for manual review.
- If no schedules match, log as orphan.

Run: python tools/backfill_schedule_ids.py
"""
from datetime import date
from task_scheduler.database import db, AssignmentDB, ScheduleDB

SESSION = None


def main(dry_run=True):
    global SESSION
    SESSION = db.get_session()
    try:
        q = SESSION.query(AssignmentDB).filter((AssignmentDB.schedule_id == None) | (AssignmentDB.schedule_id == 0)).all()
        print(f"Found {len(q)} assignments with missing schedule_id")
        updated = 0
        ambiguous = 0
        orphan = 0
        for a in q:
            matches = SESSION.query(ScheduleDB).filter(ScheduleDB.start_date <= a.assignment_date, ScheduleDB.end_date >= a.assignment_date).all()
            if len(matches) == 1:
                if not dry_run:
                    a.schedule_id = matches[0].id
                    SESSION.add(a)
                    SESSION.commit()
                updated += 1
            elif len(matches) > 1:
                ambiguous += 1
                print(f"Ambiguous assignment id={a.id} date={a.assignment_date} matches schedules {[s.id for s in matches]}")
            else:
                orphan += 1
                print(f"Orphan assignment id={a.id} date={a.assignment_date} no matching schedule")

        print(f"Summary: updated={updated}, ambiguous={ambiguous}, orphan={orphan}")
    finally:
        SESSION.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Apply changes (not a dry run)')
    args = p.parse_args()
    main(dry_run=(not args.apply))
