from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QFrame
)
from app.config.constants import FOCUS_PRESETS

class FocusPanel(QDialog):
    """Compact interactive control panel launched on character click."""

    focus_started = Signal(int)  # duration in seconds
    break_started = Signal(int)  # duration in seconds

    def __init__(self, today_focus_str: str, streak: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MoodPet Companion Panel")
        self.setFixedSize(320, 360)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.selected_duration_sec = 1500  # Default 25m

        self._build_ui(today_focus_str, streak)

    def _build_ui(self, today_focus_str: str, streak: int):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 1px solid #313244;
                border-radius: 12px;
            }
            QLabel {
                color: #CDD6F4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475A;
                color: #CBA6F7;
            }
            QPushButton:checked {
                background-color: #CBA6F7;
                color: #11111B;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("🎯 FOCUS MODE")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #CBA6F7;")
        card_layout.addWidget(header)

        sub = QLabel("Select focus session duration:")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 11px; color: #A6ADC8; margin-bottom: 8px;")
        card_layout.addWidget(sub)

        # Duration Presets Grid
        grid1 = QHBoxLayout()
        self.btn_15 = self._create_preset_btn("15m", 900)
        self.btn_25 = self._create_preset_btn("25m", 1500, default=True)
        self.btn_45 = self._create_preset_btn("45m", 2700)
        grid1.addWidget(self.btn_15)
        grid1.addWidget(self.btn_25)
        grid1.addWidget(self.btn_45)
        card_layout.addLayout(grid1)

        grid2 = QHBoxLayout()
        self.btn_60 = self._create_preset_btn("1h", 3600)
        self.btn_90 = self._create_preset_btn("90m", 5400)
        self.btn_120 = self._create_preset_btn("2h", 7200)
        grid2.addWidget(self.btn_60)
        grid2.addWidget(self.btn_90)
        grid2.addWidget(self.btn_120)
        card_layout.addLayout(grid2)

        # Start Focus Button
        self.start_btn = QPushButton("🚀 START FOCUS SESSION")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #89B4FA;
                color: #11111B;
                font-size: 13px;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #B4BEFE;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_focus)
        card_layout.addWidget(self.start_btn)

        # Break Mode Button
        self.break_btn = QPushButton("☕ Take 10m Break")
        self.break_btn.setStyleSheet("""
            QPushButton {
                background-color: #A5D6A7;
                color: #1B5E20;
                font-size: 12px;
                padding: 6px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #C8E6C9;
            }
        """)
        self.break_btn.clicked.connect(self._on_start_break)
        card_layout.addWidget(self.break_btn)

        # Stats Summary Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #181825; border-radius: 6px; padding: 6px;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(8, 4, 8, 4)

        stats_lbl = QLabel(f"Today: <b>{today_focus_str}</b>  |  Streak: <b>🔥 {streak}</b>")
        stats_lbl.setAlignment(Qt.AlignCenter)
        stats_lbl.setStyleSheet("font-size: 11px; color: #CDD6F4;")
        fl.addWidget(stats_lbl)

        card_layout.addWidget(footer)
        main_layout.addWidget(card)

    def _create_preset_btn(self, label: str, duration_sec: int, default: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        if default:
            btn.setChecked(True)
        btn.clicked.connect(lambda: self._select_preset(btn, duration_sec))
        return btn

    def _select_preset(self, selected_btn: QPushButton, duration_sec: int):
        for btn in (self.btn_15, self.btn_25, self.btn_45, self.btn_60, self.btn_90, self.btn_120):
            btn.setChecked(btn == selected_btn)
        self.selected_duration_sec = duration_sec

    def _on_start_focus(self):
        self.focus_started.emit(self.selected_duration_sec)
        self.accept()

    def _on_start_break(self):
        self.break_started.emit(600) # 10m break
        self.accept()
