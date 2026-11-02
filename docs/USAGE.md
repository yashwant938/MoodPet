# MoodPet

A Windows desktop companion that turns small focus sessions into visible progress.

## Choose your mode

The first launch asks for a tracking choice before monitoring starts. Timer-only is the default and uses saved focus-timer minutes for the daily goal; automatic mode uses tracked productive time. App-activity charts always remain separate. See the [focus journey guide](FOCUS_JOURNEY.md) for corrections, quick actions, personalities, evolution stages and the Windows download workflow.

## Run

Requires Windows 10/11 and Python 3.10 or newer.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Click the floating pet or tray icon to open your dashboard. Drag the pet to move it. Right-click for preferences, hiding the companion, or quitting. Closing the dashboard leaves the companion running; use **Exit MoodPet** to quit.

Right-click the pet to see the current task and whether its focus timer is paused. The menu also shows average hours per day for the last completed Monday–Sunday week, including zero-activity days. Focus-timer averages use saved manual sessions, including partial sessions; tracked productive activity is shown separately. Sessions spanning midnight are assigned to the day they ended.

## Your dashboard

- **Overview:** saved focus-timer or tracked-activity charts for 7 or 30 days, a 12-week activity calendar, daily goal, streaks, focus balance, and tiny daily wins. Hover chart bars and calendar cells for exact details.
- **Focus room:** preset or custom 1–180 minute sessions, pause/resume, and 5/10 minute breaks. Ending a session early saves it as partial. Timers pause after a long gap such as computer sleep.
- **Session history:** your most recent 100 sessions, lifetime stats, achievement collection, and a 90-day CSV activity export.
- **Tasks:** enter a task name and press Enter or click Add task. Project and estimate are optional. Select an active row and click **Focus on this task** (or double-click the row), then choose your duration and click **Start focus**. You can also rename, complete, archive or reopen tasks. Focus without a task by choosing **No task · just focus** in the Focus room. Saved partial and completed manual sessions contribute to the task's focused time.
- **Focus journey:** twenty stages with ten levels each, an interactive map, stage cosmetics, upcoming rewards and the original completed-session notes. Earn 1 XP per tracked productive minute, 25 XP per completed session and 10 XP per task (once). Each level costs `50 + 2 × (global level − 1)` XP. Earned XP persists independently of history resets.

## How tracking works

Activity charts count time in apps/window titles matching your rules. Idle time is tracked separately; neutral activity is omitted. Focus balance is productive time divided by productive plus distracted time. Focus timers measure elapsed session time and do not turn unrelated app activity into productive time.

A streak day requires **any positive recorded focus time**: saved manual timer time, including partials, or productive app activity. Existing legacy completion days still qualify. Your streak remains available the next day so you have time to continue it. Overview → Streak care provides two free tokens each calendar month. Choose an eligible missed past day from the last 30 days and click Use 1 free token to protect it. Tokens do not roll over, and repair adds no work time or XP. A missed full day breaks the current streak; the personal best remains. A daily goal is independent of the streak rule.

Automatic productive blocks of at least five minutes are saved once when the block ends; a block completes when it reaches your configured milestone. Switching to neutral, distracted, or idle activity ends the block. During focus timers and breaks, automatic session recording is suppressed to prevent duplicate sessions. Productive activity still counts normally. Manual session time excludes pauses. Completed sessions are assigned to their finish date; daily activity is counted as it happens.

## Saved locally

Settings live in `%USERPROFILE%\.moodpet\config.json`; history lives in `%USERPROFILE%\.moodpet\moodpet.db`. Existing databases are upgraded in place. Streaks, XP, achievements, goals, and history survive restarting the app. On a normal exit a running focus session is saved as partial. If interrupted unexpectedly, choose on restart whether to save the last checkpoint as partial or discard it. The timer does not resume automatically, and closed, paused and sleep time are not counted. Up to approximately five seconds since the last checkpoint may be lost.

The app reads foreground app names/window titles to classify activity and checks the time since your last input. It stores aggregate durations and session records locally, not window titles or keystrokes. Preferences lets you edit app rules and thresholds, choose quiet hours, and configure startup. Resetting today's statistics deletes today's sessions and may change the streak; earned XP, stage cosmetics and earned achievements remain.

## Verify

```powershell
python -m unittest discover -s tests -v
python scratch/render_dashboard.py
```

The preview script uses disposable fixture data and saves screenshots to `scratch/`; it never opens your real history.

Charts share a **Time source** selector. Timer-only mode defaults to saved Focus timers; tracked app activity is separate and is never added to timer time. The calendar uses increasing pink/red/chocolate shades at 30m, 1h, 2h, 4h and 6h+. Gold diamonds identify protected streak days. Only recorded time can be displayed; learning done outside a timer while automatic tracking is off cannot be reconstructed. See [charts and streak care](CHARTS_AND_STREAKS.md) for exact behavior.
