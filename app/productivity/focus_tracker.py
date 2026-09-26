"""Activity accounting and automatic focus-block tracking."""

import math
import time

from app.storage.database import DatabaseManager
from app.productivity.score_engine import ProductivityState


class FocusTracker:
    """Track activity, notify once at a milestone, and persist blocks once."""

    MIN_SESSION_SECONDS = 5 * 60

    def __init__(self, db: DatabaseManager, target_milestone_sec: int = 1800):
        self.db = db
        self.target_milestone_sec = max(1, int(target_milestone_sec))
        self.current_focus_start = None
        self.current_focus_seconds = 0.0
        self._last_focus_end = None
        self.milestone_reached_this_session = False
        self._seconds_remainders = {"productive": 0.0, "distracted": 0.0, "idle": 0.0}
        self.current_streak = self.db.get_streaks()["current_streak"]

    def _add_activity(self, category, elapsed):
        self._seconds_remainders[category] += elapsed
        seconds = int(self._seconds_remainders[category] + 1e-9)
        self._seconds_remainders[category] = max(0.0, self._seconds_remainders[category] - seconds)
        if seconds:
            self.db.update_today_seconds(**{f"{category}_delta": seconds})

    def update(self, state: ProductivityState, elapsed_interval_sec: float = 1.0, record_sessions: bool = True) -> dict:
        """Account for a tick and return display values and milestone events.

        Manual focus timers pass ``record_sessions=False``. Activity counters
        still advance, but the timer owns its session record and celebration.
        A productive block ends when activity leaves the productive state.
        """
        elapsed = float(elapsed_interval_sec)
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Elapsed time must be finite and nonnegative")
        milestone_triggered = False
        milestone_message = ""

        if state == ProductivityState.PRODUCTIVE:
            self._add_activity("productive", elapsed)
        elif state == ProductivityState.DISTRACTING:
            self._add_activity("distracted", elapsed)
        elif state in (ProductivityState.IDLE, ProductivityState.LONG_IDLE):
            self._add_activity("idle", elapsed)

        if not record_sessions or state != ProductivityState.PRODUCTIVE:
            if self.current_focus_start is not None:
                self.finish_current_session()
        elif elapsed > 0:
            now = time.time()
            if self.current_focus_start is None:
                self.current_focus_start = now - elapsed
                self.milestone_reached_this_session = False
            self.current_focus_seconds += elapsed
            self._last_focus_end = now
            if self.current_focus_seconds >= self.target_milestone_sec and not self.milestone_reached_this_session:
                self.milestone_reached_this_session = True
                milestone_triggered = True
                mins = int(self.current_focus_seconds // 60)
                milestone_message = f"{mins} minutes focused! You're on a roll!"

        today_stats = self.db.get_today_stats()
        self.current_streak = self.db.get_streaks()["current_streak"]
        return {
            "current_focus_seconds": int(self.current_focus_seconds),
            "milestone_triggered": milestone_triggered,
            "milestone_message": milestone_message,
            "current_streak": self.current_streak,
            "productive_seconds_today": today_stats["productive_seconds"],
            "distracted_seconds_today": today_stats["distracted_seconds"],
            "idle_seconds_today": today_stats["idle_seconds"],
            "focus_sessions_today": today_stats["focus_sessions_count"],
            "longest_session_today": today_stats["longest_session_seconds"],
        }

    def finish_current_session(self):
        """Flush an automatic block once; safe to call again or on shutdown."""
        recorded_id = None
        duration = int(self.current_focus_seconds)
        if self.current_focus_start is not None and duration >= min(self.MIN_SESSION_SECONDS, self.target_milestone_sec):
            recorded_id = self.db.record_focus_session(
                duration_seconds=duration,
                completed=self.current_focus_seconds >= self.target_milestone_sec,
                start_time=self.current_focus_start,
                end_time=self._last_focus_end,
                source="automatic",
            )
        self._reset_block()
        self.current_streak = self.db.get_streaks()["current_streak"]
        return recorded_id

    def _reset_block(self):
        self.current_focus_start = None
        self.current_focus_seconds = 0.0
        self._last_focus_end = None
        self.milestone_reached_this_session = False

    def reset_current_session(self):
        """Discard uncommitted focus and fractions after an explicit reset."""
        self._reset_block()
        self._seconds_remainders = dict.fromkeys(self._seconds_remainders, 0.0)
        self.current_streak = self.db.get_streaks()["current_streak"]

    @staticmethod
    def format_time(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hrs, mins = seconds // 3600, (seconds % 3600) // 60
        return f"{hrs}h {mins}m" if hrs else f"{mins}m"
