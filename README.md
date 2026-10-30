# MoodPet

A native Windows focus companion with a personal constellation, supportive personalities, explainable activity rules, and an interactive Qt dashboard.

## Why this project exists

Small focus sessions are easier to sustain when progress is visible. MoodPet connects foreground activity and deliberate focus sessions to daily charts, streaks, and a desktop companion that remains available from the system tray.

## Architecture

```mermaid
flowchart LR
    Consent[Automatic mode enabled by user] --> Win[Windows foreground and idle APIs]
    Win --> Track[Explainable rules + temporary corrections]
    Track --> Focus[Focus and productivity state]
    Timer[Manual focus timer] --> Focus
    Focus --> DB[Local SQLite history]
    DB --> UI[PySide6 dashboard, history and constellation]
    Focus --> Pet[Desktop companion]
    Config[JSON settings] --> Track
```

Activity monitoring, productivity state, persistence, and UI live in separate `app/` packages. Settings and history remain on the local machine.

## A calmer start

The first launch lets you choose an ivory or lavender companion, set a daily goal, and select timer-only or automatic tracking. Timer-only is the default; foreground, input-idle and eye-gaze monitoring are disabled in this mode. Existing installations see the same choice before monitoring starts, and existing history is kept.

Try `python main.py --demo` to explore fictional temporary history with no activity monitoring and no changes to your regular profile.

## Engineering Highlights

- Correct activity for the current window for up to 30 minutes, or explicitly save a keyword rule. Idle time still wins. Remembered corrections can be removed in Preferences.
- Start focus, take a break, pause/resume timers, pause tracking for 15 minutes, or inspect the current classification from the pet/tray quick actions.
- Completed sessions light a constellation star; optional 120-character intentions appear alongside keyboard-accessible session details. Breaks and missed days never remove stars.
- Gentle (default), playful and quiet personalities; quiet silences all speech, including developer events.
- Opt-in local build/test events react to fixed event names without reading code, running commands, or changing XP.
- Durable daily activity and session records drive streaks, XP, achievements, and history across restarts.
- Focus timers support pause/resume and partial-session recording; automatic sessions are suppressed during manual focus and breaks to avoid double counting.
- Idle tracking handles Windows tick-counter wraparound, with regression coverage.
- Charts offer 7/30-day activity views, a 12-week calendar, hover details, and CSV export.
- Monitoring reads foreground app names and window titles for classification; stored records contain aggregate durations and sessions, not titles or keystrokes.

## Tech Stack

**Desktop:** Python 3.10+, PySide6. **Persistence:** SQLite and JSON. **Platform:** Windows APIs. **Validation:** Python `unittest`, including storage, timer, tracking, chart, and dashboard tests.

## How It Works

Click the pet or tray icon to open the dashboard. In automatic mode, activity matching your rules is classified as productive or distracted; idle time is tracked separately. A streak day requires **15 productive minutes or one completed focus session**. Manual focus timers measure session time independently of app classifications. In timer-only mode the daily goal uses saved manual timer time; automatic-mode goals use tracked productive time. The activity charts always show recorded app activity, so these measures are never combined.

Settings are stored at `%USERPROFILE%\.moodpet\config.json`; history is at `%USERPROFILE%\.moodpet\moodpet.db`. Timers are saved as partial on a normal exit and are not resumed after restarting. A forced termination may lose the active unfinished session.

## Windows download and setup

The **Windows app and tests** workflow builds a portable ZIP, per-user installer, and SHA-256 checksums as the `MoodPet-Windows` artifact for the PR. These are unsigned preview builds. The installer installs without administrator rights and keeps the local profile on uninstall; it does not enable startup automatically. Publish reviewed artifacts as a GitHub Release after merging. No release is published automatically.

For development from source:


Requires Windows 10/11 and Python 3.10 or newer.

```powershell
git clone https://github.com/yashwant938/MoodPet.git
cd MoodPet
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Drag the pet to reposition it. Right-click for preferences or **Exit MoodPet**. Closing the dashboard leaves the companion running.

## Example

Open the dashboard, start a 25-minute focus session, pause and resume as needed, and complete it. The session appears in history and contributes to the day's streak. Reopen MoodPet to inspect the saved record. The session timer does not reclassify unrelated foreground activity as productive.

## Engineering Challenges

Time-based state must remain consistent through pauses, sleep gaps, midnight boundaries, and restarts. Tests exercise these transitions and persistence rules. Activity classification depends on editable app/title rules, so it is a useful personal signal rather than a measure of work quality.

Run the regression suite and an optional dashboard preview with disposable fixture data:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scratch/render_dashboard.py
```

## Future Improvements

- Improve recovery of unfinished sessions after unexpected termination.
- Add configurable retention and richer import/export options.

See the [usage and data guide](docs/USAGE.md) for exact scoring, history, automatic-session, and reset behavior.

See [the new experience guide](docs/FOCUS_JOURNEY.md) for corrections, tone, developer events, packaging and data behavior.
