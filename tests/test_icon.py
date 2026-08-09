"""Smoke tests for the icon factory (all status variants render)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlfovfixer import iconfactory  # noqa: E402


def test_all_statuses_render():
    for status in ("idle", "ok", "error"):
        img = iconfactory.build_image(64, status)
        assert img.size == (64, 64)
        assert img.mode == "RGBA"


def test_unknown_status_falls_back():
    img = iconfactory.build_image(32, "bogus")
    assert img.size == (32, 32)


if __name__ == "__main__":
    test_all_statuses_render()
    test_unknown_status_falls_back()
    print("ok  icon tests passed")
