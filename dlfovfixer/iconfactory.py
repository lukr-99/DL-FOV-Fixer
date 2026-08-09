"""Generate the app icon at runtime (for the tray) and export an .ico file.

The mark is a bold **field-of-view vision cone**: a fan of sightlines opening
from a camera "lens" at the bottom, drawn on a dark rounded tile. The cone is
filled with the live status color so the tray icon is unmistakable at a glance,
even at 16 px:

    "ok"    -> green   : file located and FOV matches your target
    "idle"  -> amber   : located but not applied yet / drifted, waiting
    "error" -> red     : gameinfo.gi missing / unreadable / write failed

The shape stays constant (that's the app's identity); only the color changes
(that's the state). No external art assets are needed — it's all drawn with
Pillow.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

_BG = (26, 22, 17, 255)     # warm charcoal tile
_LENS = (18, 15, 11, 255)   # dark camera "lens" at the cone apex

# Per-status colors: bright = cone fill + tile border, deep = sightlines/arc.
_STATUS = {
    "idle":  dict(bright=(240, 170, 60, 255),  deep=(150, 96, 20, 255)),
    "ok":    dict(bright=(74, 200, 110, 255),  deep=(26, 120, 60, 255)),
    "error": dict(bright=(235, 72, 72, 255),   deep=(140, 30, 30, 255)),
}


def build_image(size: int = 256, status: str = "idle") -> Image.Image:
    """Render the vision-cone icon at the given square size and status."""
    c = _STATUS.get(status, _STATUS["idle"])
    scale = 4  # supersample for crisp edges, then downsample
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded tile with a status-colored border.
    m = s * 0.05
    d.rounded_rectangle(
        [m, m, s - m, s - m], radius=s * 0.26,
        fill=_BG, outline=c["bright"], width=max(2, int(s * 0.06)),
    )

    apex = (s * 0.5, s * 0.82)
    r = s * 0.60
    half = 45           # half-angle of the cone
    up = 270            # PIL: 0=east, 270=north(up)
    box = [apex[0] - r, apex[1] - r, apex[0] + r, apex[1] + r]

    # Filled field-of-view cone.
    d.pieslice(box, up - half, up + half, fill=c["bright"])

    # Sightlines fanning through the cone (the "field of view" grid).
    ray_w = max(1, int(s * 0.013))
    for a in (-half + 6, -half * 0.5, 0, half * 0.5, half - 6):
        ang = math.radians(up + a)
        x = apex[0] + r * 0.94 * math.cos(ang)
        y = apex[1] + r * 0.94 * math.sin(ang)
        d.line([apex, (x, y)], fill=c["deep"], width=ray_w)

    # Inner range arc.
    ir = r * 0.56
    d.arc([apex[0] - ir, apex[1] - ir, apex[0] + ir, apex[1] + ir],
          up - half, up + half, fill=c["deep"], width=max(1, int(s * 0.022)))

    # Camera lens at the apex (the viewer).
    lr = s * 0.08
    d.ellipse([apex[0] - lr, apex[1] - lr, apex[0] + lr, apex[1] + lr],
              fill=_LENS, outline=c["bright"], width=max(1, int(s * 0.022)))

    return img.resize((size, size), Image.LANCZOS)


def save_ico(path: str, status: str = "idle",
             sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Write a multi-resolution .ico file (the app/exe icon uses 'idle')."""
    base = build_image(max(sizes), status)
    base.save(path, format="ICO", sizes=[(x, x) for x in sizes])
