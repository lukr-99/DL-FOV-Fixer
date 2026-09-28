# DL-FOV-Fixer architecture

This describes the app as it is today: a Python tray app packaged with PyInstaller. The planned C#
rewrite is in [docs/csharp-rewrite.md](docs/csharp-rewrite.md) and the decisions behind it are in
[docs/adr/](docs/adr/). Nothing in this file describes the rewrite as if it existed.

## Context

Deadlock has no FOV slider, so the fix is an `r_aspectratio` entry in the `ConVars` block of the
game's `gameinfo.gi`. Game updates overwrite that file. The app remembers the chosen value, plus any
extra config the user pasted, and puts it back.

Two things hold state:

- `gameinfo.gi` (and optionally `cfg/video.txt`) in the Steam library. The game reads these, and they
  are the only place a change has any effect.
- `%APPDATA%\DL-FOV-Fixer\config.json`. This is the user's remembered intent: the target value, the
  stored tweaks, and the app's own settings.

There is no server, no account and no network traffic except the update check.

## Modules today

```text
run.pyw / __main__.py
        |
        v
    app.py ------> gameinfo.py  (read, merge, write, backup)
      |     \----> tweaks.py    (parse a pasted config)
      |      \---> config.py    (settings in %APPDATA%)
      |       \--> locator.py   (find gameinfo.gi from Steam)
      |        \-> startup.py   (HKCU Run value)
      |         \> updater.py   (GitHub release check and self-replace)
      \---------> iconfactory.py (draw the status icon)
```

| Module | Responsibility |
|---|---|
| `app.py` | Tray icon, menu, dialogs, status colors, periodic re-apply, and the orchestration of everything below |
| `gameinfo.py` | KeyValues brace matching, in-place key updates, block creation, the one-time backup, and all reads and writes |
| `tweaks.py` | Turn a pasted config blob into ordered ConVars, SceneSystem and video entries, routed by key shape |
| `config.py` | Load and atomically save `config.json`, filling in defaults |
| `locator.py` | Find Steam from the registry, walk `libraryfolders.vdf`, look for Deadlock's `gameinfo.gi` |
| `startup.py` | The per-user `Run` value that starts the app at sign-in |
| `updater.py` | Read the latest GitHub Release, compare versions, download an asset, replace the running exe |
| `iconfactory.py` | Draw the green, amber and red vision-cone tray icon |

`pystray` owns the tray icon and `tkinter` provides the dialogs. A hidden Tk root also drives the
periodic timer, so the UI toolkit and the scheduler are the same object.

## Data flow

1. Start: `config.load()`, then locate `gameinfo.gi` if the stored path is empty or gone.
2. Apply: `apply_config` merges the FOV plus, if enabled, the stored tweaks into `ConVars` and
   `SceneSystem`, writing at most once and only if something changed. `setting.*` keys go to
   `cfg/video.txt` instead. The first write to each file copies it to `<name>.dlfovfixer.bak`.
3. Watch: a timer re-applies every `periodic_check_minutes`. A sharing violation (Win32 error 32 or
   33) means the game has the file open, which is expected and retried rather than reported.
4. Status: the icon is green when the file holds the target value, amber when it is found but the
   value is absent or different, and red when the file cannot be found or read.

## Delivery

`build.bat` runs PyInstaller in one-file, no-console mode and produces `dist\DL-FOV-Fixer.exe`. It
does not pass `--noupx`, so the executable is UPX compressed on any machine that has `upx` on PATH,
and is not on one that does not. The committed `DL-FOV-Fixer.spec` records an earlier build with
`upx=True`, but `build.bat` passes flags instead of using it. `.github/workflows/release.yml` builds that on a `v*` tag, runs the tests,
signs the executable when a certificate is configured, and attaches it to a GitHub Release. The
in-app updater downloads a newer release's `.exe`, then a temporary `.cmd` script waits for the
process to exit, copies the new file over the old one and starts it again.

## Known constraints

- **Defender reports the released exe as a trojan.** A PyInstaller one-file build looks like a
  self-extracting dropper, because its bootloader is the same one most droppers use. Signing is
  tracked on the board, and the rewrite removes the shape entirely.
- **The game holds the file open while it runs.** Writes fail with a sharing violation, which is a
  normal transient state rather than an error.
- **Windows only**, by construction: `winreg` for Steam discovery and for the `Run` value.
- **Version lives in two files**, `dlfovfixer/__init__.py` and `pyproject.toml`, and they have to be
  bumped together because the updater compares against `__version__`.

Where this repository does not yet meet the CodePrint baseline:

- `app.py` is both the host and the coordinator. It holds module-level state and imports every other
  module directly, so there are no injected seams and the automated tests only cover the pure parts
  (`gameinfo`, `tweaks`, and the updater's version comparison).
- There is no theme support. `pystray` menus and `tkinter` dialogs follow neither a light nor a dark
  token set.

These are the gaps the rewrite is meant to close, and the plan lists them as slices rather than
leaving them implied.

## The C# port in progress

The .NET solution `DL-FOV-Fixer.slnx` sits beside the Python app and ships nothing yet. It has the
three projects from [docs/csharp-rewrite.md](docs/csharp-rewrite.md): `DlFovFixer.Core` on `net10.0`,
and `DlFovFixer.Infrastructure` and `DlFovFixer.App` on `net10.0-windows`, each with a test project.
`Directory.Build.props` reads the version from `version.properties` and marks every build `-dev`
unless it is built with `-p:DlFovFixerReleaseBuild=true`. Architecture tests keep Core free of the
other layers, WPF, the registry and the network, and keep Infrastructure free of the shell.

`DlFovFixer.Core/GameInfo` holds the ported merge as pure text functions: `BlockMerge` for one
block, `GameInfoMerge` for the value and the tweaks together, `VideoConfigMerge` for `video.txt`,
`TweakTextParser` for pasted configs and `AspectRatio` for typed values. Reading and writing files is
not there; it arrives with the adapters. The shared vectors in `contracts/vectors/` define the
behavior, and the Python tests and the Core tests both run them.

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. It checks .NET
formatting, builds with warnings as errors, runs the .NET tests with TRX results uploaded even on
failure, and runs the Python tests.
