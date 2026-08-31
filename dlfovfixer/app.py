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
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import pystray

from . import config, gameinfo, iconfactory, locator, startup, tweaks

APP_TITLE = "DL FOV Fixer"

_cfg: dict = {}
_icon: "pystray.Icon | None" = None
_root: "tk.Tk | None" = None
_periodic_job = None
_status_error = False  # set when a locate/read/write actually fails


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


def _ask_yesno(message: str) -> bool:
    return bool(_ui_call(
        lambda: messagebox.askyesno(APP_TITLE, message, parent=_dialog_parent())
    ))


def _ask_paste():
    """Multiline paste box for importing someone's config. Returns text or None."""
    def run():
        _dialog_parent()
        top = tk.Toplevel(_root)
        top.title("Import Deadlock config")
        top.attributes("-topmost", True)
        top.geometry("660x480")
        tk.Label(
            top, justify="left",
            text=("Paste a Deadlock config below (ConVars, SceneSystem and/or\n"
                  "video.cfg settings). Keys are sorted automatically:\n"
                  "  setting.* → video.cfg    PascalCase → SceneSystem    "
                  "other → ConVars\n"
                  "r_aspectratio sets your FOV. Comments and headers are ignored."),
        ).pack(anchor="w", padx=10, pady=(10, 6))
        txt = tk.Text(top, wrap="none", width=84, height=22, undo=True)
        txt.pack(fill="both", expand=True, padx=10, pady=4)
        txt.focus_set()
        result = {"text": None}
        bar = tk.Frame(top)
        bar.pack(fill="x", padx=10, pady=(4, 10))

        def do_import():
            result["text"] = txt.get("1.0", "end")
            top.destroy()

        def do_cancel():
            top.destroy()

        tk.Button(bar, text="Import", width=12, command=do_import).pack(side="right")
        tk.Button(bar, text="Cancel", width=12, command=do_cancel).pack(
            side="right", padx=(0, 8))
        top.bind("<Escape>", lambda e: do_cancel())
        top.grab_set()
        _root.wait_window(top)
        return result["text"]
    return _ui_call(run)


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


def _compute_status() -> str:
    """Live tri-state used to color the tray icon."""
    if _status_error:
        return "error"
    if not _have_file():
        return "error"        # can't find the game file -> a problem worth red
    try:
        current = gameinfo.read_current(_path())
    except Exception:  # noqa: BLE001
        return "error"
    if current is None:
        return "idle"         # located, but FOV not applied yet
    return "ok" if current == _cfg["fov_value"] else "idle"  # idle = drifted/waiting


def _refresh_icon():
    """Recolor the tray icon and tooltip to match the current status."""
    if _icon is None:
        return
    try:
        _icon.icon = iconfactory.build_image(64, _compute_status())
        _icon.title = f"{APP_TITLE} — {_status_text()}"
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


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


def _count(results):
    applied = sum(1 for _, a in results if a in ("updated", "added"))
    skipped = sum(1 for _, a in results if a == "skipped_block")
    return applied, skipped


def apply_now(interactive: bool = True, notify: bool = True) -> bool:
    """Apply the FOV plus (if enabled) all stored tweaks in one pass."""
    global _status_error
    if not _ensure_located(interactive):
        _refresh_icon()
        if interactive:
            _notify("Couldn't find gameinfo.gi. Use 'Locate gameinfo.gi…'.")
        return False

    tw = _cfg["tweaks"]
    apply_tw = bool(_cfg.get("apply_tweaks", True))
    try:
        summary = gameinfo.apply_config(
            _path(), _cfg["fov_value"],
            convars=tw["convars"], scenesystem=tw["scenesystem"],
            apply_tweaks=apply_tw,
        )
        video = {"changed": False, "created": False, "results": []}
        if apply_tw and tw["video"]:
            video = gameinfo.merge_video_cfg(
                gameinfo.video_settings_path(_path()), tw["video"])
    except PermissionError as exc:
        # A sharing/lock violation just means the game (or a mod manager) has
        # the file open right now — transient, not a real failure. It'll be
        # re-applied on the next pass once the file is free.
        if getattr(exc, "winerror", None) in (32, 33):
            _status_error = False
            if interactive:
                _notify("File is in use (is Deadlock running?). It'll apply "
                        "automatically once the game is closed.")
            _refresh_icon()
            return False
        _status_error = True
        _refresh_icon()
        _notify(f"Failed to update files: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001
        _status_error = True
        _refresh_icon()
        _notify(f"Failed to update files: {exc}")
        return False

    _status_error = False
    if notify:
        _notify(_apply_message(summary, video, apply_tw))
    _refresh_icon()
    return True


def _apply_message(summary, video, apply_tw) -> str:
    fov = _fov_label(_cfg["fov_value"])
    changed = summary["changed"] or video["changed"]
    lead = "Applied" if changed else "Already up to date"
    parts = [f"FOV {fov}"]
    if apply_tw:
        cv_a, cv_s = _count(summary["convars"])
        sc_a, sc_s = _count(summary["scenesystem"])
        # cv includes the FOV entry; show tweak convars only.
        extra = max(cv_a - 1, 0)
        bits = []
        if extra or _cfg["tweaks"]["convars"]:
            bits.append(f"{extra} convars")
        if _cfg["tweaks"]["scenesystem"]:
            bits.append(f"{sc_a} scene")
        if _cfg["tweaks"]["video"]:
            va, _vs = _count(video["results"])
            bits.append(f"{va} video" + (" (created)" if video.get("created") else ""))
        if bits:
            parts.append(" + ".join(bits))
        skipped = cv_s + sc_s
        if skipped:
            parts.append(f"{skipped} skipped (nested)")
    return f"{lead} — " + " · ".join(parts) + "."


def check_now():
    global _status_error
    if not _ensure_located(interactive=True):
        _refresh_icon()
        _notify("Couldn't find gameinfo.gi. Use 'Locate gameinfo.gi…'.")
        return
    current = gameinfo.read_current(_path())
    _status_error = False
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
    _refresh_icon()


def set_value(value: str, apply: bool = True):
    norm = gameinfo.normalize_value(value)
    if norm is None:
        _notify("Please enter a number between 0.5 and 6.0 (e.g. 2.15).")
        return
    _cfg["fov_value"] = norm
    config.save(_cfg)
    if apply:
        apply_now(interactive=True, notify=True)
    _refresh_icon()
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
    global _status_error
    picked = _ask_gameinfo_path()
    if not picked:
        return
    if locator.looks_like_gameinfo(picked):
        _cfg["gameinfo_path"] = os.path.normpath(picked)
        config.save(_cfg)
        _status_error = False
        _notify("gameinfo.gi location saved.")
        _refresh_icon()
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


# --- Extra tweaks (pasted config) -----------------------------------------

def _on_paste_import(icon, item):
    text = _ask_paste()
    if not text or not text.strip():
        return
    parsed = tweaks.parse(text)
    tw = _cfg["tweaks"]
    for sec in ("convars", "scenesystem", "video"):
        existing = [tuple(x) for x in tw[sec]]
        merged = tweaks.merge_lists(existing, parsed[sec])
        tw[sec] = [[k, v] for k, v in merged]
    fov_note = ""
    if parsed.get("fov"):
        norm = gameinfo.normalize_value(parsed["fov"])
        if norm:
            _cfg["fov_value"] = norm
            fov_note = f"  FOV set to {_fov_label(norm)}."
    config.save(_cfg)
    _notify(f"Imported {tweaks.counts(parsed)}.{fov_note} Applying…")
    apply_now(interactive=True, notify=True)
    icon.update_menu()


def _on_view_tweaks(icon, item):
    tw = _cfg["tweaks"]
    lines = ["DL-FOV-Fixer — stored tweaks", ""]
    lines.append(f"FOV: r_aspectratio {_cfg['fov_value']}  ({_fov_label(_cfg['fov_value'])})")
    lines.append(f"Apply extra tweaks: {'yes' if _cfg.get('apply_tweaks', True) else 'no'}")
    for title, sec in (("ConVars", "convars"),
                       ("SceneSystem", "scenesystem"),
                       ("video.cfg", "video")):
        lines.append("")
        lines.append(f"[{title}]  ({len(tw[sec])})")
        for k, v in tw[sec]:
            lines.append(f"    {k}  {v}")
    path = os.path.join(tempfile.gettempdir(), "dlfovfixer_tweaks.txt")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        os.startfile(path)  # type: ignore[attr-defined]
    except OSError:
        subprocess.Popen(["notepad.exe", path])


def _on_clear_tweaks(icon, item):
    if not _ask_yesno(
        "Clear all stored extra tweaks?\n\n"
        "This only clears them from DL-FOV-Fixer; it does NOT edit or remove "
        "anything already in your gameinfo.gi."
    ):
        return
    _cfg["tweaks"] = {"convars": [], "scenesystem": [], "video": []}
    config.save(_cfg)
    _notify("Cleared stored tweaks.")
    icon.update_menu()


def _on_toggle_tweaks(icon, item):
    _cfg["apply_tweaks"] = not _cfg.get("apply_tweaks", True)
    config.save(_cfg)
    icon.update_menu()


def _on_about(icon, item):
    _show_info(
        "DL-FOV-Fixer\n\n"
        "Keeps Deadlock's FOV fix (r_aspectratio in gameinfo.gi) applied,\n"
        "and re-applies it — plus any extra pasted config — after game\n"
        "updates wipe the file.\n\n"
        f"File: {_path() or '(not located)'}\n"
        f"Target: r_aspectratio {_fov_label(_cfg['fov_value'])}\n"
        f"Extra tweaks: {tweaks.counts(_cfg['tweaks'])} "
        f"({'on' if _cfg.get('apply_tweaks', True) else 'off'})\n"
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

    tweaks_menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Stored: {tweaks.counts(_cfg['tweaks'])}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Paste / import config…", _on_paste_import),
        pystray.MenuItem("View stored tweaks…", _on_view_tweaks),
        pystray.MenuItem("Clear stored tweaks…", _on_clear_tweaks),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Apply extra tweaks (not just FOV)", _on_toggle_tweaks,
            checked=lambda item: _cfg.get("apply_tweaks", True),
        ),
    )

    return pystray.Menu(
        pystray.MenuItem(lambda item: f"{APP_TITLE} — {_status_text()}", None, enabled=False),
        pystray.MenuItem(
            lambda item: f"Target: r_aspectratio {_fov_label(_cfg['fov_value'])}",
            None, enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Apply now", _on_apply, default=True),
        pystray.MenuItem("Check file now", _on_check),
        pystray.MenuItem("Set FOV value", pystray.Menu(*presets)),
        pystray.MenuItem("Extra tweaks", tweaks_menu),
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
    _refresh_icon()
    _schedule_periodic()
    icon.update_menu()


def _schedule_periodic():
    global _periodic_job
    minutes = int(_cfg.get("periodic_check_minutes", 0) or 0)
    if minutes <= 0 or _root is None:
        return

    def tick():
        global _status_error
        if _have_file() and _cfg.get("auto_apply_on_start", True):
            try:
                tw = _cfg["tweaks"]
                summary = gameinfo.apply_config(
                    _path(), _cfg["fov_value"],
                    convars=tw["convars"], scenesystem=tw["scenesystem"],
                    apply_tweaks=bool(_cfg.get("apply_tweaks", True)),
                )
                _status_error = False
                if summary["changed"]:
                    _notify(
                        "Re-applied config after a game change — "
                        f"FOV {_fov_label(_cfg['fov_value'])}."
                    )
            except PermissionError as exc:
                # File locked (game running) — leave status as-is and retry later.
                if getattr(exc, "winerror", None) not in (32, 33):
                    _status_error = True
            except Exception:  # noqa: BLE001 - never let the timer die loudly
                _status_error = True
        _refresh_icon()
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
