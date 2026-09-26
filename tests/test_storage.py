import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path

from app.storage.database import DatabaseManager


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "moodpet.db"
        self.db = DatabaseManager(self.path)

    def add_day(self, day, productive=0, sessions=0):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO daily_stats (date, productive_seconds, focus_sessions_count) VALUES (?, ?, ?)",
                (day.isoformat(), productive, sessions),
            )

    def test_history_is_sorted_zero_filled_and_survives_restart(self):
        end = date(2026, 9, 26)
        self.add_day(end - timedelta(days=2), productive=900)
        self.add_day(end, productive=1400)
        history = DatabaseManager(self.path).get_daily_history(4, end)
        self.assertEqual([row["date"] for row in history], ["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-26"])
        self.assertEqual([row["productive_seconds"] for row in history], [0, 900, 0, 1400])
        self.assertEqual(set(history[0]), {"date", *DatabaseManager.STAT_FIELDS})
        with closing(sqlite3.connect(self.path)) as conn, conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM daily_stats").fetchone()[0], 2)

    def test_streak_threshold_gaps_grace_and_future_rows(self):
        today = date(2026, 9, 26)
        for offset in (8, 7, 6):
            self.add_day(today - timedelta(days=offset), productive=900)
        self.add_day(today - timedelta(days=3), productive=899)
        self.add_day(today - timedelta(days=2), sessions=1)
        self.add_day(today - timedelta(days=1), productive=900)
        self.add_day(today + timedelta(days=1), productive=900)
        self.assertEqual(self.db.get_streaks(today), {"current_streak": 2, "best_streak": 3, "active_days": 5})
        self.add_day(today, productive=900)
        self.assertEqual(self.db.get_streaks(today)["current_streak"], 3)
        self.assertEqual(self.db.get_streaks(today + timedelta(days=3))["current_streak"], 0)
        self.assertEqual(self.db.get_streaks(today + timedelta(days=3))["best_streak"], 4)

    def test_empty_database_has_zero_streak_and_lifetime(self):
        self.assertEqual(self.db.get_streaks(), {"current_streak": 0, "best_streak": 0, "active_days": 0})
        self.assertEqual(self.db.get_lifetime_stats(), {
            "productive_seconds": 0, "completed_sessions": 0,
            "longest_session_seconds": 0, "active_days": 0,
        })

    def test_interrupted_sessions_do_not_count_and_dates_are_truthful(self):
        ended = datetime.combine(date.today(), time(10, 0))
        aborted_id = self.db.record_focus_session(600, completed=False, end_time=ended)
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 0)
        self.assertEqual(self.db.get_streaks()["current_streak"], 0)
        completed_id = self.db.record_focus_session(1500, end_time=ended + timedelta(hours=1), source="manual")
        recent = self.db.get_recent_sessions()
        self.assertEqual([row["id"] for row in recent], [completed_id, aborted_id])
        self.assertFalse(recent[1]["completed"])
        self.assertEqual(recent[0]["source"], "manual")
        self.assertEqual(datetime.fromisoformat(recent[0]["end_time"]) - datetime.fromisoformat(recent[0]["start_time"]), timedelta(seconds=1500))
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 1)
        self.assertEqual(self.db.get_lifetime_stats()["longest_session_seconds"], 1500)
        self.assertEqual(self.db.get_lifetime_stats()["active_days"], 1)

    def test_cross_midnight_session_uses_its_end_date(self):
        started = datetime(2026, 9, 25, 23, 55)
        ended = datetime(2026, 9, 26, 0, 20)
        self.db.record_focus_session(1500, start_time=started, end_time=ended)
        session = self.db.get_recent_sessions()[0]
        self.assertEqual(session["date"], "2026-09-26")
        self.assertEqual(session["start_time"], "2026-09-25 23:55:00")
        self.assertEqual(self.db.get_daily_history(2, ended)[0]["focus_sessions_count"], 0)
        self.assertEqual(self.db.get_daily_history(2, ended)[1]["focus_sessions_count"], 1)

    def test_session_and_aggregate_roll_back_together(self):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("""
                CREATE TRIGGER reject_daily_update BEFORE UPDATE ON daily_stats
                BEGIN SELECT RAISE(ABORT, 'simulated failure'); END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.record_focus_session(1500)
        self.assertEqual(self.db.get_recent_sessions(), [])
        with closing(sqlite3.connect(self.path)) as conn, conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM daily_stats").fetchone()[0], 0)

    def test_reset_clears_today_sessions_but_preserves_previous_days(self):
        yesterday = datetime.combine(date.today() - timedelta(days=1), time(18))
        old_id = self.db.record_focus_session(1800, end_time=yesterday)
        self.db.update_today_seconds(1000, 80, 120)
        self.db.record_focus_session(1500)
        self.db.record_focus_session(600, completed=False)
        self.db.reset_today_stats()
        self.assertEqual(self.db.get_today_stats(), DatabaseManager._empty_stats())
        self.assertEqual([row["id"] for row in self.db.get_recent_sessions()], [old_id])
        self.assertEqual(self.db.get_lifetime_stats()["completed_sessions"], 1)
        self.assertEqual(self.db.get_streaks()["current_streak"], 1)

    def test_concurrent_writers_preserve_totals_and_completions(self):
        def add_session(_):
            self.db.update_today_seconds(productive_delta=10)
            self.db.record_focus_session(600)

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(add_session, range(12)))
        stats = self.db.get_today_stats()
        self.assertEqual(stats["productive_seconds"], 120)
        self.assertEqual(stats["focus_sessions_count"], 12)
        self.assertEqual(len(self.db.get_recent_sessions(20)), 12)

    def test_invalid_input_does_not_write_partial_history(self):
        for duration in (-1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                self.db.record_focus_session(duration)
        with self.assertRaises(ValueError):
            self.db.update_today_seconds(productive_delta=-1)
        with self.assertRaises(ValueError):
            self.db.record_focus_session(60, start_time="2026-09-26T12:00:00", end_time="2026-09-26T11:00:00")
        self.assertEqual(self.db.get_recent_sessions(), [])


class LegacyMigrationTests(unittest.TestCase):
    def test_migrates_in_place_preserving_ids_sessions_and_activity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.executescript("""
                    CREATE TABLE daily_stats (
                        date TEXT PRIMARY KEY, productive_seconds INTEGER DEFAULT 0,
                        distracted_seconds INTEGER DEFAULT 0, idle_seconds INTEGER DEFAULT 0,
                        focus_sessions_count INTEGER DEFAULT 0, longest_session_seconds INTEGER DEFAULT 0
                    );
                    CREATE TABLE focus_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, start_time TEXT,
                        end_time TEXT, duration_seconds INTEGER, completed INTEGER DEFAULT 1
                    );
                    INSERT INTO daily_stats VALUES ('2026-09-25', 3000, 45, 80, 2, 1800);
                    INSERT INTO focus_sessions VALUES (41, '2026-09-25', '2026-09-25 10:00:00', '2026-09-25 10:30:00', 1800, 1);
                    INSERT INTO focus_sessions VALUES (42, '2026-09-25', '2026-09-25 12:00:00', '2026-09-25 12:10:00', 600, 0);
                """)
            db = DatabaseManager(path)
            self.assertEqual([row["id"] for row in db.get_recent_sessions()], [42, 41])
            self.assertEqual({row["source"] for row in db.get_recent_sessions()}, {"legacy"})
            day = db.get_daily_history(1, "2026-09-25")[0]
            self.assertEqual(day["productive_seconds"], 3000)
            self.assertEqual(day["distracted_seconds"], 45)
            self.assertEqual(day["focus_sessions_count"], 1)
            self.assertEqual(db.get_lifetime_stats()["completed_sessions"], 1)
            self.assertEqual(DatabaseManager(path).get_recent_sessions(), db.get_recent_sessions())
            self.assertGreater(db.record_focus_session(900), 42)


if __name__ == "__main__":
    unittest.main()
