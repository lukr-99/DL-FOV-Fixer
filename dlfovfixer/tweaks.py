"""Parse a pasted Deadlock config blob into structured tweaks.

The goal is copy-paste convenience: a user grabs someone's config (which mixes
``gameinfo.gi`` ConVars, ``gameinfo.gi`` SceneSystem overrides and optional
``video.cfg`` settings, often with decorative headers, ``//`` comments and even
line numbers) and this turns it into three clean, ordered key/value lists.

Routing is by **key shape**, which is reliable for Deadlock and needs no
section headers:

    * key starts with ``setting.``   -> video.cfg
    * key is PascalCase (A-Z first)  -> gameinfo.gi SceneSystem
    * anything else (lower/r_/cl_ …) -> gameinfo.gi ConVars

``r_aspectratio`` is pulled out separately as the FOV value so it stays the
single source of truth for the FOV feature.
"""

from __future__ import annotations

import re

_COMMENT_RE = re.compile(r"(//|#).*$")
_LISTNUM_RE = re.compile(r"^\s*\d+[.)]\s*")     # "12."  or "12)"
_KEY_RE = re.compile(r"^[A-Za-z_][\w.]*$")

FOV_KEY = "r_aspectratio"


def _clean(line: str) -> str:
    line = _COMMENT_RE.sub("", line)
    line = line.strip()
    line = _LISTNUM_RE.sub("", line)
    line = line.strip().strip("{}").strip()
    return line


def _split_kv(line: str):
    """Return (key, value) from a cleaned line, or None."""
    parts = line.split(None, 1)
    if len(parts) != 2:
        return None
    key = parts[0].strip().strip('"').strip()
    if not _KEY_RE.match(key):
        return None
    vraw = parts[1].strip()
    if vraw.startswith('"'):
        m = re.match(r'"([^"]*)"', vraw)
        value = m.group(1) if m else vraw.strip('"')
    else:
        value = vraw.split()[0]
    return key, value


def _route(key: str) -> str:
    if key.startswith("setting."):
        return "video"
    if key[:1].isupper():
        return "scenesystem"
    return "convars"


def parse(text: str) -> dict:
    """Parse blob text into ordered, de-duplicated tweak lists.

    Returns ``{"convars": [(k,v)…], "scenesystem": […], "video": […],
    "fov": str|None}``. Later duplicates overwrite earlier ones while keeping
    first-seen order.
    """
    buckets = {"convars": {}, "scenesystem": {}, "video": {}}
    order = {"convars": [], "scenesystem": [], "video": []}
    fov = None

    for raw in text.splitlines():
        line = _clean(raw)
        if not line or not re.search(r"[A-Za-z]", line):
            continue
        kv = _split_kv(line)
        if kv is None:
            continue
        key, value = kv
        if key == FOV_KEY:
            fov = value
            continue
        bucket = _route(key)
        if key not in buckets[bucket]:
            order[bucket].append(key)
        buckets[bucket][key] = value

    result = {b: [(k, buckets[b][k]) for k in order[b]] for b in buckets}
    result["fov"] = fov
    return result


def merge_lists(existing, incoming):
    """Merge two ordered ``[(k, v), …]`` lists; incoming values win, order kept."""
    out = {}
    order = []
    for k, v in list(existing) + list(incoming):
        if k not in out:
            order.append(k)
        out[k] = v
    return [(k, out[k]) for k in order]


def counts(tweaks: dict) -> str:
    return "%d convars, %d scenesystem, %d video" % (
        len(tweaks.get("convars", [])),
        len(tweaks.get("scenesystem", [])),
        len(tweaks.get("video", [])),
    )
