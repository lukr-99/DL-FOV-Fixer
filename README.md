# DL-FOV-Fixer

A tiny Windows **system-tray** app that keeps your **Deadlock FOV** fix applied.

Deadlock has no in-game FOV slider. The community workaround is to add
`"r_aspectratio" "<value>"` to the `ConVars` block of Deadlock's
`gameinfo.gi` — a higher value gives a wider field of view. The catch: **every
game update can overwrite that file**, so you have to redo the edit by hand.
This app remembers your chosen value and re-applies it for you.

<p align="center">
  <img src="assets/icon.ico" width="96" alt="DL-FOV-Fixer icon">
</p>

## What it does

- **Auto-locates** `gameinfo.gi` from your Steam libraries on first run
  (reads the Steam path from the registry + `libraryfolders.vdf`). If it can't
  find it, it asks you to pick the file.
- Ensures `"r_aspectratio" "<your value>"` is present in the `ConVars` block,
  **without touching** the rest of the file (nested blocks like `rate` are left
  exactly as they are — mangling those stops the game from launching).
- **Remembers your value** across reboots (`%APPDATA%\DL-FOV-Fixer\config.json`).
- **Re-applies on launch** and, optionally, periodically — so after a Deadlock
  update wipes the file, it just fixes itself.
- Makes a one-time backup next to the original: `gameinfo.gi.dlfovfixer.bak`.

## Status at a glance

The tray icon changes color so you can tell the state without opening the menu:

| Icon | Meaning |
|------|---------|
| 🟢 **Green** | File found and your FOV value is applied — all good. |
| 🟠 **Amber** | Found, but not applied yet or it drifted (e.g. after an update). Auto-apply turns it green. |
| 🔴 **Red** | A problem — `gameinfo.gi` can't be found/read, or a write failed. |

## Tray menu

| Item | Action |
|------|--------|
| **Apply FOV now** | Write your target value into `gameinfo.gi` (also the default double-click action). |
| **Check file now** | Report whether the file currently matches your target. |
| **Set FOV value ▸** | Pick a preset (80–115°) or enter a custom `r_aspectratio` value. |
| **Open gameinfo.gi** | Open the file in your editor. |
| **Locate gameinfo.gi…** | Manually point the app at the file. |
| **Apply automatically on start** | Toggle auto-apply when the app launches. |
| **Start with Windows** | Toggle launch at sign-in (per-user `Run` key). |
| **Quit** | Exit. |

## FOV reference

`r_aspectratio` is not degrees; it scales the rendered aspect ratio. Approximate
mapping (from community testing, ~`28 × value + 31`):

| r_aspectratio | ≈ FOV |
|---------------|-------|
| 1.75 | 80° |
| 2.15 | 90° |
| 2.49 | 100° |
| 2.66 | 105° |
| 2.83 | 110° |
| 3.00 | 115° |

Default is `2` (≈ 87°). Pick whatever feels right — larger can distort at the edges.

## Run from source

```bash
pip install -r requirements.txt
pythonw run.pyw          # windowed (no console)
# or:  python -m dlfovfixer
```

## Build a standalone .exe

```bash
build.bat
```

Produces `dist\DL-FOV-Fixer.exe` — a single-file, no-console tray app with the
bundled icon. Drop it anywhere and (optionally) enable **Start with Windows**
from the tray menu.

## Tests

```bash
python -m pytest -q          # or: python tests/test_gameinfo.py
```

The tests cover updating an existing value, inserting when missing, creating a
`ConVars` block from scratch, idempotency, and — importantly — that nested
sub-blocks survive untouched.

## Notes & safety

- Only the single `r_aspectratio` line is ever changed; the file is otherwise
  byte-for-byte preserved (newlines included).
- A backup is created the first time the file is modified. **Restore** it by
  copying `gameinfo.gi.dlfovfixer.bak` back over `gameinfo.gi`.
- This edits your own local game files; it doesn't touch anything online and is
  unrelated to anti-cheat. Use at your own discretion.
- Not affiliated with Valve. "Deadlock" is a trademark of Valve Corporation.

## License

MIT — see [LICENSE](LICENSE).
