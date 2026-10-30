"""First-run setup occurs before any activity tracker is created."""
from app.ui.theme import DIALOG_STYLE
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QSpinBox, QDialogButtonBox


class WelcomeDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setStyleSheet(DIALOG_STYLE)
        self.settings = settings
        self.setWindowTitle("Welcome to MoodPet")
        self.setMinimumWidth(440)
        box = QVBoxLayout(self)
        box.setContentsMargins(28, 28, 28, 28)
        box.setSpacing(14)
        title = QLabel("A small companion. A little room to focus.")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #24563F")
        box.addWidget(title)
        text = QLabel("Choose how you want to begin. You can change these choices in Preferences anytime. Existing history is kept.")
        text.setWordWrap(True)
        box.addWidget(text)
        box.addWidget(QLabel("1 · Choose your companion"))
        self.companion = QComboBox()
        self.companion.addItem("Orbit · ivory robot", "orbit")
        self.companion.addItem("Starlight · lavender robot", "starlight")
        box.addWidget(self.companion)
        box.addWidget(QLabel("2 · Choose a daily focus goal"))
        self.goal = QSpinBox()
        self.goal.setRange(15, 720)
        self.goal.setSuffix(" minutes")
        self.goal.setValue(settings.get("daily_goal_minutes", 120))
        box.addWidget(self.goal)
        box.addWidget(QLabel("3 · Choose what MoodPet can observe"))
        self.mode = QComboBox()
        self.mode.addItem("Timer only · no app or input monitoring", "manual")
        self.mode.addItem("Automatic activity · use app names and window titles", "automatic")
        box.addWidget(self.mode)
        notice = QLabel("Automatic mode reads foreground app names, window titles and time since input. Only aggregate durations and sessions are saved locally. No keystrokes or window titles are stored. Timer-only goals use saved focus-timer time; automatic goals use tracked productive time.")
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #52665B; padding: 10px; background: #EEF6EF")
        box.addWidget(notice)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Meet my companion")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)

    def accept(self):
        self.settings.set("tracking_mode", self.mode.currentData())
        self.settings.set("companion_style", self.companion.currentData())
        self.settings.set("daily_goal_minutes", self.goal.value())
        self.settings.set("onboarding_complete", True)
        super().accept()
