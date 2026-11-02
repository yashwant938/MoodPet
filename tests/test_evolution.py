"""Durable rewards, evolution boundaries and real asynchronous Qt updates."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from PySide6.QtCore import Qt, QTimer, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.config.settings import SettingsManager
from app.productivity.progression import RULES, RULES_V1, STAGES, TOTAL_LEVELS, ProgressionRules, progress_for
from app.productivity.rewards import RewardService
from app.character.emotions import EmotionalPose, PetReactionState
from app.ui.pet_window import PetWindow
from app.storage.database import DatabaseManager


class ProgressionTests(unittest.TestCase):
    def test_every_boundary_and_twenty_stages(self):
        self.assertEqual(len(STAGES),20)
        for n in range(1,TOTAL_LEVELS+1):
            threshold = RULES.threshold(n)
            self.assertEqual(progress_for(threshold-1).completed,n-1)
            self.assertEqual(progress_for(threshold).completed,n)
            if n < TOTAL_LEVELS:
                self.assertEqual(progress_for(threshold).global_level,n+1)
            if n % 10 == 0 and n < TOTAL_LEVELS:
                self.assertEqual((progress_for(threshold).stage_index,progress_for(threshold).level),(n//10,1))
        self.assertTrue(all(RULES.cost(n+1)>RULES.cost(n) for n in range(1,TOTAL_LEVELS)))
        self.assertEqual(RULES.threshold(TOTAL_LEVELS),49800)
        self.assertEqual(progress_for(RULES.threshold(3)).minor_upgrade,1)
        self.assertEqual(progress_for(RULES.threshold(6)).minor_upgrade,2)

    def test_configurable_curve_and_maximum(self):
        rules=ProgressionRules(base_cost=10,cost_step=3)
        self.assertEqual(progress_for(10,rules).level,2)
        state=progress_for(10**100)
        self.assertTrue(state.mastered)
        self.assertEqual((state.stage_index,state.level),(19,10))

    def test_legacy_levels_never_fall(self):
        for old_level in range(1,250):
            self.assertGreaterEqual(progress_for((old_level-1)*250).global_level,min(old_level,TOTAL_LEVELS))

    def test_reaction_priority_expiry_and_break(self):
        state=PetReactionState()
        state.react(EmotionalPose.HAPPY,0,8)
        self.assertEqual(state.resolve(EmotionalPose.BREAK,1),EmotionalPose.BREAK)
        state.react(EmotionalPose.CELEBRATING,1,3)
        state.react(EmotionalPose.PROUD,1,2)
        self.assertEqual(state.resolve(EmotionalPose.FOCUSED,2),EmotionalPose.CELEBRATING)
        self.assertEqual(state.resolve(EmotionalPose.FOCUSED,5),EmotionalPose.FOCUSED)
        self.assertEqual(state.resolve(EmotionalPose.IDLE,9),EmotionalPose.IDLE)


class RewardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.db'
        self.db=DatabaseManager(self.path)

    def xp(self):
        return self.db.get_evolution_snapshot()['progress'].xp

    def test_session_partial_and_tracked_rewards_are_independent(self):
        session=self.db.record_focus_session(1500)
        self.db.record_focus_session(300,completed=False)
        self.db.record_focus_session(1800,source='automatic')
        self.db.update_today_seconds(productive_delta=59)
        self.db.update_today_seconds(productive_delta=1)
        with self.db._connection() as conn:
            self.assertFalse(RewardService.session(conn,session))
        self.assertEqual(self.xp(),51)
        self.assertEqual(DatabaseManager(self.path).get_evolution_snapshot()['progress'].xp,51)

    def test_task_completion_is_once_even_concurrently(self):
        task=self.db.create_task('Read paper')
        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _:self.db.update_task(task,status='completed'),range(10)))
        self.db.update_task(task,status='active')
        self.db.update_task(task,status='completed')
        self.db.update_task(9999,status='completed')
        self.assertEqual(self.xp(),10)

    def test_reset_preserves_xp_unlocks_and_achievements(self):
        self.db.record_focus_session(1500)
        self.db.record_focus_session(1500)
        before=self.db.get_evolution_snapshot()
        self.db.reset_today_stats()
        after=self.db.get_evolution_snapshot()
        self.assertEqual(after['progress'],before['progress'])
        self.assertEqual(after['unlocks'],(1,))
        self.assertIn('First step',after['achievements'])
        self.db.update_today_seconds(productive_delta=60)
        self.assertEqual(self.xp(),51)

    def test_reward_failure_rolls_back_session_and_counts(self):
        with self.db._connection() as conn:
            conn.execute("CREATE TRIGGER reject_reward BEFORE INSERT ON reward_events BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.record_focus_session(1500)
        self.assertEqual(self.xp(),0)
        self.assertEqual(self.db.get_recent_sessions(),[])
        self.assertEqual(self.db.get_today_stats()['focus_sessions_count'],0)

    def test_checkpoint_reward_and_unlock_acknowledgement_are_once(self):
        self.db.save_checkpoint(datetime.now(),0,2,False,new=True)
        self.db.save_checkpoint(datetime.now(),2,2,False)
        self.db.finish_checkpoint(completed=True)
        self.db.finish_checkpoint(completed=True)
        self.assertEqual(self.xp(),25)
        self.db.record_focus_session(1500)
        self.assertEqual(self.db.get_evolution_snapshot(claim_unlocks=True)['advance'],1)
        restarted=DatabaseManager(self.path)
        self.assertEqual(restarted.get_evolution_snapshot(claim_unlocks=True)['advance'],0)

    def test_migration_preserves_legacy_xp_history_and_completed_tasks(self):
        old=Path(self.temp.name)/'old.db'
        with closing(sqlite3.connect(old)) as conn,conn:
            conn.execute('CREATE TABLE daily_stats (date TEXT PRIMARY KEY, productive_seconds INTEGER, distracted_seconds INTEGER DEFAULT 0,idle_seconds INTEGER DEFAULT 0,focus_sessions_count INTEGER,longest_session_seconds INTEGER DEFAULT 0)')
            conn.execute("INSERT INTO daily_stats(date,productive_seconds,focus_sessions_count) VALUES ('2026-10-01',600,1)")
            conn.execute('CREATE TABLE focus_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT,date TEXT,start_time TEXT,end_time TEXT,duration_seconds INTEGER,completed INTEGER,source TEXT)')
            conn.execute("INSERT INTO focus_sessions VALUES (42,'2026-10-01','2026-10-01 10:00:00','2026-10-01 10:25:00',1500,1,'manual')")
            conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY,name TEXT,project TEXT,estimate_seconds INTEGER,status TEXT,created_at TEXT)")
            conn.execute("INSERT INTO tasks VALUES (9,'Historical task','',0,'completed','2026-10-01')")
        migrated=DatabaseManager(old)
        self.assertEqual(migrated.get_evolution_snapshot()['progress'].xp,35)
        self.assertEqual(migrated.get_evolution_snapshot(claim_unlocks=True)['advance'],0)
        with migrated._connection() as conn:
            self.assertFalse(RewardService.session(conn,42))
        self.assertEqual(migrated.get_recent_sessions()[0]['id'],42)
        self.assertIn('First step',migrated.get_evolution_snapshot()['achievements'])
        migrated.update_task(9,status='active')
        migrated.update_task(9,status='completed')
        self.assertEqual(DatabaseManager(old).get_evolution_snapshot()['progress'].xp,35)

    def test_arbitrary_precision_xp_survives_restart(self):
        with self.db._connection() as conn:
            RewardService.award(conn,'test:max','Test fixture',10**100)
        self.assertEqual(DatabaseManager(self.path).get_evolution_snapshot()['progress'].xp,10**100)
        self.assertEqual(len(self.db.get_evolution_snapshot()['unlocks']),TOTAL_LEVELS)

    def test_v1_curve_migration_preserves_xp_levels_and_fractional_progress(self):
        for index,xp in enumerate((0,25,55,340,6542,12400,15000,10**40)):
            path=Path(self.temp.name)/f'curve-{index}.db'
            original=DatabaseManager(path)
            old=progress_for(xp,RULES_V1)
            with original._connection() as conn:
                conn.execute('DROP TABLE pet_progress')
                conn.execute('CREATE TABLE pet_progress (singleton INTEGER PRIMARY KEY,xp TEXT,tracked_seconds TEXT,seen_level INTEGER)')
                conn.execute('INSERT INTO pet_progress VALUES (1,?,?,?)',(str(xp),'0',old.completed))
                conn.executemany('INSERT OR IGNORE INTO evolution_unlocks VALUES (?,?)',[(n,'2026-11-01') for n in range(1,old.completed+1)])
            migrated=DatabaseManager(path)
            snapshot=migrated.get_evolution_snapshot(claim_unlocks=True)
            new=snapshot['progress']
            self.assertEqual(new.xp,xp)
            self.assertGreaterEqual(new.completed,old.completed)
            self.assertEqual(snapshot['advance'],0)
            self.assertEqual(DatabaseManager(path).get_evolution_snapshot()['progress'],new)
            if not old.mastered:
                self.assertLess(abs(old.earned/old.required-new.earned/new.required),1/new.required+.0001)
            if xp==25:
                self.assertEqual(new.curve_credit,25)
                with migrated._connection() as conn:
                    RewardService.award(conn,'fixture:curve','Test fixture',52)
                self.assertEqual(migrated.get_evolution_snapshot()['unlocks'],(1,2))

    def test_demo_isolation(self):
        from app.demo import populate_demo
        demo_path=Path(self.temp.name)/'demo'
        demo_path.mkdir()
        demo=DatabaseManager(demo_path/'demo.db')
        settings=SettingsManager(demo_path/'config.json')
        populate_demo(demo,settings)
        self.assertEqual(settings.get('tracking_mode'),'manual')
        self.assertEqual(self.xp(),0)
        self.assertEqual(self.db.get_recent_sessions(),[])
        self.assertEqual(demo.get_evolution_snapshot()['progress'].stage.name,'Explorer')


class EvolutionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=SettingsManager(Path(self.temp.name)/'config.json')
        self.settings.set('animations_enabled',False)
        self.db=DatabaseManager(Path(self.temp.name)/'test.db')
        self.pet=PetWindow(self.settings,self.db)
        self.pet.logic_timer.stop(); self.pet.typing_timer.stop()
        self.pet.open_dashboard()
        self.dashboard=self.pet.dashboard
        self.dashboard.navigate(3)
        self.wait(lambda:self.pet.evolution_controller.snapshot is not None)

    def tearDown(self):
        self.pet.shutdown()
        self.dashboard.close(); self.pet.speech_bubble.close(); self.pet.close(); self.pet.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        self.app.processEvents()
        self.temp.cleanup()

    def wait(self,predicate):
        for _ in range(200):
            if predicate(): return
            QTest.qWait(10)
        self.assertTrue(predicate())

    def test_live_session_update_shared_pet_and_accessible_map(self):
        self.pet._start_focus_session(2)
        self.pet.focus_session_mgr.focus_remaining_sec=0
        self.pet._on_logic_tick()
        self.wait(lambda:self.pet.character_widget.evolution.xp==25)
        self.assertEqual(self.dashboard.journey.xp_bar.value(),500)
        self.db.record_focus_session(1500)
        self.wait(lambda:self.pet.character_widget.evolution.xp==50)
        journey=self.dashboard.journey
        self.assertEqual(self.dashboard.mini_pet.evolution,journey.pet.evolution)
        self.assertEqual(journey.pet.evolution,self.pet.character_widget.evolution)
        self.assertEqual(len(journey.map.nodes),10)
        self.assertIn('Level 2',journey.title.text())
        self.assertTrue(journey.map.nodes[0].isEnabled())
        self.assertTrue(journey.map.nodes[1].isEnabled())
        self.assertFalse(journey.map.nodes[2].isEnabled())
        QTest.mouseClick(journey.map.nodes[0],Qt.LeftButton)
        self.assertIn('Completed',journey.details.text())
        journey.stage_picker.setCurrentIndex(9)
        self.assertTrue(all(not n.isEnabled() for n in journey.map.nodes))

    def test_reduced_motion_and_quiet_on_unlock(self):
        self.settings.set('personality','quiet')
        with patch.object(self.pet.speech_bubble,'show_message') as speak:
            self.db.record_focus_session(1500)
            self.db.record_focus_session(1500)
            self.wait(lambda:self.pet.character_widget.evolution.xp==50)
            self.assertFalse(speak.called)
        self.assertFalse(self.pet.character_widget.timer.isActive())
        self.assertFalse(self.dashboard.journey.pet.timer.isActive())
        self.assertEqual(self.dashboard.journey.map.animation.state(),self.dashboard.journey.map.animation.State.Stopped)

    def test_reads_do_not_block_qt_and_subscriptions_clean_up(self):
        original=self.db.get_evolution_snapshot
        def slow(*args,**kwargs):
            time.sleep(.15)
            return original(*args,**kwargs)
        heartbeats=[]
        timer=QTimer(); timer.setInterval(10); timer.timeout.connect(lambda:heartbeats.append(1)); timer.start()
        with patch.object(self.db,'get_evolution_snapshot',side_effect=slow):
            self.pet.evolution_controller.request()
            QTest.qWait(220)
        timer.stop()
        self.assertGreater(len(heartbeats),5)
        self.pet.shutdown()
        self.assertEqual(len(self.db._listeners),0)

    def test_keyboard_details_survive_refresh_and_final_stage_is_usable(self):
        journey=self.dashboard.journey
        journey.map.nodes[0].setFocus()
        QTest.keyClick(journey.map.nodes[0],Qt.Key_Space)
        details=journey.details.text()
        journey._received(self.pet.evolution_controller.snapshot)
        self.assertEqual(journey.details.text(),details)
        with self.db._connection() as conn:
            RewardService.award(conn,'fixture:legend','Test fixture',10**50)
        self.wait(lambda:journey.progress.mastered)
        self.assertTrue(all(n.isEnabled() for n in journey.map.nodes))
        self.assertEqual(journey.xp_bar.value(),1000)
        self.assertIn('keeps growing',journey.summary.text())

    def test_all_stage_cosmetics_and_emotions_render(self):
        widget=self.pet.character_widget
        poses=(EmotionalPose.IDLE,EmotionalPose.FOCUSED,EmotionalPose.HAPPY,EmotionalPose.LAUGHING,
               EmotionalPose.EXCITED,EmotionalPose.SLEEPY,EmotionalPose.PROUD,EmotionalPose.CELEBRATING,EmotionalPose.BREAK)
        images=[]
        for stage in range(len(STAGES)):
            widget.set_evolution(progress_for(RULES.threshold(stage*10)))
            widget.set_pose(EmotionalPose.PROUD)
            images.append(widget.grab().toImage())
            self.assertFalse(images[-1].isNull())
        self.assertTrue(all(images[i]!=images[i+1] for i in range(len(STAGES)-1)))
        for pose in poses:
            widget.set_pose(pose)
            self.assertFalse(widget.grab().isNull())
