"""Packaged-app check that never reads the real profile or foreground apps."""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


def run():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from app.config.settings import SettingsManager
    from app.storage.database import DatabaseManager
    from app.productivity.focus_session import FocusSessionManager
    from app.ui.dashboard import Dashboard
    from app.ui.pet_window import PetWindow
    from app.ui.welcome import WelcomeDialog
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="moodpet-smoke-") as directory:
        settings = SettingsManager(Path(directory) / "config.json")
        settings.set("animations_enabled", False)
        db = DatabaseManager(Path(directory) / "fixture.db")
        db.record_focus_session(900, note="Packaged app check")
        db.record_focus_session(1,completed=False,end_time=datetime.now()-timedelta(days=2))
        welcome = WelcomeDialog(settings)
        welcome.show()
        app.processEvents()
        welcome.close()
        dashboard = Dashboard(db, settings, FocusSessionManager())
        dashboard.show()
        app.processEvents()
        dashboard.navigate(3)
        for _ in range(200):
            if dashboard.evolution_controller.snapshot is not None:
                break
            QTest.qWait(10)
        assert dashboard.journey.list.count() == 1
        assert dashboard.journey.map.nodes[0].isEnabled()
        assert not dashboard.journey.map.nodes[1].isEnabled()
        assert not dashboard.mini_pet.observe_activity
        assert not dashboard.grab().isNull()
        assert dashboard.measure_picker.currentData() == 'manual'
        assert sum(row['productive_seconds'] for row in dashboard.activity_chart._rows) == 901
        assert dashboard.repair_button.isEnabled()
        dashboard.pages.currentWidget().ensureWidgetVisible(dashboard.repair_button)
        QTest.mouseClick(dashboard.repair_button,Qt.LeftButton)
        assert db.get_streak_repair_status()['remaining'] == 1
        assert db.get_streaks()['current_streak'] == 3
        # Exercise the same keyboard/mouse paths as the installed application.
        dashboard.navigate(4)
        dashboard.task_name.setFocus()
        QTest.keyClicks(dashboard.task_name, "Keyboard task")
        QTest.keyClick(dashboard.task_name, Qt.Key_Return)
        assert dashboard.pages.currentIndex() == 4
        assert len(db.get_tasks()) == 1
        dashboard.task_name.setText("Mouse task")
        QTest.mouseClick(dashboard.add_task_button, Qt.LeftButton)
        assert len(db.get_tasks()) == 2
        task_id = dashboard._selected_task_id()
        assert task_id is not None
        QTest.mouseClick(dashboard.focus_task_button, Qt.LeftButton)
        assert dashboard.pages.currentIndex() == 1
        assert dashboard.task_picker.currentData() == task_id
        dashboard.close()
        dashboard.evolution_controller.close()
        pet = PetWindow(settings, db)
        pet.logic_timer.stop()
        pet.typing_timer.stop()
        pet.session_task_id = task_id
        pet.focus_session_mgr.start_focus(60)
        menu = pet._create_context_menu()
        assert menu.actions()[0].text() == "Focusing: Mouse task"
        assert menu.actions()[2].text().startswith("Focus timers:")
        assert menu.actions()[3].text().startswith("Tracked productive:")
        pet.focus_session_mgr.stop_all()
        pet.shutdown()
        menu.deleteLater()
        pet.close()
