"""Packaged-app check that never reads the real profile or foreground apps."""
import os
import tempfile
from pathlib import Path


def run():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from app.config.settings import SettingsManager
    from app.storage.database import DatabaseManager
    from app.productivity.focus_session import FocusSessionManager
    from app.ui.dashboard import Dashboard
    from app.ui.welcome import WelcomeDialog
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="moodpet-smoke-") as directory:
        settings = SettingsManager(Path(directory) / "config.json")
        settings.set("animations_enabled", False)
        db = DatabaseManager(Path(directory) / "fixture.db")
        db.record_focus_session(900, note="Packaged app check")
        welcome = WelcomeDialog(settings)
        welcome.show()
        app.processEvents()
        welcome.close()
        dashboard = Dashboard(db, settings, FocusSessionManager())
        dashboard.show()
        app.processEvents()
        dashboard.navigate(3)
        assert dashboard.journey.list.count() == 1
        assert not dashboard.mini_pet.observe_activity
        assert not dashboard.grab().isNull()
        dashboard.close()
