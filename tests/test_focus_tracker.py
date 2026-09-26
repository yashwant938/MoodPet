import tempfile
import unittest
from datetime import date, datetime, time as datetime_time, timedelta
from pathlib import Path
from unittest.mock import patch

from app.productivity.focus_tracker import FocusTracker
from app.productivity.score_engine import ProductivityState
from app.storage.database import DatabaseManager


class FocusTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = DatabaseManager(Path(self.temp.name) / "moodpet.db")
        self.tracker = FocusTracker(self.db)
        self.now = datetime.combine(date.today(), datetime_time(12)).timestamp()

    def test_milestone_notifies_once_and_end_records_one_full_session(self):
        with patch("app.productivity.focus_tracker.time") as clock:
            clock.time.side_effect = [self.now, self.now + 120]
            first = self.tracker.update(ProductivityState.PRODUCTIVE, 1800)
            self.assertTrue(first["milestone_triggered"])
            self.assertEqual(self.db.get_recent_sessions(), [])
            second = self.tracker.update(ProductivityState.PRODUCTIVE, 120)
            self.assertFalse(second["milestone_triggered"])
        result = self.tracker.update(ProductivityState.DISTRACTING, 1)
        sessions = self.db.get_recent_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["duration_seconds"], 1920)
        self.assertEqual(sessions[0]["source"], "automatic")
        self.assertTrue(sessions[0]["completed"])
        self.assertEqual(result["focus_sessions_today"], 1)
        self.assertEqual(result["current_streak"], 1)
        self.assertEqual(result["current_focus_seconds"], 0)
        self.assertIsNone(self.tracker.finish_current_session())
        self.tracker.update(ProductivityState.IDLE, 1)
        self.assertEqual(len(self.db.get_recent_sessions()), 1)

    def test_interrupted_block_is_saved_without_completed_count(self):
        with patch("app.productivity.focus_tracker.time.time", return_value=self.now):
            self.tracker.update(ProductivityState.PRODUCTIVE, 600)
        self.tracker.update(ProductivityState.NEUTRAL, 1)
        session = self.db.get_recent_sessions()[0]
        self.assertFalse(session["completed"])
        self.assertEqual(session["duration_seconds"], 600)
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 0)

    def test_manual_mode_records_activity_without_duplicate_sessions(self):
        result = self.tracker.update(ProductivityState.PRODUCTIVE, 1800, record_sessions=False)
        self.assertFalse(result["milestone_triggered"])
        self.assertEqual(result["productive_seconds_today"], 1800)
        self.assertEqual(result["current_focus_seconds"], 0)
        self.db.record_focus_session(1800, source="manual")
        self.tracker.finish_current_session()
        self.assertEqual(len(self.db.get_recent_sessions()), 1)
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 1)

    def test_switch_to_manual_finishes_only_preceding_automatic_time(self):
        with patch("app.productivity.focus_tracker.time.time", return_value=self.now):
            self.tracker.update(ProductivityState.PRODUCTIVE, 1800)
        self.tracker.update(ProductivityState.PRODUCTIVE, 60, record_sessions=False)
        self.tracker.update(ProductivityState.PRODUCTIVE, 60, record_sessions=False)
        self.assertEqual(len(self.db.get_recent_sessions()), 1)
        self.assertEqual(self.db.get_recent_sessions()[0]["duration_seconds"], 1800)
        self.assertEqual(self.db.get_today_stats()["productive_seconds"], 1920)

    def test_streak_survives_tracker_restart_and_distraction(self):
        yesterday = datetime.combine(date.today() - timedelta(days=1), datetime_time(18))
        self.db.record_focus_session(1500, end_time=yesterday)
        restarted = FocusTracker(DatabaseManager(self.db.db_path))
        self.assertEqual(restarted.current_streak, 1)
        result = restarted.update(ProductivityState.DISTRACTING, 60)
        self.assertEqual(result["current_streak"], 1)
        restarted.update(ProductivityState.PRODUCTIVE, 900, record_sessions=False)
        self.assertEqual(restarted.current_streak, 2)

    def test_reset_cannot_recreate_cleared_session(self):
        with patch("app.productivity.focus_tracker.time.time", return_value=self.now):
            self.tracker.update(ProductivityState.PRODUCTIVE, 1800)
        self.db.reset_today_stats()
        self.tracker.reset_current_session()
        self.tracker.update(ProductivityState.IDLE, 1)
        self.assertEqual(self.db.get_recent_sessions(), [])
        self.assertEqual(self.db.get_today_stats()["productive_seconds"], 0)
        self.assertEqual(self.tracker.current_streak, 0)

    def test_fractional_ticks_preserve_activity_time(self):
        for _ in range(10):
            self.tracker.update(ProductivityState.PRODUCTIVE, 0.1, record_sessions=False)
        for _ in range(2):
            self.tracker.update(ProductivityState.IDLE, 0.5)
        self.assertEqual(self.db.get_today_stats()["productive_seconds"], 1)
        self.assertEqual(self.db.get_today_stats()["idle_seconds"], 1)

    def test_small_blocks_do_not_clutter_history(self):
        with patch("app.productivity.focus_tracker.time.time", return_value=self.now):
            self.tracker.update(ProductivityState.PRODUCTIVE, 59)
        self.tracker.finish_current_session()
        self.assertEqual(self.db.get_recent_sessions(), [])

    def test_invalid_elapsed_does_not_change_counters(self):
        for elapsed in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.tracker.update(ProductivityState.PRODUCTIVE, elapsed)
        self.assertEqual(self.db.get_today_stats()["productive_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
