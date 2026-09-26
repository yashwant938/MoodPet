"""Local, durable activity history and calendar-day streaks."""

import math
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path


class DatabaseManager:
    """Store aggregate activity and focus sessions in a local SQLite database."""

    STAT_FIELDS = (
        "productive_seconds", "distracted_seconds", "idle_seconds",
        "focus_sessions_count", "longest_session_seconds",
    )
    STREAK_PRODUCTIVE_SECONDS = 15 * 60

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path is not None else Path.home() / ".moodpet" / "moodpet.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self):
        conn = self._get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Upgrade existing installs in place without deleting history."""
        with self._connection() as conn:
            # Include DDL in the same transaction as migration repairs. Without
            # an explicit BEGIN, SQLite can commit ALTER TABLE before repairs.
            conn.execute("BEGIN")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    productive_seconds INTEGER DEFAULT 0,
                    distracted_seconds INTEGER DEFAULT 0,
                    idle_seconds INTEGER DEFAULT 0,
                    focus_sessions_count INTEGER DEFAULT 0,
                    longest_session_seconds INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration_seconds INTEGER,
                    completed INTEGER DEFAULT 1,
                    source TEXT NOT NULL DEFAULT 'manual'
                )
            """)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(focus_sessions)")}
            if "source" not in columns:
                conn.execute("ALTER TABLE focus_sessions ADD COLUMN source TEXT NOT NULL DEFAULT 'legacy'")
                # Older versions counted interrupted sessions as completions.
                # Retain every session, but correct the derived daily counts.
                conn.execute("INSERT OR IGNORE INTO daily_stats (date) SELECT DISTINCT date FROM focus_sessions WHERE date IS NOT NULL")
                conn.execute("""
                    UPDATE daily_stats SET
                        focus_sessions_count = (
                            SELECT COUNT(*) FROM focus_sessions
                            WHERE focus_sessions.date = daily_stats.date AND completed = 1
                        ),
                        longest_session_seconds = MAX(longest_session_seconds, COALESCE((
                            SELECT MAX(duration_seconds) FROM focus_sessions
                            WHERE focus_sessions.date = daily_stats.date
                        ), 0))
                    WHERE date IN (SELECT date FROM focus_sessions)
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_date ON focus_sessions(date)")

    @staticmethod
    def _as_date(value=None):
        if value is None:
            return date.today()
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @staticmethod
    def _as_datetime(value):
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, (int, float)):
            result = datetime.fromtimestamp(value)
        else:
            result = datetime.fromisoformat(value)
        # Stored dates represent the user's local calendar, including explicitly
        # supplied timestamps with a timezone.
        if result.tzinfo is not None:
            result = result.astimezone().replace(tzinfo=None)
        return result

    @staticmethod
    def _seconds(value):
        if not math.isfinite(value) or value < 0:
            raise ValueError("Seconds must be finite and nonnegative")
        return int(value)

    @classmethod
    def _empty_stats(cls):
        return dict.fromkeys(cls.STAT_FIELDS, 0)

    def get_today_stats(self):
        """Fetch today's counters, creating an empty day when necessary."""
        today_str = date.today().isoformat()
        with self._connection() as conn:
            conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today_str,))
            row = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (today_str,)).fetchone()
        return {key: row[key] for key in self.STAT_FIELDS}

    def update_today_seconds(self, productive_delta=0, distracted_delta=0, idle_delta=0):
        """Atomically add nonnegative whole seconds to today's activity."""
        deltas = tuple(self._seconds(value) for value in (productive_delta, distracted_delta, idle_delta))
        today_str = date.today().isoformat()
        with self._connection() as conn:
            conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today_str,))
            conn.execute("""
                UPDATE daily_stats SET
                    productive_seconds = productive_seconds + ?,
                    distracted_seconds = distracted_seconds + ?,
                    idle_seconds = idle_seconds + ?
                WHERE date = ?
            """, (*deltas, today_str))

    def record_focus_session(self, duration_seconds, completed=True, start_time=None, end_time=None, source="manual"):
        """Record one session and its aggregate in a single transaction.

        Explicit timestamps can be datetime objects, ISO strings, or Unix
        timestamps. Without a start time it is inferred from the duration.
        Sessions belong to the local calendar day on which they end.
        Interrupted sessions remain in history but do not count as completions.
        """
        duration = self._seconds(duration_seconds)
        ended = self._as_datetime(end_time) if end_time is not None else datetime.now()
        started = self._as_datetime(start_time) if start_time is not None else ended - timedelta(seconds=duration)
        if ended < started:
            raise ValueError("Session end must not precede its start")
        if not isinstance(source, str) or not source.strip() or len(source) > 64:
            raise ValueError("Session source must be a nonempty string of at most 64 characters")
        session_date = ended.date().isoformat()
        with self._connection() as conn:
            conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (session_date,))
            cursor = conn.execute("""
                INSERT INTO focus_sessions (date, start_time, end_time, duration_seconds, completed, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_date, started.isoformat(sep=" ", timespec="seconds"),
                  ended.isoformat(sep=" ", timespec="seconds"), duration, int(bool(completed)), source.strip()))
            conn.execute("""
                UPDATE daily_stats SET
                    focus_sessions_count = focus_sessions_count + ?,
                    longest_session_seconds = MAX(longest_session_seconds, ?)
                WHERE date = ?
            """, (int(bool(completed)), duration, session_date))
            return cursor.lastrowid

    def get_daily_history(self, days=7, end_date=None):
        """Return ascending, zero-filled daily counters for a calendar range."""
        if not isinstance(days, int) or days < 1:
            raise ValueError("days must be a positive integer")
        end = self._as_date(end_date)
        start = end - timedelta(days=days - 1)
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM daily_stats WHERE date BETWEEN ? AND ? ORDER BY date", (start.isoformat(), end.isoformat())).fetchall()
        by_date = {row["date"]: dict(row) for row in rows}
        result = []
        for offset in range(days):
            key = (start + timedelta(days=offset)).isoformat()
            result.append(by_date.get(key, {"date": key, **self._empty_stats()}))
        return result

    def get_streaks(self, today=None):
        """A day qualifies with 15 productive minutes or one completed session.

        Yesterday's streak remains current until the end of today, giving the
        user the entire day to continue it. Future rows never inflate streaks.
        """
        current_day = self._as_date(today)
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT date FROM daily_stats WHERE date <= ?
                AND (productive_seconds >= ? OR focus_sessions_count > 0)
                ORDER BY date
            """, (current_day.isoformat(), self.STREAK_PRODUCTIVE_SECONDS)).fetchall()
        active_dates = [date.fromisoformat(row["date"]) for row in rows]
        best = run = 0
        previous = None
        for active_day in active_dates:
            run = run + 1 if previous is not None and active_day - previous == timedelta(days=1) else 1
            best = max(best, run)
            previous = active_day
        current = run if previous in (current_day, current_day - timedelta(days=1)) else 0
        return {"current_streak": current, "best_streak": best, "active_days": len(active_dates)}

    def get_lifetime_stats(self):
        with self._connection() as conn:
            row = conn.execute("""
                SELECT COALESCE(SUM(productive_seconds), 0) AS productive_seconds,
                    COALESCE(SUM(focus_sessions_count), 0) AS completed_sessions,
                    COALESCE(MAX(longest_session_seconds), 0) AS longest_session_seconds,
                    COALESCE(SUM(CASE WHEN productive_seconds >= ? OR focus_sessions_count > 0 THEN 1 ELSE 0 END), 0) AS active_days
                FROM daily_stats
            """, (self.STREAK_PRODUCTIVE_SECONDS,)).fetchone()
        return dict(row)

    def get_recent_sessions(self, limit=8):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT id, date, start_time, end_time, duration_seconds, completed, source
                FROM focus_sessions ORDER BY end_time DESC, id DESC LIMIT ?
            """, (limit,)).fetchall()
        return [{**dict(row), "completed": bool(row["completed"])} for row in rows]

    def reset_today_stats(self):
        """Clear today's counters and sessions together; preserve earlier days."""
        today_str = date.today().isoformat()
        with self._connection() as conn:
            conn.execute("DELETE FROM focus_sessions WHERE date = ?", (today_str,))
            conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today_str,))
            conn.execute("""
                UPDATE daily_stats SET productive_seconds = 0, distracted_seconds = 0,
                    idle_seconds = 0, focus_sessions_count = 0, longest_session_seconds = 0
                WHERE date = ?
            """, (today_str,))
