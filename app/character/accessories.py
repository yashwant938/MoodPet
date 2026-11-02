import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

class AccessoryPainter:
    """Renders accessories matching the exact reference specification image."""

    @staticmethod
    def draw_evolution(painter, stage, minor, color, phase):
        """Ten original stage silhouettes; no sprite or platform emoji dependency."""
        painter.save()
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(QColor(color))
        if stage == 0:
            painter.drawLine(0,-34,0,-45)
            painter.drawEllipse(QRectF(0,-49,12,7))
        elif stage == 1:
            painter.drawRoundedRect(QRectF(31,-14,16,29),5,5)
            painter.setPen(QPen(QColor('#86664F'),3)); painter.drawLine(32,-8,44,-8)
        elif stage == 2:
            painter.drawPie(QRectF(-29,-50,58,30),0,180*16)
            painter.drawRoundedRect(QRectF(-33,-38,66,6),3,3)
            painter.setPen(QPen(QColor('#FFF3D9'),3)); painter.drawLine(0,-48,0,-37)
        elif stage == 3:
            for x in (-44,32):
                painter.drawRoundedRect(QRectF(x,-2,12,17),4,4)
            painter.drawEllipse(QRectF(-5,-44,10,12))
        elif stage == 4:
            path=QPainterPath(QPointF(32,-5))
            for x,y in ((49,0),(46,18),(39,24),(30,14)):
                path.lineTo(x,y)
            path.closeSubpath(); painter.drawPath(path)
            painter.setPen(QPen(QColor('white'),2)); painter.drawLine(39,2,39,15)
        elif stage == 5:
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(-38,-39,76,70),33,30)
            painter.drawLine(-15,-36,0,-53); painter.drawLine(0,-53,15,-36)
        elif stage == 6:
            for sign in (-1,1):
                for i in range(4):
                    painter.drawEllipse(QRectF(sign*(20+i*5)-4,-39+i*7,9,5))
        elif stage == 7:
            for sign in (-1,1):
                path=QPainterPath(QPointF(sign*34,10))
                for x,y in ((57,-25),(51,8),(40,22)):
                    path.lineTo(sign*x,y)
                path.closeSubpath(); painter.drawPath(path)
        elif stage == 8:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(-28,-54,56,12))
            painter.drawEllipse(QPointF(math.cos(phase)*28,-48+math.sin(phase)*5),3,3)
        elif stage == 9:
            path=QPainterPath(QPointF(-24,-36))
            for x,y in ((-27,-52),(-12,-44),(0,-58),(12,-44),(27,-52),(24,-36)):
                path.lineTo(x,y)
            path.closeSubpath(); painter.drawPath(path)
            painter.setBrush(QColor('white')); painter.drawEllipse(QPointF(0,-43),3,3)
        elif stage == 10:
            painter.drawRoundedRect(QRectF(-28,18,56,8),3,3)
            path=QPainterPath(QPointF(20,20)); path.lineTo(42,32); path.lineTo(32,36); path.lineTo(16,24); path.closeSubpath()
            painter.drawPath(path)
        elif stage == 11:
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(-30,-20,60,17),7,7)
            painter.drawEllipse(QPointF(19,-11),5,5)
            painter.drawLine(19,-18,19,-4)
        elif stage == 12:
            for sign in (-1,1):
                painter.drawRoundedRect(QRectF(sign*42-8,-4,16,21),5,5)
                painter.setPen(QPen(QColor('white'),1.5)); painter.drawLine(sign*42,-1,sign*42,10)
                painter.setPen(QPen(QColor(color),2))
        elif stage == 13:
            for sign in (-1,1):
                path=QPainterPath(QPointF(sign*12,-34))
                path.lineTo(sign*21,-55); path.lineTo(sign*28,-34); path.closeSubpath(); painter.drawPath(path)
        elif stage == 14:
            painter.drawRoundedRect(QRectF(33,-12,16,32),3,3)
            painter.setPen(QPen(QColor('#F8F0D5'),4))
            painter.drawLine(32,-12,50,-12); painter.drawLine(32,20,50,20)
            painter.setPen(QPen(QColor('#476F53'),1.5)); painter.drawLine(37,-3,45,-3); painter.drawLine(37,3,45,3)
        elif stage == 15:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(-20,-56,40,14))
            for i in range(7):
                angle=i*math.pi/6
                painter.drawLine(QPointF(math.cos(angle)*26,-48-math.sin(angle)*15),QPointF(math.cos(angle)*33,-48-math.sin(angle)*20))
        elif stage == 16:
            for sign in (-1,1):
                for i in range(3):
                    path=QPainterPath(QPointF(sign*34,15-i*7))
                    path.lineTo(sign*(54-i*5),-25-i*7); path.lineTo(sign*43,16-i*7); path.closeSubpath(); painter.drawPath(path)
        elif stage == 17:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(-49,-16,98,30))
            painter.drawEllipse(QRectF(-40,-25,80,48))
            painter.setBrush(QColor(color)); painter.drawEllipse(QPointF(48,0),3,3)
        elif stage == 18:
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(-17,17,20,12)); painter.drawEllipse(QRectF(-3,17,20,12))
            painter.drawEllipse(QRectF(-25,-50,50,10))
        else:
            path=QPainterPath(QPointF(-25,-35))
            for x,y in ((-31,-50),(-16,-44),(-12,-57),(0,-45),(12,-57),(16,-44),(31,-50),(25,-35)):
                path.lineTo(x,y)
            path.closeSubpath(); painter.drawPath(path)
            painter.setBrush(QColor('white'))
            for x in (-12,0,12): painter.drawEllipse(QPointF(x,-39),2.5,2.5)
        if minor >= 1:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            for x in (-20,0,20):
                painter.drawEllipse(QPointF(x,23),1.8,1.8)
        if minor >= 2:
            for i in range(3):
                angle=phase*0.7+i*math.tau/3
                painter.drawEllipse(QPointF(math.cos(angle)*49,math.sin(angle)*33-6),2,2)
        painter.restore()

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
