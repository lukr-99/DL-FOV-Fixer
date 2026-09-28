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

## Replacing a file the game holds open says "access denied", not "in use"

- Symptom:

  ```text
  System.UnauthorizedAccessException: Access to the path '...\gameinfo.gi' is denied.
  ```

  from `File.Move(temp, path, overwrite: true)` while Deadlock is running. It maps to a red Failed
  state instead of Waiting, although nothing is wrong except that the game has the file open.
- Cause: moving over a file that another process has open fails with Win32 error 5, access denied,
  whatever share mode that process used. `File.Replace` on the same file fails with error 32, the
  sharing violation that means Waiting. Measured on Windows 11 with .NET 10: with the file open for
  reading and `FileShare.Read`, `File.Move` gives 5 and `File.Replace` gives 32.
- Fix: replace an existing file with `File.Replace(temp, path, null)`, and use `File.Move` only when
  the target does not exist yet.
- Closed off by: `FileSystemGameFilesTests.WriteText_FileOpenInTheGame_IsLockedAndLeavesTheFileAlone`
  with `FileShare.Read`, which fails if `File.Replace` is swapped back for `File.Move`.
- Seen: 2026-09-29, M4, while writing `FileSystemGameFiles`, before it shipped.

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
- Closed off by: in the C# port, `FileSystemGameFiles` reports errors 32 and 33 as a locked file and
  `ApplyService` turns that into `ApplyResult.Waiting`. `FileSystemGameFilesTests` opens the file with
  `FileShare.None` and `FileShare.Read`, and `ApplyServiceTests.Apply_GameHasTheFileOpen_IsWaiting`
  covers the mapping. The Python app still handles it by hand in `app.py`.
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
