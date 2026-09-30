"""GitHub Releases updater for the packaged tray app."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional

from . import __version__

OWNER = "lukr-99"
REPO = "DL-FOV-Fixer"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
USER_AGENT = f"DL-FOV-Fixer/{__version__}"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: Optional[int] = None


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    name: str
    html_url: str
    body: str
    version: tuple[int, ...]
    # None when the release has no installable asset. It must then be installed by hand.
    asset: Optional[ReleaseAsset]


def current_version() -> str:
    return __version__


def parse_version(value: str) -> Optional[tuple[int, ...]]:
    """Parse tags like v1.2.3 or agent-v1.2.3 into comparable numbers."""
    match = re.search(r"v?(\d+(?:\.\d+){0,3})", value.strip(), re.IGNORECASE)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(candidate: tuple[int, ...], current: tuple[int, ...]) -> bool:
    width = max(len(candidate), len(current))
    left = candidate + (0,) * (width - len(candidate))
    right = current + (0,) * (width - len(current))
    return left > right


def _request_json(url: str, timeout: float) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


INSTALLABLE_ASSET_NAME = "DL-FOV-Fixer.exe"


def select_asset(assets: Iterable[dict]) -> Optional[ReleaseAsset]:
    """Pick the one asset the updater may install: exactly DL-FOV-Fixer.exe.

    Windows file names are case-insensitive, so the case is ignored. Any other
    name (an installer, a portable build) is refused.
    """
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name.lower() != INSTALLABLE_ASSET_NAME.lower() or not url:
            continue
        return ReleaseAsset(name=name, download_url=url, size=asset.get("size"))
    return None


def latest_release(timeout: float = 10.0) -> Optional[ReleaseInfo]:
    data = _request_json(LATEST_RELEASE_URL, timeout)
    if not data or data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "")
    version = parse_version(tag)
    current = parse_version(__version__)
    if version is None or current is None or not is_newer(version, current):
        return None
    asset = select_asset(data.get("assets") or [])
    return ReleaseInfo(
        tag=tag,
        name=str(data.get("name") or tag),
        html_url=str(data.get("html_url") or ""),
        body=str(data.get("body") or ""),
        version=version,
        asset=asset,
    )


def download_asset(release: ReleaseInfo, timeout: float = 30.0) -> str:
    if release.asset is None:
        raise ValueError("This release has no installable asset.")
    filename = os.path.basename(release.asset.name) or "DL-FOV-Fixer-update.exe"
    target = os.path.join(tempfile.gettempdir(), filename)
    req = urllib.request.Request(
        release.asset.download_url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        with open(target, "wb") as fh:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                fh.write(chunk)
    return target


def install_downloaded_exe(downloaded_exe: str) -> None:
    """Replace the running PyInstaller exe, or launch the download in dev mode."""
    if not getattr(sys, "frozen", False):
        os.startfile(downloaded_exe)  # type: ignore[attr-defined]
        return

    current_exe = os.path.abspath(sys.executable)
    downloaded_exe = os.path.abspath(downloaded_exe)
    script_path = os.path.join(tempfile.gettempdir(), "DL-FOV-Fixer-update.cmd")
    script = f"""@echo off
setlocal
set "SRC={downloaded_exe}"
set "DST={current_exe}"
set "PID={os.getpid()}"
for /l %%i in (1,1,60) do (
  tasklist /fi "PID eq %PID%" | find "%PID%" >nul
  if errorlevel 1 goto replace
  timeout /t 1 /nobreak >nul
)
:replace
copy /y "%SRC%" "%DST%" >nul
start "" "%DST%"
del "%SRC%" >nul 2>nul
del "%~f0" >nul 2>nul
"""
    with open(script_path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(script)
    subprocess.Popen(
        ["cmd.exe", "/c", script_path],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
