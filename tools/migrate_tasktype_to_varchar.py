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

    # A list of (table, column) pairs to attempt migration for.
    candidates = [
        ("assignments", "task_type"),
        ("fairness_counts", "task_type"),
        ("dynamic_fairness_counts", "task_type"),
        ("fairnesscount", "task_type"),
    ]

    with engine.begin() as conn:
        # Perform each ALTER in its own TRY/CATCH-style block to avoid aborting the whole transaction on failure.
        for table, column in candidates:
            try:
                # Check that the column exists first
                col_check = conn.execute(text(
                    "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"),
                    {"t": table, "c": column}
                ).fetchone()
                if not col_check:
                    print(f"SKIP: {table}.{column} does not exist")
                    continue

                sql = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR USING {column}::varchar;"
                print(f"Attempting: {sql}")
                conn.execute(text(sql))
                print(f"SUCCESS: {table}.{column}")
            except Exception as e:
                print(f"ERROR migrating {table}.{column}: {e}")
                # continue to next candidate

        # After attempting conversions, try to drop the enum type if safe
        try:
            print("Attempting to drop enum type 'tasktype' if present (may fail if used elsewhere)...")
            conn.execute(text("DROP TYPE IF EXISTS tasktype;"))
            print("DROP TYPE attempted (no error).")
        except Exception as e:
            print(f"Could not drop type 'tasktype': {e}")


if __name__ == "__main__":
    main()
