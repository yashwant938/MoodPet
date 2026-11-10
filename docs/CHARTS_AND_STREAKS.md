# Focus charts and streak care

## What the charts measure

The Overview time-source selector controls both Your rhythm and the 12-week calendar. In timer-only mode it defaults to **Focus timers**. This reads saved manual sessions, including partial sessions, and excludes paused time. Automatic sessions and tracked activity are not added to these values. Choose **Tracked app activity** to see productive, distracted and idle app activity separately, including historical records when monitoring is currently off. Changing the chart source never enables monitoring.

The saved session's finish date determines its day, matching existing history and streak behavior. Historical records do not contain a per-second trace of pauses across midnight, so the app does not guess a different daily split. Only recorded durations can be shown; unrecorded learning time while tracking is off cannot be reconstructed.

The red/chocolate scale uses fixed bands:

| Time | Shade |
| --- | --- |
| 0 | Empty neutral |
| Positive, below 30 minutes | Pale pink |
| 30 minutes–under 1 hour | Pink |
| 1–under 2 hours | Red |
| 2–under 4 hours | Dark red |
| 4–under 6 hours | Chocolate |
| 6 hours or more | Dark chocolate |

Hover shows exact hours, minutes and seconds. Empty-state text wraps within the plot rather than clipping. The Overview remains vertically scrollable, with no horizontal overflow at its minimum supported width. Full fixture previews can be regenerated with `python docs/preview_focus.py`.

## Streak eligibility

Any positive saved manual focus time qualifies, including a partial session; any positive tracked productive activity also qualifies. Idle and distracted time alone do not qualify. Legacy days with completed-session counters remain valid. A single calendar day counts once even if both measures exist. Future records do not inflate the streak. Yesterday's streak remains current until the end of today.

Recorded work-day counts include only work days; protected days may extend current/best streaks but are not labelled as worked days. Existing earned XP and achievements remain persistent.

## Two free tokens per calendar month

Open **Overview → Streak care**. Every calendar month provides an allowance of two free repairs, with no XP charge. Unused allowance does not roll over. Select a missed past day within the last 30 days, after your first recorded work day, then use one free token. Today, future dates, existing work days, duplicate repairs and dates before your work history cannot consume a token. Protecting a day does not add focus hours, completed sessions or XP.

A gold diamond marks a protected day. Hover distinguishes protection from recorded focus time. The UI reports the updated streak after redemption. The allowance is based on the month when a token is used, so it can repair an eligible recent gap across a month boundary.

## Persistence and validation

An additive `streak_repairs` table stores one row per protected date, its redemption month and local timestamp. Redemption runs in an immediate SQLite transaction, validating the date, uniqueness and monthly limit together. Concurrent requests cannot exceed two uses per month. Restarting does not reissue spent tokens, and opening the dashboard does not spend them. Daily-stat reset does not erase protection records or refund tokens. All data remains local.

Tests cover 6h+ manual totals with tracking disabled, separate automatic/manual sources, partial work, red/chocolate thresholds, tooltips, two-day gap restoration, concurrent limits, month renewal, invalid dates, restarts, unchanged XP, and real Qt repair-button interactions. The packaged smoke test uses a disposable profile and exercises chart totals and a repair without reading the user's history.
