"""Tests for GitHub Releases update discovery."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dlfovfixer import updater  # noqa: E402


def test_parse_version_accepts_release_tags():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("DL-FOV-Fixer-v2.0") == (2, 0)
    assert updater.parse_version("not-a-version") is None


def test_is_newer_pads_short_versions():
    assert updater.is_newer((1, 0, 1), (1, 0))
    assert updater.is_newer((1, 1), (1, 0, 9))
    assert not updater.is_newer((1, 0), (1, 0, 0))


def test_select_asset_prefers_named_exe():
    asset = updater.select_asset([
        {"name": "notes.txt", "browser_download_url": "https://example.invalid/notes.txt"},
        {"name": "OtherTool.exe", "browser_download_url": "https://example.invalid/other.exe"},
        {
            "name": "DL-FOV-Fixer.exe",
            "browser_download_url": "https://example.invalid/DL-FOV-Fixer.exe",
            "size": 123,
        },
    ])

    assert asset is not None
    assert asset.name == "DL-FOV-Fixer.exe"
    assert asset.size == 123


def test_latest_release_ignores_current_version(monkeypatch):
    monkeypatch.setattr(updater, "_request_json", lambda _url, _timeout: {
        "tag_name": updater.current_version(),
        "name": updater.current_version(),
        "html_url": "https://example.invalid/releases/current",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "DL-FOV-Fixer.exe",
                "browser_download_url": "https://example.invalid/DL-FOV-Fixer.exe",
            }
        ],
    })

    assert updater.latest_release() is None


def test_latest_release_requires_exe_asset(monkeypatch):
    monkeypatch.setattr(updater, "_request_json", lambda _url, _timeout: {
        "tag_name": "v99.0.0",
        "name": "v99.0.0",
        "html_url": "https://example.invalid/releases/v99.0.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": "source.zip", "browser_download_url": "https://example.invalid/source.zip"}
        ],
    })

    assert updater.latest_release() is None


def test_latest_release_returns_newer_exe(monkeypatch):
    monkeypatch.setattr(updater, "_request_json", lambda _url, _timeout: {
        "tag_name": "v99.0.0",
        "name": "DL-FOV-Fixer 99.0.0",
        "html_url": "https://example.invalid/releases/v99.0.0",
        "body": "Changes",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "DL-FOV-Fixer.exe",
                "browser_download_url": "https://example.invalid/DL-FOV-Fixer.exe",
            }
        ],
    })

    release = updater.latest_release()

    assert release is not None
    assert release.tag == "v99.0.0"
    assert release.asset.name == "DL-FOV-Fixer.exe"
