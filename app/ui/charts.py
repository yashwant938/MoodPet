"""Small, dependency-free charts for MoodPet's activity dashboard.

All widgets accept plain dictionaries so the UI never needs a database handle.
Dates may be ISO strings, ``date`` objects, or ``datetime`` objects. Durations
are expressed in seconds. The charts deliberately leave titles to their cards.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget


INK = QColor("#182424")
MUTED = QColor("#738079")
GRID = QColor("#E9EEEB")
PRODUCTIVE = QColor("#237A57")
DISTRACTED = QColor("#E9AA75")
IDLE = QColor("#DAE2DD")
HEAT_COLORS = ("#EDF1EE", "#D3EADB", "#95CDB0", "#59A47E", "#237A57")


def _seconds(value) -> float:
    try:
        number = float(value or 0)
        return max(0.0, number) if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _rows(rows) -> list[dict]:
    """Sanitize values and merge duplicate dates into a stable daily series."""
    days = {}
    for row in rows or []:
        day = _date(row.get("date"))
        if day is None:
            continue
        entry = days.setdefault(day, {"date": day, "productive_seconds": 0.0,
                                      "distracted_seconds": 0.0, "idle_seconds": 0.0})
        for key in ("productive_seconds", "distracted_seconds", "idle_seconds"):
            entry[key] += _seconds(row.get(key))
    return [days[day] for day in sorted(days)]


def _duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    pieces = []
    if hours:
        pieces.append(f"{hours}h")
    if minutes:
        pieces.append(f"{minutes}m")
    if seconds or not pieces:
        pieces.append(f"{seconds}s")
    return " ".join(pieces)


def _font(size: int = 9, bold: bool = False) -> QFont:
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    return font


class ActivityChart(QWidget):
    """Daily stacked activity bars with a built-in legend and hover details.

    ``set_data(rows)`` accepts any length; 7 and 30 daily rows are ideal. Pass
    zero-filled daily rows to retain dates when a period has no activity.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._hit_regions = []
        self._hover_index = -1
        self.setMouseTracking(True)
        self.setMinimumSize(350, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName("Daily activity chart")
        self.setAccessibleDescription("Daily productive, distracted, and idle time. Hover over a day for exact durations.")

    def sizeHint(self):
        return QSize(640, 240)

    def set_data(self, rows):
        self._rows = _rows(rows)
        self._hover_index = -1
        self._hit_regions = []
        total = sum(row["productive_seconds"] for row in self._rows)
        self.setAccessibleDescription(
            f"{len(self._rows)} days, {_duration(total)} productive time. "
            "Hover over a day for productive, distracted, and idle durations."
        )
        self.update()

    @staticmethod
    def _scale(maximum):
        # Four horizontal divisions with human-friendly minute/hour values.
        if maximum <= 60:
            return 60.0
        if maximum <= 120:
            return 120.0
        target = maximum / 4
        # On longer days, align grid divisions to whole quarter-hours.
        if maximum > 1800:
            step = math.ceil(target / 900) * 900
        else:
            step = math.ceil(target / 60) * 60
        return step * 4

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(_font())
        metrics = painter.fontMetrics()

        legend_x = 4.0
        for label, color in (("Productive", PRODUCTIVE), ("Distracted", DISTRACTED), ("Idle", IDLE)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QRectF(legend_x, 8, 7, 7))
            painter.setPen(MUTED)
            painter.drawText(QPointF(legend_x + 13, 16), label)
            legend_x += 13 + metrics.horizontalAdvance(label) + 22

        plot = QRectF(43, 38, max(1, self.width() - 51), max(1, self.height() - 76))
        totals = [sum(row[key] for key in ("productive_seconds", "distracted_seconds", "idle_seconds"))
                  for row in self._rows]
        maximum = max(totals, default=0)
        scale = self._scale(maximum or 3600)
        for tick in range(5):
            seconds = scale * tick / 4
            y = plot.bottom() - plot.height() * tick / 4
            painter.setPen(QPen(GRID, 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(MUTED)
            label = (f"{seconds / 3600:g}h" if scale >= 7200 else
                     f"{seconds / 60:g}m" if scale > 120 else f"{seconds:g}s")
            if not tick:
                label = "0"
            painter.drawText(QRectF(0, y - 9, 34, 18), Qt.AlignRight | Qt.AlignVCenter, label)

        self._hit_regions = []
        count = len(self._rows)
        if count:
            slot = plot.width() / count
            bar_width = min(35.0, slot * (0.52 if count <= 7 else 0.64))
            label_every = 1 if count <= 7 else max(1, math.ceil(count / max(2, int(plot.width() / 62))))
            label_distance = max(2, math.ceil(54 / slot))
            for index, (row, total) in enumerate(zip(self._rows, totals)):
                center_x = plot.left() + slot * (index + 0.5)
                hit = QRectF(plot.left() + slot * index, plot.top(), slot, plot.height())
                self._hit_regions.append(hit)
                if index == self._hover_index:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor("#F0F5F2"))
                    painter.drawRoundedRect(hit.adjusted(1, -6, -1, 0), 5, 5)
                height = total / scale * plot.height()
                if total > 0:
                    outline = QPainterPath()
                    outline.addRoundedRect(QRectF(center_x - bar_width / 2, plot.bottom() - height,
                                                   bar_width, height), min(5, bar_width / 2), 5)
                    painter.save()
                    painter.setClipPath(outline)
                    y_bottom = plot.bottom()
                    for key, color in (("productive_seconds", PRODUCTIVE), ("distracted_seconds", DISTRACTED), ("idle_seconds", IDLE)):
                        segment_height = row[key] / scale * plot.height()
                        painter.fillRect(QRectF(center_x - bar_width / 2, y_bottom - segment_height,
                                               bar_width, segment_height + 0.3), color)
                        y_bottom -= segment_height
                    painter.restore()
                else:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(GRID)
                    painter.drawRoundedRect(QRectF(center_x - bar_width / 2, plot.bottom() - 3,
                                                   bar_width, 3), 1.5, 1.5)
                # Reserve the final label and suppress a nearby tick to prevent overlap.
                show_tick = index == count - 1 or (index % label_every == 0 and
                            (count <= 7 or index <= count - 1 - label_distance))
                if show_tick:
                    painter.setPen(INK if row["date"] == date.today() else MUTED)
                    label = row["date"].strftime("%a") if count <= 7 else row["date"].strftime("%d %b")
                    label_left = min(max(0, center_x - 27), self.width() - 54)
                    painter.drawText(QRectF(label_left, plot.bottom() + 11, 54, 20), Qt.AlignCenter, label)

        if not maximum:
            # A solid panel keeps the empty-state copy readable over the grid.
            message = QRectF(plot.center().x() - 135, plot.center().y() - 31, 270, 62)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawRoundedRect(message, 10, 10)
            painter.setFont(_font(11, True))
            painter.setPen(INK)
            painter.drawText(message.adjusted(0, 4, 0, -30), Qt.AlignCenter, "Your story starts here")
            painter.setFont(_font(9))
            painter.setPen(MUTED)
            painter.drawText(message.adjusted(0, 31, 0, -3), Qt.AlignCenter, "Activity will appear as you use your computer.")

    def mouseMoveEvent(self, event):
        index = next((i for i, region in enumerate(self._hit_regions)
                      if region.contains(event.position())), -1)
        if index != self._hover_index:
            self._hover_index = index
            self.update()
        if index >= 0:
            row = self._rows[index]
            text = (f"{row['date'].strftime('%A, %d %B')}\n"
                    f"Productive: {_duration(row['productive_seconds'])}\n"
                    f"Distracted: {_duration(row['distracted_seconds'])}\n"
                    f"Idle: {_duration(row['idle_seconds'])}")
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)


class ActivityHeatmap(QWidget):
    """The last 84 calendar days, shaded by productive time.

    Cells use fixed thresholds (positive time, 30, 60, 120 minutes), so a color keeps its
    meaning as the user's activity changes. Missing days are empty cells.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days = {}
        self._cells = []
        self._hover_day = None
        self.setMouseTracking(True)
        self.setMinimumSize(370, 216)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAccessibleName("Twelve week activity calendar")
        self.setAccessibleDescription("The last 84 days. Darker green means more productive time. Hover over a day for details.")

    def sizeHint(self):
        return QSize(560, 224)

    def set_data(self, rows):
        self._days = {row["date"]: row for row in _rows(rows)}
        self._cells = []
        self._hover_day = None
        self.update()

    @staticmethod
    def _level(seconds):
        if seconds <= 0:
            return 0
        return 1 if seconds < 1800 else 2 if seconds < 3600 else 3 if seconds < 7200 else 4

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(_font(8))
        today = date.today()
        start = today - timedelta(days=83)
        grid_start = start - timedelta(days=start.weekday())
        columns = (today - grid_start).days // 7 + 1
        gap = 5.0
        size = min(21.0, (self.width() - 48 - (columns - 1) * gap) / columns,
                   (self.height() - 59 - 6 * gap) / 7)
        size = max(8.0, size)
        step = size + gap
        left = 37.0
        top = 27.0
        self._cells = []

        painter.setPen(MUTED)
        for weekday, label in ((0, "M"), (2, "W"), (4, "F")):
            painter.drawText(QRectF(0, top + weekday * step, 26, size), Qt.AlignRight | Qt.AlignVCenter, label)

        last_month = None
        for column in range(columns):
            week = grid_start + timedelta(days=column * 7)
            label_day = max(week, start)
            if label_day.month != last_month:
                painter.setPen(MUTED)
                painter.drawText(QRectF(left + column * step, 0, 44, 20), Qt.AlignLeft | Qt.AlignVCenter,
                                 label_day.strftime("%b"))
                last_month = label_day.month
            for weekday in range(7):
                day = week + timedelta(days=weekday)
                if not start <= day <= today:
                    continue
                seconds = self._days.get(day, {}).get("productive_seconds", 0)
                rect = QRectF(left + column * step, top + weekday * step, size, size)
                self._cells.append((rect, day))
                painter.setBrush(QColor(HEAT_COLORS[self._level(seconds)]))
                if day == self._hover_day:
                    painter.setPen(QPen(INK, 1.5))
                elif day == today:
                    painter.setPen(QPen(QColor("#83A490"), 1.2))
                else:
                    painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect, 3.5, 3.5)

        legend_y = top + 7 * step + 9
        painter.setPen(MUTED)
        painter.drawText(QRectF(left, legend_y - 2, 54, 16), Qt.AlignLeft | Qt.AlignVCenter, "Less")
        legend_x = left + 31
        for index, color in enumerate(HEAT_COLORS):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(legend_x + index * 16, legend_y, 11, 11), 2.5, 2.5)
        painter.setPen(MUTED)
        painter.drawText(QRectF(legend_x + 83, legend_y - 2, 145, 16), Qt.AlignLeft | Qt.AlignVCenter,
                         "More productive time")

    def mouseMoveEvent(self, event):
        day = next((day for rect, day in self._cells if rect.contains(event.position())), None)
        if day != self._hover_day:
            self._hover_day = day
            self.update()
        if day is not None:
            row = self._days.get(day, {})
            text = (f"{day.strftime('%A, %d %B %Y')}\n"
                    f"Productive: {_duration(row.get('productive_seconds', 0))}\n"
                    f"Distracted: {_duration(row.get('distracted_seconds', 0))}\n"
                    f"Idle: {_duration(row.get('idle_seconds', 0))}")
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_day = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)


class GoalRing(QWidget):
    """A daily productive-time goal with percentage and minutes remaining."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0.0
        self._target = 7200.0
        self.setMinimumSize(142, 164)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAccessibleName("Daily goal progress")
        self.set_progress(0, self._target)

    def sizeHint(self):
        return QSize(174, 186)

    def set_progress(self, current_seconds, target_seconds):
        self._current = _seconds(current_seconds)
        self._target = max(1.0, _seconds(target_seconds))
        description = f"{_duration(self._current)} of {_duration(self._target)} daily goal"
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        diameter = max(64.0, min(self.width() - 24, self.height() - 43, 152))
        ring = QRectF((self.width() - diameter) / 2, 8, diameter, diameter)
        pen = QPen(QColor("#E8F0EA"), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(ring)
        progress = min(1.0, self._current / self._target)
        if progress:
            pen.setColor(PRODUCTIVE)
            painter.setPen(pen)
            painter.drawArc(ring, 90 * 16, -round(progress * 360 * 16))
        percentage = int(self._current / self._target * 100)
        painter.setFont(_font(24 if percentage < 1000 else 20, True))
        painter.setPen(INK)
        painter.drawText(ring.adjusted(0, -9, 0, -9), Qt.AlignCenter, f"{percentage}%")
        painter.setFont(_font(8, True))
        painter.setPen(PRODUCTIVE if progress >= 1 else MUTED)
        painter.drawText(ring.adjusted(0, 41, 0, 0), Qt.AlignCenter,
                         "GOAL COMPLETE" if progress >= 1 else "OF DAILY GOAL")
        painter.setFont(_font(9))
        painter.setPen(MUTED)
        remaining = max(0, math.ceil((self._target - self._current) / 60))
        caption = "Every minute adds up" if progress >= 1 else f"{remaining} min to go"
        painter.drawText(QRectF(0, ring.bottom() + 13, self.width(), 19), Qt.AlignCenter, caption)
