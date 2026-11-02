# Focus journey and user control

## Start simply

On first launch choose Orbit (ivory) or Starlight (lavender), a daily goal, and a tracking mode. Cancelling exits before the tracker starts. Existing users also make this choice; old records are preserved.

- **Timer only:** foreground apps, idle/input APIs and animated foreground-window eye tracking are not polled. Saved focus-timer minutes drive the daily goal. Timers, history, achievements and the evolution journey still work.
- **Automatic:** local app names, window titles and time since input drive editable rules. Only aggregate durations and sessions are saved. The daily goal uses tracked productive time. Timers remain independent.

Click the pet or tray icon to open the dashboard. Right-click the pet or open the tray menu for **Quick actions**. Starting a second timer is disabled while a timer is active. Pause activity tracking for 15 minutes without stopping a manual focus timer; use Resume tracking to return early. Hiding the pet does not pause tracking.

The pet's right-click menu shows the current focus task (or a paused, break, or idle state) and the average daily time for the previous complete Monday–Sunday week. All seven days count, including days without activity. Focus timers and automatically tracked productive activity are displayed separately; they can overlap and are not added together. Timer averages include saved partial and completed sessions, assigned to their end date.

## Understand and correct activity

Overview shows the current classification and reason. **Why this activity? / Correct it** opens the most recent external window; MoodPet's own windows do not earn productive time. Corrections refer to the window captured when the panel opened, not whichever app becomes foreground afterward.

Leave the keyword field blank to apply a temporary correction to that exact process and window title for up to 30 minutes. Completing or ending a focus/break timer clears temporary corrections. The taking-a-break choice also pauses an active focus timer. Idle classification always takes precedence.

Entering a keyword explicitly saves a rule for future matching window titles. These user rules take priority over default app rules; the most recently saved matching rule wins. Neutral/break corrections are temporary. Remove saved rules under Preferences → Activity / tone. Captured titles are never automatically written to settings or history; a temporary title match stays in memory.

## Tasks and interrupted timers

Open **Tasks** to add a task, an optional project label and estimate. Press Enter in the task name or project field, or click **Add task**. Select a row to rename, complete, archive or reopen it. For an active task, **Focus on this task** (or a double-click) opens the Focus room with that task selected; click **Start focus** when ready. The Focus room also lets you choose an active task, or focus without one. Task time is the sum of saved manual sessions, including partial sessions; it is kept separate from tracked app activity.

MoodPet saves an active focus checkpoint approximately every five seconds and on pause or completion. After a crash, the next launch offers to save the last observed time as a partial session or discard it. The time while MoodPet was closed is never added, and a partial session does not create completion XP. Normal exit saves the session as partial. The timer starts afresh after either decision; up to the interval since the last checkpoint may be lost.

The migration adds local `tasks` and `focus_checkpoint` tables and a nullable task reference to `focus_sessions`. Existing history is preserved. A checkpoint is consumed and recorded in the same SQLite transaction, preventing a second recovery from creating duplicate sessions.

## Your evolution journey

Focus journey now contains twenty stages: Seedling, Explorer, Builder, Warrior, Guardian, Master, Champion, Conqueror, Mythic, Legend, Pioneer, Navigator, Artificer, Sentinel, Sage, Luminary, Ascendant, Celestial, Eternal, and Infinity. Each stage has ten levels. Complete level 10 to enter the next stage. Stage entry equips a unique cosmetic; entering levels 4 and 7 adds visor and orbit details. Ivory/lavender appearance choices remain available.

Use the stage picker to explore environments and upcoming rewards. Completed and current nodes accept clicks or keyboard focus/Space to show details; future nodes remain locked. **My stage** returns to your current world. The side pet and desktop pet share the same persistent evolution state. Reduced motion stops animation loops and celebrations; quiet mode suppresses all speech.

Level costs start at 50 XP and increase by 2 XP per global level. XP remains one point per tracked productive minute plus 25 per completed session, including existing automatic completions. A completed task adds 10 XP once for that task; reopening it never grants another reward. Goals and achievements do not add overlapping XP bonuses. Manual partial sessions keep their existing zero-completion-reward behavior. The new reward ledger preserves XP and unlocked cosmetics independently of deletable daily history. All 200 levels require 49,800 XP; XP keeps accumulating after Infinity 10.

Existing XP is migrated once from the old calculation and old completed sessions are marked as already credited. Users upgrading from the 100-level journey keep their earned XP balance, unlocked levels and approximately the same within-level progress through a separate, one-time curve adjustment. This adjustment is shown in the XP-bar tooltip and does not add work rewards. The original completed-session history, dates and notes remain intact; your latest 100 completions appear beneath the map. Optional intentions remain limited to 120 characters. Missed days never remove earned XP, cosmetics or achievements. Explicit history reset still removes today's session records and affects streaks, but no longer removes earned XP or achievements.

Timer-only goals still use saved manual-session durations (including partial sessions), excluding pauses. Automatic goals use productive app time. These time measures remain separate.

## Choose a tone

Gentle is the default and uses supportive speech and non-punitive poses. Playful uses more expressive reactions with revised supportive dialogue. Quiet suppresses all speech, including session and developer-event messages. Quiet hours continue to silence speech during the configured period. The character's states describe app behavior, not a measurement of your emotions.

## Optional developer events

Enable local event reactions in Preferences → Activity / tone. A build/test script can send one fixed event name:

```powershell
python main.py --event build-passed
python main.py --event build-failed
python main.py --event tests-passed
python main.py --event tests-failed
# Packaged version:
& "$env:LOCALAPPDATA\Programs\MoodPet\MoodPet.exe" --event tests-passed
```

Events use a per-profile local file inbox, not a network server. They carry only the event name and timestamp, expire after 60 seconds, and are consumed once. At most 100 pending files are accepted and messages are rate limited. Events do not launch MoodPet, run commands, read source code or award progress. Only use hooks for tools you intentionally connect. Any process running as your Windows user can send these local events; this is not an authentication boundary against other software running as you.

## Build and verify

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
python -m unittest discover -s tests -v
python main.py --smoke-test
python packaging/build.py
# After installing Inno Setup, compile packaging/MoodPet.iss with ISCC.
```

The smoke-test uses temporary fixture data and never opens the real profile or polls activity. CI also smoke-tests the packaged executable and builds the per-user installer. Build artifacts are unsigned previews; code signing requires a publisher certificate. The test fixture preview script renders onboarding, preferences, overview, focus, history and journey screenshots.

The packaging helper limits PATH to Python and Windows system directories so unrelated Qt/ICU DLLs from other applications cannot be selected by the bundler.
