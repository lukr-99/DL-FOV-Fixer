"""DL-FOV-Fixer tray application.

Threading model
---------------
tkinter is not thread-safe, and pystray's ``run()`` blocks. So:

* The **main thread** owns a hidden Tk root and runs its ``mainloop()``.
  Every dialog / message box happens here.
* The **tray icon** runs on a worker thread. Its menu callbacks marshal any
  UI work back to the main thread via :func:`_ui_call`.

This keeps all Tk calls on one thread while the tray stays responsive.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import pystray

from . import config, gameinfo, iconfactory, locator, startup

APP_TITLE = "DL FOV Fixer"

_cfg: dict = {}
_icon: "pystray.Icon | None" = None
_root: "tk.Tk | None" = None
_periodic_job = None


# --------------------------------------------------------------------------
# Cross-thread UI marshaling
# --------------------------------------------------------------------------

def _ui_call(fn):
    """Run ``fn`` on the Tk main thread and return its result synchronously."""
    box: dict = {}
    done = threading.Event()

    def wrapper():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - propagate to caller
            box["error"] = exc
        finally:
            done.set()

    _root.after(0, wrapper)
    done.wait()
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _notify(message: str, title: str = APP_TITLE):
    if _icon is not None:
        try:
            _icon.notify(message, title)
        except Exception:  # pragma: no cover - notifications are best-effort
            pass


# --------------------------------------------------------------------------
# Dialogs (always invoked via _ui_call)
# --------------------------------------------------------------------------

def _dialog_parent():
    _root.attributes("-topmost", True)
    return _root


def _ask_value(current: str):
    def run():
        p = _dialog_parent()
        return simpledialog.askstring(
            APP_TITLE,
            "Enter r_aspectratio value.\n\n"
            "Higher = wider FOV.  Examples:\n"
            "  1.75 ≈ 80°    2.15 ≈ 90°    2.49 ≈ 100°\n"
            "  2.66 ≈ 105°   2.83 ≈ 110°   3.00 ≈ 115°",
            initialvalue=current, parent=p,
        )
    return _ui_call(run)


def _ask_gameinfo_path():
    def run():
        p = _dialog_parent()
        return filedialog.askopenfilename(
            title="Locate Deadlock's gameinfo.gi",
            parent=p,
            filetypes=[("Deadlock game info", "gameinfo.gi"), ("All files", "*.*")],
        )
    return _ui_call(run)


def _show_info(message: str):
    _ui_call(lambda: messagebox.showinfo(APP_TITLE, message, parent=_dialog_parent()))


# --------------------------------------------------------------------------
# Core operations
# --------------------------------------------------------------------------

def _path() -> str:
    return _cfg.get("gameinfo_path", "")


def _have_file() -> bool:
    return bool(_path()) and os.path.isfile(_path())

def _fov_label(value) -> str:
    deg = gameinfo.aspect_to_fov(value)
    return f"{value} (~{deg}°)" if deg is not None else str(value)


def _ensure_located(interactive: bool) -> bool:
    """Make sure we have a valid gameinfo.gi path. Returns True if we do."""
    if _have_file():
        return True
    found = locator.autolocate()
    if found:
        _cfg["gameinfo_path"] = found
        config.save(_cfg)
        return True
    if interactive:
        picked = _ask_gameinfo_path()
        if picked and locator.looks_like_gameinfo(picked):
            _cfg["gameinfo_path"] = os.path.normpath(picked)
            config.save(_cfg)
            return True
        if picked:
            _show_info("That doesn't look like a Deadlock gameinfo.gi file.")
    return False


def apply_now(interactive: bool = True, notify: bool = True) -> bool:
    if not _ensure_located(interactive):
        if interactive:
            _notify("Couldn't find gameinfo.gi. Use 'Locate gameinfo.gi…'.")
        return False
    try:
        status, prev = gameinfo.patch(_path(), _cfg["fov_value"])
    except Exception as exc:  # noqa: BLE001
        _notify(f"Failed to update file: {exc}")
        return False
    if notify:
        val = _cfg["fov_value"]
        if status == gameinfo.ALREADY_OK:
            _notify(f"FOV already set — r_aspectratio {_fov_label(val)}.")
        else:
            _notify(f"FOV applied — r_aspectratio {_fov_label(val)}.")
    return True


def check_now():
    if not _ensure_located(interactive=True):
        _notify("Couldn't find gameinfo.gi. Use 'Locate gameinfo.gi…'.")
        return
    current = gameinfo.read_current(_path())
    target = _cfg["fov_value"]
    if current is None:
        _notify("r_aspectratio is not set in the file. Click 'Apply FOV now'.")
    elif current == target:
        _notify(f"File is up to date — r_aspectratio {_fov_label(current)}.")
    else:
        _notify(
            f"File has {_fov_label(current)}, your target is {_fov_label(target)}. "
            "Click 'Apply FOV now'."
        )


def set_value(value: str, apply: bool = True):
    norm = gameinfo.normalize_value(value)
    if norm is None:
        _notify("Please enter a number between 0.5 and 6.0 (e.g. 2.15).")
        return
    _cfg["fov_value"] = norm
    config.save(_cfg)
    if apply:
        apply_now(interactive=True, notify=True)
    if _icon is not None:
        _icon.update_menu()


# --------------------------------------------------------------------------
# Menu callbacks
# --------------------------------------------------------------------------

def _on_apply(icon, item):
    apply_now(interactive=True, notify=True)
    icon.update_menu()


def _on_check(icon, item):
    check_now()
    icon.update_menu()


def _on_custom(icon, item):
    value = _ask_value(_cfg["fov_value"])
    if value is not None:
        set_value(value, apply=True)


def _make_preset(aspect: str):
    def handler(icon, item):
        set_value(aspect, apply=True)
    return handler


def _on_open_file(icon, item):
    if not _ensure_located(interactive=True):
        _notify("Couldn't find gameinfo.gi. Use 'Locate gameinfo.gi…'.")
        return
    path = _path()
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except OSError:
        subprocess.Popen(["notepad.exe", path])


def _on_locate(icon, item):
    picked = _ask_gameinfo_path()
    if not picked:
        return
    if locator.looks_like_gameinfo(picked):
        _cfg["gameinfo_path"] = os.path.normpath(picked)
        config.save(_cfg)
        _notify("gameinfo.gi location saved.")
        icon.update_menu()
    else:
        _show_info("That doesn't look like a Deadlock gameinfo.gi file.")


def _on_toggle_auto(icon, item):
    _cfg["auto_apply_on_start"] = not _cfg["auto_apply_on_start"]
    config.save(_cfg)
    icon.update_menu()


def _on_toggle_startup(icon, item):
    enable = not startup.is_enabled()
    startup.set_enabled(enable)
    _cfg["start_with_windows"] = enable
    config.save(_cfg)
    icon.update_menu()


def _on_about(icon, item):
    _show_info(
        "DL-FOV-Fixer\n\n"
        "Keeps Deadlock's FOV fix (r_aspectratio in gameinfo.gi) applied,\n"
        "and re-applies it after game updates wipe the file.\n\n"
        f"File: {_path() or '(not located)'}\n"
        f"Target: r_aspectratio {_fov_label(_cfg['fov_value'])}\n"
        f"Backup: {gameinfo.backup_path(_path()) if _have_file() else '(n/a)'}"
    )


def _on_quit(icon, item):
    if _root is not None:
        _root.after(0, _root.quit)
    icon.stop()


# --------------------------------------------------------------------------
# Menu construction
# --------------------------------------------------------------------------

def _status_text() -> str:
    if not _have_file():
        return "gameinfo.gi not located"
    current = gameinfo.read_current(_path())
    if current is None:
        return "not applied yet"
    return "up to date" if current == _cfg["fov_value"] else "needs re-apply"


def _build_menu() -> pystray.Menu:
    presets = [
        pystray.MenuItem(
            f"{deg}°   (r_aspectratio {asp})",
            _make_preset(asp),
            radio=True,
            checked=lambda item, a=asp: _cfg["fov_value"] == a,
        )
        for deg, asp in gameinfo.PRESETS
    ]
    presets.append(pystray.Menu.SEPARATOR)
    presets.append(pystray.MenuItem("Custom value…", _on_custom))

    return pystray.Menu(
        pystray.MenuItem(lambda item: f"{APP_TITLE} — {_status_text()}", None, enabled=False),
        pystray.MenuItem(
            lambda item: f"Target: r_aspectratio {_fov_label(_cfg['fov_value'])}",
            None, enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Apply FOV now", _on_apply, default=True),
        pystray.MenuItem("Check file now", _on_check),
        pystray.MenuItem("Set FOV value", pystray.Menu(*presets)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open gameinfo.gi", _on_open_file),
        pystray.MenuItem("Locate gameinfo.gi…", _on_locate),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Apply automatically on start", _on_toggle_auto,
            checked=lambda item: _cfg["auto_apply_on_start"],
        ),
        pystray.MenuItem(
            "Start with Windows", _on_toggle_startup,
            checked=lambda item: startup.is_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("About", _on_about),
        pystray.MenuItem("Quit", _on_quit),
    )


# --------------------------------------------------------------------------
# Startup / periodic behaviour
# --------------------------------------------------------------------------

def _first_run_setup():
    """On the very first launch, locate the file and adopt any existing value."""
    if config.exists():
        return
    if _ensure_located(interactive=True):
        current = gameinfo.read_current(_path())
        norm = gameinfo.normalize_value(current) if current else None
        if norm:
            # Respect the value already in the file instead of overwriting it.
            _cfg["fov_value"] = norm
    config.save(_cfg)
    _notify(
        "DL-FOV-Fixer is running in the tray. It will keep your Deadlock FOV "
        "applied after updates."
    )


def _on_setup(icon):
    """Runs on the tray thread once the icon is visible."""
    icon.visible = True
    _first_run_setup()
    if _cfg.get("auto_apply_on_start", True):
        apply_now(interactive=False, notify=True)
    _schedule_periodic()
    icon.update_menu()


def _schedule_periodic():
    global _periodic_job
    minutes = int(_cfg.get("periodic_check_minutes", 0) or 0)
    if minutes <= 0 or _root is None:
        return

    def tick():
        if _have_file() and _cfg.get("auto_apply_on_start", True):
            try:
                status, _ = gameinfo.patch(_path(), _cfg["fov_value"])
                if status != gameinfo.ALREADY_OK:
                    _notify(
                        f"Re-applied FOV after a game change — "
                        f"r_aspectratio {_fov_label(_cfg['fov_value'])}."
                    )
            except Exception:  # noqa: BLE001 - never let the timer die loudly
                pass
        _schedule_periodic()

    _periodic_job = _root.after(minutes * 60 * 1000, tick)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    global _cfg, _icon, _root

    _cfg = config.load()

    _root = tk.Tk()
    _root.withdraw()
    _root.title(APP_TITLE)

    _icon = pystray.Icon(
        "dl-fov-fixer",
        icon=iconfactory.build_image(64),
        title=APP_TITLE,
        menu=_build_menu(),
    )

    threading.Thread(
        target=lambda: _icon.run(setup=_on_setup), name="tray", daemon=True
    ).start()

    try:
        _root.mainloop()
    finally:
        try:
            _icon.stop()
        except Exception:  # pragma: no cover
            pass


if __name__ == "__main__":
    main()
