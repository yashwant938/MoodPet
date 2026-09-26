import random
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont

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

class AnimationManager:
    """Manages particle systems: confetti, ZZZ, tears, sparkles, typing key feedback."""

    def __init__(self):
        self.particles = []

    def trigger_confetti(self, width: float, height: float):
        colors = ["#FF1744", "#FF9100", "#FFEA00", "#00E676", "#00E5FF", "#D500F9"]
        for _ in range(50):
            px = width / 2 + random.uniform(-25, 25)
            py = height / 2 + random.uniform(-15, 15)
            dx = random.uniform(-140, 140)
            dy = random.uniform(-200, -50)
            lifetime = random.uniform(1.2, 2.5)
            color = random.choice(colors)
            size = random.uniform(4, 9)
            self.particles.append(Particle(px, py, dx, dy, lifetime, color, size, ptype="confetti"))

    def trigger_typing_sparkle(self, x: float, y: float):
        colors = ["#80DEEA", "#FFFFFF", "#80CBC4"]
        for _ in range(2):
            dx = random.uniform(-20, 20)
            dy = random.uniform(-30, -10)
            self.particles.append(Particle(x, y, dx, dy, 0.4, random.choice(colors), 3, ptype="sparkle"))

    def update(self, dt: float, width: float, height: float, pose_name: str):
        dead_particles = []
        for p in self.particles:
            p.update(dt)
            if p.ptype == "confetti":
                p.dy += 190 * dt  # Gravity
            if p.is_dead():
                dead_particles.append(p)

        for p in dead_particles:
            self.particles.remove(p)

        # Periodic spawns based on pose
        if pose_name == "SLEEPY" and random.random() < 0.03:
            px = width / 2 + 25
            py = height / 2 - 20
            self.particles.append(Particle(px, py, random.uniform(10, 25), random.uniform(-30, -15), 2.5, "#B39DDB", 14, ptype="text", char="z"))

        elif pose_name == "SAD" and random.random() < 0.08:
            px = width / 2 + random.choice([-16, 16])
            py = height / 2 + 5
            self.particles.append(Particle(px, py, 0, random.uniform(40, 80), 1.0, "#64B5F6", 5, ptype="tear"))

    def render(self, painter: QPainter):
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
                font = QFont("Segoe UI", int(p.size), QFont.Bold)
                painter.setFont(font)
                painter.drawText(QPointF(p.x, p.y), p.char)
