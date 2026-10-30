from app.ui.theme import DIALOG_STYLE
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from app.productivity.score_engine import ProductivityState


class ActivityDialog(QDialog):
    def __init__(self, pet):
        super().__init__(pet)
        self.setStyleSheet(DIALOG_STYLE)
        self.pet = pet
        self.window = dict(pet.current_window)
        self.setWindowTitle("Why this activity?")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.reason = QLabel(pet.activity_summary())
        self.reason.setWordWrap(True)
        layout.addWidget(self.reason)
        explanation = QLabel("Corrections apply to the window you were using when this panel opened. They expire after 30 minutes or when a focus/break timer ends. Idle time is still idle.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("Optional keyword to remember (3–100 characters)")
        self.keyword.setMaxLength(100)
        layout.addWidget(self.keyword)
        scope = QLabel("Leave blank for a temporary correction. Entering a keyword saves a rule for all future window titles containing it. No captured title is saved automatically.")
        scope.setWordWrap(True)
        layout.addWidget(scope)
        for name, state in (("I'm learning · productive", ProductivityState.PRODUCTIVE), ("I'm taking a break · neutral", ProductivityState.NEUTRAL), ("This is distracting", ProductivityState.DISTRACTING)):
            button = QPushButton(name)
            button.setEnabled(bool(self.window) and pet.activity_policy.enabled)
            button.clicked.connect(lambda checked=False, choice=state: self.correct(choice))
            layout.addWidget(button)
        pause = QPushButton("Pause activity tracking for 15 minutes")
        pause.clicked.connect(lambda: (pet.pause_tracking(), self.accept()))
        layout.addWidget(pause)

    def correct(self, state):
        try:
            self.pet.activity_policy.correct(self.window, state, self.keyword.text())
        except ValueError as error:
            QMessageBox.information(self, "Check your correction", str(error))
            return
        if state == ProductivityState.NEUTRAL and self.pet.focus_session_mgr.is_focus_active and not self.pet.focus_session_mgr.is_paused:
            self.pet._toggle_session_pause()
        self.pet._say("Thanks for telling me. Your choice will guide this activity.")
        self.accept()
