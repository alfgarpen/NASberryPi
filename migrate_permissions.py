"""
migrate_permissions.py
----------------------
Migration script that creates the 'file_permission' table in nas_users.db
if it does not already exist.

Safe to run multiple times (idempotent).

Run once inside the running container, or before the app starts:
    python migrate_permissions.py
"""
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'nas_users.db')


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}.")
        print("The app will create it fresh (including file_permission) on first run. No migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if the table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_permission'")
    exists = cursor.fetchone()

    if exists:
        print("Table 'file_permission' already exists. Nothing to do.")
    else:
        cursor.execute("""
            CREATE TABLE file_permission (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                rel_path   VARCHAR(512) NOT NULL UNIQUE,
                owner_id   INTEGER REFERENCES user(id),
                visibility VARCHAR(20)  NOT NULL DEFAULT 'shared',
                can_read   BOOLEAN      NOT NULL DEFAULT 1,
                can_write  BOOLEAN      NOT NULL DEFAULT 1,
                can_delete BOOLEAN      NOT NULL DEFAULT 0,
                created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Migration successful: created 'file_permission' table.")

    conn.close()


if __name__ == '__main__':
    migrate()
