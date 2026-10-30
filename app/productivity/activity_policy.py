"""User-controlled activity classification; temporary corrections never touch disk."""
import time

from app.productivity.score_engine import ProductivityEngine, ProductivityState


class ActivityPolicy:
    def __init__(self, settings, clock=time.monotonic):
        self.settings = settings
        self.clock = clock
        self.engine = ProductivityEngine(settings)
        self.paused_until = 0
        self.corrections = {}

    @property
    def enabled(self):
        return self.settings.get("tracking_mode", "manual") == "automatic" and self.clock() >= self.paused_until

    def pause(self, seconds=900):
        self.paused_until = self.clock() + seconds
        self.engine.distraction_start_time = None

    def resume(self):
        self.paused_until = 0

    def clear_corrections(self):
        self.corrections.clear()

    def correct(self, window, state, keyword=""):
        if state not in (ProductivityState.PRODUCTIVE, ProductivityState.NEUTRAL, ProductivityState.DISTRACTING):
            raise ValueError("Choose a productive, neutral or distracting classification")
        key = (window.get("process_name", ""), window.get("title", ""))
        if not any(key):
            raise ValueError("No current window to correct")
        keyword = keyword.strip().lower()
        if keyword:
            if len(keyword) < 3 or len(keyword) > 100:
                raise ValueError("A remembered keyword must be 3–100 characters")
            # Persistent rules are explicit user-entered keywords, never captured titles.
            if state == ProductivityState.NEUTRAL:
                raise ValueError("Neutral corrections are temporary")
            rules = dict(self.settings.get("classification_rules", {}))
            rules.pop(keyword, None)
            rules[keyword] = state.value
            self.settings.set("classification_rules", rules)
        self.corrections[key] = (self.clock() + 1800, state)
        self.engine.distraction_start_time = None

    def evaluate(self, window, idle):
        if not self.enabled:
            return ProductivityState.NEUTRAL, {"reason": "Tracking paused" if self.clock() < self.paused_until else "Timer-only mode · app activity is not read"}
        self.corrections = {key: value for key, value in self.corrections.items() if value[0] > self.clock()}
        # Idle always takes precedence over a correction.
        if idle < self.settings.get("idle_threshold_sec", 60):
            key = (window.get("process_name", ""), window.get("title", ""))
            if key in self.corrections:
                return self.corrections[key][1], {"reason": "Your temporary correction · up to 30 minutes or session end"}
        if idle < self.settings.get("idle_threshold_sec", 60):
            title = window.get("title", "").lower()
            for keyword, value in reversed(list(self.settings.get("classification_rules", {}).items())):
                if keyword and keyword in title and value in ("PRODUCTIVE", "DISTRACTING"):
                    return ProductivityState(value), {"reason": f"Your remembered keyword: {keyword}"}
        return self.engine.evaluate(window, idle)
