"""Recalculate fairness counts from assignments (without HTTP/auth).

Usage: python tools/recalculate_fairness.py
"""
from datetime import date, timedelta
from task_scheduler.database import db, AssignmentDB, FairnessCount, DynamicFairnessCount
from task_scheduler.api import SchedulingConfig
from task_scheduler.api import TaskType


def main():
    session = db.get_session()
    try:
        try:
            config = SchedulingConfig.from_yaml("data/config.yaml")
            window_days = getattr(config, 'fairness_window_days', 90)
        except Exception:
            window_days = 90
        cutoff = date.today() - timedelta(days=window_days)

        print(f"Recalculating fairness using window {window_days} days (cutoff {cutoff})")

        with session.begin():
            session.query(FairnessCount).delete(synchronize_session=False)
            session.query(DynamicFairnessCount).delete(synchronize_session=False)

            rows = session.query(AssignmentDB.member_id, AssignmentDB.task_type, AssignmentDB.custom_task_name).filter(
                AssignmentDB.assignment_date >= cutoff
            ).all()

            enum_task_values = {t.value for t in TaskType}
            counts = 0
            for member_id, task_type, custom_name in rows:
                counts += 1
                if custom_name or (isinstance(task_type, str) and task_type not in enum_task_values):
                    tname = custom_name or task_type or 'CUSTOM'
                    dfc = session.query(DynamicFairnessCount).filter(
                        DynamicFairnessCount.member_id == member_id,
                        DynamicFairnessCount.task_name == tname
                    ).first()
                    if not dfc:
                        dfc = DynamicFairnessCount(member_id=member_id, task_name=tname, count=0, updated_at=date.today())
                        session.add(dfc)
                    dfc.count = (dfc.count or 0) + 1
                    dfc.updated_at = date.today()
                else:
                    task_str = task_type
                    fc = session.query(FairnessCount).filter(
                        FairnessCount.member_id == member_id,
                        FairnessCount.task_type == task_str
                    ).first()
                    if not fc:
                        fc = FairnessCount(member_id=member_id, task_type=task_str, count=0, period_start=date.today()-timedelta(days=window_days), period_end=date.today())
                        session.add(fc)
                    fc.count = (fc.count or 0) + 1
                    fc.updated_at = date.today()
        print(f"Processed {counts} assignment rows; fairness counters rebuilt.")
    finally:
        session.close()


if __name__ == '__main__':
    main()
