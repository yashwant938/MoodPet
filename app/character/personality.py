import random
from app.character.emotions import EmotionalPose

class CharacterPersonality:
    """Generates friendly, sarcastic, supportive, and dramatic dialogue lines matching reference poses."""

    DIALOGUE = {
        EmotionalPose.IDLE: [
            "Ready when you are! ✨",
            "What are we building today?",
            "Standing by... 🤖",
            "All systems nominal!"
        ],
        EmotionalPose.HAPPY: [
            "Let's go! Time to cook 🔥",
            "In the flow zone ✨",
            "Making solid progress!",
            "Lock in time 🚀"
        ],
        EmotionalPose.EXCITED: [
            "THAT'S MY GUY 🔥🎉",
            "UNSTOPPABLE! 🏆",
            "ABSOLUTE MACHINE! 🚀",
            "Productivity streak increased! 🔥"
        ],
        EmotionalPose.FOCUSED: [
            "We are locked in now. 🤓",
            "Do not disturb: Genius at work 🧠",
            "Lines of code going up! 📈",
            "Focus level: MAXIMUM ⚡"
        ],
        EmotionalPose.THINKING: [
            "Hmm... how do we optimize this? 🤔",
            "Processing algorithm...",
            "Everything okay over there?",
            "Just checking in... 👀"
        ],
        EmotionalPose.SUSPICIOUS: [
            "Taking a quick break? 🤨",
            "Wasn't this supposed to be 5 minutes?",
            "Is that YouTube I see? 😑",
            "Bro... 👀"
        ],
        EmotionalPose.ANGRY: ["Ready for one small next step?", "Your pace, your choice."],
        EmotionalPose.SAD: ["I'll be here when you are ready.", "Take the time you need."],
        EmotionalPose.CRYING: ["A pause is part of the journey.", "A fresh start is always an option."],
        EmotionalPose.SLEEPY: [
            "Wake me when you're ready 😴",
            "Z z z ... 💤",
            "Power napping 💤"
        ],
        EmotionalPose.SHOCKED: [
            "Whoa! What just happened? 😳",
            "Did the build just pass?! 😳"
        ],
        EmotionalPose.WINK: [
            "Gotcha! 😉",
            "Nice move! 😉"
        ],
        EmotionalPose.TYPING: [
            "Keypress speed: OVER 9000! ⌨️⚡",
            "Keep those fingers flying!",
            "Typing furiously... 🔥"
        ],
        EmotionalPose.CODING: [
            "Writing beautiful code! 👨‍💻",
            "Debugging like a pro! 🐛",
            "Sipping coffee & crushing bugs ☕"
        ],
        EmotionalPose.READING: [
            "Studying documentation... 📚",
            "Knowledge level increasing! 💡"
        ],
        EmotionalPose.BREAK: [
            "Ahhh... well-deserved break ☕",
            "Recharging the battery 🔋",
            "Relaxing time 😌",
            "Enjoy your break!"
        ],
        EmotionalPose.CELEBRATION: [
            "FOCUS SESSION COMPLETE! LET'S GOOO! 🎉🔥",
            "CHAMPION PRODUCTIVITY! 🏆",
            "YOU CRUSHED THAT SESSION! 🎉"
        ]
    }

    @classmethod
    def get_speech(cls, pose: EmotionalPose, tone="gentle") -> str:
        if tone == "quiet":
            return ""
        if tone != "playful":
            if pose in (EmotionalPose.EXCITED, EmotionalPose.CELEBRATION):
                return "One small win, saved. Nice work showing up."
            if pose == EmotionalPose.BREAK:
                return "Enjoy your break. You can come back when you are ready."
            return random.choice(["Ready when you are.", "A small next step is enough.", "You can pause whenever you need."])
        lines = cls.DIALOGUE.get(pose, ["Let's get back to work!"])
        return random.choice(lines)
