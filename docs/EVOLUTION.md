# Evolution and durable rewards

## Rules and migration

`app/productivity/progression.py` is the single definition of stages, cosmetics and the version-one curve. Global levels 1–100 map to ten local levels in each of ten stages. Completing global level `n` costs `25 + 2 × (n − 1)` XP; completing `n` levels requires `25n + n(n − 1)` lifetime XP. Stage transitions occur after completing levels 10, 20, and so on. Completing all 100 costs 12,400 XP (496 completed-session rewards, before productive-minute and task rewards). Costs are configurable through the typed rules object; changing the released curve requires an explicit future migration.

The old UI used `floor(productive_seconds / 60) + 25 × completed_sessions` and `floor(XP / 250) + 1`. Migration snapshots exactly that XP balance from existing daily aggregates. The new curve places a user at or above their previous global level, capped at the map's 100-level display; users above that cap enter mastered Legend and retain all XP. The original migration event retains their legacy balance. All original session rows and notes remain. Historical completed sessions and already-completed tasks are marked as credited, preventing replay. An existing active task can earn its first new task reward after upgrade.

The additive, transactional SQLite migration creates:

- `pet_progress`: decimal-text XP and a monotonically increasing productive-seconds counter, plus the last acknowledged completed level.
- `reward_events`: unique event identifiers such as `session:42` and `task:7`, reward kind, XP and local timestamp.
- `evolution_unlocks`: the persistent set of completed levels, up to 100.
- `earned_achievements`: permanent records of the four existing milestones.

Decimal-text XP plus Python integers allow continued accumulation beyond SQLite's signed 64-bit integer range. The UI caps progress bars and formats very large totals compactly.

## Reward lifecycle

`RewardService` runs inside the same transaction as session, task or productive-time persistence. Completed sessions retain the existing 25-XP reward, including eligible automatic completions. Tracked productive minutes retain their 1-XP rate. Manual partial sessions earn no completion XP. A task completion awards 10 XP once per task ID. Reopen/archive/recomplete does not create another award. Goals and achievements add no extra XP, avoiding overlapping bonuses. Reward failure rolls back the associated write; checkpoint recovery still consumes and saves once atomically.

Resetting a daily activity row no longer reduces XP, cosmetics or earned achievements. The monotonic productive-seconds counter continues independently so a reset cannot replay old minute rewards. The explicit history reset can still remove today's sessions and change the streak, matching its existing purpose.

Unlock acknowledgement is persisted before the UI emits an advancement animation. Restarting does not replay the animation. If the process terminates between acknowledgement and painting, that short animation may be skipped; earned progress is retained.

## UI and pet state

`EvolutionController` coalesces database notifications and reads consistent snapshots on a bounded Qt thread pool. It feeds one progression state to the floating pet, sidebar and evolution view. The map paints only in response to changes. Ten native level buttons per stage provide keyboard focus, tooltips and click/Space details, while the stage picker previews future environments. The original session notes remain below the map.

The existing robot is rendered with original QPainter accessories and faces. `PetReactionState` resolves overlapping reactions by explicit priority and monotonic expiry; celebration outranks short reactions and falls back to focus/break/base poses after expiry. Breathing, blinking, bounce, laughter, proud brows, sleep and celebrations use a bounded 30-FPS render loop. Hidden pets stop their timers; reduced motion stops loops, particles and unlock effects. Quiet personality uses the existing speech gate for all messages. Ivory and lavender shell choices remain independent of progression.

## Validation and previews

Run:

```powershell
python -m unittest discover -s tests -v
python main.py --smoke-test
python docs/preview_evolution.py
python main.py --demo
python packaging/build.py
```

Screenshots under `docs/images/evolution-*.png` use fictional temporary data. Demo mode uses a separate temporary profile, has an explicit fictional-data label, and can run alongside a normal profile. Timer-only remains the default; no tracking consent or privacy settings are modified.

Regression coverage includes every threshold, stage boundaries, historical migration, rollback, reward concurrency and idempotency, checkpoint recovery, retained achievements, arbitrary-precision totals, asynchronous updates, keyboard interaction, all pet cosmetics/poses, reduced motion, quiet mode and demo isolation. Windows CI also builds the portable executable and per-user installer and runs the packaged smoke test.

Known limits: cosmetics equip automatically with the current stage; there is no wardrobe selector. The new snapshot reads and acknowledgements are asynchronous, while core session/task/activity writes retain the existing synchronous SQLite transaction path, now including their small reward writes; unusually slow storage can delay those existing operations. This PR does not add goal bonuses, new achievement bonuses, weekly analytics or break reminders.
