# Contributing

## Local verification

Run what your change touches. CI (`.github/workflows/ci.yml`) runs the same checks on every pull
request, and the release workflow runs the Python tests again on a `v1.*` tag.

```powershell
py -m pip install -r requirements.txt
py -m pytest -q
dotnet format DL-FOV-Fixer.slnx --verify-no-changes
dotnet build DL-FOV-Fixer.slnx -c Release
dotnet test --solution DL-FOV-Fixer.slnx -c Release --no-build
py ..\CodePrint\tools\validate_repository.py --root .
```

The .NET SDK is pinned in `global.json`. The C# app's version lives in `version.properties`, and a
build is `-dev` unless it is made with `-p:DlFovFixerReleaseBuild=true`.

Use `py`, never `python`. The `python` command can resolve to the Microsoft Store build, which writes
to a private copy of `%APPDATA%` (see [docs/pitfalls.md](docs/pitfalls.md)).

Building the executable needs PyInstaller and produces `dist\DL-FOV-Fixer.exe`:

```powershell
.\build.bat
```

## Building the installer

The C# app ships as a per-user Inno Setup installer. You need the .NET SDK from `global.json` and
Inno Setup 6 (`choco install innosetup`).

```powershell
.\installer\build-installer.ps1            # dev build, version ends in -dev
.\installer\build-installer.ps1 -Release -ManifestKeyPath 'E:\DL-FOV-Fixer-signing\release-manifest-signing.pem'
```

The script publishes the app, compiles `installer/DL-FOV-Fixer.iss`, and writes these files to
`artifacts/` (ignored by Git): `DL-FOV-Fixer-<version>-setup.exe`, its `.sha256`, `manifest.json`
and `manifest.sig`. Pass `-IsccPath` if `ISCC.exe` is not on `PATH` or in the usual install folders.

`manifest.sig` is what makes a release installable through the app's updater (ADR 0006). The script
signs with the key in `-ManifestKeyPath` or the `DLFOVFIXER_MANIFEST_SIGNING_KEY` environment
variable, checks that it matches `contracts/keys/release-manifest-public.b64` before it builds
anything, and checks the signature before it ends. A dev build without a key only skips the
signature, and `-Release` without one fails. `tools/setup-update-signing.ps1` made the key once, see
[contracts/keys/README.md](contracts/keys/README.md).

Authenticode signing is optional and only happens when `WINDOWS_CERT_PFX_BASE64` (and
`WINDOWS_CERT_PASSWORD`) are set. It only quiets SmartScreen on a browser download. Do not run the
installer on your own machine to test a build unless you want it installed. Never change the `AppId`
in the `.iss` file.

To release, make sure `version.properties` matches the tag, then push a tag such as `v2.0.0`.
`.github/workflows/release-windows.yml` builds, signs the manifest and creates a draft release.
Tags `v1.*` still go through `release.yml` for the Python build.

## Changing the merge

`gameinfo.gi` is a file the game must still be able to parse, and the user's install is their only
copy. A change to the merge keeps every rule in [AGENTS.md](AGENTS.md), and gets a case that proves
it: a vector in `contracts/vectors/` that both test suites read. See
[contracts/vectors/README.md](contracts/vectors/README.md) for the format and how to add a case.

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
