import time
from datetime import datetime

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QCursor, QAction
from PySide6.QtWidgets import QWidget, QMenu, QApplication

from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.monitor.activity_tracker import ActivityTracker
from app.productivity.score_engine import ProductivityEngine, ProductivityState
from app.productivity.focus_tracker import FocusTracker
from app.productivity.focus_session import FocusSessionManager
from app.character.emotions import EmotionalStateEngine, EmotionalPose
from app.character.personality import CharacterPersonality
from app.ui.character import HumanCharacterWidget
from app.ui.speech_bubble import SpeechBubble
from app.ui.dashboard import Dashboard
from app.ui.settings_dialog import SettingsDialog

class PetWindow(QWidget):
    """Main floating overlay window hosting the human companion character, focus panel, and activity loop."""

    def __init__(self, settings: SettingsManager, db: DatabaseManager):
        super().__init__()
        self.settings = settings
        self.db = db

        # Core logic modules
        self.tracker = ActivityTracker()
        self.prod_engine = ProductivityEngine(self.settings)
        self.focus_tracker = FocusTracker(self.db, target_milestone_sec=self.settings.get("focus_milestone_target_sec", 1800))
        self.emotion_engine = EmotionalStateEngine()
        self.focus_session_mgr = FocusSessionManager()
        self.dashboard = None
        self._last_tick = time.monotonic()
        self._next_speech = time.monotonic() + 300
        self._celebration_until = 0
        self._shutdown_done = False

        # Window Flags & Transparency
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Human Character Widget
        self.character_widget = HumanCharacterWidget(self)
        self.character_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setToolTip("Click for your dashboard · Drag to move · Right-click for more")
        self.setCursor(Qt.PointingHandCursor)
        self.update_pet_size()

        # Speech Bubble
        self.speech_bubble = SpeechBubble(self)

        # Drag tracking
        self.drag_position = QPoint()
        self.is_dragging = False
        self.last_idle_time = 0.0

        # Initial Position Setup
        self._position_window()

        # Main Monitor & Logic Loop (~1 second intervals)
        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self._on_logic_tick)
        self.logic_timer.start(1000)

        # Typing animation check timer (~200 ms)
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self._check_typing_activity)
        self.typing_timer.start(200)

        # Context Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._apply_preferences()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def update_pet_size(self):
        """Resizes companion widget based on scale settings."""
        scale = float(self.settings.get("pet_scale", 1.0))
        w = int(150 * scale)
        h = int(160 * scale)
        self.resize(w, h)
        self.character_widget.resize(w, h)

    def _position_window(self):
        """Positions window at saved coordinates or bottom-right corner."""
        saved_x = self.settings.get("window_x", -1)
        saved_y = self.settings.get("window_y", -1)

        screen = QApplication.primaryScreen().availableGeometry()
        if saved_x >= 0 and saved_y >= 0 and saved_x < screen.width() and saved_y < screen.height():
            self.move(saved_x, saved_y)
        else:
            x = screen.width() - self.width() - 30
            y = screen.height() - self.height() - 30
            self.move(x, y)

    def _update_speech_bubble_position(self):
        """Aligns speech bubble directly above character."""
        if self.speech_bubble.isVisible():
            bw = self.speech_bubble.width()
            bh = self.speech_bubble.height()
            pet_pos = self.mapToGlobal(QPoint(0, 0))
            
            bx = pet_pos.x() + (self.width() - bw) // 2
            by = pet_pos.y() - bh + 5
            self.speech_bubble.move(bx, by)

    def _check_typing_activity(self):
        """Detects active keyboard/mouse input without recording keystrokes and triggers typing arms."""
        idle_sec = self.tracker.get_system_idle_seconds()
        # Input detected if idle is under 1 second and actively changing
        is_active = (idle_sec < 1.0) and (idle_sec < self.last_idle_time or self.last_idle_time < 0.2)
        self.last_idle_time = idle_sec
        self.character_widget.set_typing(is_active)

    def _on_logic_tick(self):
        """Runs periodic activity monitoring, score evaluation, focus sessions, and emotion state updates."""
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_tick)
        self._last_tick = now
        # A suspended computer must not earn hours of activity or finish a timer.
        if elapsed > 5:
            self.focus_tracker.finish_current_session()
            if (self.focus_session_mgr.is_focus_active or self.focus_session_mgr.is_break_active) and not self.focus_session_mgr.is_paused:
                self.focus_session_mgr.toggle_pause()
                self._say("Welcome back! Your timer is paused. Resume when you're ready.")
            elapsed = 0.0
        # 1. Fetch system activity
        idle_sec = self.tracker.get_system_idle_seconds()
        active_window = self.tracker.get_active_window_info()

        # 2. Evaluate productivity state
        prod_state, debug_meta = self.prod_engine.evaluate(active_window, idle_sec)

        # 3. Tick focus & break sessions
        was_timed = self.focus_session_mgr.is_focus_active or self.focus_session_mgr.is_break_active
        session_info = self.focus_session_mgr.tick(elapsed_sec=elapsed)
        if session_info["focus_finished"]:
            self._celebration_until = now + 8
            self._say("Session complete! One more small win, saved. Time to stretch?", extra_seconds=3)
            self.db.record_focus_session(
                duration_seconds=int(self.focus_session_mgr.focus_total_sec), completed=True,
                start_time=self.focus_session_mgr.focus_started_at, source="manual",
            )
        if session_info["break_finished"]:
            self._say("Welcome back. A fresh little focus session is waiting for you.")

        # Update character mode and subtle timer
        self.character_widget.set_focus_mode(session_info["is_focus"], session_info["timer_text"])
        self.character_widget.set_break_mode(session_info["is_break"], session_info["timer_text"])

        # 4. Focus tracker stats tick
        focus_meta = self.focus_tracker.update(prod_state, elapsed_interval_sec=elapsed, record_sessions=not was_timed)
        if focus_meta["milestone_triggered"]:
            self._celebration_until = now + 6
            self._say(focus_meta["milestone_message"])

        # 5. Evaluate human emotional pose
        distraction_elapsed = debug_meta.get("elapsed_sec", 0.0) if prod_state == ProductivityState.DISTRACTING else 0.0
        pose = self.emotion_engine.update(
            prod_state_name=prod_state.name,
            distraction_elapsed_sec=distraction_elapsed,
            idle_sec=idle_sec,
            is_in_focus_mode=session_info["is_focus"],
            is_in_break_mode=session_info["is_break"]
        )

        # 6. Apply pose to character
        self.character_widget.set_pose(EmotionalPose.EXCITED if now < self._celebration_until else pose)

        # 7. Periodic speech lines
        if now >= self._next_speech:
            self._next_speech = now + 300
            if not self.speech_bubble.isVisible():
                self._say(CharacterPersonality.get_speech(pose))

        self._update_speech_bubble_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # If moved more than 5px, treat as drag
            diff = (event.globalPosition().toPoint() - self.frameGeometry().topLeft()) - self.drag_position
            if diff.manhattanLength() > 5:
                self.is_dragging = True
                new_pos = event.globalPosition().toPoint() - self.drag_position
                
                screen = QApplication.primaryScreen().availableGeometry()
                new_x = max(screen.left(), min(new_pos.x(), screen.right() - self.width()))
                new_y = max(screen.top(), min(new_pos.y(), screen.bottom() - self.height()))
                
                self.move(new_x, new_y)
                self._update_speech_bubble_position()
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.is_dragging = False
                pos = self.pos()
                self.settings.set("window_x", pos.x())
                self.settings.set("window_y", pos.y())
            else:
                # Open interactive Focus Panel on click!
                self._open_focus_panel()
            event.accept()

    def _open_focus_panel(self):
        """Compatibility entry point: clicking the pet opens the dashboard."""
        self.open_dashboard()

    def open_dashboard(self):
        if self.dashboard is None:
            self.dashboard = Dashboard(self.db, self.settings, self.focus_session_mgr, parent=self)
            self.dashboard.focus_started.connect(self._start_focus_session)
            self.dashboard.break_started.connect(self._start_break_session)
            self.dashboard.pause_requested.connect(self._toggle_session_pause)
            self.dashboard.stop_requested.connect(self._stop_session)
            self.dashboard.settings_requested.connect(self.open_settings)
            screen = QApplication.primaryScreen().availableGeometry()
            self.dashboard.resize(min(1180, screen.width() - 40), min(860, screen.height() - 60))
        self.dashboard.navigate(0)
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _start_focus_session(self, duration_sec: int):
        if self.focus_session_mgr.is_focus_active or self.focus_session_mgr.is_break_active:
            return
        self.focus_tracker.finish_current_session()
        self.focus_session_mgr.start_focus(duration_sec)
        self._last_tick = time.monotonic()
        self.character_widget.set_pose(EmotionalPose.FOCUSED)
        mins = int(duration_sec // 60)
        self._say(f"Okay. We're locked in for {mins}m now! 🤓🔥")
        self._refresh_dashboard()

    def _start_break_session(self, duration_sec: int):
        if self.focus_session_mgr.is_focus_active or self.focus_session_mgr.is_break_active:
            return
        self.focus_tracker.finish_current_session()
        self.focus_session_mgr.start_break(duration_sec)
        self._last_tick = time.monotonic()
        self.character_widget.set_pose(EmotionalPose.BREAK)
        self._say("Enjoy your well-deserved break! ☕😌")
        self._refresh_dashboard()

    def _toggle_session_pause(self):
        self.focus_session_mgr.toggle_pause()
        self._last_tick = time.monotonic()
        self._refresh_dashboard()

    def _stop_session(self):
        if self.focus_session_mgr.is_focus_active:
            elapsed = int(self.focus_session_mgr.focus_elapsed_sec)
            if elapsed > 0:
                self.db.record_focus_session(elapsed, completed=False,
                    start_time=self.focus_session_mgr.focus_started_at, source="manual")
        self.focus_session_mgr.stop_all()
        self.character_widget.set_focus_mode(False)
        self.character_widget.set_break_mode(False)
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        if self.dashboard is not None and self.dashboard.isVisible():
            self.dashboard.refresh()

    def _say(self, message, extra_seconds=0):
        if self.settings.get("quiet_hours_enabled", False):
            now = datetime.now().strftime("%H:%M")
            start = self.settings.get("quiet_start", "22:00")
            end = self.settings.get("quiet_end", "08:00")
            quiet = start <= now < end if start < end else now >= start or now < end
            if quiet:
                return
        self.speech_bubble.show_message(message, float(self.settings.get("auto_hide_message_sec", 6)) + extra_seconds)
        self._update_speech_bubble_position()

    def _apply_preferences(self):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(self.settings.get("always_on_top", True)))
        if self.settings.get("animations_enabled", True):
            self.character_widget.timer.start(16)
        else:
            self.character_widget.timer.stop()
        self.focus_tracker.target_milestone_sec = self.settings.get("focus_milestone_target_sec", 1800)

    def shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self.logic_timer.stop()
        self.typing_timer.stop()
        self._stop_session()
        self.focus_tracker.finish_current_session()

    def _show_context_menu(self, pos):
        """Right click context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: #CBA6F7;
            }
        """)

        today = self.db.get_today_stats()
        prod_fmt = self.focus_tracker.format_time(today["productive_seconds"])
        streak = self.focus_tracker.current_streak
        stats_act = QAction(f"🔥 Streak: {streak} days  |  📊 Today: {prod_fmt}", menu)
        stats_act.setEnabled(False)
        menu.addAction(stats_act)
        menu.addSeparator()

        focus_act = QAction("📊 Open Dashboard", menu)
        focus_act.triggered.connect(self._open_focus_panel)
        menu.addAction(focus_act)

        settings_act = QAction("⚙️ Preferences", menu)
        settings_act.triggered.connect(self.open_settings)
        menu.addAction(settings_act)

        menu.addSeparator()

        hide_act = QAction("🙈 Hide Companion", menu)
        hide_act.triggered.connect(self.hide)
        menu.addAction(hide_act)

        exit_act = QAction("❌ Exit MoodPet", menu)
        exit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_act)

        menu.exec(QCursor.pos())

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self.db, self.focus_tracker, parent=self)
        if dialog.exec():
            self.update_pet_size()
            self._apply_preferences()
            self.show()
            self._refresh_dashboard()
