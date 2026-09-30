# MoodPet

A Windows desktop companion that turns small focus sessions into visible progress.

## Run

Requires Windows 10/11 and Python 3.10 or newer.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Click the floating pet or tray icon to open your dashboard. Drag the pet to move it. Right-click for preferences, hiding the companion, or quitting. Closing the dashboard leaves the companion running; use **Exit MoodPet** to quit.

## Your dashboard

- **Overview:** live activity charts for 7 or 30 days, a 12-week activity calendar, daily goal, streaks, focus balance, and tiny daily wins. Hover chart bars and calendar cells for exact details.
- **Focus room:** preset or custom 1–180 minute sessions, pause/resume, and 5/10 minute breaks. Ending a session early saves it as partial. Timers pause after a long gap such as computer sleep.
- **Session history:** your most recent 100 sessions, lifetime stats, achievement collection, and a 90-day CSV activity export.
- **Companion growth:** 1 XP for each productive minute and 25 XP for each completed session; every 250 XP gains a level. Progress is calculated from saved history.

## How tracking works

Activity charts count time in apps/window titles matching your rules. Idle time is tracked separately; neutral activity is omitted. Focus balance is productive time divided by productive plus distracted time. Focus timers measure elapsed session time and do not turn unrelated app activity into productive time.

A streak day requires **15 productive minutes or one completed focus session**. Your streak remains available the next day so you have time to continue it. A missed full day breaks the current streak; the personal best remains. A daily goal is independent of the streak rule.

Automatic productive blocks of at least five minutes are saved once when the block ends; a block completes when it reaches your configured milestone. Switching to neutral, distracted, or idle activity ends the block. During focus timers and breaks, automatic session recording is suppressed to prevent duplicate sessions. Productive activity still counts normally. Manual session time excludes pauses. Completed sessions are assigned to their finish date; daily activity is counted as it happens.

## Saved locally

Settings live in `%USERPROFILE%\.moodpet\config.json`; history lives in `%USERPROFILE%\.moodpet\moodpet.db`. Existing databases are upgraded in place. Streaks, XP, achievements, goals, and history survive restarting the app. Timers are not resumed after quitting; a running focus session is saved as partial on a normal exit. A forced process termination may lose the current unfinished session, while previously saved activity remains.

The app reads foreground app names/window titles to classify activity and checks the time since your last input. It stores aggregate durations and session records locally, not window titles or keystrokes. Preferences lets you edit app rules and thresholds, choose quiet hours, and configure startup. Resetting today's statistics also deletes today's sessions, which may change your streak and XP.

## Verify

```powershell
python -m unittest discover -s tests -v
python scratch/render_dashboard.py
```

The preview script uses disposable fixture data and saves screenshots to `scratch/`; it never opens your real history.
