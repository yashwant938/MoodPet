import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QBrush, QFont, QPainterPath

from PySide6.QtWidgets import QWidget
from app.character.emotions import EmotionalPose
from app.character.eye_tracking import EyeTracker
from app.character.accessories import AccessoryPainter
from app.ui.animations import AnimationManager

class HumanCharacterWidget(QWidget):
    """Renders a glossy 3D AI Robot Companion matching the reference visual specification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pose = EmotionalPose.IDLE
        self.eye_tracker = EyeTracker(lerp_speed=0.15)
        self.anim_mgr = AnimationManager()

        self.is_typing = False
        self.is_in_focus = False
        self.is_in_break = False
        self.timer_text = ""

        self.anim_time = 0.0
        self.blink_timer = 0.0
        self.is_blinking = False
        self.next_blink = random.uniform(2.0, 5.0)

        # Render loop ~60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def set_pose(self, pose: EmotionalPose):
        if self.pose != pose:
            self.pose = pose
            if pose in (EmotionalPose.EXCITED, EmotionalPose.CELEBRATION):
                self.anim_mgr.trigger_confetti(self.width(), self.height())
            self.update()

    def set_typing(self, active: bool):
        self.is_typing = active
        if active and random.random() < 0.15:
            self.anim_mgr.trigger_typing_sparkle(self.width() / 2, self.height() / 2 + 18)

    def set_focus_mode(self, is_focus: bool, timer_text: str = ""):
        self.is_in_focus = is_focus
        self.timer_text = timer_text
        self.update()

    def set_break_mode(self, is_break: bool, timer_text: str = ""):
        self.is_in_break = is_break
        self.timer_text = timer_text
        self.update()

    def _on_tick(self):
        dt = 0.016
        self.anim_time += dt

        # Update eye gaze + typing movement
        pet_global_pos = self.mapToGlobal(QPointF(self.width() / 2.0, self.height() / 2.0))
        self.eye_tracker.update(pet_global_pos, is_typing=self.is_typing, dt=dt)

        # Handle Blinking
        self.blink_timer += dt
        if self.blink_timer >= self.next_blink:
            self.is_blinking = True
            if self.blink_timer >= self.next_blink + 0.15:
                self.is_blinking = False
                self.blink_timer = 0.0
                self.next_blink = random.uniform(2.5, 6.0)

        self.anim_mgr.update(dt, self.width(), self.height(), self.pose.name)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 - 8.0 # Center offset

        # Physics Offset & Bounce
        float_y = math.sin(self.anim_time * 2.5) * 3.5
        shake_x = 0.0
        scale_x = 1.0
        scale_y = 1.0

        if self.pose == EmotionalPose.ANGRY:
            shake_x = math.sin(self.anim_time * 28.0) * 3.5
        elif self.pose in (EmotionalPose.EXCITED, EmotionalPose.CELEBRATION):
            bounce = abs(math.sin(self.anim_time * 7.0)) * 12.0
            float_y = -bounce
            if bounce < 2.0:
                scale_x = 1.08
                scale_y = 0.92

        # 1. Ground Drop Shadow
        painter.setPen(Qt.NoPen)
        shadow_w = 60.0 * scale_x
        shadow_h = 10.0
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawEllipse(QPointF(cx + shake_x, cy + 42), shadow_w / 2, shadow_h / 2)

        # 2. Draw Beanbag if Break Mode
        if self.pose == EmotionalPose.BREAK:
            AccessoryPainter.draw_beanbag_and_boba(painter, cx + shake_x, cy + 18)

        # 3. Draw Laptop/Desk if Typing/Coding/Focus
        if self.pose in (EmotionalPose.TYPING, EmotionalPose.CODING, EmotionalPose.FOCUSED) or self.is_in_focus:
            AccessoryPainter.draw_laptop_and_desk(painter, cx + shake_x, cy + 16, self.is_typing, self.anim_time)

        # Apply Transforms for Robot Body
        painter.save()
        painter.translate(cx + shake_x, cy + float_y)
        painter.scale(scale_x, scale_y)

        # 4. Draw Glossy 3D White Robot Head & Body
        # Head & Body Outer Shell
        shell_rect = QRectF(-35, -35, 70, 64)
        
        grad_body = QRadialGradient(0, -10, 45)
        grad_body.setColorAt(0.0, QColor("#FFFFFF"))
        grad_body.setColorAt(0.7, QColor("#F0F4F8"))
        grad_body.setColorAt(1.0, QColor("#D9E1E8"))

        painter.setPen(QPen(QColor(0, 0, 0, 25), 2.0))
        painter.setBrush(QBrush(grad_body))
        painter.drawRoundedRect(shell_rect, 32, 28)

        # Cat-like Robot Ears / Antennas
        ear_left = QPainterPath()
        ear_left.moveTo(-25, -28)
        ear_left.quadTo(-20, -42, -10, -32)
        ear_left.closeSubpath()
        painter.drawPath(ear_left)

        ear_right = QPainterPath()
        ear_right.moveTo(25, -28)
        ear_right.quadTo(20, -42, 10, -32)
        ear_right.closeSubpath()
        painter.drawPath(ear_right)

        # Floating Side Arms
        arm_y_off = math.sin(self.anim_time * 14.0) * 2.5 if self.is_typing else 0.0
        painter.setBrush(QBrush(grad_body))
        painter.drawEllipse(QPointF(-38, 2 + arm_y_off), 6.5, 9.5)
        painter.drawEllipse(QPointF(38, 2 - arm_y_off), 6.5, 9.5)

        # 5. Draw Black Glass LED Screen Face Plate
        screen_rect = QRectF(-27, -26, 54, 42)
        grad_screen = QLinearGradient(0, -26, 0, 16)
        grad_screen.setColorAt(0.0, QColor("#0D1117"))
        grad_screen.setColorAt(1.0, QColor("#161B22"))

        # LED Bezel Glow
        bezel_color = QColor("#00E5FF") if self.pose != EmotionalPose.ANGRY else QColor("#FF1744")
        painter.setPen(QPen(bezel_color, 1.8))
        painter.setBrush(QBrush(grad_screen))
        painter.drawRoundedRect(screen_rect, 18, 16)

        # Glass Glare Specular Highlight
        glare_path = QPainterPath()
        glare_path.moveTo(8, -24)
        glare_path.lineTo(23, -24)
        glare_path.lineTo(16, -14)
        glare_path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawPath(glare_path)

        # 6. Draw Glowing Neon LED Screen Expressions
        gaze_off = self.eye_tracker.get_eye_offset(max_offset_px=5.5)
        eye_l = QPointF(-12 + gaze_off.x(), -8 + gaze_off.y())
        eye_r = QPointF(12 + gaze_off.x(), -8 + gaze_off.y())

        led_color = QColor("#00F0FF") # Default cyan LED glow
        if self.pose in (EmotionalPose.ANGRY, EmotionalPose.CRYING):
            led_color = QColor("#FF1744")
        elif self.pose == EmotionalPose.EXCITED:
            led_color = QColor("#FFEA00")

        painter.setPen(QPen(led_color, 2.8, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)

        if self.is_blinking and self.pose != EmotionalPose.SLEEPY:
            # Horizontal LED blink lines
            painter.drawLine(int(eye_l.x() - 6), int(eye_l.y()), int(eye_l.x() + 6), int(eye_l.y()))
            painter.drawLine(int(eye_r.x() - 6), int(eye_r.y()), int(eye_r.x() + 6), int(eye_r.y()))

        elif self.pose in (EmotionalPose.HAPPY, EmotionalPose.CELEBRATION):
            # Curved happy LED eyes ^^
            path_l = QPainterPath()
            path_l.moveTo(eye_l.x() - 7, eye_l.y() + 2)
            path_l.quadTo(eye_l.x(), eye_l.y() - 6, eye_l.x() + 7, eye_l.y() + 2)
            painter.drawPath(path_l)

            path_r = QPainterPath()
            path_r.moveTo(eye_r.x() - 7, eye_r.y() + 2)
            path_r.quadTo(eye_r.x(), eye_r.y() - 6, eye_r.x() + 7, eye_r.y() + 2)
            painter.drawPath(path_r)

            # Mouth
            path_m = QPainterPath()
            path_m.moveTo(-5, 4)
            path_m.quadTo(0, 10, 5, 4)
            painter.drawPath(path_m)

        elif self.pose == EmotionalPose.EXCITED:
            # Star eyes ★ ★
            painter.setBrush(QBrush(QColor("#FFEA00")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(eye_l, 6, 6)
            painter.drawEllipse(eye_r, 6, 6)

            painter.setPen(QPen(QColor("#FFEA00"), 2.5))
            path_m = QPainterPath()
            path_m.moveTo(-6, 3)
            path_m.quadTo(0, 12, 6, 3)
            path_m.closeSubpath()
            painter.drawPath(path_m)

        elif self.pose == EmotionalPose.SLEEPY:
            # Closed line eyes
            painter.drawLine(int(eye_l.x() - 6), int(eye_l.y()), int(eye_l.x() + 6), int(eye_l.y()))
            painter.drawLine(int(eye_r.x() - 6), int(eye_r.y()), int(eye_r.x() + 6), int(eye_r.y()))
            painter.drawEllipse(QPointF(0, 5), 2.5, 2.5)

        elif self.pose == EmotionalPose.CRYING:
            # Crying drooping eyes + LED tear streams
            painter.drawLine(int(eye_l.x() - 6), int(eye_l.y() - 2), int(eye_l.x() + 6), int(eye_l.y() + 2))
            painter.drawLine(int(eye_r.x() - 6), int(eye_r.y() + 2), int(eye_r.x() + 6), int(eye_r.y() - 2))

            # Tear Streams
            painter.setPen(QPen(QColor("#00E5FF"), 3.0))
            painter.drawLine(int(eye_l.x()), int(eye_l.y() + 4), int(eye_l.x()), int(eye_l.y() + 18))
            painter.drawLine(int(eye_r.x()), int(eye_r.y() + 4), int(eye_r.x()), int(eye_r.y() + 18))

        elif self.pose == EmotionalPose.ANGRY:
            # Sharp angry LED eyebrows & eyes
            painter.drawLine(int(eye_l.x() - 7), int(eye_l.y() - 5), int(eye_l.x() + 5), int(eye_l.y() - 1))
            painter.drawLine(int(eye_r.x() + 7), int(eye_r.y() - 5), int(eye_r.x() - 5), int(eye_r.y() - 1))

            painter.setBrush(QBrush(QColor("#FF1744")))
            painter.drawEllipse(eye_l, 4.5, 4.5)
            painter.drawEllipse(eye_r, 4.5, 4.5)

        elif self.pose == EmotionalPose.SHOCKED:
            # Ring LED eyes O O
            painter.drawEllipse(eye_l, 6.5, 6.5)
            painter.drawEllipse(eye_r, 6.5, 6.5)
            painter.drawEllipse(QPointF(0, 5), 3, 4)

        else: # IDLE / FOCUSED / TYPING / CODING
            # Bright LED rounded rect eyes
            painter.setBrush(QBrush(led_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(eye_l.x() - 5, eye_l.y() - 5, 10, 10), 3, 3)
            painter.drawRoundedRect(QRectF(eye_r.x() - 5, eye_r.y() - 5, 10, 10), 3, 3)

            # Tiny smile
            painter.setPen(QPen(led_color, 2.0))
            painter.drawLine(-3, 5, 3, 5)

        # 7. Draw Accessories
        if self.pose in (EmotionalPose.FOCUSED, EmotionalPose.CODING) or self.is_in_focus:
            AccessoryPainter.draw_red_headband(painter, 0, -5)

        if self.pose in (EmotionalPose.TYPING, EmotionalPose.CODING):
            AccessoryPainter.draw_headphones(painter, 0, -5)

        if self.pose == EmotionalPose.CELEBRATION:
            AccessoryPainter.draw_glowsticks(painter, 0, 5, self.anim_time)

        painter.restore()

        # 8. Render Particle Effects
        self.anim_mgr.render(painter)

        # 9. Dark Pill Timer Badge Overlay underneath robot (matches reference)
        if self.timer_text:
            badge_rect = QRectF(cx - 38, h - 22, 76, 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0B0E14"))
            painter.drawRoundedRect(badge_rect, 9, 9)

            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignCenter, f"⏱ {self.timer_text}")
