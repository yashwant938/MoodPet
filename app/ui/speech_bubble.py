from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

class SpeechBubble(QWidget):
    """Animated speech bubble widget floating above the pet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 10, 14, 16)

        self.label = QLabel("", self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.layout.addWidget(self.label)

        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Auto hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_bubble)

        self.hide()

    def show_message(self, text: str, auto_hide_sec: float = 6.0):
        """Displays speech bubble with animated fade in."""
        if not text:
            return

        self.label.setText(text)
        self.adjustSize()
        
        # Bring to front & show
        self.show()
        self.raise_()

        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

        if auto_hide_sec > 0:
            self.hide_timer.start(int(auto_hide_sec * 1000))

    def hide_bubble(self):
        """Fades out and hides speech bubble."""
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self._on_fade_finished)
        self.fade_anim.start()

    def _on_fade_finished(self):
        if self.opacity_effect.opacity() == 0.0:
            self.hide()
            try:
                self.fade_anim.finished.disconnect(self._on_fade_finished)
            except Exception:
                pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() - 10 # Reserve bottom 10px for speech arrow pointer

        # Draw bubble body
        bubble_rect = QRectF(2, 2, w - 4, h - 4)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 12, 12)

        # Draw Arrow Pointer pointing down
        cx = w / 2.0
        path.moveTo(cx - 7, h - 2)
        path.lineTo(cx, h + 8)
        path.lineTo(cx + 7, h - 2)
        path.closeSubpath()

        # Background fill and stroke
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
        painter.setBrush(QBrush(QColor(25, 28, 36, 235)))
        painter.drawPath(path)
