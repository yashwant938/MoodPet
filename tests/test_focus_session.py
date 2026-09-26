import unittest
from datetime import datetime

from app.productivity.focus_session import FocusSessionManager


class FocusSessionManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = FocusSessionManager()

    def test_completion_is_reported_once_and_focus_time_is_capped(self):
        before = datetime.now()
        self.manager.start_focus(60)
        after = datetime.now()
        self.assertLessEqual(before, self.manager.focus_started_at)
        self.assertLessEqual(self.manager.focus_started_at, after)

        state = self.manager.tick(12.5)
        self.assertFalse(state["focus_finished"])
        self.assertEqual(state["timer_text"], "00:48")
        self.assertEqual(self.manager.focus_elapsed_sec, 12.5)

        state = self.manager.tick(100)
        self.assertTrue(state["focus_finished"])
        self.assertFalse(state["is_focus"])
        self.assertEqual(state["timer_text"], "00:00")
        self.assertEqual(self.manager.focus_elapsed_sec, 60)
        self.assertEqual(self.manager.focus_remaining_sec, 0)
        self.assertIsNotNone(self.manager.focus_started_at)
        self.assertFalse(self.manager.tick()["focus_finished"])

    def test_pause_preserves_focus_time_and_resume_continues_countdown(self):
        self.manager.start_focus(120)
        started_at = self.manager.focus_started_at
        self.manager.tick(20)
        self.assertTrue(self.manager.toggle_pause())
        state = self.manager.tick(500)
        self.assertTrue(state["is_focus"])
        self.assertTrue(state["is_paused"])
        self.assertFalse(state["focus_finished"])
        self.assertEqual(state["timer_text"], "01:40")
        self.assertEqual(self.manager.focus_elapsed_sec, 20)
        self.assertEqual(self.manager.focus_started_at, started_at)

        self.assertFalse(self.manager.toggle_pause())
        self.manager.tick(30)
        self.assertEqual(self.manager.focus_elapsed_sec, 50)
        self.assertEqual(self.manager.focus_remaining_sec, 70)

    def test_break_can_pause_and_completes_once(self):
        self.manager.start_break(10)
        self.assertEqual(self.manager.break_total_sec, 10)
        self.manager.toggle_pause()
        state = self.manager.tick(100)
        self.assertTrue(state["is_break"])
        self.assertTrue(state["is_paused"])
        self.assertEqual(state["timer_text"], "BREAK 00:10")
        self.manager.toggle_pause()
        state = self.manager.tick(10)
        self.assertTrue(state["break_finished"])
        self.assertFalse(state["is_break"])
        self.assertEqual(state["timer_text"], "BREAK 00:00")
        self.assertFalse(self.manager.tick()["break_finished"])

    def test_starting_other_timer_clears_previous_state_and_pause(self):
        self.manager.start_focus(120)
        self.manager.tick(45)
        self.manager.toggle_pause()
        self.manager.start_break()
        self.assertFalse(self.manager.is_focus_active)
        self.assertFalse(self.manager.is_paused)
        self.assertEqual(self.manager.focus_remaining_sec, 0)
        self.assertEqual(self.manager.focus_total_sec, 0)
        self.assertEqual(self.manager.focus_elapsed_sec, 0)
        self.assertIsNone(self.manager.focus_started_at)
        self.assertTrue(self.manager.is_break_active)
        self.assertEqual(self.manager.break_remaining_sec, 600)

        self.manager.toggle_pause()
        self.manager.start_focus(30)
        self.assertTrue(self.manager.is_focus_active)
        self.assertFalse(self.manager.is_paused)
        self.assertFalse(self.manager.is_break_active)
        self.assertEqual(self.manager.break_remaining_sec, 0)
        self.assertEqual(self.manager.break_total_sec, 0)
        self.assertEqual(self.manager.focus_remaining_sec, 30)

    def test_stop_resets_all_state_without_reporting_completion(self):
        for start in (self.manager.start_focus, self.manager.start_break):
            with self.subTest(start=start.__name__):
                start(30)
                self.manager.tick(10)
                self.manager.toggle_pause()
                self.manager.stop_all()
                self.assertEqual(self.manager.focus_total_sec, 0)
                self.assertEqual(self.manager.focus_remaining_sec, 0)
                self.assertEqual(self.manager.focus_elapsed_sec, 0)
                self.assertIsNone(self.manager.focus_started_at)
                self.assertEqual(self.manager.break_total_sec, 0)
                self.assertEqual(self.manager.break_remaining_sec, 0)
                self.assertFalse(self.manager.toggle_pause())
                self.assertEqual(self.manager.tick(), {
                    "is_focus": False,
                    "is_break": False,
                    "is_paused": False,
                    "timer_text": "",
                    "focus_finished": False,
                    "break_finished": False,
                })

    def test_invalid_duration_does_not_replace_active_timer(self):
        self.manager.start_focus(60)
        self.manager.tick(10)
        started_at = self.manager.focus_started_at
        for start in (self.manager.start_focus, self.manager.start_break):
            for duration in (0, -1, float("inf"), float("-inf"), float("nan")):
                with self.subTest(start=start.__name__, duration=duration):
                    with self.assertRaises(ValueError):
                        start(duration)
                    self.assertTrue(self.manager.is_focus_active)
                    self.assertEqual(self.manager.focus_remaining_sec, 50)
                    self.assertEqual(self.manager.focus_started_at, started_at)

    def test_invalid_elapsed_does_not_advance_timer(self):
        self.manager.start_focus(60)
        for elapsed in (-1, float("inf"), float("-inf"), float("nan")):
            with self.subTest(elapsed=elapsed):
                with self.assertRaises(ValueError):
                    self.manager.tick(elapsed)
                self.assertEqual(self.manager.focus_elapsed_sec, 0)
        self.assertEqual(self.manager.tick(0)["timer_text"], "01:00")
        self.assertEqual(self.manager.focus_remaining_sec, 60)


if __name__ == "__main__":
    unittest.main()
