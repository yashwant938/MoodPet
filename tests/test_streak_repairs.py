"""Recorded focus totals and atomic, monthly free streak protection."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path
from app.storage.database import DatabaseManager


class StreakRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=DatabaseManager(Path(self.temp.name)/'history.db')

    def focus(self,day,seconds=1,completed=False,source='manual'):
        self.db.record_focus_session(seconds,completed=completed,source=source,end_time=datetime.combine(day,time(12)))

    def test_any_positive_saved_focus_counts_without_minimum_or_completion(self):
        today=date(2026,11,10)
        self.focus(today-timedelta(days=1),seconds=1)
        self.focus(today,seconds=12)
        self.focus(today+timedelta(days=1),seconds=100)
        self.assertEqual(self.db.get_streaks(today),{'current_streak':2,'best_streak':2,'active_days':2})
        self.assertEqual(self.db.get_streaks(today+timedelta(days=3))['current_streak'],0)

    def test_one_tracked_productive_second_counts_but_idle_does_not(self):
        self.db.update_today_seconds(idle_delta=7200,distracted_delta=3600)
        self.assertEqual(self.db.get_streaks()['current_streak'],0)
        self.db.update_today_seconds(productive_delta=1)
        self.assertEqual(self.db.get_streaks()['current_streak'],1)

    def test_saved_focus_history_shows_six_hours_and_excludes_automatic_sessions(self):
        day=date(2026,11,7)
        self.focus(day,21600,True)
        self.focus(day,600,False)
        self.focus(day,7200,True,'automatic')
        rows=self.db.get_focus_history(7,day)
        self.assertEqual(len(rows),7)
        self.assertEqual(rows[-1]['productive_seconds'],22200)
        self.assertEqual(sum(row['productive_seconds'] for row in rows),22200)
        self.assertEqual(self.db.get_daily_history(7,day)[-1]['productive_seconds'],0)

    def test_two_repairs_bridge_gaps_without_awarding_work_or_xp(self):
        today=date(2026,11,10)
        self.focus(today-timedelta(days=3),10)
        self.focus(today,10)
        before=self.db.get_evolution_snapshot()['progress'].xp
        self.assertEqual(self.db.get_streaks(today)['current_streak'],1)
        self.db.repair_streak_day(today-timedelta(days=1),today=today)
        self.db.repair_streak_day(today-timedelta(days=2),today=today)
        self.assertEqual(self.db.get_streaks(today),{'current_streak':4,'best_streak':4,'active_days':2})
        self.assertEqual(self.db.get_evolution_snapshot()['progress'].xp,before)
        self.assertEqual(len(self.db.get_recent_sessions()),2)
        self.assertEqual(self.db.get_streak_repair_status(today)['remaining'],0)
        self.assertEqual(DatabaseManager(self.db.db_path).get_streaks(today)['current_streak'],4)

    def test_monthly_allowance_renews_without_stockpiling_or_repair_replay(self):
        october=date(2026,10,31)
        self.focus(date(2026,10,20))
        self.db.repair_streak_day(date(2026,10,28),today=october)
        self.db.repair_streak_day(date(2026,10,29),today=october)
        with self.assertRaises(ValueError):
            self.db.repair_streak_day(date(2026,10,27),today=october)
        november=date(2026,11,1)
        self.assertEqual(self.db.get_streak_repair_status(november)['remaining'],2)
        with self.assertRaises(ValueError):
            self.db.repair_streak_day(date(2026,10,28),today=november)
        self.assertEqual(self.db.get_streak_repair_status(november)['remaining'],2)
        self.db.repair_streak_day(date(2026,10,31),today=november)
        self.assertEqual(self.db.get_streak_repair_status(november)['remaining'],1)
        self.assertEqual(self.db.get_streak_repair_status(date(2026,12,1))['remaining'],2)

    def test_concurrent_redemptions_never_exceed_monthly_limit(self):
        today=date(2026,11,10)
        self.focus(today-timedelta(days=10))
        def redeem(offset):
            try:
                self.db.repair_streak_day(today-timedelta(days=offset),today=today)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=5) as pool:
            results=list(pool.map(redeem,range(1,6)))
        self.assertEqual(sum(results),2)
        self.assertEqual(self.db.get_streak_repair_status(today)['remaining'],0)

    def test_invalid_days_do_not_spend_tokens_and_empty_profiles_have_no_fake_streak(self):
        today=date(2026,11,10)
        self.assertEqual(self.db.get_streak_repair_status(today)['eligible_dates'],[])
        with self.assertRaises(ValueError):
            self.db.repair_streak_day(today-timedelta(days=1),today=today)
        self.focus(today-timedelta(days=4))
        for day in (today,today+timedelta(days=1),today-timedelta(days=4),today-timedelta(days=31)):
            with self.assertRaises(ValueError):
                self.db.repair_streak_day(day,today=today)
        self.assertEqual(self.db.get_streak_repair_status(today)['remaining'],2)
