"""Read, verify and patch Deadlock's ``gameinfo.gi`` FOV ConVar.

Deadlock has no in-game FOV slider. The community fix is to add
``"r_aspectratio" "<value>"`` to the ``ConVars`` block of
``...\\Deadlock\\game\\citadel\\gameinfo.gi``. A higher value = wider FOV.
Every game update can overwrite this file, which is the whole reason this
tool exists.

The editing here is deliberately *surgical* text manipulation rather than a
full KeyValues round-trip: we never reformat the file, we only change (or
insert) the single ``r_aspectratio`` line, and we brace-match so we never
touch the nested ``rate``/``speaker_config`` sub-blocks that live inside
``ConVars`` (mangling those makes the game refuse to launch).
"""

from __future__ import annotations

import os
import re
import shutil

# The ConVar that controls FOV, and the tool's fallback default value.
# Kept as module constants so a future game change only needs an edit here.
CONVAR_NAME = "r_aspectratio"
DEFAULT_VALUE = "2"

BACKUP_SUFFIX = ".dlfovfixer.bak"

# Approximate FOV (degrees) for a given r_aspectratio, derived from the
# community tutorial data points (1.75->80, 2.15->90, 2.49->100, 2.66->105,
# 2.83->110, 3.00->115). The relationship is very close to linear:
#     fov ~= 28 * aspect + 31
_FOV_SLOPE = 28.0
_FOV_INTERCEPT = 31.0

# Handy presets shown in the tray menu: (degrees, r_aspectratio string).
PRESETS = [
    (80, "1.75"),
    (90, "2.15"),
    (100, "2.49"),
    (105, "2.66"),
    (110, "2.83"),
    (115, "3.00"),
]

# patch() result codes.
ALREADY_OK = "already_ok"   # value was already correct, file untouched
UPDATED = "updated"         # existing r_aspectratio value was changed
ADDED = "added"             # r_aspectratio inserted into existing ConVars block
CREATED = "created"         # a whole ConVars block was created


def aspect_to_fov(value) -> int | None:
    """Approximate horizontal FOV in degrees for an r_aspectratio value."""
    try:
        return round(_FOV_SLOPE * float(value) + _FOV_INTERCEPT)
    except (TypeError, ValueError):
        return None


def fov_to_aspect(fov) -> float:
    """Inverse of :func:`aspect_to_fov`, rounded to 2 decimals."""
    return round((float(fov) - _FOV_INTERCEPT) / _FOV_SLOPE, 2)


def normalize_value(raw) -> str | None:
    """Validate and normalize a user-entered r_aspectratio value.

    Returns the cleaned string (preserving the user's own formatting such as
    ``"2"`` vs ``"2.15"``) or ``None`` if it isn't a sensible positive number.
    """
    if raw is None:
        return None
    text = str(raw).strip().replace(",", ".")
    if not text:
        return None
    try:
        num = float(text)
    except ValueError:
        return None
    # Guard against nonsense that could make the game look broken.
    if not (0.5 <= num <= 6.0):
        return None
    return text


# --------------------------------------------------------------------------
# Low-level file helpers
# --------------------------------------------------------------------------

def _read(path: str):
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, newline


def _write(path: str, text: str) -> None:
    # Write bytes so we fully control newlines and never emit a BOM.
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))


def _matching_brace(text: str, open_idx: int) -> int:
    """Index of the ``}`` matching the ``{`` at ``open_idx``, or -1.

    Honors KeyValues quoting and ``//`` line comments so stray braces inside
    strings or comments don't throw off the depth count.
    """
    depth = 0
    i = open_idx
    n = len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            if nl == -1:
                return -1
            i = nl
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _block_span(text: str, name: str):
    """Return ``(open_brace_idx, close_brace_idx)`` of a named KV block.

    Matches the block header ``name`` (quoted or unquoted) as a whole word
    followed by its ``{`` … ``}``. Returns ``None`` if not found (or unbalanced).
    """
    for m in re.finditer(re.escape(name), text):
        start, end = m.start(), m.end()
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        # Whole-word only (allow a leading/trailing quote for "Name").
        if before.isalnum() or before == "_":
            continue
        if after.isalnum() or after == "_":
            continue
        j = end
        while j < len(text) and text[j] in ' \t\r\n"':
            j += 1
        if j < len(text) and text[j] == "{":
            close = _matching_brace(text, j)
            if close != -1:
                return j, close
    return None


def _outer_block_span(text: str):
    """Span of the first (outermost) ``{`` … ``}`` in the text, or ``None``."""
    i = text.find("{")
    if i == -1:
        return None
    close = _matching_brace(text, i)
    return (i, close) if close != -1 else None


# Matches a top-level ``"r_aspectratio" "value"`` pair (value on the same line).
_ENTRY_RE = re.compile(r'"%s"[ \t]*"([^"]*)"' % re.escape(CONVAR_NAME))


def _current_from_text(text: str):
    span = _block_span(text, "ConVars")
    block = text[span[0]:span[1] + 1] if span else text
    m = _ENTRY_RE.search(block)
    return m.group(1) if m else None


def read_current(path: str):
    """Current r_aspectratio value in the file, or ``None`` if not set."""
    text, _ = _read(path)
    return _current_from_text(text)


def backup_path(path: str) -> str:
    return path + BACKUP_SUFFIX


def _ensure_backup(path: str) -> None:
    """Copy the file to a one-time backup (never overwrites an existing one)."""
    bak = backup_path(path)
    if not os.path.exists(bak):
        shutil.copy2(path, bak)


def restore_backup(path: str) -> bool:
    """Restore the original file from the one-time backup, if present."""
    bak = backup_path(path)
    if os.path.exists(bak):
        shutil.copy2(bak, path)
        return True
    return False


def patch(path: str, value: str, make_backup: bool = True):
    """Ensure ``r_aspectratio`` equals ``value`` in ``gameinfo.gi``.

    Idempotent: if the value already matches, the file is left untouched.

    Returns ``(status, previous_value)`` where ``status`` is one of the module
    result codes and ``previous_value`` is the value found before patching
    (``None`` if it wasn't set).
    """
    value = normalize_value(value) or DEFAULT_VALUE
    text, nl = _read(path)
    span = _block_span(text, "ConVars")
    entry = '"%s"\t"%s"' % (CONVAR_NAME, value)

    if span is None:
        # No ConVars block at all: create one just before GameInfo's final '}'.
        close = text.rstrip().rfind("}")
        if close == -1:
            raise ValueError("Unrecognized gameinfo.gi (no closing brace found).")
        block = (
            "\tConVars" + nl +
            "\t{" + nl +
            "\t\t" + entry + nl +
            "\t}" + nl +
            "\t"
        )
        new_text = text[:close] + block + text[close:]
        prev, status = None, CREATED
    else:
        open_idx, close_idx = span
        block = text[open_idx:close_idx + 1]
        m = _ENTRY_RE.search(block)
        if m:
            prev = m.group(1)
            if prev == value:
                return ALREADY_OK, prev
            new_block = block[:m.start()] + entry + block[m.end():]
            new_text = text[:open_idx] + new_block + text[close_idx + 1:]
            status = UPDATED
        else:
            # Insert on a fresh line right after the opening brace, i.e. at the
            # very top of the block — safely outside any nested sub-block.
            insert_at = open_idx + 1
            new_text = text[:insert_at] + nl + "\t\t" + entry + text[insert_at:]
            prev, status = None, ADDED

    if make_backup:
        _ensure_backup(path)
    _write(path, new_text)
    return status, prev


# --------------------------------------------------------------------------
# Generic block merging (for pasted ConVars / SceneSystem / video.cfg tweaks)
# --------------------------------------------------------------------------

def _fmt(key: str, value: str, quoted: bool) -> str:
    return '"%s"\t"%s"' % (key, value) if quoted else "%s\t%s" % (key, value)


def _merge_one(inner: str, key: str, value: str, quoted: bool):
    """Apply one key=value to a block's inner text.

    Returns ``(new_inner_or_None, action)`` where action is ``"updated"``,
    ``"skipped_block"`` (key exists as a nested sub-block — left alone), or
    ``"add"`` (caller should insert it).
    """
    kesc = re.escape(key)
    if quoted:
        m = re.search(r'("%s"[ \t]+)"[^"]*"' % kesc, inner)
        if m:
            return inner[:m.start()] + m.group(1) + '"%s"' % value + inner[m.end():], "updated"
        if re.search(r'"%s"\s*\{' % kesc, inner):
            return inner, "skipped_block"
    else:
        # NB: end with a lookahead for the line break (CRLF or LF) rather than
        # ``$`` — a plain ``$`` fails on CRLF files because of the trailing \r.
        m = re.search(
            r'(?m)^([ \t]*%s[ \t]+)(\S+)([ \t]*)((?://[^\r\n]*)?)(?=\r?\n|\Z)' % kesc,
            inner,
        )
        if m:
            repl = m.group(1) + value + m.group(3) + m.group(4)
            return inner[:m.start()] + repl + inner[m.end():], "updated"
        if re.search(r'(?m)^[ \t]*%s\s*\{' % kesc, inner):
            return inner, "skipped_block"
    return None, "add"


def merge_block(text: str, block_name: str, entries, quoted: bool, create: bool = True):
    """Merge ``entries`` (``[(k, v), …]``) into a named block.

    Existing simple keys are updated in place (comments preserved); missing keys
    are inserted at the top of the block; keys that already exist as a nested
    sub-block are skipped. Returns ``(new_text, results)`` with results as a list
    of ``(key, action)``.
    """
    entries = list(entries)
    if not entries:
        return text, []
    nl = "\r\n" if "\r\n" in text else "\n"
    span = _block_span(text, block_name)

    if span is None:
        if not create:
            return text, [(k, "no_block") for k, _ in entries]
        outer = _outer_block_span(text)
        if outer is None:
            return text, [(k, "no_root") for k, _ in entries]
        body = "".join("\t\t%s%s" % (_fmt(k, v, quoted), nl) for k, v in entries)
        block = "\t%s%s\t{%s%s\t}%s\t" % (block_name, nl, nl, body, nl)
        close = outer[1]
        return text[:close] + block + text[close:], [(k, "added") for k, _ in entries]

    open_i, close_i = span
    head, inner, tail = text[:open_i + 1], text[open_i + 1:close_i], text[close_i:]
    results, adds = [], []
    for k, v in entries:
        new_inner, action = _merge_one(inner, k, v, quoted)
        if action == "add":
            adds.append((k, v))
            results.append((k, "added"))
        else:
            inner = new_inner
            results.append((k, action))
    if adds:
        body = "".join("\t\t%s%s" % (_fmt(k, v, quoted), nl) for k, v in adds)
        inner = nl + body + inner
    return head + inner + tail, results


def apply_config(path, fov_value, convars=None, scenesystem=None,
                 apply_tweaks=True, make_backup=True):
    """Ensure FOV plus (optionally) all pasted ConVars/SceneSystem tweaks.

    Writes at most once; idempotent. Returns a summary dict.
    """
    convars = list(convars or [])
    scenesystem = list(scenesystem or [])
    text, _ = _read(path)
    original = text
    prev_fov = _current_from_text(text)

    cv_entries = [(CONVAR_NAME, normalize_value(fov_value) or DEFAULT_VALUE)]
    if apply_tweaks:
        cv_entries += [(k, v) for k, v in convars if k != CONVAR_NAME]
    text, cv_results = merge_block(text, "ConVars", cv_entries, quoted=True, create=True)

    sc_results = []
    if apply_tweaks and scenesystem:
        text, sc_results = merge_block(text, "SceneSystem", scenesystem,
                                       quoted=False, create=True)

    changed = text != original
    if changed:
        if make_backup:
            _ensure_backup(path)
        _write(path, text)
    return {
        "changed": changed,
        "prev_fov": prev_fov,
        "convars": cv_results,
        "scenesystem": sc_results,
    }


# --------------------------------------------------------------------------
# video settings (optional; cfg/video.txt next to gameinfo.gi)
# --------------------------------------------------------------------------

def video_settings_path(gameinfo_path: str) -> str:
    return os.path.join(os.path.dirname(gameinfo_path), "cfg", "video.txt")


def merge_video_cfg(path, entries, make_backup=True, create=True):
    """Merge ``setting.*`` entries into the video settings file (video.txt),
    creating it if needed."""
    entries = list(entries)
    if not entries:
        return {"changed": False, "created": False, "results": []}

    if not os.path.isfile(path):
        if not create:
            return {"changed": False, "created": False, "results": []}
        nl = "\r\n"
        body = "".join('\t"%s"\t\t"%s"%s' % (k, v, nl) for k, v in entries)
        text = '"video.cfg"%s{%s%s}%s' % (nl, nl, body, nl)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _write(path, text)
        return {"changed": True, "created": True,
                "results": [(k, "added") for k, _ in entries]}

    text, nl = _read(path)
    original = text
    span = _outer_block_span(text)
    if span is None:
        # No block to merge into; wrap a fresh one.
        body = "".join('\t"%s"\t\t"%s"%s' % (k, v, nl) for k, v in entries)
        text = '"video.cfg"%s{%s%s}%s' % (nl, nl, body, nl)
        if make_backup:
            _ensure_backup(path)
        _write(path, text)
        return {"changed": True, "created": False,
                "results": [(k, "added") for k, _ in entries]}

    open_i, close_i = span
    head, inner, tail = text[:open_i + 1], text[open_i + 1:close_i], text[close_i:]
    results, adds = [], []
    for k, v in entries:
        new_inner, action = _merge_one(inner, k, v, quoted=True)
        if action == "add":
            adds.append((k, v))
            results.append((k, "added"))
        else:
            inner = new_inner
            results.append((k, action))
    if adds:
        body = "".join('\t"%s"\t\t"%s"%s' % (k, v, nl) for k, v in adds)
        inner = nl + body + inner
    text = head + inner + tail

    changed = text != original
    if changed:
        if make_backup:
            _ensure_backup(path)
        _write(path, text)
    return {"changed": changed, "created": False, "results": results}
