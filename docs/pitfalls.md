# Pitfalls

Mistakes this repository has already made, kept short so they are not made twice. When something
fails in a way you did not expect, search here for the error text before debugging it.

Add an entry in the same commit as the fix when a bug took longer to find than to fix, came back, or
came from a tool or platform trap. Put new entries at the top, in this shape:

```markdown
## What goes wrong, in a few words

- Symptom: the exact error text, or what you see
- Cause: why it happens
- Fix: what to do about it
- Closed off by: the test, check, or tool that now catches it, or "not yet"
- Seen: date and where (milestone, PR, or commit)
```

A pitfall that could hit another repository is also reported to CodePrint. CodePrint's
`docs/pitfalls/README.md` explains how.

## A PyInstaller one-file build is reported as a trojan

- Symptom: Windows Defender reports `DL-FOV-Fixer.exe` as a trojan and removes it, on the build
  machine and for anyone who downloads the release.
- Cause: the one-file bootloader unpacks the interpreter into a temporary folder and runs it from
  there, which is the shape most droppers have, so the match is on the packaging and not on anything
  the app does. `build.bat` does not pass `--noupx`, so a build machine with `upx` on PATH compresses
  the executable too and makes the match stronger.
- Fix: sign the artifact and let it build reputation, submit it to Microsoft as a false positive, and
  stop shipping a self-extracting bundle. The last one is the C# rewrite
  ([docs/csharp-rewrite.md](csharp-rewrite.md)). `--onedir` and a self-built bootloader are the cheap
  experiments if the Python build has to live longer.
- Closed off by: not yet. The release workflow's signing step and its step summary at least make an
  unsigned release visible in the run.
- Seen: 2026-08 onwards, v1.0.0.

## A plain `$` in a regex does not match at the end of a CRLF line

- Symptom: an unquoted `SceneSystem` key is found but never updated, and only in files with Windows
  line endings. The same case passes on a file with LF endings.
- Cause: in Python's `re`, `$` under `MULTILINE` matches only right before `\n`. On CRLF text the
  `\r` sits between the value and the `\n`, and `\r` counts as whitespace, so `(\S+)[ \t]*$` stops
  before the `\r` and then cannot match.
- Fix: end the pattern with a line-break lookahead, `(?=\r?\n|\Z)`, instead of `$`. In .NET write
  `\z`, because .NET's `\Z` also matches before a final `\n`.
- Closed off by: the CRLF form of every case in `contracts/vectors/gameinfo-merge.json` and
  `gameinfo-apply.json`, run by `tests/test_vectors.py` and by `DlFovFixer.Core.Tests`. Removing the
  `\r?` from the C# lookahead fails four of them.
- Seen: 2026-09, in `gameinfo._merge_one`.

## A locked gameinfo.gi is a normal state, not an error

- Symptom:

  ```text
  PermissionError: [WinError 32] The process cannot access the file because it is being used by
  another process
  ```

  The tray icon turns red while Deadlock is running, and goes back to normal after the game closes.
- Cause: the game, or a mod manager, holds `gameinfo.gi` or `cfg/video.txt` open. A write then fails
  with a sharing violation, Win32 error 32 or 33, which is expected and heals itself on the next pass.
- Fix: treat those two error numbers as a transient waiting state. Keep the last known status, retry
  on the next tick, and say "file is in use (is Deadlock running?)" when the user asked for the apply
  explicitly. Any other permission error is still a real error.
- Closed off by: not yet. The C# port makes it the named `Waiting` state, with a test that opens the
  file with `FileShare.None`.
- Seen: 2026-09, commit 887fe47.

## The `python` command writes to a private copy of AppData

- Symptom: a script saves a file under `%APPDATA%` and reads it back fine, but the real app,
  PowerShell and `py` still see the old file, or none.
- Cause: `python` can resolve to the Microsoft Store build through its WindowsApps alias. Started from
  an agent tool inside a packaged app, it runs under that package's file-system virtualization, so
  writes land in `%LOCALAPPDATA%\Packages\<package>\LocalCache` instead of the real folder.
- Fix: use `py`, the launcher of a normal Python install, or PowerShell, for anything that must touch
  real user folders. `(Get-Command python).Source` under `WindowsApps` means it is the Store build.
- Closed off by: not yet.
- Seen: 2026-08. Also in CodePrint's `docs/pitfalls/windows-tooling.md`.
