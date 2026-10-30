import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QMenu
from app.config.settings import SettingsManager
from app.storage.database import DatabaseManager
from app.productivity.activity_policy import ActivityPolicy
from app.productivity.score_engine import ProductivityState as State
from app.character.emotions import EmotionalPose
from app.character.personality import CharacterPersonality
from app.developer_events import send_event, receive_events
from app.ui.pet_window import PetWindow
from app.ui.welcome import WelcomeDialog


class NewExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = SettingsManager(self.root / "config.json")
        self.settings.set("animations_enabled", False)
        self.db = DatabaseManager(self.root / "fixture.db")
        self.window = {"process_name": "chrome.exe", "title": "YouTube", "pid": 1}

    def tearDown(self):
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.app.processEvents()
        self.temp.cleanup()

    def policy(self):
        self.settings.set("tracking_mode", "automatic")
        return ActivityPolicy(self.settings, clock=lambda: 100)

    def test_welcome_cancel_is_not_consent_and_accept_saves_choices(self):
        welcome = WelcomeDialog(self.settings)
        welcome.reject()
        self.assertFalse(SettingsManager(self.settings.config_path).get("onboarding_complete"))
        welcome.mode.setCurrentIndex(1)
        welcome.companion.setCurrentIndex(1)
        welcome.accept()
        saved = SettingsManager(self.settings.config_path)
        self.assertTrue(saved.get("onboarding_complete"))
        self.assertEqual(saved.get("tracking_mode"), "automatic")
        self.assertEqual(saved.get("companion_style"), "starlight")
        welcome.deleteLater()

    def test_temporary_correction_expires_and_is_not_saved(self):
        policy = self.policy()
        before = self.settings.config_path.read_text()
        policy.correct(self.window, State.PRODUCTIVE)
        self.assertEqual(policy.evaluate(self.window, 0)[0], State.PRODUCTIVE)
        self.assertEqual(self.settings.config_path.read_text(), before)
        self.assertEqual(policy.evaluate(self.window, 90)[0], State.IDLE)
        policy.clock = lambda: 1901
        self.assertNotEqual(policy.evaluate(self.window, 0)[0], State.PRODUCTIVE)

    def test_temporary_correction_is_window_specific_and_cleared_at_session_end(self):
        policy = self.policy()
        policy.correct(self.window, State.PRODUCTIVE)
        other = {**self.window, "title": "An unrelated window"}
        self.assertEqual(policy.evaluate(other, 0)[0], State.NEUTRAL)
        policy.clear_corrections()
        self.assertNotEqual(policy.evaluate(self.window, 0)[0], State.PRODUCTIVE)

    def test_tracking_pause_expires_and_can_be_resumed_early(self):
        policy = self.policy()
        policy.pause()
        self.assertFalse(policy.enabled)
        self.assertEqual(policy.evaluate(self.window, 0)[0], State.NEUTRAL)
        policy.clock = lambda: 1001
        self.assertTrue(policy.enabled)
        policy.pause()
        policy.resume()
        self.assertTrue(policy.enabled)

    def test_saved_keyword_is_explicit_and_overrides_default_app_rule(self):
        policy = self.policy()
        window = {"process_name": "code.exe", "title": "An unrelated game"}
        policy.correct(window, State.DISTRACTING, keyword="game")
        saved = SettingsManager(self.settings.config_path)
        self.assertEqual(ActivityPolicy(saved).evaluate(window, 0)[0], State.DISTRACTING)
        self.assertNotIn(window["title"], saved.config_path.read_text())
        self.assertEqual(saved.get("classification_rules"), {"game": "DISTRACTING"})

    def test_manual_and_paused_modes_do_not_read_foreground_idle_or_gaze(self):
        with patch("app.ui.pet_window.ActivityTracker") as tracker:
            pet = PetWindow(self.settings, self.db)
            pet.logic_timer.stop()
            pet.typing_timer.stop()
            try:
                with patch.object(pet.character_widget.eye_tracker, "update") as gaze:
                    pet._on_logic_tick()
                    pet._check_typing_activity()
                    pet.character_widget._on_tick()
                    gaze.assert_not_called()
                tracker.return_value.get_system_idle_seconds.assert_not_called()
                tracker.return_value.get_active_window_info.assert_not_called()
                self.settings.set("tracking_mode", "automatic")
                pet.pause_tracking()
                pet._on_logic_tick()
                pet._check_typing_activity()
                tracker.return_value.get_active_window_info.assert_not_called()
                self.assertEqual(self.db.get_today_stats()["productive_seconds"], 0)
            finally:
                self.close_pet(pet)

    def close_pet(self, pet):
        pet.shutdown()
        if pet.dashboard:
            pet.dashboard.close()
            pet.dashboard.deleteLater()
        pet.speech_bubble.close()
        pet.close()
        pet.deleteLater()

    def test_quick_actions_and_notes_reach_saved_constellation(self):
        pet = PetWindow(self.settings, self.db)
        pet.logic_timer.stop()
        pet.typing_timer.stop()
        try:
            with patch.object(pet, "_say"):
                pet.open_dashboard()
                pet.dashboard.session_note.setText("One small fix")
                menu = QMenu()
                pet.populate_quick_menu(menu)
                menu.actions()[0].trigger()
                self.assertTrue(pet.focus_session_mgr.is_focus_active)
                pet.focus_session_mgr.focus_remaining_sec = 0
                pet._on_logic_tick()
                pet.dashboard.refresh()
                self.assertEqual(pet.dashboard.journey.list.count(), 1)
                self.assertEqual(self.db.get_journey_sessions()[0]["note"], "One small fix")
                self.assertEqual(self.db.get_today_stats()["productive_seconds"], 0)
                menu.deleteLater()
        finally:
            self.close_pet(pet)

    def test_partial_session_does_not_light_a_star_and_notes_are_bounded(self):
        self.db.record_focus_session(300, completed=False, note="Stopped early")
        self.assertEqual(self.db.get_journey_sessions(), [])
        with self.assertRaises(ValueError):
            self.db.record_focus_session(300, note="x" * 121)

    def test_timer_only_goal_uses_saved_manual_time_without_activity_double_counting(self):
        self.db.record_focus_session(900, source="manual")
        self.db.record_focus_session(600, source="automatic")
        pet = PetWindow(self.settings, self.db)
        pet.logic_timer.stop()
        pet.typing_timer.stop()
        try:
            pet.open_dashboard()
            self.assertEqual(pet.dashboard.stat_values["productive"].text(), "15m")
            self.assertEqual(self.db.get_today_stats()["productive_seconds"], 0)
            self.assertIn("15m of", pet.dashboard.goal_summary.text())
        finally:
            self.close_pet(pet)

    def test_developer_reaction_does_not_award_progress_or_start_timer(self):
        self.settings.set("developer_events_enabled", True)
        pet = PetWindow(self.settings, self.db)
        pet.logic_timer.stop()
        pet.typing_timer.stop()
        try:
            before = self.db.get_today_stats()
            send_event(self.settings, "build-passed")
            with patch.object(pet, "_say") as say:
                pet._on_logic_tick()
                say.assert_called_once()
            self.assertEqual(before, self.db.get_today_stats())
            self.assertFalse(pet.focus_session_mgr.is_focus_active)
            self.assertEqual(self.db.get_journey_sessions(), [])
        finally:
            self.close_pet(pet)

    def test_event_opt_in_validation_expiry_and_single_consumption(self):
        with self.assertRaises(ValueError):
            send_event(self.settings, "build-passed")
        self.settings.set("developer_events_enabled", True)
        send_event(self.settings, "tests-passed")
        self.assertEqual(receive_events(self.settings), ["tests-passed"])
        self.assertEqual(receive_events(self.settings), [])
        with self.assertRaises(ValueError):
            send_event(self.settings, "execute-shell")
        (self.root / "events" / "old.json").write_text(json.dumps({"time": 0, "event": "build-passed"}))
        (self.root / "events" / "bad.json").write_text("[]")
        self.assertEqual(receive_events(self.settings), [])

    def test_quiet_tone_suppresses_speech_and_gentle_text_is_supportive(self):
        self.assertEqual(CharacterPersonality.get_speech(EmotionalPose.ANGRY, "quiet"), "")
        self.assertNotIn("CLOSE", CharacterPersonality.get_speech(EmotionalPose.ANGRY))
        pet = PetWindow(self.settings, self.db)
        pet.logic_timer.stop()
        pet.typing_timer.stop()
        try:
            self.settings.set("personality", "quiet")
            with patch.object(pet.speech_bubble, "show_message") as message:
                pet._say("A developer event")
                message.assert_not_called()
        finally:
            self.close_pet(pet)
