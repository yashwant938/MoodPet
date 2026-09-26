"""Render isolated fixture data for visual QA. Never opens the user's database."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.productivity.focus_session import FocusSessionManager
from app.ui.dashboard import Dashboard


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    for font in ("segoeui.ttf", "segoeuib.ttf", "seguisl.ttf", "seguisb.ttf"):
        QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{font}")
    output = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(dir=output) as temp:
        settings = SettingsManager(Path(temp) / "config.json")
        db = DatabaseManager(Path(temp) / "preview.db")
        for offset in range(84):
            day = date.today() - timedelta(days=offset)
            productive = (offset * 977 + 4700) % 12000 if offset % 9 != 8 else 0
            with db._connection() as conn:
                conn.execute("INSERT OR REPLACE INTO daily_stats (date, productive_seconds, distracted_seconds, idle_seconds) VALUES (?, ?, ?, ?)",
                             (day.isoformat(), productive, offset * 173 % 1700, 700))
        for offset in range(7):
            finish = datetime.now() - timedelta(days=offset, hours=1)
            db.record_focus_session(1500, completed=offset != 3, end_time=finish)
        manager = FocusSessionManager()
        dashboard = Dashboard(db, settings, manager)
        dashboard.show()
        app.processEvents()
        for index, name in enumerate(("overview", "focus", "history")):
            dashboard.navigate(index)
            app.processEvents()
            dashboard.grab().save(str(output / f"dashboard-{name}.png"))
        dashboard.resize(960, 640)
        dashboard.navigate(0)
        app.processEvents()
        dashboard.grab().save(str(output / "dashboard-small.png"))
        dashboard.hide()
        empty_db = DatabaseManager(Path(temp) / "empty.db")
        empty_dashboard = Dashboard(empty_db, settings, FocusSessionManager())
        empty_dashboard.show()
        app.processEvents()
        empty_dashboard.grab().save(str(output / "dashboard-empty.png"))
        empty_dashboard.hide()
    print("Dashboard previews saved in scratch/")


if __name__ == "__main__":
    main()
