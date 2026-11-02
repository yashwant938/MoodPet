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
from PySide6.QtGui import QColor, QPalette
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
        self.settings.set("tracking_mode", "automatic")  # explicit opt-in fixture
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

    def test_timer_only_charts_and_repair_button_show_real_data(self):
        self.settings.set('tracking_mode','manual')
        today=datetime.now().date()
        before=today-timedelta(days=2)
        self.db.record_focus_session(22200,end_time=datetime.combine(before,datetime.min.time())+timedelta(hours=12))
        self.db.record_focus_session(12,completed=False)
        dashboard=self.dashboard()
        self.assertEqual(dashboard.measure_picker.currentData(),'manual')
        self.assertEqual(sum(r['productive_seconds'] for r in dashboard.activity_chart._rows),22212)
        self.assertIn('6h 10m saved focus time',dashboard.chart_summary.text())
        self.assertIn('6h 10m of saved focus time',dashboard.badge_label.text())
        dashboard.resize(960,640)
        self.app.processEvents()
        self.assertEqual(dashboard.pages.currentWidget().horizontalScrollBar().maximum(),0)
        self.assertEqual(self.db.get_streaks()['current_streak'],1)
        xp=self.db.get_evolution_snapshot()['progress'].xp
        self.assertTrue(dashboard.repair_button.isEnabled())
        dashboard.pages.currentWidget().ensureWidgetVisible(dashboard.repair_button)
        self.app.processEvents()
        QTest.mouseClick(dashboard.repair_button,Qt.LeftButton)
        self.assertEqual(self.db.get_streaks()['current_streak'],3)
        self.assertEqual(self.db.get_streak_repair_status()['remaining'],1)
        self.assertEqual(self.db.get_evolution_snapshot()['progress'].xp,xp)
        self.assertIn(today-timedelta(days=1),dashboard.heatmap.repaired_days)
        dashboard.measure_picker.setCurrentIndex(1)
        self.assertEqual(sum(r['productive_seconds'] for r in dashboard.activity_chart._rows),0)

    def test_pet_menu_shows_current_task_and_separate_weekly_averages(self):
        self.db.get_previous_week_totals = lambda: {
            "start": datetime(2026, 10, 26).date(), "end": datetime(2026, 11, 1).date(),
            "timer_seconds": 7 * 5400, "tracked_seconds": 7 * 7200,
        }
        idle = self.pet._create_context_menu()
        texts = [a.text() for a in idle.actions()]
        self.assertEqual(texts[:4], ["No focus session running", "Last week (26 Oct–01 Nov) · daily average",
                         "Focus timers: 1h 30m / day", "Tracked productive: 2h 00m / day"])
        self.assertTrue(all(not action.isEnabled() for action in idle.actions()[:4]))
        dashboard = self.dashboard()
        task_id = self.db.create_task("Research & design")
        dashboard._refresh_tasks(task_id)
        self.pet._start_focus_session(1500)
        self.assertEqual(self.pet.session_task_id, task_id)
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "Focusing: Research && design")
        self.db.update_task(task_id, name="Read papers")
        self.pet._toggle_session_pause()
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "Paused: Read papers")
        self.pet._stop_session()
        self.pet._start_break_session(300)
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "Taking a break")
        self.pet._toggle_session_pause()
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "Break paused")
        self.pet._stop_session()
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "No focus session running")

    def test_pet_menu_shows_focus_without_task_and_shortens_long_names(self):
        dashboard = self.dashboard()
        self.pet._start_focus_session(60)
        self.assertEqual(self.pet._create_context_menu().actions()[0].text(), "Focusing: No task selected")
        self.pet._stop_session()
        task_id = self.db.create_task("Long " * 18)
        dashboard._refresh_tasks(task_id)
        self.pet._start_focus_session(60)
        self.assertTrue(self.pet._create_context_menu().actions()[0].text().endswith("…"))

    def test_task_picker_attaches_completed_session_and_counts_time_once(self):
        dashboard = self.dashboard()
        dashboard.navigate(4)
        dashboard.task_name.setText("Review a patch")
        dashboard.task_project.setText("Compiler")
        dashboard.task_estimate.setValue(25)
        dashboard._add_task()
        self.assertEqual(dashboard.task_picker.currentText(), "Compiler / Review a patch")
        dashboard.navigate(1)
        self.pet._start_focus_session(4)
        self.tick(2)
        self.pet._toggle_session_pause()
        self.tick(2)
        self.pet._toggle_session_pause()
        self.tick(2)
        dashboard.refresh()
        self.assertEqual(self.db.get_tasks()[0]["focused_seconds"], 4)
        self.assertEqual(self.db.get_recent_sessions()[0]["task_name"], "Review a patch")
        self.assertEqual(self.db.get_today_stats()["focus_sessions_count"], 1)

    def test_enter_adds_one_task_without_navigation_from_either_text_field(self):
        dashboard = self.dashboard()
        dashboard.navigate(4)
        dashboard.task_name.setFocus()
        QTest.keyClicks(dashboard.task_name, "Review patch")
        QTest.keyClick(dashboard.task_name, Qt.Key_Return)
        self.assertEqual(len(self.db.get_tasks()), 1)
        self.assertEqual(dashboard.pages.currentIndex(), 4)
        self.assertEqual(dashboard._selected_task_id(), self.db.get_tasks()[0]['id'])
        QTest.keyClicks(dashboard.task_name, "Read docs")
        dashboard.task_project.setFocus()
        QTest.keyClicks(dashboard.task_project, "Systems")
        QTest.keyClick(dashboard.task_project, Qt.Key_Return)
        self.assertEqual(len(self.db.get_tasks()), 2)
        self.assertEqual(dashboard.pages.currentIndex(), 4)
        self.assertEqual(dashboard.task_picker.currentText(), "Systems / Read docs")

    def test_mouse_add_and_focus_action_and_double_click_choose_correct_task(self):
        dashboard = self.dashboard()
        dashboard.navigate(4)
        QTest.keyClicks(dashboard.task_name, "First task")
        QTest.mouseClick(dashboard.add_task_button, Qt.LeftButton)
        first = dashboard._selected_task_id()
        self.assertIsNotNone(first)
        self.assertTrue(dashboard.focus_task_button.isEnabled())
        QTest.mouseClick(dashboard.focus_task_button, Qt.LeftButton)
        self.assertEqual(dashboard.pages.currentIndex(), 1)
        self.assertEqual(dashboard.task_picker.currentData(), first)
        dashboard.navigate(4)
        QTest.keyClicks(dashboard.task_name, "Second task")
        QTest.mouseClick(dashboard.add_task_button, Qt.LeftButton)
        second = dashboard._selected_task_id()
        self.assertNotEqual(first, second)
        # The original task moved to row 1; double-click that row.
        cell = dashboard.tasks_table.visualItemRect(dashboard.tasks_table.item(1, 0)).center()
        QTest.mouseClick(dashboard.tasks_table.viewport(), Qt.LeftButton, pos=cell)
        QTest.mouseDClick(dashboard.tasks_table.viewport(), Qt.LeftButton, pos=cell)
        self.app.processEvents()
        self.assertEqual(dashboard.pages.currentIndex(), 1)
        self.assertEqual(dashboard.task_picker.currentData(), first)

    def test_refresh_preserves_task_popup_highlight_and_table_selection(self):
        first = self.db.create_task("First")
        self.db.create_task("Second")
        dashboard = self.dashboard()
        dashboard.navigate(4)
        dashboard.tasks_table.selectRow(1)
        dashboard.refresh()
        self.assertEqual(dashboard._selected_task_id(), first)
        dashboard.navigate(1)
        dashboard.task_picker.showPopup()
        self.app.processEvents()
        view = dashboard.task_picker.view()
        view.setCurrentIndex(dashboard.task_picker.model().index(dashboard.task_picker.findData(first), 0))
        before = view.currentIndex().row()
        dashboard.refresh()
        self.assertTrue(view.isVisible())
        self.assertEqual(view.currentIndex().row(), before)
        third = self.db.create_task("Arrived while choosing")
        dashboard.refresh()
        self.assertEqual(view.currentIndex().row(), before)
        self.assertEqual(dashboard.task_picker.findData(third), -1)
        QTest.keyClick(view, Qt.Key_Return)
        self.app.processEvents()
        self.assertEqual(dashboard.task_picker.currentData(), first)
        dashboard.refresh()
        self.assertNotEqual(dashboard.task_picker.findData(third), -1)
        self.assertEqual(dashboard.task_picker.currentData(), first)
        self.assertEqual(dashboard._selected_task_id(), first)

    def test_new_or_archived_task_cannot_replace_running_timer_task(self):
        first = self.db.create_task("In progress")
        dashboard = self.dashboard()
        dashboard.navigate(1)
        dashboard.task_picker.setCurrentIndex(dashboard.task_picker.findData(first))
        self.pet._start_focus_session(60)
        dashboard.navigate(4)
        dashboard.task_name.setText("Next task")
        QTest.mouseClick(dashboard.add_task_button, Qt.LeftButton)
        self.assertFalse(dashboard.focus_task_button.isEnabled())
        dashboard._focus_selected_task()  # Also guard a delayed double-click.
        self.db.update_task(first, status='archived')
        dashboard.refresh()
        self.assertEqual(self.pet.session_task_id, first)
        self.assertEqual(dashboard.task_picker.currentData(), first)
        self.tick(2)
        self.pet._stop_session()
        self.assertEqual(self.db.get_recent_sessions()[0]['task_id'], first)

    def test_task_and_intention_fields_are_readable_with_dark_system_palette(self):
        original = self.app.palette()
        dark = QPalette(original)
        dark.setColor(QPalette.Base, QColor('#101010'))
        dark.setColor(QPalette.Text, QColor('#eeeeee'))
        self.app.setPalette(dark)
        try:
            dashboard = self.dashboard()
            dashboard.navigate(4)
            self.app.processEvents()
            for field in (dashboard.task_name, dashboard.task_project, dashboard.session_note):
                palette = field.palette()
                self.assertEqual(palette.color(QPalette.Base).name(), '#ffffff')
                self.assertEqual(palette.color(QPalette.Text).name(), '#20372d')
                self.assertNotEqual(palette.color(QPalette.PlaceholderText), palette.color(QPalette.Base))
        finally:
            self.app.setPalette(original)

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
        for _ in range(100):
            if dashboard.evolution_controller.snapshot is not None:
                break
            QTest.qWait(10)
        self.assertEqual(dashboard.xp_label.text(), "5 / 52 XP")
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
