# Contributing

## Local verification

Run what your change touches. The release workflow runs the tests on a `v*` tag; there is no pull
request workflow yet, which the C# scaffold slice adds.

```powershell
py -m pip install -r requirements.txt
py -m pytest -q
py ..\CodePrint\tools\validate_repository.py --root .
```

Use `py`, never `python`. The `python` command can resolve to the Microsoft Store build, which writes
to a private copy of `%APPDATA%` (see [docs/pitfalls.md](docs/pitfalls.md)).

Building the executable needs PyInstaller and produces `dist\DL-FOV-Fixer.exe`:

```powershell
.\build.bat
```

## Changing the merge

`gameinfo.gi` is a file the game must still be able to parse, and the user's install is their only
copy. A change to the merge keeps every rule in [AGENTS.md](AGENTS.md), and gets a case that proves
it: today a test in `tests/`, and from the C# port on, a vector in `contracts/vectors/` that both
test suites read.

Never reformat the file, never rewrite a key that already exists as a sub-block, and never overwrite
an existing `.dlfovfixer.bak`.

## Change shape

- One coherent behavior or repository change per commit. Split independent slices.
- Conventional Commits: `type(optional-scope): imperative summary`.
- Tests and the documentation that explains a behavior belong in the same commit as that behavior.
- No commit leaves the repository failing.
- Bump `dlfovfixer/__init__.py` and `pyproject.toml` together. The updater compares against
  `__version__`, so a mismatch ships a release that cannot see itself.
- Plain English, and no em-dashes.

## Tracking

Work is tracked on this repository's GoalMaker project. Move an item to Doing when you start it, list
the items in a pull request as `GoalMaker: <item id>` lines, and let the merge to `main` close them.
