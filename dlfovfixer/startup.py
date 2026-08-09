"""Optional 'launch on Windows sign-in' via the per-user Run registry key."""

from __future__ import annotations

import os
import sys

try:
    import winreg  # Windows only
except ImportError:  # pragma: no cover
    winreg = None

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "DL-FOV-Fixer"


def _launch_command() -> str:
    """The command Windows should run at sign-in to start this tray app."""
    if getattr(sys, "frozen", False):
        # Packaged single-file exe.
        return '"%s"' % sys.executable
    # Dev mode: run the windowed launcher with pythonw so no console appears.
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo_root, "run.pyw")
    return '"%s" "%s"' % (pyw, script)


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _VALUE_NAME)
        return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    if winreg is None:
        return
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.SetValueEx(k, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
    else:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as k:
                winreg.DeleteValue(k, _VALUE_NAME)
        except OSError:
            pass
