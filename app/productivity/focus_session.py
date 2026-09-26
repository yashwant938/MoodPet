"""Focus and break countdowns driven by elapsed time supplied by the UI."""

from datetime import datetime
import math


class FocusSessionManager:
    """Manage one pausable countdown and report each completion exactly once."""

    def __init__(self):
        self.stop_all()

    @property
    def focus_elapsed_sec(self) -> float:
        """Time spent focusing, excluding pauses and countdown overshoot."""
        return self.focus_total_sec - self.focus_remaining_sec

    @staticmethod
    def _validate_duration(duration_sec: float):
        if not math.isfinite(duration_sec) or duration_sec <= 0:
            raise ValueError("Timer duration must be a finite positive number.")

    def start_focus(self, duration_sec: float):
        self._validate_duration(duration_sec)
        self.stop_all()
        self.is_focus_active = True
        self.focus_total_sec = duration_sec
        self.focus_remaining_sec = duration_sec
        self.focus_started_at = datetime.now()

    def start_break(self, duration_sec: float = 600):
        self._validate_duration(duration_sec)
        self.stop_all()
        self.is_break_active = True
        self.break_total_sec = duration_sec
        self.break_remaining_sec = duration_sec

    def stop_all(self):
        self.is_focus_active = False
        self.focus_remaining_sec = 0
        self.focus_total_sec = 0
        self.focus_started_at: datetime | None = None
        self.is_break_active = False
        self.break_remaining_sec = 0
        self.break_total_sec = 0
        self.is_paused = False

    def toggle_pause(self) -> bool:
        """Pause or resume an active countdown; an idle timer stays unpaused."""
        if self.is_focus_active or self.is_break_active:
            self.is_paused = not self.is_paused
        return self.is_paused

    @staticmethod
    def _format_remaining(remaining_sec: float, prefix: str = "") -> str:
        # Keep a positive fractional second visible until the timer finishes.
        mins, secs = divmod(math.ceil(remaining_sec), 60)
        return f"{prefix}{mins:02d}:{secs:02d}"

    def tick(self, elapsed_sec: float = 1.0) -> dict:
        """Advance the active timer, retaining completed focus data for logging.

        Paused time and elapsed time beyond completion are never counted as
        focus time. The caller decides how to measure time across system sleep.
        """
        if not math.isfinite(elapsed_sec) or elapsed_sec < 0:
            raise ValueError("Elapsed time must be a finite nonnegative number.")

        focus_finished = False
        break_finished = False
        timer_text = ""

        if self.is_focus_active:
            if not self.is_paused:
                self.focus_remaining_sec = max(0.0, self.focus_remaining_sec - elapsed_sec)
            timer_text = self._format_remaining(self.focus_remaining_sec)
            if self.focus_remaining_sec <= 0:
                self.is_focus_active = False
                focus_finished = True

        elif self.is_break_active:
            if not self.is_paused:
                self.break_remaining_sec = max(0.0, self.break_remaining_sec - elapsed_sec)
            timer_text = self._format_remaining(self.break_remaining_sec, "BREAK ")
            if self.break_remaining_sec <= 0:
                self.is_break_active = False
                break_finished = True

        return {
            "is_focus": self.is_focus_active,
            "is_break": self.is_break_active,
            "is_paused": self.is_paused,
            "timer_text": timer_text,
            "focus_finished": focus_finished,
            "break_finished": break_finished,
        }
