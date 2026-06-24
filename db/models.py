"""
db/models.py
Subscriber model and database initialization.
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

# Detect environment
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///micro_grc.db")
_IS_POSTGRES = DATABASE_URL.startswith("postgres")


def _get_sqlite_path() -> str:
    """Extract file path from sqlite:/// URL."""
    return DATABASE_URL.replace("sqlite:///", "")


@contextmanager
def get_connection():
    """
    Context manager that yields a DB connection.
    Handles both SQLite and PostgreSQL transparently.
    """
    if _IS_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(_get_sqlite_path())
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db():
    """
    Create tables if they don't exist.
    Call once at app startup from app.py.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number    TEXT NOT NULL UNIQUE,
                language        TEXT NOT NULL DEFAULT 'en',
                business_type   TEXT NOT NULL,
                has_employees   INTEGER NOT NULL DEFAULT 0,
                collects_data   INTEGER NOT NULL DEFAULT 0,
                has_premises    INTEGER NOT NULL DEFAULT 0,
                above_threshold INTEGER NOT NULL DEFAULT 0,
                risk_level      TEXT,
                opted_in_at     TEXT NOT NULL,
                next_reminder_at TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            )
        """)
        # Index for the daily scheduler query
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_next_reminder
            ON subscribers(next_reminder_at, is_active)
        """)


# ---------------------------------------------------------------------------
# Subscriber CRUD
# ---------------------------------------------------------------------------

def upsert_subscriber(
    phone_number: str,
    language: str,
    business_type: str,
    flags: dict,
    risk_level: str,
) -> bool:
    """
    Insert a new subscriber or reactivate an existing one.
    flags: {"has_employees", "collects_data", "has_premises", "above_threshold"}
    Returns True if this was a new subscription.
    """
    now = datetime.utcnow().isoformat()
    next_reminder = (datetime.utcnow() + timedelta(days=30)).date().isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()

        # Check if already exists
        cursor.execute(
            "SELECT id, is_active FROM subscribers WHERE phone_number = ?",
            (phone_number,)
        ) if not _IS_POSTGRES else cursor.execute(
            "SELECT id, is_active FROM subscribers WHERE phone_number = %s",
            (phone_number,)
        )
        existing = cursor.fetchone()

        if existing:
            # Reactivate and update their profile
            sql = """
                UPDATE subscribers SET
                    language = ?, business_type = ?,
                    has_employees = ?, collects_data = ?,
                    has_premises = ?, above_threshold = ?,
                    risk_level = ?, is_active = 1,
                    next_reminder_at = ?
                WHERE phone_number = ?
            """ if not _IS_POSTGRES else """
                UPDATE subscribers SET
                    language = %s, business_type = %s,
                    has_employees = %s, collects_data = %s,
                    has_premises = %s, above_threshold = %s,
                    risk_level = %s, is_active = 1,
                    next_reminder_at = %s
                WHERE phone_number = %s
            """
            cursor.execute(sql, (
                language, business_type,
                int(flags.get("has_employees", False)),
                int(flags.get("collects_data", False)),
                int(flags.get("has_premises", False)),
                int(flags.get("above_threshold", False)),
                risk_level, next_reminder, phone_number
            ))
            return not bool(existing["is_active"])  # True if was inactive

        # New subscriber
        sql = """
            INSERT INTO subscribers (
                phone_number, language, business_type,
                has_employees, collects_data, has_premises, above_threshold,
                risk_level, opted_in_at, next_reminder_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """ if not _IS_POSTGRES else """
            INSERT INTO subscribers (
                phone_number, language, business_type,
                has_employees, collects_data, has_premises, above_threshold,
                risk_level, opted_in_at, next_reminder_at, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        cursor.execute(sql, (
            phone_number, language, business_type,
            int(flags.get("has_employees", False)),
            int(flags.get("collects_data", False)),
            int(flags.get("has_premises", False)),
            int(flags.get("above_threshold", False)),
            risk_level, now, next_reminder
        ))
        return True


def deactivate_subscriber(phone_number: str) -> bool:
    """Opt a user out. Called when they reply STOP."""
    ph = "?" if not _IS_POSTGRES else "%s"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscribers SET is_active = 0 WHERE phone_number = {ph}",
            (phone_number,)
        )
        return cursor.rowcount > 0


def get_due_subscribers() -> list:
    """
    Return all active subscribers whose next_reminder_at is today or earlier.
    Called by the daily scheduler.
    """
    today = datetime.utcnow().date().isoformat()
    ph = "?" if not _IS_POSTGRES else "%s"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM subscribers WHERE is_active = 1 AND next_reminder_at <= {ph}",
            (today,)
        )
        return [dict(row) for row in cursor.fetchall()]


def update_next_reminder(phone_number: str, days: int = 30):
    """Advance next_reminder_at by N days after a reminder is sent."""
    next_date = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    ph = "?" if not _IS_POSTGRES else "%s"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscribers SET next_reminder_at = {ph} WHERE phone_number = {ph}",
            (next_date, phone_number)
        )