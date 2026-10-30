"""A constellation from saved completed sessions, with keyboard-readable details."""
import math
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QToolTip


def session_text(session):
    minutes = session["duration_seconds"] // 60
    return f"{session['date']} · {minutes} min · {session.get('note') or 'A small step forward'}"


class Constellation(QWidget):
    selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions = []
        self.selected_index = -1
        self.setMinimumHeight(230)
        self.setMouseTracking(True)
        self.setAccessibleName("Focus constellation")

    def set_sessions(self, sessions):
        self.sessions = sessions
        self.setAccessibleDescription(f"{len(sessions)} completed sessions. Use the session list below to read each star.")
        self.update()

    def points(self):
        # The same session ID always has the same position as history grows.
        return [QPointF(25 + ((s['id'] * 0.61803398875) % 1) * max(1, self.width() - 50),
                        25 + ((s['id'] * 0.41421356237) % 1) * max(1, self.height() - 50)) for s in self.sessions]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111D32"))
        # Faint background points are decoration; large stars are saved completions.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#26364C"))
        for i in range(65):
            painter.drawEllipse(QPointF((i * 137 + 23) % max(1, self.width()), (i * 71 + 19) % max(1, self.height())), 1, 1)
        points = self.points()
        painter.setPen(QPen(QColor("#38577D"), 1))
        # Join sessions on the same date; breaks never remove or darken stars.
        for index in range(1, len(points)):
            if index < 30:
                painter.drawLine(points[index - 1], points[index])
        for index, point in enumerate(points):
            if index == self.selected_index:
                painter.setPen(QPen(QColor("#B9AAF3"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(point, 14, 14)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#294567"))
            painter.drawEllipse(point, 9, 9)
            painter.setBrush(QColor("#C8EFFF"))
            painter.drawEllipse(point, 3.5, 3.5)
        if not points:
            painter.setPen(QColor("#C7D9EC"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Your first completed session will light a star.\nBreaks are welcome here.")

    def mouseMoveEvent(self, event):
        for index, point in enumerate(self.points()):
            if math.hypot(point.x() - event.position().x(), point.y() - event.position().y()) < 12:
                QToolTip.showText(event.globalPosition().toPoint(), session_text(self.sessions[index]), self)
                return
        QToolTip.hideText()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            for index, point in enumerate(self.points()):
                if math.hypot(point.x() - event.position().x(), point.y() - event.position().y()) < 12:
                    self.selected.emit(index)
                    return


class JourneyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        title = QLabel("A constellation of small steps")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #24563F")
        box.addWidget(title)
        subtitle = QLabel("Each completed session lights a star. Your recent 100 completions are shown; breaks and missed days never remove a star.")
        subtitle.setWordWrap(True)
        box.addWidget(subtitle)
        self.sky = Constellation()
        self.sky.setMinimumHeight(300)
        box.addWidget(self.sky)
        self.summary = QLabel("0 stars · your first completed session starts the constellation")
        box.addWidget(self.summary)
        self.list = QListWidget()
        self.list.setAccessibleName("Completed sessions and notes")
        self.list.setMinimumHeight(160)
        self.list.setMaximumHeight(260)
        self.list.setSpacing(3)
        self.list.setStyleSheet("QListWidget { background: white; border: 1px solid #D5E3DB; border-radius: 8px; padding: 10px; } QListWidget::item { padding: 9px; border-radius: 5px; } QListWidget::item:selected { background: #DDF2E4; color: #174A34; }")
        box.addWidget(self.list)
        self.sky.selected.connect(self.list.setCurrentRow)
        self.list.currentRowChanged.connect(self.select_star)
        box.addStretch()

    def select_star(self, index):
        self.sky.selected_index = index
        self.sky.update()

    def refresh(self, db):
        sessions = db.get_journey_sessions()
        if sessions == self.sky.sessions:
            return
        self.sky.set_sessions(sessions)
        self.list.clear()
        self.list.addItems([session_text(row) for row in sessions])
        self.summary.setText(f"{len(sessions)} stars · {sum(row['duration_seconds'] for row in sessions) // 60} completed minutes · select a star or a session below")
