#!/usr/bin/env pythonw
"""Windowed launcher (no console). Also the target used by 'Start with Windows'
and by PyInstaller when building the .exe."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dlfovfixer.app import main  # noqa: E402

if __name__ == "__main__":
    main()
