"""Tests for the config parser and the block-merge engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlfovfixer import gameinfo, tweaks  # noqa: E402

# A messy blob like the ones users paste: headers, line numbers, comments,
# bare + quoted pairs, and all three target sections mixed together.
BLOB = """
============ SOMEONE'S CONFIG ============
----- VIDEO.CFG -----
12.  "setting.defaultres" "2560"     // your res
13.  "setting.fps_max" "0"
----- CONVARS -----
r_aspectratio 2                       // FOV
r_directlighting 0                    // lighting
rate 786432                           // bandwidth
threadpool_thread_limit 0
----- SCENESYSTEM -----
   GpuLightBinner 1
   CSMCascadeResolution 0
   SunLightShadowRenderMode Depth
   WellKnownLightCookies
   {
"""


def test_parse_routes_by_key_shape():
    p = tweaks.parse(BLOB)
    cv = dict(p["convars"])
    sc = dict(p["scenesystem"])
    vid = dict(p["video"])
    assert p["fov"] == "2"                       # r_aspectratio pulled out
    assert "r_aspectratio" not in cv
    assert cv["r_directlighting"] == "0"
    assert cv["rate"] == "786432"
    assert cv["threadpool_thread_limit"] == "0"
    assert sc["GpuLightBinner"] == "1"
    assert sc["SunLightShadowRenderMode"] == "Depth"
    assert "WellKnownLightCookies" not in sc     # block header (no value) ignored
    assert vid["setting.defaultres"] == "2560"
    assert vid["setting.fps_max"] == "0"


def test_parse_dedup_last_wins_order_kept():
    p = tweaks.parse("cl_foo 1\ncl_bar 2\ncl_foo 9\n")
    assert p["convars"] == [("cl_foo", "9"), ("cl_bar", "2")]


# ---- merge engine, exercised against a faithful mini gameinfo.gi ----------

MINI = '''"GameInfo"
{
\tConVars
\t{
\t\t"r_aspectratio" "2.3"
\t\t"r_directlighting" "1"                 // keep this comment
\t\t"rate"
\t\t{
\t\t\t"default"\t"786432"
\t\t}
\t}

\tSceneSystem
\t{
\t\tGpuLightBinner 1
\t\tCSMCascadeResolution 2048
\t}
}
'''


def _balanced(t):
    return t.count("{") == t.count("}")


def test_merge_convars_update_add_skipblock():
    entries = [("r_directlighting", "0"), ("cl_new", "1"), ("rate", "786432")]
    out, results = gameinfo.merge_block(MINI, "ConVars", entries, quoted=True)
    ra = dict(results)
    assert ra["r_directlighting"] == "updated"
    assert ra["cl_new"] == "added"
    assert ra["rate"] == "skipped_block"          # rate is a nested block -> untouched
    assert '"r_directlighting" "0"                 // keep this comment' in out
    assert '"cl_new"\t"1"' in out
    assert '"default"\t"786432"' in out and _balanced(out)


def test_merge_scenesystem_unquoted():
    entries = [("CSMCascadeResolution", "0"), ("VolumetricFog", "0")]
    out, results = gameinfo.merge_block(MINI, "SceneSystem", entries, quoted=False)
    ra = dict(results)
    assert ra["CSMCascadeResolution"] == "updated"
    assert ra["VolumetricFog"] == "added"
    assert "CSMCascadeResolution 0" in out
    assert "VolumetricFog\t0" in out and _balanced(out)


def test_scenesystem_update_crlf():
    # Real gameinfo.gi uses CRLF; unquoted keys must UPDATE, not duplicate.
    crlf = MINI.replace("\n", "\r\n")
    out, results = gameinfo.merge_block(
        crlf, "SceneSystem", [("CSMCascadeResolution", "0")], quoted=False)
    assert dict(results)["CSMCascadeResolution"] == "updated"
    assert out.count("CSMCascadeResolution") == 1  # no duplicate added
    assert "CSMCascadeResolution 0" in out


def test_apply_config_end_to_end(tmp_path):
    p = tmp_path / "gameinfo.gi"
    p.write_bytes(MINI.encode("utf-8"))
    summary = gameinfo.apply_config(
        str(p), "2.83",
        convars=[("r_directlighting", "0"), ("cl_new", "1")],
        scenesystem=[("VolumetricFog", "0")],
        make_backup=False,
    )
    assert summary["changed"] and summary["prev_fov"] == "2.3"
    text = p.read_text(encoding="utf-8")
    assert gameinfo.read_current(str(p)) == "2.83"
    assert '"cl_new"\t"1"' in text
    assert "VolumetricFog\t0" in text
    assert _balanced(text)
    # idempotent second pass
    s2 = gameinfo.apply_config(
        str(p), "2.83",
        convars=[("r_directlighting", "0"), ("cl_new", "1")],
        scenesystem=[("VolumetricFog", "0")], make_backup=False,
    )
    assert not s2["changed"]


def test_video_cfg_create_and_merge(tmp_path):
    p = tmp_path / "cfg" / "video.txt"
    r = gameinfo.merge_video_cfg(str(p), [("setting.fps_max", "0")], make_backup=False)
    assert r["created"] and os.path.isfile(p)
    r2 = gameinfo.merge_video_cfg(str(p), [("setting.fps_max", "240"),
                                           ("setting.mat_vsync", "0")], make_backup=False)
    assert not r2["created"]
    text = p.read_text(encoding="utf-8")
    assert '"setting.fps_max"' in text and "240" in text
    assert '"setting.mat_vsync"' in text and _balanced(text)


if __name__ == "__main__":
    import tempfile
    import types

    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and isinstance(fn, types.FunctionType):
            if fn.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as d:
                    class _P:
                        def __truediv__(self, o):
                            return _F(os.path.join(d, o))
                    class _F(str):
                        def write_bytes(self, b): open(self, "wb").write(b)
                        def read_text(self, encoding="utf-8"): return open(self, encoding=encoding).read()
                        def __truediv__(self, o):
                            os.makedirs(self, exist_ok=True)
                            return _F(os.path.join(self, o))
                    fn(_P())
            else:
                fn()
            n += 1
            print("ok ", name)
    print(f"\n{n} tests passed")
