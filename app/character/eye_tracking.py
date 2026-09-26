import math
import win32gui
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

class EyeTracker:
    """Tracks active window position AND typing cadence to smoothly animate robot LED eyes."""

    def __init__(self, lerp_speed: float = 0.15):
        self.lerp_speed = lerp_speed
        self.current_gaze = QPointF(0.0, 0.0) # (dx, dy) in [-1.0, 1.0]
        self.target_gaze = QPointF(0.0, 0.0)
        self.typing_anim_time = 0.0

    def update(self, pet_global_pos: QPointF, is_typing: bool = False, dt: float = 0.016):
        """Calculates active window center + typing glance offset with smooth lerp."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                win_cx = (left + right) / 2.0
                win_cy = (top + bottom) / 2.0

                screen = QApplication.primaryScreen().availableGeometry()
                pet_cx = pet_global_pos.x()
                pet_cy = pet_global_pos.y()

                dx = (win_cx - pet_cx) / (screen.width() / 2.0)
                dy = (win_cy - pet_cy) / (screen.height() / 2.0)

                dx = max(-1.0, min(1.0, dx))
                dy = max(-1.0, min(1.0, dy))

                self.target_gaze = QPointF(dx, dy)
            else:
                self.target_gaze = QPointF(0.0, 0.0)
        except Exception:
            self.target_gaze = QPointF(0.0, 0.0)

        # Apply typing glance movement if typing is detected
        if is_typing:
            self.typing_anim_time += dt
            # Eyes glance down towards keyboard & alternate slightly left/right while typing
            typing_dy = 0.45 # Glance down at keyboard
            typing_dx = math.sin(self.typing_anim_time * 8.0) * 0.35
            
            # Blend window gaze with typing gaze
            target_x = self.target_gaze.x() * 0.5 + typing_dx * 0.5
            target_y = self.target_gaze.y() * 0.3 + typing_dy * 0.7
            self.target_gaze = QPointF(target_x, target_y)

        # Smooth Lerp
        cur_x = self.current_gaze.x() + (self.target_gaze.x() - self.current_gaze.x()) * self.lerp_speed
        cur_y = self.current_gaze.y() + (self.target_gaze.y() - self.current_gaze.y()) * self.lerp_speed
        self.current_gaze = QPointF(cur_x, cur_y)

    def get_eye_offset(self, max_offset_px: float = 6.0) -> QPointF:
        """Returns pixel offset vector for rendering LED pupils."""
        return QPointF(self.current_gaze.x() * max_offset_px, self.current_gaze.y() * max_offset_px)
