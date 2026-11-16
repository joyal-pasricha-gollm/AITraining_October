from datetime import date, timedelta
from app.database import connection, init_db

def seed():
    init_db()
    start=date.today()+timedelta(days=2)
    sample_trips = [
        ("EMP104", "Jaipur", start, "Client meeting"),
        ("EMP105", "Mumbai", start + timedelta(days=1), "Partner workshop"),
        ("EMP106", "Bengaluru", start + timedelta(days=2), "Project review"),
    ]
    with connection() as conn:
        for employee_id, destination, trip_start, purpose in sample_trips:
            exists=conn.execute(
                "SELECT 1 FROM trips WHERE employee_id=? AND start_date=?",
                (employee_id, trip_start.isoformat()),
            ).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO trips(employee_id,destination,start_date,end_date,purpose,status,created_at)
                    VALUES(?,?,?,?,?,'planned',datetime('now'))""",
                    (
                        employee_id,
                        destination,
                        trip_start.isoformat(),
                        (trip_start + timedelta(days=2)).isoformat(),
                        purpose,
                    ),
                )
    print("Database initialized with sample trips for EMP104, EMP105, and EMP106.")

if __name__ == "__main__": seed()
