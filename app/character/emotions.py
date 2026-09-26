from enum import Enum

class EmotionalPose(Enum):
    IDLE = "IDLE"
    HAPPY = "HAPPY"
    EXCITED = "EXCITED"
    FOCUSED = "FOCUSED"
    THINKING = "THINKING"
    SUSPICIOUS = "SUSPICIOUS"
    SLEEPY = "SLEEPY"
    SAD = "SAD"
    CRYING = "CRYING"
    ANGRY = "ANGRY"
    SHOCKED = "SHOCKED"
    WINK = "WINK"
    TYPING = "TYPING"
    CODING = "CODING"
    READING = "READING"
    BREAK = "BREAK"
    CELEBRATION = "CELEBRATION"

class EmotionalStateEngine:
    """Manages continuous internal emotional variables and pose transitions based on reference design."""

    def __init__(self):
        self.focus_level = 50.0
        self.happiness = 70.0
        self.boredom = 0.0
        self.frustration = 0.0
        self.concern = 0.0
        self.energy = 80.0

        self.current_pose = EmotionalPose.IDLE

    def update(self, prod_state_name: str, distraction_elapsed_sec: float, idle_sec: float, is_in_focus_mode: bool, is_in_break_mode: bool, is_typing: bool = False) -> EmotionalPose:
        if is_in_break_mode:
            self.happiness = min(100.0, self.happiness + 0.5)
            self.current_pose = EmotionalPose.BREAK
            return self.current_pose

        if idle_sec >= 300: # 5+ mins
            self.current_pose = EmotionalPose.SLEEPY
            return self.current_pose

        if idle_sec >= 60: # 1-5 mins
            if idle_sec >= 180:
                self.current_pose = EmotionalPose.SAD
            else:
                self.current_pose = EmotionalPose.THINKING
            return self.current_pose

        # Active user
        if is_in_focus_mode:
            self.current_pose = EmotionalPose.FOCUSED
            return self.current_pose

        if prod_state_name == "PRODUCTIVE":
            if is_typing:
                self.current_pose = EmotionalPose.CODING
            else:
                self.current_pose = EmotionalPose.HAPPY

        elif prod_state_name == "DISTRACTING" or distraction_elapsed_sec > 0:
            if distraction_elapsed_sec < 120:
                self.current_pose = EmotionalPose.SUSPICIOUS
            elif distraction_elapsed_sec < 300:
                self.current_pose = EmotionalPose.ANGRY
            else:
                self.current_pose = EmotionalPose.CRYING

        else: # NEUTRAL
            if is_typing:
                self.current_pose = EmotionalPose.TYPING
            else:
                self.current_pose = EmotionalPose.IDLE

        return self.current_pose
