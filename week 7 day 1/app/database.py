import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from app.config import get_settings
from app.schemas import TripCreate

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    destination TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','completed','cancelled')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trips_employee ON trips(employee_id);
"""

@contextmanager
def connection():
    conn = sqlite3.connect(get_settings().database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)

def create_trip(data: TripCreate) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cur = conn.execute(
            """INSERT INTO trips(employee_id,destination,start_date,end_date,purpose,status,created_at)
               VALUES(?,?,?,?,?,'planned',?)""",
            (data.employee_id, data.destination, data.start_date.isoformat(),
             data.end_date.isoformat(), data.purpose, now),
        )
        row = conn.execute("SELECT * FROM trips WHERE trip_id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

def get_trip(trip_id: int) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM trips WHERE trip_id=?", (trip_id,)).fetchone()
    return dict(row) if row else None
