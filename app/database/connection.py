import sqlite3

from app.config import get_settings


def connect():
    path = get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    get_settings().uploads_path.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS submission (
            id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            file_id TEXT NOT NULL UNIQUE,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL CHECK(file_size >= 0),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_submission_assignment ON submission(assignment_id)")
