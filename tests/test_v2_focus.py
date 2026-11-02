"""Task and crash-checkpoint regression checks with disposable profiles."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import closing

from app.storage.database import DatabaseManager


class FocusRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'history.db'
        self.db = DatabaseManager(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_task_history_status_and_restart(self):
        task = self.db.create_task('Fix a linker bug', 'ELD', 3600)
        started = datetime.now() - timedelta(minutes=20)
        self.db.save_checkpoint(started, 0, 1500, False, task_id=task, new=True)
        self.db.save_checkpoint(started, 600, 1500, True)
        self.assertTrue(self.db.get_checkpoint()['paused'])
        self.db.finish_checkpoint()
        db = DatabaseManager(self.path)
        self.assertEqual(db.get_tasks()[0]['focused_seconds'], 600)
        self.assertEqual(db.get_recent_sessions()[0]['task_name'], 'Fix a linker bug')
        db.update_task(task, name='Test a linker fix', status='completed')
        self.assertEqual(db.get_tasks()[0]['status'], 'completed')
        db.update_task(task, status='archived')
        self.assertEqual(db.get_tasks()[0]['focused_seconds'], 600)

    def test_restart_recovery_saves_last_checkpoint_once_without_completion_xp(self):
        started = datetime.now() - timedelta(hours=2)
        self.db.save_checkpoint(started, 0, 1500, False, new=True)
        self.db.save_checkpoint(started, 320, 1500, False)
        db = DatabaseManager(self.path)
        self.assertEqual(db.get_checkpoint()['elapsed'], 320)
        self.assertTrue(db.finish_checkpoint())
        self.assertFalse(db.finish_checkpoint())
        self.assertEqual(len(db.get_recent_sessions()), 1)
        self.assertFalse(db.get_recent_sessions()[0]['completed'])
        self.assertEqual(db.get_lifetime_stats()['completed_sessions'], 0)

    def test_discard_and_completed_save_are_idempotent(self):
        started = datetime.now()
        self.db.save_checkpoint(started, 0, 2, False, new=True)
        self.db.save_checkpoint(started, 2, 2, False)
        self.db.finish_checkpoint(completed=True)
        self.assertFalse(self.db.finish_checkpoint(completed=True))
        self.assertEqual(self.db.get_today_stats()['focus_sessions_count'], 1)
        self.db.save_checkpoint(started, 0, 2, False, new=True)
        self.db.finish_checkpoint(discard=True)
        self.assertEqual(len(self.db.get_recent_sessions()), 1)

    def test_recovery_transaction_rolls_back_on_database_failure(self):
        started = datetime.now()
        self.db.save_checkpoint(started, 0, 90, False, new=True)
        self.db.save_checkpoint(started, 30, 90, False)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("CREATE TRIGGER reject_session BEFORE INSERT ON focus_sessions BEGIN SELECT RAISE(ABORT, 'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.finish_checkpoint()
        self.assertIsNotNone(self.db.get_checkpoint())
        self.assertEqual(self.db.get_recent_sessions(), [])

    def test_cross_midnight_uses_last_checkpoint_day_and_clock_cannot_reverse_end(self):
        now = datetime.now()
        started = now - timedelta(days=1)
        self.db.save_checkpoint(started, 0, 1500, False, new=True)
        self.db.save_checkpoint(started, 600, 1500, True)
        self.db.finish_checkpoint()
        self.assertEqual(self.db.get_recent_sessions()[0]['date'], now.date().isoformat())
        future = now + timedelta(days=1)
        self.db.save_checkpoint(future, 0, 60, False, new=True)
        checkpoint = self.db.get_checkpoint()
        self.assertGreaterEqual(datetime.fromisoformat(checkpoint['updated']), future)

    def test_existing_checkpoint_cannot_be_overwritten_by_new_session(self):
        self.db.save_checkpoint(datetime.now(), 0, 60, False, new=True)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.save_checkpoint(datetime.now(), 0, 60, False, new=True)


if __name__ == '__main__':
    unittest.main()
