"""Locate Deadlock's ``gameinfo.gi`` automatically from a Steam install.

Strategy:
  1. Find the main Steam install (registry, then common fallback paths).
  2. Enumerate every Steam library folder via ``libraryfolders.vdf``.
  3. Look for ``steamapps\\common\\Deadlock\\game\\citadel\\gameinfo.gi``.
"""

from __future__ import annotations

import os
import re

try:
    import winreg  # Windows only
except ImportError:  # pragma: no cover - non-Windows dev machines
    winreg = None

DEADLOCK_APPID = "1422450"

# Path of gameinfo.gi relative to a Steam library root.
_REL_GAMEINFO = os.path.join(
    "steamapps", "common", "Deadlock", "game", "citadel", "gameinfo.gi"
)

_COMMON_STEAM_DIRS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
    r"D:\Steam",
    r"D:\SteamLibrary",
    r"E:\Steam",
    r"E:\SteamLibrary",
]


def _steam_from_registry():
    if winreg is None:
        return None
    for hive, key, val in [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]:
        try:
            with winreg.OpenKey(hive, key) as k:
                value, _ = winreg.QueryValueEx(k, val)
                if value:
                    return os.path.normpath(value)
        except OSError:
            continue
    return None


def _steam_roots():
    roots = []
    reg = _steam_from_registry()
    if reg:
        roots.append(reg)
    for p in _COMMON_STEAM_DIRS:
        if os.path.isdir(p):
            roots.append(os.path.normpath(p))
    # De-duplicate while preserving order.
    return list(dict.fromkeys(roots))


def _library_folders(steam_root: str):
    """All Steam library roots reachable from a given Steam install."""
    libs = [steam_root]
    vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # "path"  "D:\\SteamLibrary"  -> vdf doubles the backslashes.
        for m in re.finditer(r'"path"\s*"([^"]+)"', text):
            libs.append(os.path.normpath(m.group(1).replace("\\\\", "\\")))
    except OSError:
        pass
    return list(dict.fromkeys(libs))


def autolocate():
    """Return the path to Deadlock's gameinfo.gi, or ``None`` if not found."""
    for root in _steam_roots():
        for lib in _library_folders(root):
            candidate = os.path.join(lib, _REL_GAMEINFO)
            if os.path.isfile(candidate):
                return candidate
    return None


def looks_like_gameinfo(path: str) -> bool:
    """Cheap sanity check that a user-picked file is a Deadlock gameinfo.gi."""
    if not path or os.path.basename(path).lower() != "gameinfo.gi":
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return "GameInfo" in head
