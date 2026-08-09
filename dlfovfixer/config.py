"""Persistent settings stored in ``%APPDATA%\\DL-FOV-Fixer\\config.json``.

Keeping the chosen FOV value here is what lets the tool "remember" the user's
preference across reboots and re-apply it after every Deadlock update.
"""

from __future__ import annotations

import json
import os

APP_NAME = "DL-FOV-Fixer"

CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "gameinfo_path": "",          # resolved path to gameinfo.gi
    "fov_value": "2",             # r_aspectratio value to enforce
    "auto_apply_on_start": True,  # re-apply automatically when the app launches
    "periodic_check_minutes": 10, # re-check while running (0 disables)
    "start_with_windows": False,  # launch on Windows sign-in
}


def load() -> dict:
    """Load config, filling in any missing keys with defaults."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            cfg.update({k: data[k] for k in DEFAULTS if k in data})
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    os.replace(tmp, CONFIG_PATH)


def exists() -> bool:
    return os.path.isfile(CONFIG_PATH)
