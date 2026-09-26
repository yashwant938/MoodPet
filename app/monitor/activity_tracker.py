import ctypes
import os
import win32gui
import win32process
import psutil

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_ulong)
    ]

class ActivityTracker:
    """Monitors system active window title, process name, and mouse/keyboard idle duration."""

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._kernel32.GetTickCount64.restype = ctypes.c_ulonglong

    def get_system_idle_seconds(self) -> float:
        """Returns elapsed seconds since last mouse or keyboard input."""
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if self._user32.GetLastInputInfo(ctypes.byref(lii)):
            # GetTickCount64 returns milliseconds since system boot
            current_tick = self._kernel32.GetTickCount64()
            # LASTINPUTINFO uses a wrapping 32-bit tick even on 64-bit Windows.
            idle_ms = (current_tick - lii.dwTime) & 0xFFFFFFFF
            return max(0.0, idle_ms / 1000.0)
        return 0.0

    def get_active_window_info(self) -> dict:
        """Returns info about current foreground window (title, process_name, pid)."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return {"title": "", "process_name": "", "pid": 0}

            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            process_name = ""
            if pid > 0:
                try:
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    process_name = ""

            return {
                "title": window_title,
                "process_name": process_name,
                "pid": pid
            }
        except Exception as e:
            return {"title": "", "process_name": "", "pid": 0}
