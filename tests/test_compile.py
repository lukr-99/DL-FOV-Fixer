"""Every module of the app must at least compile.

The tests import only the modules without a UI. app.py needs pystray and a display, so no test
imports it, and a syntax error there once passed the whole suite (docs/pitfalls.md).
"""

import pathlib
import py_compile

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "dlfovfixer"


@pytest.mark.parametrize("module", sorted(PACKAGE.glob("*.py")), ids=lambda path: path.name)
def test_module_compiles(module):
    py_compile.compile(str(module), doraise=True)
