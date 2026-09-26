"""Windows idle-clock regressions without reading real keyboard/mouse activity."""

import ctypes
import unittest
from unittest.mock import Mock, patch

from app.monitor.activity_tracker import ActivityTracker, LASTINPUTINFO


class ActivityTrackerTests(unittest.TestCase):
    def setUp(self):
        self.user32 = Mock()
        self.kernel32 = Mock()
        patcher = patch("app.monitor.activity_tracker.ctypes.windll")
        windll = patcher.start()
        self.addCleanup(patcher.stop)
        windll.user32 = self.user32
        windll.kernel32 = self.kernel32
        self.tracker = ActivityTracker()

    def set_clock(self, current_tick, last_input_tick):
        self.kernel32.GetTickCount64.return_value = current_tick

        def get_last_input_info(pointer):
            info = pointer._obj
            self.assertEqual(info.cbSize, ctypes.sizeof(LASTINPUTINFO))
            info.dwTime = last_input_tick
            return 1

        self.user32.GetLastInputInfo.side_effect = get_last_input_info

    def test_system_uptime_api_preserves_unsigned_64_bit_return_value(self):
        self.assertIs(self.kernel32.GetTickCount64.restype, ctypes.c_ulonglong)

    def test_normal_uptime_returns_fractional_seconds(self):
        self.set_clock(current_tick=123_456_789, last_input_tick=123_454_289)
        self.assertEqual(self.tracker.get_system_idle_seconds(), 2.5)
        self.user32.GetLastInputInfo.assert_called_once()
        self.kernel32.GetTickCount64.assert_called_once_with()

    def test_long_uptime_uses_the_same_32_bit_clock_as_last_input(self):
        self.set_clock(current_tick=3 * (1 << 32) + 54_321, last_input_tick=50_321)
        self.assertEqual(self.tracker.get_system_idle_seconds(), 4.0)

    def test_last_input_before_clock_rollover_keeps_short_idle_duration(self):
        self.set_clock(current_tick=(1 << 32) + 1_500, last_input_tick=(1 << 32) - 2_500)
        self.assertEqual(self.tracker.get_system_idle_seconds(), 4.0)

    def test_failed_last_input_query_returns_zero_without_reading_uptime(self):
        self.user32.GetLastInputInfo.return_value = 0
        self.assertEqual(self.tracker.get_system_idle_seconds(), 0.0)
        self.kernel32.GetTickCount64.assert_not_called()


if __name__ == "__main__":
    unittest.main()
