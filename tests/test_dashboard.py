"""Offscreen integration checks using disposable local history and settings."""

import csv
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config.settings import SettingsManager
from app.productivity.score_engine import ProductivityState
from app.storage.database import DatabaseManager
from app.ui.pet_window import PetWindow
from app.ui.settings_dialog import SettingsDialog


class DashboardIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = SettingsManager(Path(self.temp.name) / "config.json")
        self.settings.set("animations_enabled", False)
        self.db = DatabaseManager(Path(self.temp.name) / "history.db")
        self.tracker_patch = patch("app.ui.pet_window.ActivityTracker")
        tracker = self.tracker_patch.start().return_value
        tracker.get_system_idle_seconds.return_value = 0
        tracker.get_active_window_info.return_value = {"title": "Notes", "process_name": "notes.exe", "pid": 0}
        self.pet = PetWindow(self.settings, self.db)
        self.pet.logic_timer.stop()
        self.pet.typing_timer.stop()
        self.speech_patch = patch.object(self.pet, "_say")
        self.speech_patch.start()

    def tearDown(self):
        self.pet.shutdown()
        if self.pet.dashboard is not None:
            self.pet.dashboard.close()
        self.pet.speech_bubble.close()
        self.pet.close()
        self.pet.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.app.processEvents()
        self.speech_patch.stop()
        self.tracker_patch.stop()
        self.temp.cleanup()

    def dashboard(self):
        self.pet.open_dashboard()
        self.app.processEvents()
        dashboard = self.pet.dashboard
        dashboard.refresh_timer.stop()
        dashboard.clock_timer.stop()
        return dashboard

    def tick(self, elapsed, state=ProductivityState.PRODUCTIVE):
        """Advance only the integration clock; never read foreground apps."""
        now = self.pet._last_tick + elapsed
        with patch("app.ui.pet_window.time.monotonic", return_value=now), \
                patch.object(self.pet.prod_engine, "evaluate", return_value=(state, {})):
            self.pet._on_logic_tick()

    def test_pet_click_opens_overview_and_reuses_dashboard(self):
        self.pet.show()
        self.app.processEvents()
        QTest.mouseClick(self.pet, Qt.LeftButton, pos=QPoint(60, 60))
        self.app.processEvents()
        dashboard = self.pet.dashboard
        self.assertIsNotNone(dashboard)
        self.assertTrue(dashboard.isVisible())
        self.assertEqual(dashboard.pages.currentIndex(), 0)
        QTest.mouseClick(dashboard.nav_buttons[2], Qt.LeftButton)
        self.assertEqual(dashboard.pages.currentIndex(), 2)
        dashboard.close()
        QTest.mouseClick(self.pet, Qt.LeftButton, pos=QPoint(60, 60))
        self.assertIs(self.pet.dashboard, dashboard)
        self.assertTrue(dashboard.isVisible())
        self.assertEqual(dashboard.pages.currentIndex(), 0)

    def test_drag_moves_pet_without_opening_dashboard(self):
        self.pet.move(150, 150)
        self.pet.show()
        self.app.processEvents()
        before = self.pet.pos()
        QTest.mousePress(self.pet, Qt.LeftButton, pos=QPoint(30, 30))
        QTest.mouseMove(self.pet, QPoint(70, 60))
        QTest.mouseRelease(self.pet, Qt.LeftButton, pos=QPoint(70, 60))
        self.assertIsNone(self.pet.dashboard)
        self.assertNotEqual(self.pet.pos(), before)
        reloaded = SettingsManager(self.settings.config_path)
        self.assertEqual(reloaded.get("window_x"), self.pet.x())
        self.assertEqual(reloaded.get("window_y"), self.pet.y())

    def test_real_history_drives_stats_charts_and_session_rows(self):
        self.db.update_today_seconds(productive_delta=1800, distracted_delta=600, idle_delta=300)
        self.db.record_focus_session(900, completed=True, source="manual")
        self.db.record_focus_session(300, completed=False, source="automatic")
        dashboard = self.dashboard()
        self.assertEqual(dashboard.stat_values["productive"].text(), "30m")
        self.assertEqual(dashboard.stat_values["streak"].text(), "1 days")
        self.assertEqual(dashboard.stat_values["balance"].text(), "75%")
        self.assertEqual(dashboard.stat_values["sessions"].text(), "1")
        self.assertIn("7 days, 30m productive", dashboard.activity_chart.accessibleDescription())
        self.assertIn("30m of 2h daily goal", dashboard.goal_ring.accessibleDescription())
        self.assertEqual(dashboard.history_table.rowCount(), 2)
        results = {dashboard.history_table.item(row, 3).text() for row in range(2)}
        self.assertEqual(results, {"Completed", "Partial"})
        types = {dashboard.history_table.item(row, 2).text() for row in range(2)}
        self.assertEqual(types, {"Automatic", "Focus timer"})
        self.assertIn("55 / 250 XP", dashboard.xp_label.text())
        self.assertFalse(dashboard.grab().isNull())

        dashboard.period_picker.setCurrentIndex(1)
        self.assertEqual(dashboard.period, 30)
        self.assertIn("30 days, 30m productive", dashboard.activity_chart.accessibleDescription())
        QTest.mouseClick(dashboard.nav_buttons[2], Qt.LeftButton)
        self.assertEqual(dashboard.pages.currentIndex(), 2)
        self.assertTrue(dashboard.nav_buttons[2].isChecked())

    def test_daily_goal_persists_and_updates_progress(self):
        self.db.update_today_seconds(productive_delta=1800)
        dashboard = self.dashboard()
        dashboard.goal_input.setValue(30)
        self.assertEqual(SettingsManager(self.settings.config_path).get("daily_goal_minutes"), 30)
        self.assertIn("Goal reached!", dashboard.goal_summary.text())
        self.assertIn("30m of 30m daily goal", dashboard.goal_ring.accessibleDescription())
        self.assertTrue(dashboard.quest_labels[2].text().startswith("●"))

    def test_focus_controls_emit_durations_pause_resume_and_stop(self):
        dashboard = self.dashboard()
        QTest.mouseClick(dashboard.nav_buttons[1], Qt.LeftButton)
        started = QSignalSpy(dashboard.focus_started)
        paused = QSignalSpy(dashboard.pause_requested)
        stopped = QSignalSpy(dashboard.stop_requested)
        QTest.mouseClick(dashboard.duration_buttons[2], Qt.LeftButton)
        self.assertEqual(dashboard.timer_display.text(), "45:00")
        dashboard.focus_duration.setValue(2)
        QTest.mouseClick(dashboard.start_focus_button, Qt.LeftButton)
        self.assertEqual(started.count(), 1)
        self.assertEqual(started.at(0), [120])
        self.assertFalse(dashboard.start_focus_button.isEnabled())
        self.assertTrue(dashboard.pause_button.isEnabled())
        self.assertTrue(all(not button.isEnabled() for button in dashboard.break_buttons))

        self.tick(2)
        QTest.mouseClick(dashboard.pause_button, Qt.LeftButton)
        self.assertEqual(paused.count(), 1)
        self.assertTrue(self.pet.focus_session_mgr.is_paused)
        self.assertEqual(dashboard.pause_button.text(), "Resume")
        self.assertIn("PAUSED", dashboard.timer_status.text())
        self.tick(3)
        self.assertEqual(self.pet.focus_session_mgr.focus_elapsed_sec, 2)
        QTest.mouseClick(dashboard.pause_button, Qt.LeftButton)
        self.assertFalse(self.pet.focus_session_mgr.is_paused)
        QTest.mouseClick(dashboard.stop_button, Qt.LeftButton)
        self.assertEqual(stopped.count(), 1)
        self.assertFalse(self.pet.focus_session_mgr.is_focus_active)
        self.assertTrue(dashboard.start_focus_button.isEnabled())
        sessions = self.db.get_recent_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertFalse(sessions[0]["completed"])
        self.assertEqual(sessions[0]["duration_seconds"], 2)

    def test_break_controls_emit_duration_without_creating_focus_history(self):
        dashboard = self.dashboard()
        dashboard.navigate(1)
        started = QSignalSpy(dashboard.break_started)
        QTest.mouseClick(dashboard.break_buttons[0], Qt.LeftButton)
        self.assertEqual(started.at(0), [300])
        self.assertTrue(self.pet.focus_session_mgr.is_break_active)
        self.assertEqual(dashboard.timer_display.text(), "05:00")
        self.assertIn("BREATHE", dashboard.timer_status.text())
        QTest.mouseClick(dashboard.pause_button, Qt.LeftButton)
        self.assertTrue(self.pet.focus_session_mgr.is_paused)
        QTest.mouseClick(dashboard.stop_button, Qt.LeftButton)
        self.assertFalse(self.pet.focus_session_mgr.is_break_active)
        self.assertEqual(self.db.get_recent_sessions(), [])

    def test_completion_stop_and_shutdown_do_not_duplicate_sessions(self):
        self.pet.focus_tracker.target_milestone_sec = 2
        self.pet._start_focus_session(4)
        self.tick(2)
        self.tick(2)
        self.tick(1, ProductivityState.NEUTRAL)
        self.pet._stop_session()
        self.pet._stop_session()
        self.pet.shutdown()
        self.pet.shutdown()
        sessions = self.db.get_recent_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertTrue(sessions[0]["completed"])
        self.assertEqual(sessions[0]["duration_seconds"], 4)
        self.assertEqual(sessions[0]["source"], "manual")
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 1)
        self.assertEqual(DatabaseManager(self.db.db_path).get_streaks()["current_streak"], 1)

    def test_interruption_is_saved_once_without_growing_completed_count(self):
        self.pet._start_focus_session(60)
        self.tick(3)
        self.pet._stop_session()
        self.pet._stop_session()
        self.pet.shutdown()
        sessions = self.db.get_recent_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertFalse(sessions[0]["completed"])
        self.assertEqual(sessions[0]["duration_seconds"], 3)
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 0)

    def test_suspension_pauses_timer_without_awarding_unobserved_activity(self):
        self.pet._start_focus_session(60)
        self.tick(2)
        self.tick(3600)
        self.assertTrue(self.pet.focus_session_mgr.is_paused)
        self.assertEqual(self.pet.focus_session_mgr.focus_elapsed_sec, 2)
        self.assertEqual(self.db.get_today_stats()["productive_seconds"], 2)
        self.assertEqual(self.db.get_recent_sessions(), [])

    def test_statistics_reset_clears_pending_state_and_keeps_previous_days(self):
        previous = datetime.now() - timedelta(days=1)
        self.db.record_focus_session(900, start_time=previous - timedelta(seconds=900), end_time=previous)
        self.db.update_today_seconds(productive_delta=1800)
        self.db.record_focus_session(600)
        self.pet._start_focus_session(60)
        self.tick(3)
        dialog = SettingsDialog(self.settings, self.db, self.pet.focus_tracker, parent=self.pet)
        with patch("app.ui.settings_dialog.QMessageBox.question", return_value=QMessageBox.Yes), \
                patch("app.ui.settings_dialog.QMessageBox.information"):
            dialog._reset_today_stats()
        self.assertFalse(self.pet.focus_session_mgr.is_focus_active)
        self.pet._stop_session()
        self.pet.focus_tracker.finish_current_session()
        self.assertTrue(all(value == 0 for value in self.db.get_today_stats().values()))
        remaining = self.db.get_recent_sessions()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["date"], previous.date().isoformat())
        dialog.deleteLater()

    def test_export_contains_real_activity_and_full_calendar_range(self):
        self.db.update_today_seconds(productive_delta=1234)
        dashboard = self.dashboard()
        output = Path(self.temp.name) / "activity.csv"
        with patch("app.ui.dashboard.QFileDialog.getSaveFileName", return_value=(str(output), "CSV files (*.csv)")), \
                patch("app.ui.dashboard.QMessageBox.information"):
            dashboard.export_activity()
        with output.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 90)
        self.assertEqual(int(rows[-1]["productive_seconds"]), 1234)
        self.assertEqual(sum(int(row["productive_seconds"]) for row in rows), 1234)

    def test_dashboard_honors_disabled_animations(self):
        dashboard = self.dashboard()
        self.assertFalse(dashboard.mini_pet.timer.isActive())


if __name__ == "__main__":
    unittest.main()
