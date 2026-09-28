"""Runs the shared behavior vectors in contracts/vectors against the Python app.

The C# port reads the same files, so a case added here is a case both implementations must pass.
See contracts/vectors/README.md for the format.
"""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dlfovfixer import gameinfo, tweaks  # noqa: E402

VECTORS = ROOT / "contracts" / "vectors"


def _load(name):
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


def _text(lines):
    return None if lines is None else "\n".join(lines)


def _pairs(items):
    return [list(item) for item in items]


def _cases(name):
    """Every case in LF form, plus a CRLF form when the case has text input."""
    params = []
    for case in _load(name)["cases"]:
        params.append(pytest.param(case, False, id=case["name"] + " [LF]"))
        if case["input"] is not None:
            params.append(pytest.param(case, True, id=case["name"] + " [CRLF]"))
    return params


def _eol(text, crlf):
    return text.replace("\n", "\r\n") if crlf and text is not None else text


def _count_writes(monkeypatch):
    writes = []
    real = gameinfo._write
    monkeypatch.setattr(gameinfo, "_write", lambda p, t: (writes.append(p), real(p, t)))
    return writes


@pytest.mark.parametrize("case, crlf", _cases("gameinfo-merge.json"))
def test_merge_block(case, crlf):
    source = _eol(_text(case["input"]), crlf)
    expected = _eol(_text(case["expected"]["output"]), crlf)
    entries = [tuple(e) for e in case["entries"]]

    out, results = gameinfo.merge_block(
        source, case["block"], entries, quoted=case["quoted"], create=case["create"])

    assert out == expected
    assert _pairs(results) == case["expected"]["results"]
    again, _ = gameinfo.merge_block(
        out, case["block"], entries, quoted=case["quoted"], create=case["create"])
    assert again == out


@pytest.mark.parametrize("case, crlf", _cases("gameinfo-apply.json"))
def test_apply_config(case, crlf, tmp_path, monkeypatch):
    path = tmp_path / "gameinfo.gi"
    path.write_bytes(_eol(_text(case["input"]), crlf).encode("utf-8"))
    expected = case["expected"]
    args = dict(
        convars=[tuple(e) for e in case["convars"]],
        scenesystem=[tuple(e) for e in case["scenesystem"]],
        apply_tweaks=case["applyTweaks"],
        make_backup=False,
    )

    summary = gameinfo.apply_config(str(path), case["fov"], **args)

    assert path.read_bytes() == _eol(_text(expected["output"]), crlf).encode("utf-8")
    assert summary["changed"] == expected["changed"]
    assert summary["prev_fov"] == expected["previousFov"]
    assert _pairs(summary["convars"]) == expected["convars"]
    assert _pairs(summary["scenesystem"]) == expected["scenesystem"]

    writes = _count_writes(monkeypatch)
    again = gameinfo.apply_config(str(path), case["fov"], **args)
    assert not again["changed"]
    assert writes == []


@pytest.mark.parametrize("case, crlf", _cases("video-config.json"))
def test_merge_video_cfg(case, crlf, tmp_path, monkeypatch):
    path = tmp_path / "cfg" / "video.txt"
    if case["input"] is not None:
        path.parent.mkdir()
        path.write_bytes(_eol(_text(case["input"]), crlf).encode("utf-8"))
    entries = [tuple(e) for e in case["entries"]]
    expected = case["expected"]

    result = gameinfo.merge_video_cfg(str(path), entries, make_backup=False)

    assert result["changed"] == expected["changed"]
    assert result["created"] == expected["created"]
    assert _pairs(result["results"]) == expected["results"]
    assert path.read_bytes() == _eol(_text(expected["output"]), crlf).encode("utf-8")

    writes = _count_writes(monkeypatch)
    again = gameinfo.merge_video_cfg(str(path), entries, make_backup=False)
    assert not again["changed"]
    assert writes == []


@pytest.mark.parametrize(
    "case", [pytest.param(c, id=c["name"]) for c in _load("tweak-parsing.json")["cases"]])
def test_parse_tweaks(case):
    parsed = tweaks.parse(_text(case["input"]))

    expected = case["expected"]
    assert parsed["fov"] == expected["fov"]
    for section in ("convars", "scenesystem", "video"):
        assert _pairs(parsed[section]) == expected[section]


@pytest.mark.parametrize(
    "case", [pytest.param(c, id=c["name"]) for c in _load("tweak-parsing.json")["mergeLists"]])
def test_merge_lists(case):
    merged = tweaks.merge_lists(
        [tuple(e) for e in case["existing"]], [tuple(e) for e in case["incoming"]])

    assert _pairs(merged) == case["expected"]


FOV = _load("fov-value.json")


@pytest.mark.parametrize("case", FOV["normalize"], ids=lambda c: repr(c["input"]))
def test_normalize_value(case):
    assert gameinfo.normalize_value(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", FOV["toDegrees"], ids=lambda c: repr(c["input"]))
def test_aspect_to_fov(case):
    assert gameinfo.aspect_to_fov(case["input"]) == case["expected"]


def test_presets_and_default():
    assert [[d, v] for d, v in gameinfo.PRESETS] == [[p["degrees"], p["value"]] for p in FOV["presets"]]
    assert gameinfo.DEFAULT_VALUE == FOV["defaultValue"]


def test_every_vector_file_is_read():
    read = {"gameinfo-merge.json", "gameinfo-apply.json", "video-config.json",
            "tweak-parsing.json", "fov-value.json"}
    assert set(os.listdir(VECTORS)) - {"README.md"} == read
