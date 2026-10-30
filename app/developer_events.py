"""Opt-in local event inbox. No server, arbitrary text, commands or code access."""
import json
import time
import uuid
from pathlib import Path

EVENTS = {
    "build-passed": "Your build passed. A small celebration for a step forward!",
    "build-failed": "The build needs another look. Take your time with the logs.",
    "tests-passed": "Tests passed. Nice work checking your changes!",
    "tests-failed": "A test needs attention. One small fix at a time.",
}


def send_event(settings, event):
    if event not in EVENTS:
        raise ValueError("Unknown developer event")
    if not settings.get("developer_events_enabled", False):
        raise ValueError("Enable developer events in MoodPet Preferences first")
    inbox = settings.config_path.parent / "events"
    inbox.mkdir(exist_ok=True)
    # Bound the inbox if MoodPet is not running.
    files = list(inbox.glob("*.json"))
    if len(files) >= 100:
        raise ValueError("Event inbox is full; open MoodPet to clear it")
    payload = json.dumps({"event": event, "time": time.time()})
    path = inbox / (uuid.uuid4().hex + ".json")
    temp = path.with_suffix(".tmp")
    temp.write_text(payload, encoding="utf-8")
    temp.replace(path)


def receive_events(settings):
    inbox = settings.config_path.parent / "events"
    if not inbox.exists():
        return []
    events = []
    for path in sorted(inbox.glob("*.json"))[:100]:
        try:
            if path.is_symlink() or path.stat().st_size > 512:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - float(payload["time"])
            if settings.get("developer_events_enabled", False) and 0 <= age <= 60 and payload["event"] in EVENTS:
                events.append(payload["event"])
        except (OSError, ValueError, TypeError, KeyError):
            pass
        finally:
            try:
                path.unlink()
            except OSError:
                pass
    return events
