import time
from enum import Enum
from app.config.settings import SettingsManager

class ProductivityState(Enum):
    PRODUCTIVE = "PRODUCTIVE"
    NEUTRAL = "NEUTRAL"
    DISTRACTING = "DISTRACTING"
    IDLE = "IDLE"
    LONG_IDLE = "LONG_IDLE"

class ProductivityEngine:
    """Evaluates active window info, process names, and system idle duration to determine state."""

    def __init__(self, settings: SettingsManager):
        self.settings = settings
        self.distraction_start_time = None

    def evaluate(self, window_info: dict, idle_seconds: float) -> tuple[ProductivityState, dict]:
        """
        Evaluates current state.
        Returns (ProductivityState, debug_metadata).
        """
        title = window_info.get("title", "").lower()
        process_name = window_info.get("process_name", "").lower()

        idle_threshold = self.settings.get("idle_threshold_sec", 60)
        long_idle_threshold = self.settings.get("long_idle_threshold_sec", 300)
        grace_period = self.settings.get("distraction_grace_period_sec", 120)

        # 1. Idle checks
        if idle_seconds >= long_idle_threshold:
            self.distraction_start_time = None
            return ProductivityState.LONG_IDLE, {"reason": f"Idle for {int(idle_seconds)}s"}
        
        if idle_seconds >= idle_threshold:
            self.distraction_start_time = None
            return ProductivityState.IDLE, {"reason": f"Idle for {int(idle_seconds)}s"}

        # 2. Productive check
        productive_apps = [app.lower() for app in self.settings.get("productive_apps", [])]
        productive_keywords = [kw.lower() for kw in self.settings.get("productive_keywords", [])]

        is_productive_app = process_name in productive_apps
        is_productive_keyword = any(kw in title for kw in productive_keywords)

        if is_productive_app or is_productive_keyword:
            self.distraction_start_time = None
            return ProductivityState.PRODUCTIVE, {
                "matched": process_name if is_productive_app else title,
                "reason": "Matched productive rule"
            }

        # 3. Distraction check
        distracting_apps = [app.lower() for app in self.settings.get("distracting_apps", [])]
        distracting_keywords = [kw.lower() for kw in self.settings.get("distracting_keywords", [])]

        is_distracting_app = process_name in distracting_apps
        is_distracting_keyword = any(kw in title for kw in distracting_keywords)

        if is_distracting_app or is_distracting_keyword:
            now = time.time()
            if self.distraction_start_time is None:
                self.distraction_start_time = now

            distraction_elapsed = now - self.distraction_start_time
            if distraction_elapsed >= grace_period:
                return ProductivityState.DISTRACTING, {
                    "matched": process_name if is_distracting_app else title,
                    "elapsed_sec": int(distraction_elapsed),
                    "reason": "Grace period expired"
                }
            else:
                remaining_grace = int(grace_period - distraction_elapsed)
                return ProductivityState.NEUTRAL, {
                    "matched": process_name if is_distracting_app else title,
                    "grace_remaining_sec": remaining_grace,
                    "reason": "In distraction grace period"
                }

        # 4. Fallback to NEUTRAL
        self.distraction_start_time = None
        return ProductivityState.NEUTRAL, {"reason": "Unclassified active app"}
