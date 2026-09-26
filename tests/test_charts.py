"""Headless rendering/interaction regressions for the dashboard charts."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from datetime import date, timedelta
from unittest.mock import patch

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QFontDatabase, QMouseEvent
from PySide6.QtWidgets import QApplication

from app.ui.charts import ActivityChart, ActivityHeatmap, GoalRing


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Windows' offscreen Qt backend does not enumerate native fonts.
        for font in ("segoeui.ttf", "segoeuib.ttf"):
            path = f"C:/Windows/Fonts/{font}"
            if os.path.exists(path):
                QFontDatabase.addApplicationFont(path)

    def render(self, widget, width, height):
        self.addCleanup(widget.close)
        widget.resize(width, height)
        widget.show()
        self.app.processEvents()
        pixmap = widget.grab()
        self.assertFalse(pixmap.isNull())
        return pixmap

    @staticmethod
    def move(widget, point):
        event = QMouseEvent(QEvent.MouseMove, point, point,
                            Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        widget.mouseMoveEvent(event)

    def test_short_sessions_have_readable_second_and_minute_scales(self):
        chart = ActivityChart()
        self.addCleanup(chart.close)
        for maximum in (1, 15, 59, 60, 61, 119, 120, 121, 239, 240, 1800, 7200):
            scale = chart._scale(maximum)
            self.assertGreaterEqual(scale, maximum)
            # Every grid line is a whole number in the unit shown to the user.
            if scale <= 120:
                self.assertEqual((scale / 4) % 1, 0)
            elif scale < 7200:
                self.assertEqual((scale / 4) % 60, 0)

    def test_thirty_days_at_minimum_width_keep_last_day_hoverable(self):
        chart = ActivityChart()
        rows = [{"date": date.today() - timedelta(days=29 - index),
                 "productive_seconds": index * 61,
                 "distracted_seconds": 3, "idle_seconds": 4}
                for index in range(30)]
        chart.set_data(rows)
        self.render(chart, 350, 220)
        self.assertEqual(len(chart._hit_regions), 30)
        for region in chart._hit_regions:
            self.assertGreaterEqual(region.left(), 0)
            self.assertLessEqual(region.right(), chart.width())
            self.assertLessEqual(region.bottom(), chart.height())
        with patch("app.ui.charts.QToolTip.showText") as show:
            self.move(chart, chart._hit_regions[-1].center())
            tooltip = show.call_args.args[1]
            self.assertIn(date.today().strftime("%A, %d %B"), tooltip)
            self.assertIn("Productive: 29m 29s", tooltip)
            self.assertIn("Distracted: 3s", tooltip)
            self.assertIn("Idle: 4s", tooltip)
        # Changing the range clears old hit regions before the next paint.
        chart.set_data([])
        with patch("app.ui.charts.QToolTip.showText") as show:
            self.move(chart, QPointF(340, 100))
            show.assert_not_called()
        self.assertFalse(chart.grab().isNull())

    def test_heatmap_has_exactly_eighty_four_calendar_days_with_empty_day_details(self):
        chart = ActivityHeatmap()
        chart.set_data([])
        self.render(chart, 370, 216)
        dates = [day for _, day in chart._cells]
        self.assertEqual(len(dates), 84)
        self.assertEqual(len(set(dates)), 84)
        self.assertEqual(min(dates), date.today() - timedelta(days=83))
        self.assertEqual(max(dates), date.today())
        for rect, _ in chart._cells:
            self.assertGreaterEqual(rect.left(), 0)
            self.assertLessEqual(rect.right(), chart.width())
            self.assertLessEqual(rect.bottom(), chart.height())
        today_cell = next(rect for rect, day in chart._cells if day == date.today())
        with patch("app.ui.charts.QToolTip.showText") as show:
            self.move(chart, today_cell.center())
            self.assertIn("Productive: 0s", show.call_args.args[1])

    def test_invalid_legacy_durations_do_not_break_charts_or_goal_progress(self):
        chart = ActivityChart()
        chart.set_data([
            {"date": date.today(), "productive_seconds": float("nan"), "idle_seconds": -12},
            {"date": date.today(), "productive_seconds": 61, "distracted_seconds": "bad"},
            {"date": "not-a-date", "productive_seconds": 9000},
        ])
        self.render(chart, 350, 220)
        with patch("app.ui.charts.QToolTip.showText") as show:
            self.move(chart, chart._hit_regions[0].center())
            self.assertIn("Productive: 1m 1s", show.call_args.args[1])
            self.assertIn("Idle: 0s", show.call_args.args[1])
        ring = GoalRing()
        ring.set_progress(float("inf"), 0)
        self.render(ring, 142, 164)
        self.assertIn("0s of 1s", ring.toolTip())
        ring.set_progress(8200, 7200)
        self.assertFalse(ring.grab().isNull())
        self.assertIn("2h 16m 40s of 2h", ring.toolTip())


if __name__ == "__main__":
    unittest.main()
