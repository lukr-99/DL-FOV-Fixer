# DL-FOV-Fixer

DL-FOV-Fixer is a small Windows tray app that keeps your Deadlock field of view (FOV) fix applied.

Deadlock has no in-game FOV slider. The community fix adds `"r_aspectratio" "<value>"` to the
`ConVars` block of Deadlock's `gameinfo.gi` file. A higher value gives a wider view. A game update can
overwrite that file, so the edit must be redone. This app remembers your value and applies it again
for you.

<p align="center">
  <img src="assets/icon.ico" width="96" alt="DL-FOV-Fixer icon, a tray icon">
</p>

## Status

- Version 2.0.0, released 2026-09-30. See [CHANGELOG.md](CHANGELOG.md).
- Unreleased changes on `main` add a new About window and move the tray to the shared
  `DotNetLib.Tray` package. See the Unreleased section of [CHANGELOG.md](CHANGELOG.md).

## Features

- **Finds the file for you.** On first run it looks for `gameinfo.gi` in your Steam libraries. If it
  cannot find the file, it asks you to pick it, and it keeps the value already in the file.
- **Edits only what it must.** It sets `r_aspectratio` in the `ConVars` block and leaves the rest of
  the file alone. Nested blocks such as `rate` are not changed, because changing them can stop the
  game from starting.
- **Re-applies after a game update.** It watches the file and also checks on a timer. It waits while
  the game has the file open, then applies the value.
- **Tray status.** The icon is green when the FOV is applied, amber when it is waiting to apply, and
  red when there is a problem.
- **Extra tweaks.** You can paste a whole config. The app stores it and applies it with the FOV.
- **Updates.** It checks this repository's releases. An update installs only when the manifest
  signature and the installer's SHA-256 both match.

## Requirements

- Windows 10 or 11, 64-bit.
- Deadlock installed through Steam.
- To build from source, the .NET SDK pinned in `global.json` (10.0.200 or a newer feature band).

## Install

Download `DL-FOV-Fixer-<version>-setup.exe` from the
[latest release](https://github.com/lukr-99/DL-FOV-Fixer/releases/latest) and run it. The installer
is per user. It needs no admin prompt. It installs to `%LOCALAPPDATA%\Programs\DL-FOV-Fixer` and adds
a Start menu entry.

If you are coming from version 1.x, run the installer the same way. It replaces the old
`DL-FOV-Fixer.exe` in that folder and keeps your FOV, your stored tweaks, and your settings in
`%APPDATA%\DL-FOV-Fixer\config.json`. A copy of 1.x kept somewhere else can be deleted.

### Windows SmartScreen warning

The installer is not code-signed. The first time you run a downloaded version, SmartScreen shows
"Windows protected your PC". Click **More info**, then **Run anyway**.

To check that the download is the file the release built, compare its SHA-256 hash with the
`.sha256` file on the same release:

```powershell
(Get-FileHash .\DL-FOV-Fixer-2.0.0-setup.exe -Algorithm SHA256).Hash.ToLower()
```

To uninstall, use **Settings > Apps**. Your settings stay in `%APPDATA%\DL-FOV-Fixer`, so a reinstall
uses them again.

## Tray menu

| Item | What it does |
| --- | --- |
| Apply now | Writes the FOV, and the extra tweaks if they are enabled, into the files. A left click on the icon does the same. |
| Check file now | Reports whether `gameinfo.gi` matches your FOV target. |
| Set FOV value | Pick a preset from 80 to 115 degrees, or enter a custom `r_aspectratio` value. |
| Extra tweaks | Paste or import a config, view or clear stored tweaks, and turn applying them on or off. |
| Check for updates, Install update | Look for a newer release and install it. |
| Check updates on start | Turn the update check on startup on or off. |
| Open gameinfo.gi | Opens the file in your editor. |
| Locate gameinfo.gi | Lets you point the app at the file yourself. |
| Apply automatically on start | Turn applying on startup and after game updates on or off. |
| Start with Windows | Start the app when you sign in. Uses the per-user Run key. |
| Theme | Follow Windows, or use Light or Dark. |
| About, Quit | Shows what the app is doing, or exits it. |

## Extra tweaks

FOV is not the only setting a game update can overwrite. Open **Extra tweaks**, then
**Paste / import config**, and paste a config. The app stores it and applies it with the FOV.

The app routes each key by its shape, so you do not need the section headers:

| Key looks like | Goes to |
| --- | --- |
| `setting.*` | `cfg/video.txt` |
| `PascalCase`, for example `GpuLightBinner` | `gameinfo.gi`, `SceneSystem` block |
| Anything else, for example `r_*`, `cl_*`, `lb_*` | `gameinfo.gi`, `ConVars` block |

You can paste bare pairs (`r_directlighting 0`) or quoted pairs (`"r_directlighting" "0"`). Comments
that start with `//` and decorative headers are ignored. `r_aspectratio` is treated as your FOV.

The merge changes only the keys you set. Existing keys are updated in place and their comments are
kept. New keys are added at the top of the block. Nested sub-blocks, such as `rate` and
`speaker_config`, are left untouched, so the game still starts.

Modern Deadlock keeps most video settings in `.vcfg` files, and there may be no `video.txt`. The app
creates `cfg/video.txt` from any `setting.*` keys you paste, but the game may not read it. The
`gameinfo.gi` ConVars and SceneSystem tweaks are the reliable part.

## FOV reference

`r_aspectratio` is not degrees. It scales the rendered aspect ratio. From community tests, the
approximate FOV is `28 × value + 31`:

| r_aspectratio | Approximate FOV |
| --- | --- |
| 1.75 | 80° |
| 2.15 | 90° |
| 2.49 | 100° |
| 2.66 | 105° |
| 2.83 | 110° |
| 3.00 | 115° |

The default is `2`, about 87°. Pick the value you like. Large values can stretch the edges of the
picture.

## Build and test

The build uses the SDK in `global.json`. Packages come from the dotnetlib feed. See
[CONTRIBUTING.md](CONTRIBUTING.md) for how to get access.

```powershell
dotnet build DL-FOV-Fixer.slnx -c Release
dotnet test --solution DL-FOV-Fixer.slnx -c Release --no-build
```

To run the app against a scratch config, so a test run does not touch your real settings or game
files:

```powershell
dotnet run --project src/DlFovFixer.App -- --settings C:\Temp\dlfov-test\config.json
```

## Architecture

The app has three projects under `src/`: `DlFovFixer.Core` (domain rules), `DlFovFixer.Infrastructure`
(files, Steam, registry, and the updater), and `DlFovFixer.App` (the tray app and the composition
root). Tests live under `tests/`. The behavior the app must keep is stored as data in
`contracts/vectors/`. See [ARCHITECTURE.md](ARCHITECTURE.md) and the decisions in
[docs/adr/](docs/adr/).

## Data safety

- The app edits only your local Deadlock files: `gameinfo.gi`, and `cfg/video.txt` when you paste
  `setting.*` keys. It does not touch anything online and is not related to anti-cheat.
- Before it first changes a file, it makes a backup next to the original: `gameinfo.gi.dlfovfixer.bak`,
  and `video.txt.dlfovfixer.bak` if that file exists. The backup is never replaced.
- Do not copy an old backup back after a game update. The backup holds the game files from that day.
  Restoring it can undo Valve's changes and stop the game from starting. To get a clean file, use
  Steam's **Verify integrity of game files**, then apply your FOV again in the app.
- Your settings are in `%APPDATA%\DL-FOV-Fixer\config.json`.
- The security policy is in [SECURITY.md](SECURITY.md).

Use this app at your own risk. It is not affiliated with Valve. "Deadlock" is a trademark of Valve
Corporation.

## Delivery

Releases are built by the Windows release workflow in `.github/workflows/release-windows.yml`. A
release is a Git tag `vX.Y.Z` that matches `version.properties`. The installer build and the release
steps are in [CONTRIBUTING.md](CONTRIBUTING.md). Each release has the installer, its `.sha256` file,
and the signed `manifest.json`.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md). You may use it for personal and noncommercial purposes.
Selling it or using it commercially needs permission.
