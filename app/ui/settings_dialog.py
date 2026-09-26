from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QListWidget,
    QLineEdit, QGroupBox, QFormLayout, QTimeEdit, QMessageBox, QFrame
)
from PySide6.QtCore import QTime
from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.productivity.focus_tracker import FocusTracker

class SettingsDialog(QDialog):
    """Full-featured modern settings & statistics dashboard dialog."""

    def __init__(self, settings: SettingsManager, db: DatabaseManager, focus_tracker: FocusTracker, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.db = db
        self.focus_tracker = focus_tracker

        self.setWindowTitle("MoodPet Preferences")
        self.resize(640, 570)
        self.setMinimumSize(590, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #313244;
                background-color: #181825;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #181825;
                color: #A6ADC8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #313244;
                color: #CBA6F7;
                font-weight: bold;
            }
            QGroupBox {
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                color: #CBA6F7;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #CDD6F4;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QListWidget {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton {
                background-color: #89B4FA;
                color: #11111B;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #B4BEFE;
            }
            QCheckBox {
                color: #CDD6F4;
            }
        """)

        main_layout = QVBoxLayout(self)

        # Tabs
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        self._build_general_tab()
        self._build_rules_tab()
        self._build_thresholds_tab()
        self._build_stats_tab()

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.clicked.connect(self.save_and_apply)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #45475A; color: #CDD6F4;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Companion Preferences")
        form = QFormLayout(box)

        # Pet Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.6, 2.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(float(self.settings.get("pet_scale", 1.0)))
        form.addRow("Pet Size Scale:", self.scale_spin)

        # Auto hide duration
        self.msg_delay_spin = QSpinBox()
        self.msg_delay_spin.setRange(2, 20)
        self.msg_delay_spin.setValue(int(self.settings.get("auto_hide_message_sec", 6)))
        form.addRow("Message Auto-Hide (sec):", self.msg_delay_spin)

        # Checkboxes
        self.always_top_chk = QCheckBox("Always on Top")
        self.always_top_chk.setChecked(bool(self.settings.get("always_on_top", True)))
        form.addRow(self.always_top_chk)

        self.animations_chk = QCheckBox("Enable Pet Animations")
        self.animations_chk.setChecked(bool(self.settings.get("animations_enabled", True)))
        form.addRow(self.animations_chk)

        self.startup_chk = QCheckBox("Start with Windows")
        self.startup_chk.setChecked(bool(self.settings.get("start_with_windows", False)))
        form.addRow(self.startup_chk)

        layout.addWidget(box)

        # Quiet Hours Group
        quiet_box = QGroupBox("Quiet Hours")
        qform = QFormLayout(quiet_box)

        self.quiet_chk = QCheckBox("Enable Quiet Hours (Silence Speech)")
        self.quiet_chk.setChecked(bool(self.settings.get("quiet_hours_enabled", False)))
        qform.addRow(self.quiet_chk)

        self.quiet_start_edit = QTimeEdit()
        self.quiet_start_edit.setDisplayFormat("HH:mm")
        q_start = QTime.fromString(self.settings.get("quiet_start", "22:00"), "HH:mm")
        self.quiet_start_edit.setTime(q_start)
        qform.addRow("Start Time:", self.quiet_start_edit)

        self.quiet_end_edit = QTimeEdit()
        self.quiet_end_edit.setDisplayFormat("HH:mm")
        q_end = QTime.fromString(self.settings.get("quiet_end", "08:00"), "HH:mm")
        self.quiet_end_edit.setTime(q_end)
        qform.addRow("End Time:", self.quiet_end_edit)

        layout.addWidget(quiet_box)
        layout.addStretch()
        self.tabs.addTab(tab, "⚙️ General")

    def _build_rules_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Productive Apps Column
        prod_box = QGroupBox("Productive Apps & Keywords")
        prod_layout = QVBoxLayout(prod_box)
        self.prod_list = QListWidget()
        for app in self.settings.get("productive_apps", []) + self.settings.get("productive_keywords", []):
            self.prod_list.addItem(app)
        prod_layout.addWidget(self.prod_list)

        prod_input_layout = QHBoxLayout()
        self.prod_input = QLineEdit()
        self.prod_input.setPlaceholderText("e.g. code.exe or github")
        prod_input_layout.addWidget(self.prod_input)
        add_prod_btn = QPushButton("+")
        add_prod_btn.clicked.connect(self._add_productive)
        prod_input_layout.addWidget(add_prod_btn)
        rem_prod_btn = QPushButton("-")
        rem_prod_btn.clicked.connect(self._rem_productive)
        prod_input_layout.addWidget(rem_prod_btn)
        prod_layout.addLayout(prod_input_layout)
        layout.addWidget(prod_box)

        # Distracting Apps Column
        dist_box = QGroupBox("Distracting Apps & Keywords")
        dist_layout = QVBoxLayout(dist_box)
        self.dist_list = QListWidget()
        for app in self.settings.get("distracting_apps", []) + self.settings.get("distracting_keywords", []):
            self.dist_list.addItem(app)
        dist_layout.addWidget(self.dist_list)

        dist_input_layout = QHBoxLayout()
        self.dist_input = QLineEdit()
        self.dist_input.setPlaceholderText("e.g. youtube or reddit")
        dist_input_layout.addWidget(self.dist_input)
        add_dist_btn = QPushButton("+")
        add_dist_btn.clicked.connect(self._add_distracting)
        dist_input_layout.addWidget(add_dist_btn)
        rem_dist_btn = QPushButton("-")
        rem_dist_btn.clicked.connect(self._rem_distracting)
        dist_input_layout.addWidget(rem_dist_btn)
        dist_layout.addLayout(dist_input_layout)
        layout.addWidget(dist_box)

        self.tabs.addTab(tab, "🎯 App Rules")

    def _add_productive(self):
        txt = self.prod_input.text().strip().lower()
        if txt:
            self.prod_list.addItem(txt)
            self.prod_input.clear()

    def _rem_productive(self):
        for item in self.prod_list.selectedItems():
            self.prod_list.takeItem(self.prod_list.row(item))

    def _add_distracting(self):
        txt = self.dist_input.text().strip().lower()
        if txt:
            self.dist_list.addItem(txt)
            self.dist_input.clear()

    def _rem_distracting(self):
        for item in self.dist_list.selectedItems():
            self.dist_list.takeItem(self.dist_list.row(item))

    def _build_thresholds_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Behavior & Sensitivity Thresholds")
        form = QFormLayout(box)

        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(15, 600)
        self.idle_spin.setValue(int(self.settings.get("idle_threshold_sec", 60)))
        form.addRow("Short Idle Threshold (seconds):", self.idle_spin)

        self.long_idle_spin = QSpinBox()
        self.long_idle_spin.setRange(60, 3600)
        self.long_idle_spin.setValue(int(self.settings.get("long_idle_threshold_sec", 300)))
        form.addRow("Long Idle / Sleep Threshold (seconds):", self.long_idle_spin)

        self.grace_spin = QSpinBox()
        self.grace_spin.setRange(10, 600)
        self.grace_spin.setValue(int(self.settings.get("distraction_grace_period_sec", 120)))
        form.addRow("Distraction Grace Period (seconds):", self.grace_spin)

        self.milestone_spin = QSpinBox()
        self.milestone_spin.setRange(5, 180)
        target_mins = int(self.settings.get("focus_milestone_target_sec", 1800) // 60)
        self.milestone_spin.setValue(target_mins)
        form.addRow("Focus Milestone Target (minutes):", self.milestone_spin)

        layout.addWidget(box)
        layout.addStretch()
        self.tabs.addTab(tab, "⏱️ Thresholds")

    def _build_stats_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        box = QGroupBox("Today's Productivity Summary")
        vbox = QVBoxLayout(box)

        stats = self.db.get_today_stats()
        prod_str = self.focus_tracker.format_time(stats["productive_seconds"])
        dist_str = self.focus_tracker.format_time(stats["distracted_seconds"])
        longest_str = self.focus_tracker.format_time(stats["longest_session_seconds"])

        def make_card(title, value):
            frame = QFrame()
            frame.setStyleSheet("background-color: #313244; border-radius: 6px; padding: 6px;")
            fl = QHBoxLayout(frame)
            fl.addWidget(QLabel(title))
            val_lbl = QLabel(str(value))
            val_lbl.setStyleSheet("color: #89B4FA; font-weight: bold; font-size: 14px;")
            fl.addWidget(val_lbl, 0, Qt.AlignRight)
            return frame

        vbox.addWidget(make_card("🔥 Current Streak:", f"{self.focus_tracker.current_streak} days"))
        vbox.addWidget(make_card("📊 Productive Time Today:", prod_str))
        vbox.addWidget(make_card("⏳ Distraction Time Today:", dist_str))
        vbox.addWidget(make_card("🎯 Completed Focus Sessions:", f"{stats['focus_sessions_count']} sessions"))
        vbox.addWidget(make_card("🏆 Longest Focus Session:", longest_str))

        layout.addWidget(box)

        reset_btn = QPushButton("🔄 Reset Today's Statistics")
        reset_btn.setStyleSheet("background-color: #F38BA8; color: #11111B;")
        reset_btn.clicked.connect(self._reset_today_stats)
        layout.addWidget(reset_btn)

        layout.addStretch()
        self.tabs.addTab(tab, "📊 Dashboard")

    def _reset_today_stats(self):
        reply = QMessageBox.question(self, "Confirm Reset", "Reset today's activity and delete today's session history? This can change your streak and XP. Earlier days are kept.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            parent = self.parent()
            if parent is not None and hasattr(parent, "focus_session_mgr"):
                parent.focus_session_mgr.stop_all()
                parent.character_widget.set_focus_mode(False)
                parent.character_widget.set_break_mode(False)
            self.db.reset_today_stats()
            self.focus_tracker.reset_current_session()
            QMessageBox.information(self, "Reset", "Today's statistics have been reset.")
            self.accept()

    def save_and_apply(self):
        """Save form values to SettingsManager."""
        self.settings.set("pet_scale", self.scale_spin.value())
        self.settings.set("auto_hide_message_sec", self.msg_delay_spin.value())
        self.settings.set("always_on_top", self.always_top_chk.isChecked())
        self.settings.set("animations_enabled", self.animations_chk.isChecked())
        
        # Windows startup registry integration
        new_startup = self.startup_chk.isChecked()
        self.settings.set_start_with_windows(new_startup)

        # Quiet hours
        self.settings.set("quiet_hours_enabled", self.quiet_chk.isChecked())
        self.settings.set("quiet_start", self.quiet_start_edit.time().toString("HH:mm"))
        self.settings.set("quiet_end", self.quiet_end_edit.time().toString("HH:mm"))

        # App Rules
        prod_items = [self.prod_list.item(i).text() for i in range(self.prod_list.count())]
        prod_apps = [item for item in prod_items if item.endswith(".exe")]
        prod_kws = [item for item in prod_items if not item.endswith(".exe")]
        self.settings.set("productive_apps", prod_apps)
        self.settings.set("productive_keywords", prod_kws)

        dist_items = [self.dist_list.item(i).text() for i in range(self.dist_list.count())]
        dist_apps = [item for item in dist_items if item.endswith(".exe")]
        dist_kws = [item for item in dist_items if not item.endswith(".exe")]
        self.settings.set("distracting_apps", dist_apps)
        self.settings.set("distracting_keywords", dist_kws)

        # Thresholds
        self.settings.set("idle_threshold_sec", self.idle_spin.value())
        self.settings.set("long_idle_threshold_sec", self.long_idle_spin.value())
        self.settings.set("distraction_grace_period_sec", self.grace_spin.value())
        self.settings.set("focus_milestone_target_sec", self.milestone_spin.value() * 60)

        self.accept()
