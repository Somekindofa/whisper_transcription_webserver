"""
Umbrella migration script for SQLite DB schema upgrades.
- Adds missing columns to 'files' table as needed.
- Safe to run multiple times (idempotent).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "storage" / "transcriptions.db"

MIGRATIONS = [
    # (column_name, column_type, default_value)
    ("progress_percent", "REAL", "0"),
    ("processing_seconds", "REAL", "0"),
]

def column_exists(conn, table, column):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate():
    with sqlite3.connect(DB_PATH) as conn:
        for col, col_type, default in MIGRATIONS:
            if not column_exists(conn, "files", col):
                print(f"Adding column '{col}' to 'files' table...")
                conn.execute(f"ALTER TABLE files ADD COLUMN {col} {col_type} DEFAULT {default}")
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
