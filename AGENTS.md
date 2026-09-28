# AGENTS

## Required context

1. [ARCHITECTURE.md](ARCHITECTURE.md) before changing module boundaries. It describes the Python app
   that ships today.
2. [CONTEXT.md](CONTEXT.md) before introducing a domain word.
3. [docs/csharp-rewrite.md](docs/csharp-rewrite.md) and [docs/adr/](docs/adr/) before starting work on
   the C# port, or before deciding anything the ADRs already decided.
4. [docs/pitfalls.md](docs/pitfalls.md) when something fails in a way you did not expect. Search it
   and CodePrint's `docs/pitfalls/` for the error text before debugging. CodePrint usually sits beside
   this repository; find it by name if it does not.

## Baseline (CodePrint)

- One top-level type per matching file, folders by capability and then by role.
- Constructor injection and one explicit composition root. Domain code does not reach for UI, files,
  the registry or the network.
- Add or update deterministic tests with every behavior change.
- Behavior that both implementations must share lives in `contracts/vectors/`, and both test suites
  read those files rather than keeping their own copies.
- Conventional Commits, and several coherent commits when a change has independent slices.
- Never leave the repository in a failing state, and never commit a signing certificate, a password or
  a machine path.
- Plain English in all text, and no em-dashes.

## The file this app writes

`gameinfo.gi` is a file the game must still be able to parse, and the user's install is the only copy
they have. Anything touching the merge follows three rules:

- Preserve everything outside the keys being written, newlines included.
- Never rewrite a key that exists as a sub-block.
- Keep the one-time backup, and never overwrite an existing one.

Cover a change to that code with a vector in `contracts/vectors/`, not only with a test.

## Pitfalls

- Add an entry to `docs/pitfalls.md` in the same commit as the fix when a bug took longer to find than
  to fix, came back, or came from a tool or platform trap. Put the exact error text in the symptom.
- Add the test or check that catches it when one is possible, and name it in the entry.
- If it could hit another repository, report it as a `pitfall` bug on the CodePrint project in
  GoalMaker. Do not edit CodePrint from this repository's session.

## Tracking

- This repository's board is its GoalMaker project. Find it with `find_project` and this folder.
- Move an item to Doing when you start it. A bug or idea you notice but will not fix now goes on the
  board with enough notes to act on later.
- A pull request lists its items as `GoalMaker: <item id>` lines, and an item reaches Done only when
  its work is merged to `main`.

## Verification

```powershell
py -m pytest -q
py ..\CodePrint\tools\validate_repository.py --root .
```

Use `py`, not `python`. The `python` command can resolve to the Microsoft Store build, which writes to
a private copy of `%APPDATA%` (see [docs/pitfalls.md](docs/pitfalls.md)).
