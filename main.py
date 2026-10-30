import sys
import os
import argparse
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QSharedMemory
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.ui.pet_window import PetWindow
from app.ui.welcome import WelcomeDialog
from app.developer_events import send_event, EVENTS

def create_tray_icon_pixmap():
    """Generates a cute tray icon pixmap."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Gold body
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#FFB300"))
    painter.drawEllipse(2, 2, 28, 28)
    
    # Eyes & smile
    painter.setBrush(QColor("#212121"))
    painter.drawEllipse(8, 10, 4, 5)
    painter.drawEllipse(20, 10, 4, 5)
    
    painter.setPen(QColor("#212121"))
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(10, 14, 12, 10, 200 * 16, 140 * 16)
    
    painter.end()
    return pixmap

def main():
    parser = argparse.ArgumentParser(description="MoodPet · a small companion for focus")
    parser.add_argument("--event", choices=EVENTS, help="Send a local developer event to a running companion")
    parser.add_argument("--profile-dir", type=Path, help="Use a separate local profile")
    parser.add_argument("--demo", action="store_true", help="Explore with fictional temporary data; no monitoring")
    parser.add_argument("--smoke-test", action="store_true", help="Check the packaged dashboard with temporary data and exit")
    args = parser.parse_args()
    if args.event:
        try:
            send_event(SettingsManager(args.profile_dir / "config.json" if args.profile_dir else None), args.event)
        except ValueError as error:
            parser.error(str(error))
        return
    if args.smoke_test:
        from app.smoke_test import run
        run()
        return
    demo_profile = tempfile.TemporaryDirectory(prefix="moodpet-demo-") if args.demo else None
    profile = Path(demo_profile.name) if demo_profile else args.profile_dir

    # Set high DPI scaling policies
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("MoodPet")

    # Single Instance Guard
    shared_mem = QSharedMemory("MoodPetSingleInstanceKey")
    if not shared_mem.create(1):
        print("MoodPet is already running!")
        sys.exit(0)

    # Core Managers
    settings = SettingsManager(profile / "config.json" if profile else None)
    db = DatabaseManager(profile / "moodpet.db" if profile else None)
    if args.demo:
        settings.set("onboarding_complete", True)
        settings.set("tracking_mode", "manual")
        for minutes, note in [(25, "Learn a C++ concept"), (15, "Read a chapter"), (30, "Test one small fix")]:
            db.record_focus_session(minutes * 60, note=note)
    if not settings.get("onboarding_complete", False):
        if WelcomeDialog(settings).exec() != WelcomeDialog.Accepted:
            return

    # Pet Window
    pet_window = PetWindow(settings, db)
    pet_window.show()

    # System Tray Icon Setup
    tray_icon = QSystemTrayIcon(app)
    tray_pixmap = create_tray_icon_pixmap()
    tray_icon.setIcon(QIcon(tray_pixmap))
    tray_icon.setToolTip("MoodPet - Virtual Desktop Companion 😊")

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #1E1E2E;
            color: #CDD6F4;
            border: 1px solid #313244;
            border-radius: 6px;
            padding: 4px;
        }
        QMenu::item:selected {
            background-color: #313244;
            color: #CBA6F7;
        }
    """)

    show_act = QAction("😊 Show Companion", tray_menu)
    show_act.triggered.connect(pet_window.show)
    tray_menu.addAction(show_act)

    hide_act = QAction("🙈 Hide Companion", tray_menu)
    hide_act.triggered.connect(pet_window.hide)
    tray_menu.addAction(hide_act)

    dashboard_act = QAction("📊 Open Dashboard", tray_menu)
    dashboard_act.triggered.connect(pet_window.open_dashboard)
    tray_menu.addAction(dashboard_act)
    quick_menu = tray_menu.addMenu("Quick actions")
    quick_menu.aboutToShow.connect(lambda: pet_window.populate_quick_menu(quick_menu))

    settings_act = QAction("⚙️ Preferences", tray_menu)
    settings_act.triggered.connect(pet_window.open_settings)
    tray_menu.addAction(settings_act)

    tray_menu.addSeparator()

    exit_act = QAction("❌ Exit MoodPet", tray_menu)
    exit_act.triggered.connect(app.quit)
    tray_menu.addAction(exit_act)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    # One click opens the same dashboard as clicking the companion.
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.Trigger:
            pet_window.open_dashboard()

    tray_icon.activated.connect(on_tray_activated)

    # Initial message
    pet_window._say("Hello! Click me to see your progress or start a focus session. ✨")

    result = app.exec()
    if demo_profile:
        demo_profile.cleanup()
    sys.exit(result)

if __name__ == "__main__":
    main()
