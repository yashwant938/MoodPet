import random
import time
from datetime import datetime
from enum import Enum
from app.productivity.score_engine import ProductivityState

class EmotionState(Enum):
    HAPPY = "HAPPY"
    ANGRY = "ANGRY"
    SAD = "SAD"
    SLEEPING = "SLEEPING"
    EXCITED = "EXCITED"

class EmotionStateMachine:
    """Manages pet emotion transitions, message generation, and cooldowns."""

    MESSAGES = {
        EmotionState.HAPPY: [
            "Let's go! 🔥",
            "You're doing great!",
            "Keep cooking 👨‍💻",
            "Nice focus!",
            "Lock in! 🚀",
            "In the flow zone ✨"
        ],
        EmotionState.ANGRY: [
            "BRO... GET BACK TO WORK 😭",
            "You said 5 minutes... 💀",
            "We both know you're procrastinating.",
            "Close YouTube. NOW.",
            "Your goals are watching you 😤",
            "Stop scrolling! 🛑"
        ],
        EmotionState.SAD: [
            "Are you still alive? 😭",
            "Bro... do something.",
            "I'm getting lonely 😭",
            "Let's get back to it.",
            "Don't leave me hanging..."
        ],
        EmotionState.SLEEPING: [
            "Wake me when you're ready 😴",
            "Z z z ... 💤",
            "Power nap time 💤"
        ],
        EmotionState.EXCITED: [
            "You crushed that session! 🎉",
            "Productivity streak increased! 🔥",
            "Unstoppable! 🏆",
            "Focus master! 🚀"
        ]
    }

    def __init__(self, message_cooldown_sec: float = 20.0):
        self.current_emotion = EmotionState.HAPPY
        self.message_cooldown_sec = message_cooldown_sec
        self.last_message_time = 0
        self.dnd_mode = False

    def update_state(self, prod_state: ProductivityState, milestone_triggered: bool = False, custom_milestone_msg: str = None) -> tuple[EmotionState, str | None]:
        """
        Determines target emotion state and returns (EmotionState, message_to_display_or_None).
        """
        now = time.time()
        new_emotion = self.current_emotion
        custom_msg = None

        if milestone_triggered:
            new_emotion = EmotionState.EXCITED
            custom_msg = custom_milestone_msg or random.choice(self.MESSAGES[EmotionState.EXCITED])
        else:
            if prod_state == ProductivityState.PRODUCTIVE:
                new_emotion = EmotionState.HAPPY
            elif prod_state == ProductivityState.DISTRACTING:
                new_emotion = EmotionState.ANGRY
            elif prod_state == ProductivityState.IDLE:
                new_emotion = EmotionState.SAD
            elif prod_state == ProductivityState.LONG_IDLE:
                new_emotion = EmotionState.SLEEPING
            else: # NEUTRAL
                new_emotion = EmotionState.HAPPY

        state_changed = (new_emotion != self.current_emotion)
        self.current_emotion = new_emotion

        # Determine if speech bubble message should pop up
        should_speak = False
        message = None

        if state_changed:
            should_speak = True
        elif (now - self.last_message_time) >= self.message_cooldown_sec:
            # Chance to speak periodically
            should_speak = random.random() < 0.45

        if should_speak and not self.dnd_mode:
            if custom_msg:
                message = custom_msg
            else:
                message = random.choice(self.MESSAGES[new_emotion])
            self.last_message_time = now

        return new_emotion, message

    def is_quiet_hours(self, quiet_enabled: bool, quiet_start: str, quiet_end: str) -> bool:
        """Check if current system time falls within quiet hours."""
        if not quiet_enabled:
            return False
        try:
            now = datetime.now().time()
            start = datetime.strptime(quiet_start, "%H:%M").time()
            end = datetime.strptime(quiet_end, "%H:%M").time()
            if start <= end:
                return start <= now <= end
            else: # Overnight quiet hours
                return now >= start or now <= end
        except Exception:
            return False
