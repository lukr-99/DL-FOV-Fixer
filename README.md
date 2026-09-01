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
| **Apply now** | Write the FOV (and, if enabled, all extra tweaks) into the files. Default double-click action. |
| **Check file now** | Report whether `gameinfo.gi` currently matches your FOV target. |
| **Set FOV value ▸** | Pick a preset (80–115°) or enter a custom `r_aspectratio` value. |
| **Extra tweaks ▸** | Paste/import a config, view or clear stored tweaks, toggle applying them. |
| **Open gameinfo.gi** | Open the file in your editor. |
| **Locate gameinfo.gi…** | Manually point the app at the file. |
| **Apply automatically on start** | Toggle auto-apply when the app launches. |
| **Start with Windows** | Toggle launch at sign-in (per-user `Run` key). |
| **Check for updates** | Look for a newer public GitHub Release and install its `.exe` asset. |
| **Quit** | Exit. |

## Extra tweaks — paste a whole config

FOV isn't the only thing an update wipes. **Extra tweaks ▸ Paste / import config…**
opens a box where you can paste someone's whole config; the app stores it and
re-applies it alongside the FOV, so a game update can't blow away your setup.

Keys are routed automatically **by shape** — no need to keep the section
headers:

| Key looks like | Goes to |
|----------------|---------|
| `setting.*` | `cfg/video.txt` |
| `PascalCase` (e.g. `GpuLightBinner`) | `gameinfo.gi` → `SceneSystem` |
| anything else (e.g. `r_*`, `cl_*`, `lb_*`) | `gameinfo.gi` → `ConVars` |

You can paste bare (`r_directlighting 0`) or quoted (`"r_directlighting" "0"`)
pairs, with `//` comments and decorative headers — all of that is ignored, and
`r_aspectratio` is treated as your FOV. Merging is **surgical**: existing keys
are updated in place (comments kept), new keys are added at the top of the
block, and anything that already exists as a nested sub-block (e.g. `rate`,
`speaker_config`) is left untouched so the game still launches.

> **Note on video settings:** modern Deadlock keeps video settings in `.vcfg`
> files and there may be no `video.txt`. The app will create `cfg/video.txt`
> from any `setting.*` keys you paste, but whether the game reads it can vary —
> the `gameinfo.gi` ConVars/SceneSystem tweaks are the reliable part.

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

## Releases and updates

The app checks `https://api.github.com/repos/lukr-99/DL-FOV-Fixer/releases/latest`
for a newer non-draft, non-prerelease GitHub Release. The release must include a
Windows `.exe` asset, preferably named `DL-FOV-Fixer.exe`.

To publish an update:

```bash
# 1. Bump the version in dlfovfixer/__init__.py and pyproject.toml.
# 2. Commit the version bump.
git tag v1.1.0
git push origin v1.1.0
```

The release workflow runs tests, builds `dist\DL-FOV-Fixer.exe`, and attaches it
to the GitHub Release. Installed copies check for updates on start by default,
and users can also trigger **Check for updates** from the tray menu.

## Tests

```bash
python -m pytest -q          # or: python tests/test_gameinfo.py
```

The tests cover updating an existing value, inserting when missing, creating a
`ConVars` block from scratch, idempotency, and — importantly — that nested
sub-blocks survive untouched.

## Notes & safety

- Only the keys you set are changed — the FOV plus any tweaks you import.
  Existing keys are updated in place (comments kept), the rest of the file is
  preserved byte-for-byte (newlines included), and nested sub-blocks are never
  rewritten.
- A one-time backup (`gameinfo.gi.dlfovfixer.bak`, and `video.txt.dlfovfixer.bak`
  if applicable) is made the first time each file is modified. **Restore** it by
  copying the `.bak` back over the original.
- This edits your own local game files; it doesn't touch anything online and is
  unrelated to anti-cheat. Use at your own discretion.
- Not affiliated with Valve. "Deadlock" is a trademark of Valve Corporation.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md) — free for personal and non-commercial use; selling or other commercial use requires permission.
