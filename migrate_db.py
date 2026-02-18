"""
migrate_db.py
-------------
One-time migration script to add the 'must_change_password' column
to the existing 'user' table in nas_users.db.

Run this ONCE before starting the app after the model update:
    python migrate_db.py

Safe to run multiple times (checks if column already exists).
"""
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'nas_users.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}.")
        print("The app will create it fresh on first run. No migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'must_change_password' in columns:
        print("Column 'must_change_password' already exists. Nothing to do.")
    else:
        cursor.execute(
            "ALTER TABLE user ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
        )
        conn.commit()
        print("Migration successful: added 'must_change_password' column.")

    conn.close()

if __name__ == '__main__':
    migrate()
