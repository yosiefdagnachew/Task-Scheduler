"""Inspect assignments table using the configured PostgreSQL `DATABASE_URL`.

Usage:
  set DATABASE_URL to your Postgres URL, then run:
    python task_scheduler/inspect_db.py
"""
import os
from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError("Set DATABASE_URL environment variable to your PostgreSQL URL before running this script.")
if not url.startswith("postgresql"):
    raise RuntimeError("This inspector only supports PostgreSQL. Ensure DATABASE_URL begins with 'postgresql'.")

engine = create_engine(url)
with engine.connect() as conn:
    print('Columns for assignments:')
    try:
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='assignments' ORDER BY ordinal_position;"))
        for row in res:
            print(row)
    except Exception as e:
        print('Failed to read information_schema for assignments:', e)

    print('\nSample rows (id, assignment_date, task_type, recurrence, custom_task_name):')
    try:
        rows = conn.execute(text("SELECT id, assignment_date, task_type, recurrence, custom_task_name FROM assignments ORDER BY id LIMIT 50;"))
        for r in rows:
            print(r)
    except Exception as e:
        print('Failed to query assignments:', e)