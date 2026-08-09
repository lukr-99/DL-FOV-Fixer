"""Generate the app icon at runtime (for the tray) and export an .ico file.

The look is Deadlock-flavored: a dark warm tile with an amber border, a faint
field-of-view "cone" motif, and bold "FOV" lettering. No external art assets
are needed — everything is drawn with Pillow.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

# Palette (RGBA) — Deadlock's dark/amber-with-teal feel.
_BG = (22, 18, 14, 255)         # near-black, warm
_BORDER = (196, 148, 74, 255)   # amber
_TEXT = (240, 200, 128, 255)    # light gold
_CONE = (96, 178, 176, 255)     # muted teal

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


def build_image(size: int = 256) -> Image.Image:
    """Render the icon at the given square size."""
    scale = 4  # supersample for crisp edges, then downsample
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = s * 0.06
    radius = s * 0.24
    border_w = max(2, int(s * 0.045))
    d.rounded_rectangle(
        [margin, margin, s - margin, s - margin],
        radius=radius, fill=_BG, outline=_BORDER, width=border_w,
    )

    # Field-of-view "cone" fanning up from the bottom center (behind the text).
    apex = (s * 0.5, s * 0.86)
    spread = s * 0.30
    top_y = s * 0.30
    cone_w = max(2, int(s * 0.018))
    for dx in (-spread, spread):
        d.line([apex, (s * 0.5 + dx, top_y)], fill=_CONE + (), width=cone_w)
    # A small arc across the top of the cone to suggest the view angle.
    d.arc(
        [s * 0.5 - spread, top_y - spread * 0.5,
         s * 0.5 + spread, top_y + spread * 1.5],
        start=200, end=340, fill=_CONE, width=cone_w,
    )

    # "FOV" lettering, centered.
    font = _load_font(int(s * 0.30))
    text = "FOV"
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    tx = (s - (r - l)) / 2 - l
    ty = s * 0.52 - t
    # subtle shadow for legibility on the cone
    d.text((tx + scale, ty + scale), text, font=font, fill=(0, 0, 0, 150))
    d.text((tx, ty), text, font=font, fill=_TEXT)

    return img.resize((size, size), Image.LANCZOS)


def save_ico(path: str, sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Write a multi-resolution .ico file."""
    base = build_image(max(sizes))
    base.save(path, format="ICO", sizes=[(x, x) for x in sizes])
