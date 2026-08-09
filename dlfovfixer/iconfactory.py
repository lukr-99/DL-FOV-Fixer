"""Generate the app icon at runtime (for the tray) and export an .ico file.

The look is Deadlock-flavored: a dark warm tile with a colored border, a faint
field-of-view "cone" motif, and bold "FOV" lettering. A small corner dot and
the border color encode the live status so the tray icon is readable at a
glance:

    "ok"    -> green   : file located and FOV matches your target
    "idle"  -> amber   : located but not applied yet / drifted, waiting
    "error" -> red     : gameinfo.gi missing / unreadable / write failed

No external art assets are needed — everything is drawn with Pillow.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

_BG = (22, 18, 14, 255)      # near-black, warm
_TEXT = (240, 200, 128, 255)  # light gold (always readable)

# Per-status accent colors: border ring, FOV cone, and corner status dot.
_STATUS = {
    "idle": dict(border=(196, 148, 74, 255), cone=(96, 178, 176, 255), dot=(214, 162, 84, 255)),
    "ok":   dict(border=(86, 184, 98, 255),  cone=(96, 178, 176, 255), dot=(96, 208, 110, 255)),
    "error": dict(border=(210, 76, 76, 255), cone=(150, 96, 96, 255),  dot=(232, 78, 78, 255)),
}

_FONT_CANDIDATES = [
    "arialbd.ttf", "segoeuib.ttf", "bahnschrift.ttf",
    "impact.ttf", "seguisb.ttf", "arial.ttf",
]


def _load_font(px: int) -> ImageFont.FreeTypeFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def build_image(size: int = 256, status: str = "idle") -> Image.Image:
    """Render the icon at the given square size for the given status."""
    colors = _STATUS.get(status, _STATUS["idle"])
    scale = 4  # supersample for crisp edges, then downsample
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = s * 0.06
    radius = s * 0.24
    border_w = max(2, int(s * 0.05))
    d.rounded_rectangle(
        [margin, margin, s - margin, s - margin],
        radius=radius, fill=_BG, outline=colors["border"], width=border_w,
    )

    # Field-of-view "cone" fanning up from the bottom center (behind the text).
    apex = (s * 0.5, s * 0.86)
    spread = s * 0.30
    top_y = s * 0.30
    cone_w = max(2, int(s * 0.018))
    for dx in (-spread, spread):
        d.line([apex, (s * 0.5 + dx, top_y)], fill=colors["cone"], width=cone_w)
    d.arc(
        [s * 0.5 - spread, top_y - spread * 0.5,
         s * 0.5 + spread, top_y + spread * 1.5],
        start=200, end=340, fill=colors["cone"], width=cone_w,
    )

    # "FOV" lettering, centered.
    font = _load_font(int(s * 0.30))
    text = "FOV"
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    tx = (s - (r - l)) / 2 - l
    ty = s * 0.52 - t
    d.text((tx + scale, ty + scale), text, font=font, fill=(0, 0, 0, 150))  # shadow
    d.text((tx, ty), text, font=font, fill=_TEXT)

    # Status dot in the bottom-right corner (dark ring for contrast).
    dr = s * 0.15
    cx, cy = s * 0.78, s * 0.78
    d.ellipse([cx - dr - scale, cy - dr - scale, cx + dr + scale, cy + dr + scale],
              fill=(12, 10, 8, 255))
    d.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=colors["dot"])

    return img.resize((size, size), Image.LANCZOS)


def save_ico(path: str, status: str = "idle",
             sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Write a multi-resolution .ico file (the app/exe icon uses 'idle')."""
    base = build_image(max(sizes), status)
    base.save(path, format="ICO", sizes=[(x, x) for x in sizes])
