#!/usr/bin/env python3
"""Migrate Postgres enum `task_type` columns to VARCHAR.

Usage: set DATABASE_URL in the environment, then run:
  python tools/migrate_tasktype_to_varchar.py

The script will try to ALTER TABLE for common tables and print results.
"""
import os
import sys
from sqlalchemy import create_engine, text


def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(2)

    engine = create_engine(url)
    dialect = engine.dialect.name
    print(f"Connected using dialect: {dialect}")

    if dialect == "sqlite":
        print("SQLite detected — no enum-to-varchar migration needed.")
        return

    # Tables to attempt migration for. Add more if your schema differs.
    candidate_tables = [
        "assignments",
        "fairness_counts",
        "dynamic_fairness_counts",
        "fairnesscount",
    ]

    with engine.connect() as conn:
        for t in candidate_tables:
            try:
                print(f"Attempting ALTER TABLE {t} ALTER COLUMN task_type TYPE VARCHAR USING task_type::varchar;")
                conn.execute(text(f"ALTER TABLE {t} ALTER COLUMN task_type TYPE VARCHAR USING task_type::varchar;"))
                print(f"SUCCESS: {t}")
            except Exception as e:
                print(f"SKIP/ERROR for {t}: {e}")

        # Optionally drop the enum type if present (best to verify first).
        try:
            # Attempt to find enum types named like tasktype
            print("Attempting to drop enum type 'tasktype' if present (may fail if used elsewhere)...")
            conn.execute(text("DROP TYPE IF EXISTS tasktype;"))
            print("DROP TYPE attempted (no error).")
        except Exception as e:
            print(f"Could not drop type 'tasktype': {e}")


if __name__ == "__main__":
    main()
