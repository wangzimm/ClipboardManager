"""Settings management — read/write config, auto-start, retention."""
import os
import sys
import ctypes

from database import get_setting, set_setting

# Retention stored in hours, default 72 (3 days)
_HOURS_MAP = [
    (1, "1 小时"),
    (3, "3 小时"),
    (6, "6 小时"),
    (12, "12 小时"),
    (24, "1 天"),
    (72, "3 天"),
    (120, "5 天"),
    (168, "7 天"),
]


_CLEANUP_HOURS = [
    (1, "1 小时"),
    (3, "3 小时"),
    (12, "12 小时"),
    (24, "1 天"),
    (168, "7 天"),
]


def get_hours_options():
    """Return list of (hours, label) tuples for settings UI."""
    return _HOURS_MAP


def get_cleanup_hours_options():
    """Return shorter list of (hours, label) for the manual cleanup dialog."""
    return _CLEANUP_HOURS


def get_retention_hours():
    return int(get_setting("retention_hours", "72"))


def set_retention_hours(hours):
    set_setting("retention_hours", str(hours))


# ── Legacy compat ──────────────────────────────────────────────────
def get_retention_days():
    """Backwards-compat: convert old retention_days setting to hours."""
    legacy = get_setting("retention_days", None)
    if legacy is not None:
        return int(legacy)
    return max(1, get_retention_hours() // 24)


def set_retention_days(days):
    set_retention_hours(days * 24)


def get_auto_start():
    return get_setting("auto_start", "true") == "true"


def set_auto_start(enable):
    set_setting("auto_start", "true" if enable else "false")
    _win_auto_start(enable)


def _win_auto_start(enable):
    import winreg

    key = r"Software\Microsoft\Windows\CurrentVersion\Run"

    if getattr(sys, "frozen", False):
        exe_path = sys.executable
    else:
        exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

    if enable:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_WRITE) as reg:
            winreg.SetValueEx(reg, "ClipboardManager", 0, winreg.REG_SZ, exe_path)
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_WRITE) as reg:
                winreg.DeleteValue(reg, "ClipboardManager")
        except FileNotFoundError:
            pass
