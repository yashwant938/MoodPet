"""Reward validation and idempotency inside the caller's SQLite transaction."""
from datetime import date, datetime, timedelta
from app.productivity.progression import RULES, progress_for


class RewardService:
    @staticmethod
    def migrate(conn):
        conn.execute('''CREATE TABLE IF NOT EXISTS pet_progress (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), xp TEXT NOT NULL,
            tracked_seconds TEXT NOT NULL, seen_level INTEGER NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reward_events (
            event_id TEXT PRIMARY KEY, kind TEXT NOT NULL, xp TEXT NOT NULL, created_at TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS evolution_unlocks (
            level INTEGER PRIMARY KEY, earned_at TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS earned_achievements (
            name TEXT PRIMARY KEY, earned_at TEXT NOT NULL)''')
        if conn.execute('SELECT 1 FROM pet_progress').fetchone():
            RewardService.sync_achievements(conn)
            return
        row = conn.execute('''SELECT COALESCE(SUM(MAX(0, productive_seconds)),0),
            COALESCE(SUM(MAX(0, focus_sessions_count)),0) FROM daily_stats''').fetchone()
        seconds, completions = map(int, row)
        xp = seconds // 60 + completions * RULES.session_xp
        completed = progress_for(xp).completed
        conn.execute('INSERT INTO pet_progress VALUES (1,?,?,?)', (str(xp), str(seconds), completed))
        stamp = datetime.now().isoformat()
        conn.execute('INSERT INTO reward_events VALUES (?,?,?,?)', ('migration:v1', 'Historical XP', str(xp), stamp))
        # Historical sessions were already included in the migration balance.
        conn.execute("INSERT OR IGNORE INTO reward_events SELECT 'session:'||id, 'Historical session', '0', ? FROM focus_sessions WHERE completed=1", (stamp,))
        conn.execute("INSERT OR IGNORE INTO reward_events SELECT 'task:'||id, 'Historical task', '0', ? FROM tasks WHERE status='completed'", (stamp,))
        conn.executemany('INSERT INTO evolution_unlocks VALUES (?,?)', [(i, stamp) for i in range(1, completed + 1)])
        RewardService.sync_achievements(conn)

    @staticmethod
    def sync_achievements(conn):
        productive, completed = conn.execute('SELECT COALESCE(SUM(productive_seconds),0), COALESCE(SUM(focus_sessions_count),0) FROM daily_stats').fetchone()
        days = [date.fromisoformat(r[0]) for r in conn.execute('SELECT date FROM daily_stats WHERE date<=? AND (productive_seconds>=900 OR focus_sessions_count>0) ORDER BY date', (date.today().isoformat(),))]
        best = run = 0
        previous = None
        for day in days:
            run = run + 1 if previous and day-previous == timedelta(days=1) else 1
            best = max(best,run); previous = day
        for earned, name in ((completed>=1,'First step'), (best>=3,'Finding rhythm'), (best>=7,'A week of you'), (productive>=36000,'Deep roots')):
            if earned:
                conn.execute('INSERT OR IGNORE INTO earned_achievements VALUES (?,?)', (name,datetime.now().isoformat()))

    @staticmethod
    def award(conn, event_id: str, kind: str, amount: int) -> bool:
        if not isinstance(amount, int) or amount < 0:
            raise ValueError('Reward XP must be a nonnegative integer')
        stamp = datetime.now().isoformat()
        inserted = conn.execute('INSERT OR IGNORE INTO reward_events VALUES (?,?,?,?)',
                                (event_id, kind, str(amount), stamp)).rowcount
        if not inserted:
            return False
        old = int(conn.execute('SELECT xp FROM pet_progress WHERE singleton=1').fetchone()[0])
        new = old + amount  # Python int + decimal TEXT storage: no SQLite int64 overflow.
        conn.execute('UPDATE pet_progress SET xp=? WHERE singleton=1', (str(new),))
        conn.executemany('INSERT OR IGNORE INTO evolution_unlocks VALUES (?,?)',
                         [(i, stamp) for i in range(progress_for(old).completed + 1, progress_for(new).completed + 1)])
        RewardService.sync_achievements(conn)
        return True

    @classmethod
    def session(cls, conn, session_id):
        row = conn.execute('SELECT completed FROM focus_sessions WHERE id=?', (session_id,)).fetchone()
        return bool(row and row[0] and cls.award(conn, f'session:{session_id}', 'Focus completed', RULES.session_xp))

    @classmethod
    def task(cls, conn, task_id):
        row = conn.execute('SELECT status FROM tasks WHERE id=?', (task_id,)).fetchone()
        return bool(row and row[0] == 'completed' and cls.award(conn, f'task:{task_id}', 'Task completed', RULES.task_xp))

    @classmethod
    def tracked(cls, conn, seconds):
        old = int(conn.execute('SELECT tracked_seconds FROM pet_progress WHERE singleton=1').fetchone()[0])
        new = old + seconds
        conn.execute('UPDATE pet_progress SET tracked_seconds=? WHERE singleton=1', (str(new),))
        amount = new // 60 - old // 60
        if amount:
            cls.award(conn, f'tracked:{new}', 'Productive minutes', amount)
