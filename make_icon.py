"""Regenerate assets/icon.ico from the runtime icon factory."""

import os

from dlfovfixer import iconfactory

OUT = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    iconfactory.save_ico(OUT)
    print("Wrote", OUT)
