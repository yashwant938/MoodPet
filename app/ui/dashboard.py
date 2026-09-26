"""The companion's local-first productivity dashboard."""
import csv
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.ui.charts import ActivityChart, ActivityHeatmap, GoalRing
from app.ui.character import HumanCharacterWidget
from app.character.emotions import EmotionalPose


def duration(seconds):
    minutes = max(0, int(seconds)) // 60
    return f"{minutes // 60}h {minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


def label(text, role=None):
    widget = QLabel(text)
    if role:
        widget.setObjectName(role)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return frame, layout


def navigation_icon(kind):
    """Draw crisp navigation symbols without depending on symbol fonts."""
    icon = QIcon()
    for state, color in ((QIcon.Off, "#C4D5CA"), (QIcon.On, "#193C2E")):
        pixmap = QPixmap(36, 36)
        pixmap.fill(Qt.transparent)
        pixmap.setDevicePixelRatio(2)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if kind == "overview":
            for x, y, h in ((3, 10, 5), (8, 6, 9), (13, 3, 12)):
                painter.drawRoundedRect(QRectF(x, y, 2, h), 0.8, 0.8)
        elif kind == "focus":
            painter.drawEllipse(QRectF(2.5, 2.5, 13, 13))
            painter.drawLine(QPointF(9, 5), QPointF(9, 9))
            painter.drawLine(QPointF(9, 9), QPointF(12, 11))
        elif kind == "history":
            for y in (4, 9, 14):
                painter.drawPoint(QPointF(3, y))
                painter.drawLine(QPointF(7, y), QPointF(15, y))
        else:
            painter.drawEllipse(QRectF(5, 5, 8, 8))
            painter.drawEllipse(QRectF(8, 8, 2, 2))
            for start, end in (((9, 1), (9, 4)), ((9, 14), (9, 17)), ((1, 9), (4, 9)), ((14, 9), (17, 9))):
                painter.drawLine(QPointF(*start), QPointF(*end))
        painter.end()
        icon.addPixmap(pixmap, QIcon.Normal, state)
    return icon


STYLE = """
QDialog, QWidget#page { background: #F5F7F6; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #20372D; }
QLabel { background: transparent; border: none; }
QLabel#muted { color: #79877F; font-size: 12px; }
QLabel#eyebrow { color: #6D8275; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#heading { font-size: 29px; font-weight: 700; letter-spacing: -1px; }
QLabel#sectionTitle { font-size: 16px; font-weight: 600; }
QLabel#statValue { font-size: 29px; font-weight: 600; }
QFrame#card { background: white; border: 1px solid #E3E9E5; border-radius: 16px; }
QFrame#sidebar { background: #193C2E; border: none; }
QFrame#sidebar QLabel { color: #F2F7F3; }
QFrame#sidebar QLabel#muted { color: #B3C7BA; }
QFrame#sidebar QPushButton { background: transparent; color: #C4D5CA; text-align: left; border: none; padding: 13px 16px; }
QFrame#sidebar QPushButton:hover { background: #264D3C; }
QFrame#sidebar QPushButton:checked { background: #DDF3E5; color: #193C2E; font-weight: 700; }
QPushButton { background: #FFFFFF; border: 1px solid #DAE3DC; border-radius: 9px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #EFF5F0; border-color: #9EBBAB; }
QPushButton:checked { background: #E6F4EA; color: #237A57; border-color: #6EA389; }
QPushButton:disabled { color: #A1ABA5; background: #F1F4F2; border-color: #E5EAE7; }
QPushButton#primary { background: #237A57; color: white; border: none; padding: 12px 20px; }
QPushButton#primary:hover { background: #196643; }
QPushButton#primary:disabled { background: #AEC7B8; }
QPushButton#stop { color: #AD614D; }
QComboBox, QSpinBox { background: white; border: 1px solid #DAE3DC; border-radius: 8px; padding: 7px 10px; }
QComboBox QAbstractItemView { background: white; color: #20372D; selection-background-color: #E6F4EA; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(__ASSET_DIR__/chevron-down.svg); width: 10px; height: 10px; }
QSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; border: none; width: 23px; height: 18px; }
QSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; border: none; width: 23px; height: 18px; }
QSpinBox::up-arrow { image: url(__ASSET_DIR__/chevron-up.svg); width: 10px; height: 10px; }
QSpinBox::down-arrow { image: url(__ASSET_DIR__/chevron-down.svg); width: 10px; height: 10px; }
QProgressBar { background: #EAF0EC; border: none; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: #5C9875; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #F5F7F6; width: 8px; }
QScrollBar::handle:vertical { background: #CCD8CF; border-radius: 4px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTableWidget { background: white; alternate-background-color: #F8FAF8; border: none; gridline-color: #EDF1EE; selection-background-color: #E6F4EA; selection-color: #20372D; }
QHeaderView::section { background: #F3F7F4; color: #6A7B70; font-size: 11px; font-weight: 600; border: none; padding: 12px 6px; }
QToolTip { background: #193C2E; color: white; border: none; padding: 8px; }
""".replace("__ASSET_DIR__", (Path(__file__).parent / "assets").as_posix())


class Dashboard(QDialog):
    focus_started = Signal(int)
    break_started = Signal(int)
    pause_requested = Signal()
    stop_requested = Signal()
    settings_requested = Signal()

    def __init__(self, db, settings, session_manager, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = settings
        self.session = session_manager
        self.period = 7
        self.setWindowTitle("MoodPet — Your focus, growing.")
        self.setWindowFlags(Qt.Window)
        self.resize(1180, 860)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(STYLE)
        self._build()
        self.refresh()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.refresh_timer_state)

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(198)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 28, 18, 24)
        side.setSpacing(9)
        brand = label("moodpet", "heading")
        brand.setStyleSheet("font-size: 26px; color: white; padding-left: 12px;")
        side.addWidget(brand)
        tagline = label("SMALL STEPS. REAL GROWTH.", "muted")
        tagline.setStyleSheet("font-size: 8px; color: #B3C7BA; padding-left: 12px; letter-spacing: 1px;")
        side.addWidget(tagline)
        side.addSpacing(32)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = []
        for index, text in enumerate(("Overview", "Focus room", "Session history")):
            button = QPushButton(text)
            button.setIcon(navigation_icon(("overview", "focus", "history")[index]))
            button.setIconSize(QSize(18, 18))
            button.setCheckable(True)
            self.nav_group.addButton(button, index)
            button.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            self.nav_buttons.append(button)
            side.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()
        self.mini_pet = HumanCharacterWidget()
        self.mini_pet.setFixedSize(150, 130)
        self.mini_pet.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.mini_pet.set_pose(EmotionalPose.HAPPY)
        side.addWidget(self.mini_pet, 0, Qt.AlignHCenter)
        self.level_label = label("Your growing companion", "sectionTitle")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setStyleSheet("font-size: 13px;")
        side.addWidget(self.level_label)
        self.xp_label = label("Every focused minute counts.", "muted")
        self.xp_label.setAlignment(Qt.AlignCenter)
        self.xp_label.setWordWrap(True)
        side.addWidget(self.xp_label)
        self.xp_bar = QProgressBar()
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setFixedHeight(5)
        side.addWidget(self.xp_bar)
        side.addSpacing(20)
        prefs = QPushButton("Preferences")
        prefs.setIcon(navigation_icon("settings"))
        prefs.setIconSize(QSize(18, 18))
        prefs.clicked.connect(self.settings_requested.emit)
        side.addWidget(prefs)
        local = label("●  Saved on this device", "muted")
        local.setStyleSheet("font-size: 10px; color: #B3C7BA; padding-left: 12px;")
        side.addWidget(local)
        root.addWidget(sidebar)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self._build_overview()
        self._build_focus()
        self._build_history()

    def _page(self):
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 27, 30, 26)
        layout.setSpacing(20)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.pages.addWidget(scroll)
        return layout

    def _build_overview(self):
        layout = self._page()
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        self.date_label = label("YOUR DAILY COMPANION", "eyebrow")
        titles.addWidget(self.date_label)
        titles.addWidget(label("Your focus, growing.", "heading"))
        titles.addWidget(label("Make room for what matters. One small session at a time.", "muted"))
        top.addLayout(titles, 1)
        start = QPushButton("Start a session  →")
        start.setObjectName("primary")
        start.clicked.connect(lambda: self.navigate(1))
        top.addWidget(start, 0, Qt.AlignVCenter)
        layout.addLayout(top)

        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_values = {}
        self.stat_details = {}
        for key, title, detail in (
            ("productive", "PRODUCTIVE TODAY", "Time in your productive apps"),
            ("streak", "CURRENT STREAK", "Keep showing up"),
            ("balance", "FOCUS BALANCE", "Productive / classified time"),
            ("sessions", "SESSIONS TODAY", "Completed focus sessions"),
        ):
            frame, box = card()
            box.setContentsMargins(17, 17, 17, 17)
            box.addWidget(label(title, "eyebrow"))
            self.stat_values[key] = label("—", "statValue")
            box.addWidget(self.stat_values[key])
            self.stat_details[key] = label(detail, "muted")
            self.stat_details[key].setWordWrap(True)
            box.addWidget(self.stat_details[key])
            stats.addWidget(frame, 1)
        layout.addLayout(stats)

        middle = QHBoxLayout()
        middle.setSpacing(18)
        activity, activity_layout = card()
        chart_header = QHBoxLayout()
        chart_header.addWidget(label("Your rhythm", "sectionTitle"))
        chart_header.addStretch()
        self.period_picker = QComboBox()
        self.period_picker.addItem("Last 7 days", 7)
        self.period_picker.addItem("Last 30 days", 30)
        self.period_picker.currentIndexChanged.connect(self._period_changed)
        chart_header.addWidget(self.period_picker)
        activity_layout.addLayout(chart_header)
        self.chart_summary = label("Activity adds up to progress.", "muted")
        activity_layout.addWidget(self.chart_summary)
        self.activity_chart = ActivityChart()
        self.activity_chart.setMinimumHeight(220)
        activity_layout.addWidget(self.activity_chart)
        self.insight_label = label("", "muted")
        self.insight_label.setWordWrap(True)
        activity_layout.addWidget(self.insight_label)
        middle.addWidget(activity, 2)

        goal, goal_layout = card()
        goal.setMinimumWidth(225)
        goal_layout.addWidget(label("A little daily ambition", "sectionTitle"))
        goal_layout.addWidget(label("Your productive-time goal", "muted"))
        self.goal_ring = GoalRing()
        self.goal_ring.setFixedHeight(158)
        goal_layout.addWidget(self.goal_ring)
        self.goal_summary = label("", "muted")
        self.goal_summary.setAlignment(Qt.AlignCenter)
        goal_layout.addWidget(self.goal_summary)
        goal_row = QHBoxLayout()
        goal_row.addWidget(label("Daily goal", "muted"))
        self.goal_input = QSpinBox()
        self.goal_input.setRange(15, 720)
        self.goal_input.setSingleStep(15)
        self.goal_input.setSuffix(" min")
        self.goal_input.setValue(int(self.settings.get("daily_goal_minutes", 120)))
        self.goal_input.setKeyboardTracking(False)
        self.goal_input.valueChanged.connect(self._save_goal)
        goal_row.addWidget(self.goal_input)
        goal_layout.addLayout(goal_row)
        middle.addWidget(goal, 1)
        layout.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.setSpacing(18)
        consistency, consistency_layout = card()
        consistency_layout.addWidget(label("Little steps, lasting habits", "sectionTitle"))
        consistency_layout.addWidget(label("Your last 12 weeks. Hover a day to explore.", "muted"))
        self.heatmap = ActivityHeatmap()
        self.heatmap.setMinimumHeight(155)
        consistency_layout.addWidget(self.heatmap)
        self.streak_detail = label("", "muted")
        self.streak_detail.setWordWrap(True)
        consistency_layout.addWidget(self.streak_detail)
        bottom.addWidget(consistency, 2)

        quest, quest_layout = card()
        quest.setMinimumWidth(225)
        quest_layout.addWidget(label("Today's tiny wins", "sectionTitle"))
        quest_layout.addWidget(label("Build momentum, your way.", "muted"))
        self.quest_labels = []
        for _ in range(3):
            item = label("")
            item.setWordWrap(True)
            quest_layout.addWidget(item)
            self.quest_labels.append(item)
        quest_layout.addStretch()
        self.badge_label = label("", "muted")
        self.badge_label.setWordWrap(True)
        quest_layout.addWidget(self.badge_label)
        bottom.addWidget(quest, 1)
        layout.addLayout(bottom)
        foot = label("A streak day = 15 productive minutes or one completed session. Your history stays here, on your device.", "muted")
        foot.setWordWrap(True)
        layout.addWidget(foot)
        layout.addStretch()

    def _build_focus(self):
        layout = self._page()
        layout.addWidget(label("MAKE SOME SPACE", "eyebrow"))
        layout.addWidget(label("One thing at a time.", "heading"))
        layout.addWidget(label("Pick a duration, settle in, and let your companion keep time.", "muted"))
        frame, box = card()
        box.setContentsMargins(36, 30, 36, 32)
        self.timer_status = label("READY WHEN YOU ARE", "eyebrow")
        self.timer_status.setAlignment(Qt.AlignCenter)
        box.addWidget(self.timer_status)
        self.timer_display = label("25:00")
        self.timer_display.setStyleSheet("font-size: 76px; font-weight: 300; color: #237A57;")
        self.timer_display.setAlignment(Qt.AlignCenter)
        box.addWidget(self.timer_display)
        self.timer_progress = QProgressBar()
        self.timer_progress.setRange(0, 1000)
        self.timer_progress.setTextVisible(False)
        self.timer_progress.setFixedHeight(7)
        box.addWidget(self.timer_progress)
        box.addSpacing(12)
        presets = QHBoxLayout()
        self.duration_group = QButtonGroup(self)
        self.duration_buttons = []
        for minutes in (15, 25, 45, 60, 90):
            button = QPushButton(f"{minutes} min")
            button.setCheckable(True)
            button.setChecked(minutes == 25)
            self.duration_group.addButton(button, minutes)
            button.clicked.connect(lambda checked=False, m=minutes: self.focus_duration.setValue(m))
            self.duration_buttons.append(button)
            presets.addWidget(button)
        box.addLayout(presets)
        custom = QHBoxLayout()
        custom.addStretch()
        custom.addWidget(label("Or set your own", "muted"))
        self.focus_duration = QSpinBox()
        self.focus_duration.setRange(1, 180)
        self.focus_duration.setSuffix(" min")
        self.focus_duration.setValue(25)
        self.focus_duration.valueChanged.connect(self._duration_changed)
        custom.addWidget(self.focus_duration)
        custom.addStretch()
        box.addLayout(custom)
        controls = QHBoxLayout()
        self.start_focus_button = QPushButton("Start focus  →")
        self.start_focus_button.setObjectName("primary")
        self.start_focus_button.clicked.connect(lambda: self.focus_started.emit(self.focus_duration.value() * 60))
        controls.addWidget(self.start_focus_button)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_requested.emit)
        controls.addWidget(self.pause_button)
        self.stop_button = QPushButton("End session")
        self.stop_button.setObjectName("stop")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        controls.addWidget(self.stop_button)
        box.addLayout(controls)
        breaks = QHBoxLayout()
        breaks.addStretch()
        self.break_buttons = []
        for minutes in (5, 10):
            button = QPushButton(f"Take a {minutes} min break")
            button.clicked.connect(lambda checked=False, m=minutes: self.break_started.emit(m * 60))
            self.break_buttons.append(button)
            breaks.addWidget(button)
        breaks.addStretch()
        box.addLayout(breaks)
        note = label("Timers measure your session. Activity charts measure time in your productive apps.\nEnding early saves a partial session; completed sessions grow your streak.", "muted")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        box.addWidget(note)
        layout.addWidget(frame)
        tip, tip_layout = card()
        tip_layout.addWidget(label("Give your next session a small, clear finish line.", "sectionTitle"))
        tip_layout.addWidget(label("One paragraph. One solved problem. One thing moved forward. You choose.", "muted"))
        layout.addWidget(tip)
        layout.addStretch()

    def _build_history(self):
        layout = self._page()
        layout.addWidget(label("PROOF OF PROGRESS", "eyebrow"))
        heading = QHBoxLayout()
        heading.addWidget(label("Every session has a story.", "heading"), 1)
        export = QPushButton("Export 90-day activity ↓")
        export.clicked.connect(self.export_activity)
        heading.addWidget(export)
        layout.addLayout(heading)
        self.lifetime_label = label("", "muted")
        self.lifetime_label.setWordWrap(True)
        layout.addWidget(self.lifetime_label)
        frame, box = card()
        box.addWidget(label("Recent sessions", "sectionTitle"))
        box.addWidget(label("Your latest 100 sessions, including those you ended early.", "muted"))
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["STARTED", "DURATION", "TYPE", "RESULT", "FINISHED"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        self.history_table.setMinimumHeight(340)
        box.addWidget(self.history_table)
        self.history_empty = label("Your first session is a fresh start. Visit the Focus room to begin.", "muted")
        self.history_empty.setWordWrap(True)
        box.addWidget(self.history_empty)
        layout.addWidget(frame)
        milestone, milestone_layout = card()
        milestone_layout.addWidget(label("Your collection", "sectionTitle"))
        self.achievements = label("")
        self.achievements.setWordWrap(True)
        milestone_layout.addWidget(self.achievements)
        layout.addWidget(milestone)
        layout.addStretch()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.refresh()

    def _period_changed(self):
        self.period = self.period_picker.currentData()
        self.refresh()

    def _save_goal(self, value):
        self.settings.set("daily_goal_minutes", value)
        self.refresh()

    def _duration_changed(self, value):
        self.duration_group.setExclusive(False)
        for button in self.duration_buttons:
            button.setChecked(self.duration_group.id(button) == value)
        self.duration_group.setExclusive(True)
        self.refresh_timer_state()

    def refresh(self):
        today = self.db.get_today_stats()
        streaks = self.db.get_streaks()
        lifetime = self.db.get_lifetime_stats()
        rows = self.db.get_daily_history(self.period)
        productive = today["productive_seconds"]
        classified = productive + today["distracted_seconds"]
        self.date_label.setText(datetime.now().strftime("%A, %d %B").upper())
        self.stat_values["productive"].setText(duration(productive))
        self.stat_values["streak"].setText(f"{streaks['current_streak']} days")
        self.stat_details["streak"].setText(f"Personal best: {streaks['best_streak']} days")
        self.stat_values["balance"].setText(f"{round(productive / classified * 100)}%" if classified else "—")
        self.stat_values["sessions"].setText(str(today["focus_sessions_count"]))
        self.activity_chart.set_data(rows)
        total = sum(row["productive_seconds"] for row in rows)
        self.chart_summary.setText(f"{duration(total)} productive across the last {self.period} days")
        if total:
            best = max(rows, key=lambda row: row["productive_seconds"])
            best_day = date.fromisoformat(best["date"]).strftime("%a, %d %b")
            self.insight_label.setText(f"Your strongest day: {best_day} · {duration(best['productive_seconds'])} productive. Keep finding your rhythm.")
        else:
            self.insight_label.setText("Your story starts here. Use a productive app and your activity will appear automatically.")
        target = self.goal_input.value() * 60
        self.goal_ring.set_progress(productive, target)
        self.goal_summary.setText(f"{duration(productive)} of {duration(target)}" + (" · Goal reached!" if productive >= target else ""))
        self.heatmap.set_data(self.db.get_daily_history(84))
        self.streak_detail.setText(f"{streaks['active_days']} qualifying days, all time · Best streak: {streaks['best_streak']} days")
        for widget, done, text in zip(self.quest_labels,
                (productive >= 900, today["focus_sessions_count"] > 0, productive >= target),
                ("Find 15 minutes of focus", "Complete a focus session", "Reach your daily goal")):
            widget.setText(f"{'●' if done else '○'}  {text}")
            widget.setStyleSheet(f"color: {'#237A57' if done else '#728176'}; padding: 5px 0;")
        xp = int(lifetime["productive_seconds"] // 60) + lifetime["completed_sessions"] * 25
        level = xp // 250 + 1
        self.level_label.setText(f"Level {level} · {'Seedling' if level < 5 else 'Sprout' if level < 10 else 'Bloom'}")
        self.xp_label.setText(f"{xp % 250} / 250 XP to the next level")
        self.xp_bar.setValue(round((xp % 250) / 250 * 100))
        self.xp_bar.setToolTip("1 XP per productive minute + 25 XP per completed session. Progress is calculated from saved history.")
        self.badge_label.setText(f"Your companion has grown with you for {duration(lifetime['productive_seconds'])} of productive time.")
        self.lifetime_label.setText(f"All time: {duration(lifetime['productive_seconds'])} productive · {lifetime['completed_sessions']} completed sessions · Longest session {duration(lifetime['longest_session_seconds'])}")
        milestones = [
            (lifetime["completed_sessions"] >= 1, "First step", "1 completed session"),
            (streaks["best_streak"] >= 3, "Finding rhythm", "3-day streak"),
            (streaks["best_streak"] >= 7, "A week of you", "7-day streak"),
            (lifetime["productive_seconds"] >= 36000, "Deep roots", "10 productive hours"),
        ]
        self.achievements.setText("\n\n".join(f"{'● Unlocked' if done else '○ In progress'}   ·   {title}   —   {condition}" for done, title, condition in milestones))
        sessions = self.db.get_recent_sessions(100)
        self.history_table.setRowCount(len(sessions))
        self.history_empty.setVisible(not sessions)
        for i, session in enumerate(sessions):
            def stamp(value):
                try:
                    return datetime.fromisoformat(value).strftime("%d %b, %H:%M")
                except (ValueError, TypeError):
                    return str(value or "—")
            values = [stamp(session["start_time"]), duration(session["duration_seconds"]),
                      {"automatic": "Automatic", "legacy": "Earlier session"}.get(session.get("source"), "Focus timer"),
                      "Completed" if session["completed"] else "Partial", stamp(session["end_time"])]
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(str(session.get("start_time", "")) if j == 0 else value)
                if j == 3:
                    item.setForeground(QColor("#237A57" if session["completed"] else "#AA7751"))
                self.history_table.setItem(i, j, item)
            self.history_table.setRowHeight(i, 46)
        self.refresh_timer_state()

    def refresh_timer_state(self):
        session = self.session
        active = session.is_focus_active or session.is_break_active
        paused = getattr(session, "is_paused", False)
        remaining = (session.focus_remaining_sec if session.is_focus_active else session.break_remaining_sec) if active else self.focus_duration.value() * 60
        total = (session.focus_total_sec if session.is_focus_active else session.break_total_sec) if active else 0
        seconds = max(0, int(remaining + 0.999))
        self.timer_display.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
        self.timer_status.setText("PAUSED · TAKE YOUR TIME" if active and paused else "A LITTLE ROOM TO BREATHE" if session.is_break_active else "YOU'RE MAKING PROGRESS" if active else "READY WHEN YOU ARE")
        self.timer_progress.setValue(round((1 - remaining / total) * 1000) if total else 0)
        self.start_focus_button.setEnabled(not active)
        self.focus_duration.setEnabled(not active)
        for button in self.duration_buttons + self.break_buttons:
            button.setEnabled(not active)
        self.pause_button.setEnabled(active)
        self.pause_button.setText("Resume" if paused else "Pause")
        self.stop_button.setEnabled(active)
        self.mini_pet.set_pose(EmotionalPose.BREAK if session.is_break_active else EmotionalPose.FOCUSED if session.is_focus_active else EmotionalPose.HAPPY)

    def export_activity(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export your last 90 days", f"moodpet-activity-{date.today()}.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            rows = self.db.get_daily_history(90)
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        except (OSError, csv.Error) as error:
            QMessageBox.warning(self, "Export could not be saved", str(error))
            return
        QMessageBox.information(self, "Export saved", "Your last 90 days of activity are ready in your CSV file.")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.refresh_timer.start(5000)
        self.clock_timer.start(250)
        if self.settings.get("animations_enabled", True):
            self.mini_pet.timer.start(16)
        else:
            self.mini_pet.timer.stop()

    def hideEvent(self, event):
        self.refresh_timer.stop()
        self.clock_timer.stop()
        self.mini_pet.timer.stop()
        super().hideEvent(event)
