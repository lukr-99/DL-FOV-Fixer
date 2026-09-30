# DL-FOV-Fixer

A tiny Windows **system-tray** app that keeps your **Deadlock FOV** fix applied.

Deadlock has no in-game FOV slider. The community workaround is to add
`"r_aspectratio" "<value>"` to the `ConVars` block of Deadlock's
`gameinfo.gi`. A higher value gives a wider field of view. The catch: **every
game update can overwrite that file**, so you have to redo the edit by hand.
This app remembers your chosen value and re-applies it for you.

<p align="center">
  <img src="assets/icon.ico" width="96" alt="DL-FOV-Fixer icon">
</p>

## What it does

- **Auto-locates** `gameinfo.gi` from your Steam libraries on first run
  (reads the Steam path from the registry and `libraryfolders.vdf`). If it can't
  find it, it asks you to pick the file.
- Ensures `"r_aspectratio" "<your value>"` is present in the `ConVars` block,
  **without touching** the rest of the file. Nested blocks like `rate` are left
  exactly as they are, because mangling those stops the game from launching.
- **Remembers your value** across reboots (`%APPDATA%\DL-FOV-Fixer\config.json`).
- **Re-applies on launch** and, optionally, periodically, so after a Deadlock
  update wipes the file, it just fixes itself.
- Makes a one-time backup next to the original: `gameinfo.gi.dlfovfixer.bak`.

## Download and the Windows warning

Get `DL-FOV-Fixer.exe` from the
[latest release](https://github.com/lukr-99/DL-FOV-Fixer/releases/latest).

The release is **not code-signed yet**, so Windows is suspicious of it the first time:

- **SmartScreen** shows "Windows protected your PC". Click **More info**, then
  **Run anyway**. It only asks once per version.
- **Microsoft Defender** may report the file as a trojan. That is a false positive:
  the app is built with PyInstaller, whose self-extracting starter is the same one a
  lot of real malware uses, and Defender matches that pattern, not anything this app
  does. The source is all in this repository if you want to check. A signed release
  and a rewrite that does not use PyInstaller are both on the way.

To check that your download is the file the release built, compare its SHA-256 with
the `DL-FOV-Fixer.exe.sha256` file on the same release (published from the first
release after 1.0.2 on):

```powershell
(Get-FileHash .\DL-FOV-Fixer.exe -Algorithm SHA256).Hash.ToLower()
```

Once releases are signed, right-click the file, choose **Properties**, then
**Digital Signatures**, and check the signer is Lukáš Krejčí. Or run
`Get-AuthenticodeSignature .\DL-FOV-Fixer.exe` and look for `Valid`.

## Status at a glance

The tray icon changes color so you can tell the state without opening the menu:

| Icon | Meaning |
|------|---------|
| 🟢 **Green** | File found and your FOV value is applied. All good. |
| 🟠 **Amber** | Found, but not applied yet or it drifted, for example after an update. Auto-apply turns it green. |
| 🔴 **Red** | A problem: `gameinfo.gi` can't be found or read, or a write failed. |

## Tray menu

| Item | Action |
|------|--------|
| **Apply now** | Write the FOV (and, if enabled, all extra tweaks) into the files. Default double-click action. |
| **Check file now** | Report whether `gameinfo.gi` currently matches your FOV target. |
| **Set FOV value ▸** | Pick a preset (80 to 115°) or enter a custom `r_aspectratio` value. |
| **Extra tweaks ▸** | Paste or import a config, view or clear stored tweaks, toggle applying them. |
| **Open gameinfo.gi** | Open the file in your editor. |
| **Locate gameinfo.gi…** | Manually point the app at the file. |
| **Apply automatically on start** | Toggle auto-apply when the app launches. |
| **Start with Windows** | Toggle launch at sign-in (per-user `Run` key). |
| **Check for updates** | Look for a newer public GitHub Release and install its `DL-FOV-Fixer.exe`. |
| **Quit** | Exit. |

## Extra tweaks: paste a whole config

FOV isn't the only thing an update wipes. **Extra tweaks ▸ Paste / import config…**
opens a box where you can paste someone's whole config. The app stores it and
re-applies it alongside the FOV, so a game update can't blow away your setup.

Keys are routed automatically **by shape**, so there is no need to keep the section
headers:

| Key looks like | Goes to |
|----------------|---------|
| `setting.*` | `cfg/video.txt` |
| `PascalCase` (for example `GpuLightBinner`) | `gameinfo.gi` → `SceneSystem` |
| anything else (for example `r_*`, `cl_*`, `lb_*`) | `gameinfo.gi` → `ConVars` |

You can paste bare (`r_directlighting 0`) or quoted (`"r_directlighting" "0"`)
pairs, with `//` comments and decorative headers. All of that is ignored, and
`r_aspectratio` is treated as your FOV. Merging is **surgical**: existing keys
are updated in place (comments kept), new keys are added at the top of the
block, and anything that already exists as a nested sub-block (for example `rate`,
`speaker_config`) is left untouched, keys inside it included, so the game still launches.

> **Note on video settings:** modern Deadlock keeps video settings in `.vcfg`
> files and there may be no `video.txt`. The app will create `cfg/video.txt`
> from any `setting.*` keys you paste, but whether the game reads it can vary.
> The `gameinfo.gi` ConVars and SceneSystem tweaks are the reliable part.

## FOV reference

`r_aspectratio` is not degrees; it scales the rendered aspect ratio. Approximate
mapping (from community testing, about `28 × value + 31`):

| r_aspectratio | ≈ FOV |
|---------------|-------|
| 1.75 | 80° |
| 2.15 | 90° |
| 2.49 | 100° |
| 2.66 | 105° |
| 2.83 | 110° |
| 3.00 | 115° |

Default is `2` (about 87°). Pick whatever feels right. Larger values can distort at the edges.

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

Produces `dist\DL-FOV-Fixer.exe`, a single-file, no-console tray app with the
bundled icon. Drop it anywhere and (optionally) enable **Start with Windows**
from the tray menu.

## Releases and updates

The app checks `https://api.github.com/repos/lukr-99/DL-FOV-Fixer/releases/latest`
for a newer non-draft, non-prerelease GitHub Release. Since 1.0.2 it installs only
an asset named exactly `DL-FOV-Fixer.exe`. A newer release without one (the 2.x
installer, for example) is announced with a link to the release page instead.

To publish a 1.x update:

```bash
# 1. Bump the version in dlfovfixer/__init__.py and pyproject.toml.
# 2. Commit the version bump.
git tag v1.0.3
git push origin v1.0.3
```

The release workflow runs the tests, builds `dist\DL-FOV-Fixer.exe`, and attaches it
and its SHA-256 to the GitHub Release. Installed copies check for updates on start by
default, and users can also trigger **Check for updates** from the tray menu. The C#
2.x app ships from `v2.*` tags instead (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Tests

```bash
py -m pytest -q
```

The tests run the shared behavior vectors in `contracts/vectors/`: updating an
existing value, inserting when missing, creating a `ConVars` block from scratch,
idempotency, and, most importantly, that nested sub-blocks survive untouched.

## Notes & safety

- Only the keys you set are changed: the FOV plus any tweaks you import.
  Existing keys are updated in place (comments kept), the rest of the file is
  preserved byte for byte (newlines included), and nested sub-blocks are never
  rewritten.
- A one-time backup (`gameinfo.gi.dlfovfixer.bak`, and `video.txt.dlfovfixer.bak`
  if applicable) is made the first time each file is modified, and it is never
  replaced. It holds the game version of that day. **Do not copy an old backup back
  after a game update**: it would undo Valve's changes to the file and can stop the
  game from starting. To get a clean file, use Steam's **Verify integrity of game
  files** instead, then let the app apply your FOV again.
- This edits your own local game files. It doesn't touch anything online and is
  unrelated to anti-cheat. Use at your own discretion.
- Not affiliated with Valve. "Deadlock" is a trademark of Valve Corporation.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md): free for personal and non-commercial use; selling or other commercial use requires permission.
