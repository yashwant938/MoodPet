import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

class AccessoryPainter:
    """Renders accessories matching the exact reference specification image."""

    @staticmethod
    def draw_red_headband(painter: QPainter, head_cx: float, head_cy: float):
        """Draws red headband with '集中' (Concentrate) text."""
        band_rect = QRectF(head_cx - 28, head_cy - 28, 56, 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#D32F2F"))
        painter.drawRoundedRect(band_rect, 3, 3)

        # Headband ribbon tails on right side
        tail = QPainterPath()
        tail.moveTo(head_cx + 28, head_cy - 26)
        tail.lineTo(head_cx + 38, head_cy - 18)
        tail.lineTo(head_cx + 34, head_cy - 12)
        tail.lineTo(head_cx + 28, head_cy - 20)
        tail.closeSubpath()
        painter.drawPath(tail)

        # White Kanji Text: 集中
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Yu Gothic", 7, QFont.Bold)
        painter.setFont(font)
        painter.drawText(band_rect, Qt.AlignCenter, "集中")

    @staticmethod
    def draw_headphones(painter: QPainter, head_cx: float, head_cy: float):
        """Draws dark blue tech headphones 🎧 over robot head."""
        # Headband arc
        path = QPainterPath()
        path.moveTo(head_cx - 30, head_cy - 12)
        path.quadTo(head_cx, head_cy - 44, head_cx + 30, head_cy - 12)
        painter.setPen(QPen(QColor("#263238"), 4.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Earcups
        painter.setPen(QPen(QColor("#37474F"), 1.5))
        painter.setBrush(QColor("#1A237E"))
        painter.drawRoundedRect(QRectF(head_cx - 35, head_cy - 18, 9, 20), 4, 4)
        painter.drawRoundedRect(QRectF(head_cx + 26, head_cy - 18, 9, 20), 4, 4)

    @staticmethod
    def draw_laptop_and_desk(painter: QPainter, cx: float, cy: float, is_typing: bool, anim_time: float):
        """Draws open laptop with GitHub/Python sticker logos and glowing keyboard."""
        # Laptop base / keyboard
        base_rect = QRectF(cx - 24, cy + 18, 48, 8)
        painter.setPen(QPen(QColor("#263238"), 1.0))
        painter.setBrush(QColor("#37474F"))
        painter.drawRoundedRect(base_rect, 2, 2)

        # Open Screen Lid
        lid_rect = QRectF(cx - 22, cy + 2, 44, 16)
        painter.setBrush(QColor("#1C2026"))
        painter.drawRoundedRect(lid_rect, 2, 2)

        # Screen Code Lines
        painter.setPen(QPen(QColor("#00E5FF"), 1.2))
        painter.drawLine(int(cx - 18), int(cy + 6), int(cx - 5), int(cy + 6))
        painter.setPen(QPen(QColor("#FF4081"), 1.2))
        painter.drawLine(int(cx - 18), int(cy + 10), int(cx + 8), int(cy + 10))
        painter.setPen(QPen(QColor("#76FF03"), 1.2))
        painter.drawLine(int(cx - 18), int(cy + 14), int(cx - 2), int(cy + 14))

        # Keypress LED flashes when typing
        if is_typing:
            painter.setPen(Qt.NoPen)
            for i in range(4):
                kx = cx - 16 + i * 8
                ky = cy + 20
                if int(anim_time * 15 + i) % 2 == 0:
                    painter.setBrush(QColor("#80DEEA"))
                    painter.drawRect(QRectF(kx, ky, 5, 3))

    @staticmethod
    def draw_beanbag_and_boba(painter: QPainter, cx: float, cy: float):
        """Draws cozy navy beanbag 🛋️ and boba tea 🧋 for Break Mode."""
        # Beanbag base
        bag_rect = QRectF(cx - 42, cy + 10, 84, 30)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1A237E"))
        painter.drawRoundedRect(bag_rect, 15, 15)

        # Boba Tea Cup
        boba_rect = QRectF(cx + 25, cy + 8, 12, 18)
        painter.setPen(QPen(QColor("#795548"), 1.0))
        painter.setBrush(QColor("#D7CCC8"))
        painter.drawRoundedRect(boba_rect, 3, 3)

        # Straw
        painter.setPen(QPen(QColor("#FF4081"), 2.0))
        painter.drawLine(int(cx + 31), int(cy + 8), int(cx + 34), int(cy + 1))

    @staticmethod
    def draw_glowsticks(painter: QPainter, cx: float, cy: float, anim_time: float):
        """Draws glowing glowsticks for Celebration mode."""
        # Left Glowstick
        painter.save()
        painter.translate(cx - 28, cy - 5)
        painter.rotate(-20 + math.sin(anim_time * 10) * 15)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#00E5FF"))
        painter.drawRoundedRect(QRectF(-2, -12, 4, 20), 2, 2)
        painter.restore()

        # Right Glowstick
        painter.save()
        painter.translate(cx + 28, cy - 5)
        painter.rotate(20 - math.sin(anim_time * 10) * 15)
        painter.setBrush(QColor("#FF4081"))
        painter.drawRoundedRect(QRectF(-2, -12, 4, 20), 2, 2)
        painter.restore()
