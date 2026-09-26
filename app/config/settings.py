import json
import os
import winreg
from pathlib import Path

class SettingsManager:
    """Manages application settings stored in a JSON configuration file."""

    DEFAULT_SETTINGS = {
        "productive_apps": [
            "code.exe", "visualstudio.exe", "devenv.exe", "idea64.exe",
            "clion64.exe", "pycharm64.exe", "webstorm64.exe", "rider64.exe",
            "cmd.exe", "powershell.exe", "windows-terminal.exe", "wt.exe",
            "git-bash.exe", "sublime_text.exe", "notepad++.exe"
        ],
        "productive_keywords": [
            "vscode", "visual studio", "intellij", "clion", "pycharm", "webstorm",
            "terminal", "powershell", "cmd.exe", "github", "gitlab", "stackoverflow",
            "docs.", "documentation", "python", "jupyter", "cursor", "sublime",
            "chatgpt", "claude", "antigravity", "codepen", "replit", "developer"
        ],
        "distracting_apps": [
            "discord.exe", "steam.exe", "epicgames.exe", "spotify.exe",
            "roblox.exe", "leagueoflegends.exe", "netflix.exe", "tiktok.exe"
        ],
        "distracting_keywords": [
            "youtube", "reddit", "instagram", "netflix", "twitch", "steam",
            "roblox", "tiktok", "facebook", "twitter", "x.com", "9gag",
            "anime", "prime video", "hulu", "hbo", "disney+"
        ],
        "idle_threshold_sec": 60,
        "long_idle_threshold_sec": 300,
        "distraction_grace_period_sec": 120,
        "focus_milestone_target_sec": 1800,  # 30 minutes
        "daily_goal_minutes": 120,
        "pet_scale": 1.0,
        "always_on_top": True,
        "auto_hide_message_sec": 6,
        "quiet_hours_enabled": False,
        "quiet_start": "22:00",
        "quiet_end": "08:00",
        "sound_enabled": True,
        "animations_enabled": True,
        "start_with_windows": False,
        "window_x": -1,
        "window_y": -1
    }

    def __init__(self, config_path=None):
        if config_path is None:
            app_dir = Path.home() / ".moodpet"
            app_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = app_dir / "config.json"
        else:
            self.config_path = Path(config_path)

        self.settings = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self):
        """Load settings from disk."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"Error loading config.json: {e}")
        else:
            self.save()

    def save(self):
        """Save current settings to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving config.json: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def set_start_with_windows(self, enable: bool):
        """Configure Windows startup registry key."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "MoodPet"
        python_exe = os.sys.executable
        main_script = os.path.abspath("main.py")
        cmd = f'"{python_exe}" "{main_script}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.set("start_with_windows", enable)
        except Exception as e:
            print(f"Error setting registry startup: {e}")
