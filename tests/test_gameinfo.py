"""Unit tests for the gameinfo.gi patcher. Run with:  python -m pytest -q
(or plain `python tests/test_gameinfo.py`)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlfovfixer import gameinfo  # noqa: E402

# A trimmed but structurally faithful gameinfo.gi, including a nested block
# inside ConVars (the thing we must never damage).
SAMPLE = '''"GameInfo"
{
\tgame \t"citadel"

\tConVars
\t{
\t\t"r_aspectratio" "2.3"
\t\t"rate"
\t\t{
\t\t\t"min"\t\t"98304"
\t\t\t"default"\t"786432"
\t\t}
\t\t"fps_max"\t"400"
\t}

\tMemory
\t{
\t\t"Foo" "1"
\t}
}
'''

SAMPLE_NO_ASPECT = SAMPLE.replace('\t\t"r_aspectratio" "2.3"\n', "")
SAMPLE_NO_CONVARS = '''"GameInfo"
{
\tgame \t"citadel"

\tMemory
\t{
\t\t"Foo" "1"
\t}
}
'''


def _write(tmp, text):
    with open(tmp, "wb") as fh:
        fh.write(text.encode("utf-8"))


def _balanced(text):
    return text.count("{") == text.count("}")


def test_reads_existing_value(tmp_path):
    p = tmp_path / "gameinfo.gi"
    _write(p, SAMPLE)
    assert gameinfo.read_current(str(p)) == "2.3"


def test_update_existing_value(tmp_path):
    p = tmp_path / "gameinfo.gi"
    _write(p, SAMPLE)
    status, prev = gameinfo.patch(str(p), "2", make_backup=False)
    assert status == gameinfo.UPDATED
    assert prev == "2.3"
    assert gameinfo.read_current(str(p)) == "2"
    with open(p, encoding="utf-8") as fh:
        out = fh.read()
    # Nested rate block must survive intact.
    assert '"rate"' in out and '"default"\t"786432"' in out
    assert _balanced(out)


def test_idempotent(tmp_path):
    p = tmp_path / "gameinfo.gi"
    _write(p, SAMPLE)
    gameinfo.patch(str(p), "2", make_backup=False)
    before = open(p, "rb").read()
    status, _ = gameinfo.patch(str(p), "2", make_backup=False)
    assert status == gameinfo.ALREADY_OK
    assert open(p, "rb").read() == before  # untouched


def test_insert_when_missing(tmp_path):
    p = tmp_path / "gameinfo.gi"
    _write(p, SAMPLE_NO_ASPECT)
    status, prev = gameinfo.patch(str(p), "2.15", make_backup=False)
    assert status == gameinfo.ADDED
    assert prev is None
    assert gameinfo.read_current(str(p)) == "2.15"
    out = open(p, encoding="utf-8").read()
    assert '"rate"' in out and _balanced(out)


def test_create_convars_block(tmp_path):
    p = tmp_path / "gameinfo.gi"
    _write(p, SAMPLE_NO_CONVARS)
    status, _ = gameinfo.patch(str(p), "2.49", make_backup=False)
    assert status == gameinfo.CREATED
    assert gameinfo.read_current(str(p)) == "2.49"
    out = open(p, encoding="utf-8").read()
    assert "ConVars" in out and _balanced(out)


def test_normalize():
    assert gameinfo.normalize_value("2") == "2"
    assert gameinfo.normalize_value(" 2,15 ") == "2.15"
    assert gameinfo.normalize_value("abc") is None
    assert gameinfo.normalize_value("99") is None
    assert gameinfo.normalize_value("") is None


def test_fov_mapping():
    assert gameinfo.aspect_to_fov("2.15") == 91  # ~90
    assert gameinfo.aspect_to_fov("3.00") == 115


if __name__ == "__main__":
    import tempfile
    import types

    passed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and isinstance(fn, types.FunctionType):
            if "tmp_path" in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
                with tempfile.TemporaryDirectory() as d:
                    class _P:
                        def __truediv__(self, other):
                            return os.path.join(d, other)
                    fn(_P())
            else:
                fn()
            passed += 1
            print(f"ok  {name}")
    print(f"\n{passed} tests passed")
