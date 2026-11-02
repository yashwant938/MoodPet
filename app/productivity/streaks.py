"""Recorded work days and local, explicit streak protection."""
from datetime import date, timedelta

MONTHLY_REPAIR_TOKENS = 2
REPAIR_WINDOW_DAYS = 30


def work_days(conn, today=None):
    """Positive timer/activity time qualifies; legacy completion days survive."""
    today = today or date.today()
    rows = conn.execute('''SELECT date FROM daily_stats
        WHERE date<=? AND (productive_seconds>0 OR focus_sessions_count>0)
        UNION SELECT date FROM focus_sessions
        WHERE date<=? AND source='manual' AND duration_seconds>0''',
        (today.isoformat(), today.isoformat())).fetchall()
    return {date.fromisoformat(r[0]) for r in rows if r[0]}


def streak_summary(worked, protected, today):
    days = sorted(day for day in worked | protected if day <= today)
    best = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous is not None and day-previous == timedelta(days=1) else 1
        best = max(best,run)
        previous = day
    current = run if previous in (today,today-timedelta(days=1)) else 0
    return {'current_streak':current,'best_streak':best,'active_days':len(worked)}
