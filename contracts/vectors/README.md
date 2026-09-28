# Behavior vectors

These files describe what the merge must do, as data. The Python tests (`tests/test_vectors.py`)
and the C# tests (`tests/DlFovFixer.Core.Tests`) both read them, so a case added here is a case both
implementations must pass. Neither suite keeps its own copy.

| File | What it covers |
|---|---|
| `gameinfo-merge.json` | Merging keys into one named block: update in place, insert, skip a sub-block, create the block |
| `gameinfo-apply.json` | Applying the FOV value and the stored tweaks to a whole `gameinfo.gi` |
| `video-config.json` | Merging `setting.*` entries into `cfg/video.txt`, including creating it |
| `tweak-parsing.json` | Sorting a pasted config into ConVars, SceneSystem and video entries, and merging stored lists |
| `fov-value.json` | Which typed values are accepted, the FOV in degrees, and the menu presets |

## Rules every runner follows

- A text field is an array of lines joined with LF. `null` means no text, for example a file that
  does not exist.
- Every case in `gameinfo-merge.json`, `gameinfo-apply.json` and `video-config.json` that has text
  input also runs with each LF replaced by CRLF, in the input and in the expected output.
- Every one of those cases then runs a second time on its own output. The second run must change
  nothing, and the Python runner also checks that it writes nothing.
- Result names are the Python app's: `updated`, `added`, `skipped_block`, `no_block`, `no_root`.

## Adding a case

Write the input by hand, and say in the name what the case proves. Take the expected output from
running the current Python app, then read it line by line before committing it: the vector is the
contract, so a wrong expectation locks in a bug. A new file needs a runner on both sides, and both
suites fail when a file has none.

Some expectations record today's behavior rather than an ideal one, and a change to them is a
change to what the app writes:

- An inserted key is followed by a blank line, because the inserted lines end with a line break and
  the block's first line already starts with one.
- A created block leaves the root's closing brace indented by one tab.
- A `video.txt` with no block at all is replaced by a fresh block. The one-time backup keeps the
  original.
