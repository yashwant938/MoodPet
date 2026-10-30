# Focus journey and user control

## Start simply

On first launch choose Orbit (ivory) or Starlight (lavender), a daily goal, and a tracking mode. Cancelling exits before the tracker starts. Existing users also make this choice; old records are preserved.

- **Timer only:** foreground apps, idle/input APIs and animated foreground-window eye tracking are not polled. Saved focus-timer minutes drive the daily goal. Timers, history, achievements and the constellation still work.
- **Automatic:** local app names, window titles and time since input drive editable rules. Only aggregate durations and sessions are saved. The daily goal uses tracked productive time. Timers remain independent.

Click the pet or tray icon to open the dashboard. Right-click the pet or open the tray menu for **Quick actions**. Starting a second timer is disabled while a timer is active. Pause activity tracking for 15 minutes without stopping a manual focus timer; use Resume tracking to return early. Hiding the pet does not pause tracking.

## Understand and correct activity

Overview shows the current classification and reason. **Why this activity? / Correct it** opens the most recent external window; MoodPet's own windows do not earn productive time. Corrections refer to the window captured when the panel opened, not whichever app becomes foreground afterward.

Leave the keyword field blank to apply a temporary correction to that exact process and window title for up to 30 minutes. Completing or ending a focus/break timer clears temporary corrections. The taking-a-break choice also pauses an active focus timer. Idle classification always takes precedence.

Entering a keyword explicitly saves a rule for future matching window titles. These user rules take priority over default app rules; the most recently saved matching rule wins. Neutral/break corrections are temporary. Remove saved rules under Preferences → Activity / tone. Captured titles are never automatically written to settings or history; a temporary title match stays in memory.

## Grow a constellation

Each saved completed session appears as a bright star in Focus journey. The view shows the most recent 100 completions; faint background points are decoration. Select a star to find its session, or use the keyboard-accessible list. Optional session intentions are stored locally and limited to 120 characters. Partial sessions remain in history and do not light stars. The existing history reset can remove today's sessions and therefore their stars; missing a day or taking a break does not.

Daily-goal time, completion streaks, and XP retain explicit meanings. Timer-only goals use saved manual-session durations (including partial sessions), excluding pauses. Automatic goals use productive app time. XP remains one point per tracked productive minute plus 25 per completion; timer-only users still earn completion XP.

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
