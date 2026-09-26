import math
import random
import time
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QWidget
from app.emotion.state_machine import EmotionState

class Particle:
    def __init__(self, x, y, dx, dy, lifetime, color, size, ptype="sparkle", char="Z"):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = QColor(color)
        self.size = size
        self.ptype = ptype
        self.char = char

    def update(self, dt):
        self.x += self.dx * dt
        self.y += self.dy * dt
        self.lifetime -= dt

    def is_dead(self):
        return self.lifetime <= 0

class CharacterWidget(QWidget):
    """Renders an expressive, animated vector desktop pet mascot with physics & particles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.emotion = EmotionState.HAPPY
        self.pet_scale = 1.0
        
        self.anim_time = 0.0
        self.blink_timer = 0.0
        self.is_blinking = False
        self.next_blink = random.uniform(2.0, 5.0)

        self.particles = []
        self.confetti_burst_timer = 0.0

        # Animation timer ~60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def set_emotion(self, emotion: EmotionState):
        if self.emotion != emotion:
            self.emotion = emotion
            if emotion == EmotionState.EXCITED:
                self.trigger_confetti()
            self.update()

    def trigger_confetti(self):
        """Spawns confetti explosion particles."""
        colors = ["#FF1744", "#FF9100", "#FFEA00", "#00E676", "#00E5FF", "#D500F9"]
        for _ in range(40):
            px = self.width() / 2 + random.uniform(-20, 20)
            py = self.height() / 2 + random.uniform(-10, 10)
            dx = random.uniform(-120, 120)
            dy = random.uniform(-180, -40)
            lifetime = random.uniform(1.2, 2.5)
            color = random.choice(colors)
            size = random.uniform(4, 8)
            self.particles.append(Particle(px, py, dx, dy, lifetime, color, size, ptype="confetti"))

    def _on_tick(self):
        dt = 0.016
        self.anim_time += dt

        # Handle blinking
        self.blink_timer += dt
        if self.blink_timer >= self.next_blink:
            self.is_blinking = True
            if self.blink_timer >= self.next_blink + 0.15:
                self.is_blinking = False
                self.blink_timer = 0.0
                self.next_blink = random.uniform(2.5, 6.0)

        # Particle updates
        dead_particles = []
        for p in self.particles:
            p.update(dt)
            if p.ptype == "confetti":
                p.dy += 180 * dt  # Gravity
            if p.is_dead():
                dead_particles.append(p)

        for p in dead_particles:
            self.particles.remove(p)

        # Periodic emotion-specific particle generation
        if self.emotion == EmotionState.SLEEPING and random.random() < 0.03:
            px = self.width() / 2 + 25
            py = self.height() / 2 - 15
            self.particles.append(Particle(px, py, random.uniform(10, 25), random.uniform(-30, -15), 2.5, "#B39DDB", 14, ptype="text", char="z"))

        elif self.emotion == EmotionState.SAD and random.random() < 0.08:
            px = self.width() / 2 + random.choice([-15, 15])
            py = self.height() / 2 + 5
            self.particles.append(Particle(px, py, 0, random.uniform(40, 80), 1.0, "#64B5F6", 5, ptype="tear"))

        elif self.emotion == EmotionState.HAPPY and random.random() < 0.04:
            px = self.width() / 2 + random.uniform(-35, 35)
            py = self.height() / 2 + random.uniform(-35, 35)
            self.particles.append(Particle(px, py, random.uniform(-10, 10), random.uniform(-20, -5), 1.2, "#FFEE58", 4, ptype="sparkle"))

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        cx = w / 2.0
        cy = h / 2.0 + 10  # Slight offset down to allow floating room

        # Physics Offset calculation
        float_y = 0.0
        shake_x = 0.0
        scale_x = 1.0
        scale_y = 1.0

        if self.emotion == EmotionState.HAPPY:
            float_y = math.sin(self.anim_time * 3.5) * 6.0
        elif self.emotion == EmotionState.ANGRY:
            shake_x = math.sin(self.anim_time * 28.0) * 4.0
        elif self.emotion == EmotionState.SAD:
            float_y = math.sin(self.anim_time * 1.5) * 3.0 + 6.0
        elif self.emotion == EmotionState.SLEEPING:
            scale_pulse = math.sin(self.anim_time * 2.0) * 0.03
            scale_x += scale_pulse
            scale_y -= scale_pulse
            float_y = 4.0
        elif self.emotion == EmotionState.EXCITED:
            bounce = abs(math.sin(self.anim_time * 7.0)) * 14.0
            float_y = -bounce
            if bounce < 2.0:
                scale_x = 1.12
                scale_y = 0.88
            else:
                scale_x = 0.92
                scale_y = 1.08

        # Draw Ground Shadow
        painter.setPen(Qt.NoPen)
        shadow_w = (65.0 - float_y * 0.8) * scale_x
        shadow_h = 12.0
        shadow_color = QColor(0, 0, 0, max(20, int(60 - float_y * 2)))
        painter.setBrush(shadow_color)
        painter.drawEllipse(QPointF(cx + shake_x, cy + 35), shadow_w / 2, shadow_h / 2)

        # Apply transforms for body
        painter.save()
        painter.translate(cx + shake_x, cy + float_y)
        painter.scale(scale_x, scale_y)

        # Draw Main Pet Body
        body_rect = QRectF(-42, -40, 84, 75)

        # Gradient setup per emotion
        grad = QLinearGradient(0, -40, 0, 35)
        if self.emotion == EmotionState.HAPPY:
            grad.setColorAt(0.0, QColor("#FFE082"))
            grad.setColorAt(1.0, QColor("#FFB300"))
        elif self.emotion == EmotionState.ANGRY:
            grad.setColorAt(0.0, QColor("#FF7043"))
            grad.setColorAt(1.0, QColor("#D84315"))
        elif self.emotion == EmotionState.SAD:
            grad.setColorAt(0.0, QColor("#90CAF9"))
            grad.setColorAt(1.0, QColor("#1E88E5"))
        elif self.emotion == EmotionState.SLEEPING:
            grad.setColorAt(0.0, QColor("#D1C4E9"))
            grad.setColorAt(1.0, QColor("#7E57C2"))
        elif self.emotion == EmotionState.EXCITED:
            grad.setColorAt(0.0, QColor("#FF80AB"))
            grad.setColorAt(1.0, QColor("#FF1744"))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(0, 0, 0, 40), 2.5))
        painter.drawRoundedRect(body_rect, 38, 35)

        # Draw Cheeks
        blush_color = QColor(255, 100, 120, 110)
        painter.setBrush(blush_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-32, -3, 13, 8)
        painter.drawEllipse(19, -3, 13, 8)

        # Draw Eyes
        painter.setPen(QPen(QColor("#212121"), 3.0, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(QColor("#212121"))

        if self.is_blinking and self.emotion not in (EmotionState.SLEEPING, EmotionState.ANGRY):
            # Blink lines
            painter.drawLine(-22, -12, -10, -12)
            painter.drawLine(10, -12, 22, -12)
        elif self.emotion == EmotionState.SLEEPING:
            # Sleeping curved eyes (u u)
            path_eye_l = QPainterPath()
            path_eye_l.moveTo(-24, -14)
            path_eye_l.quadTo(-17, -8, -10, -14)
            painter.drawPath(path_eye_l)

            path_eye_r = QPainterPath()
            path_eye_r.moveTo(10, -14)
            path_eye_r.quadTo(17, -8, 24, -14)
            painter.drawPath(path_eye_r)

        elif self.emotion == EmotionState.ANGRY:
            # Slanted angry eyes
            painter.drawLine(-24, -18, -10, -12)
            painter.drawLine(24, -18, 10, -12)
            painter.drawEllipse(-20, -13, 8, 8)
            painter.drawEllipse(12, -13, 8, 8)

        elif self.emotion == EmotionState.EXCITED:
            # Star / Happy eyes (^^)
            path_eye_l = QPainterPath()
            path_eye_l.moveTo(-24, -10)
            path_eye_l.quadTo(-17, -18, -10, -10)
            painter.drawPath(path_eye_l)

            path_eye_r = QPainterPath()
            path_eye_r.moveTo(10, -10)
            path_eye_r.quadTo(17, -18, 24, -10)
            painter.drawPath(path_eye_r)

        else: # HAPPY or SAD regular big shiny eyes
            # Main iris
            painter.drawEllipse(-24, -19, 14, 16)
            painter.drawEllipse(10, -19, 14, 16)
            # Eye highlights
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-22, -17, 5, 5)
            painter.drawEllipse(12, -17, 5, 5)
            painter.drawEllipse(-16, -10, 3, 3)
            painter.drawEllipse(18, -10, 3, 3)

        # Draw Mouth
        painter.setPen(QPen(QColor("#212121"), 2.8, Qt.SolidLine, Qt.RoundCap))
        if self.emotion == EmotionState.HAPPY:
            path_mouth = QPainterPath()
            path_mouth.moveTo(-8, 3)
            path_mouth.quadTo(0, 12, 8, 3)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path_mouth)

        elif self.emotion == EmotionState.ANGRY:
            path_mouth = QPainterPath()
            path_mouth.moveTo(-10, 10)
            path_mouth.lineTo(-4, 4)
            path_mouth.lineTo(2, 10)
            path_mouth.lineTo(8, 4)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path_mouth)

            # Draw Anger Vein (💢) on top right head
            painter.setPen(QPen(QColor("#D50000"), 2.5))
            painter.drawLine(22, -32, 32, -32)
            painter.drawLine(27, -37, 27, -27)

        elif self.emotion == EmotionState.SAD:
            path_mouth = QPainterPath()
            path_mouth.moveTo(-8, 10)
            path_mouth.quadTo(0, 2, 8, 10)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path_mouth)

        elif self.emotion == EmotionState.SLEEPING:
            painter.setBrush(QColor("#212121"))
            painter.drawEllipse(-3, 3, 6, 6)

        elif self.emotion == EmotionState.EXCITED:
            path_mouth = QPainterPath()
            path_mouth.moveTo(-10, 2)
            path_mouth.quadTo(0, 18, 10, 2)
            path_mouth.closeSubpath()
            painter.setBrush(QColor("#D50000"))
            painter.drawPath(path_mouth)

        painter.restore()

        # Draw Particles in Screen Coordinates
        for p in self.particles:
            alpha = max(0, int(255 * (p.lifetime / p.max_lifetime)))
            c = QColor(p.color)
            c.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c)

            if p.ptype in ("confetti", "sparkle"):
                painter.drawRect(QRectF(p.x, p.y, p.size, p.size))
            elif p.ptype == "tear":
                painter.drawEllipse(QPointF(p.x, p.y), p.size / 2, p.size)
            elif p.ptype == "text":
                painter.setPen(c)
                font = QFont("Arial", int(p.size), QFont.Bold)
                painter.setFont(font)
                painter.drawText(QPointF(p.x, p.y), p.char)
