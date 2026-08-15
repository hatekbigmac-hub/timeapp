"""Auto-update from GitHub Releases.

Flow: ask the GitHub API for the latest release of `owner/repo`, compare its tag
with APP_VERSION, download the TimeApp.exe asset, then hand off to a small .bat
that waits for this process to exit, swaps the file and relaunches.

Safety rules enforced here:
  * only https://api.github.com is queried, and the download URL must be an
    https github.com host — an attacker-supplied redirect elsewhere is refused;
  * the payload must be a real Windows executable (MZ header) and non-trivial in
    size before it is allowed to replace anything;
  * the running exe is never overwritten in place (Windows locks it).
"""

import os
import re
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlparse

import requests

import version

API = "https://api.github.com/repos/{repo}/releases/latest"
ASSET_NAME = "TimeApp.exe"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com",
                 "release-assets.githubusercontent.com")
MIN_SIZE = 2 * 1024 * 1024  # a real build is tens of MB; anything tiny is wrong


def normalize_repo(text: str) -> str:
    """Accept 'owner/repo' or a full github.com URL; return 'owner/repo' or ''."""
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("http"):
        parts = [p for p in urlparse(text).path.split("/") if p]
        if len(parts) >= 2:
            text = f"{parts[0]}/{parts[1]}"
    text = text.removesuffix(".git")
    return text if REPO_RE.match(text) else ""


def _host_ok(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def check(repo: str, timeout=15):
    """Return {'version','url','notes'} for a newer release, or None."""
    repo = normalize_repo(repo)
    if not repo:
        return None
    resp = requests.get(API.format(repo=repo), timeout=timeout,
                        headers={"Accept": "application/vnd.github+json"})
    if resp.status_code != 200:
        return None
    data = resp.json()
    tag = data.get("tag_name") or data.get("name") or ""
    if not version.is_newer(tag):
        return None
    for asset in data.get("assets") or []:
        if (asset.get("name") or "").lower() == ASSET_NAME.lower():
            url = asset.get("browser_download_url") or ""
            if _host_ok(url):
                return {"version": tag.lstrip("vV"), "url": url,
                        "notes": (data.get("body") or "")[:300]}
    return None


def download(url: str, timeout=120) -> str:
    """Download the new exe to a temp file; return its path (raises on trouble)."""
    if not _host_ok(url):
        raise ValueError("refused: download URL is not a github.com https host")
    dest = os.path.join(tempfile.gettempdir(), "TimeApp_update.exe")
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        if not _host_ok(resp.url):  # a redirect must stay on github hosts
            raise ValueError("refused: redirected off github.com")
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                if chunk:
                    fh.write(chunk)
    size = os.path.getsize(dest)
    if size < MIN_SIZE:
        os.remove(dest)
        raise ValueError(f"refused: downloaded file is too small ({size} bytes)")
    with open(dest, "rb") as fh:
        if fh.read(2) != b"MZ":
            os.remove(dest)
            raise ValueError("refused: downloaded file is not a Windows executable")
    return dest


def apply_update(new_exe: str, target_exe: str = None) -> bool:
    """Spawn the swap script and return True if it started. Caller then quits."""
    target_exe = target_exe or (sys.executable if getattr(sys, "frozen", False) else None)
    if not target_exe or not os.path.exists(new_exe):
        return False
    script = os.path.join(tempfile.gettempdir(), "timeapp_update.bat")
    name = os.path.basename(target_exe)
    body = f"""@echo off
set "TARGET={target_exe}"
set "NEWFILE={new_exe}"
rem wait for the running app to exit (up to ~60s)
set /a tries=0
:wait
tasklist /FI "IMAGENAME eq {name}" 2>nul | find /I "{name}" >nul
if errorlevel 1 goto swap
set /a tries+=1
if %tries% GEQ 60 goto giveup
ping -n 2 127.0.0.1 >nul
goto wait
:swap
move /Y "%NEWFILE%" "%TARGET%" >nul
if errorlevel 1 goto giveup
start "" "%TARGET%"
:giveup
del "%~f0" >nul 2>&1
"""
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(body)
    creation = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen(["cmd", "/c", script], creationflags=creation,
                     close_fds=True, cwd=tempfile.gettempdir())
    return True


class UpdateChecker(threading.Thread):
    """Periodically checks for a new release; calls on_found(info) once per version."""

    FIRST_DELAY = 45.0
    INTERVAL = 6 * 3600.0

    def __init__(self, store, on_found=None):
        super().__init__(daemon=True, name="updater")
        self.store = store
        self.on_found = on_found
        self.stop_event = threading.Event()
        self.latest = None       # info dict for an available update
        self.last_error = None
        self._announced = set()

    def run(self):
        if self.stop_event.wait(self.FIRST_DELAY):
            return
        while not self.stop_event.is_set():
            self.check_once()
            if self.stop_event.wait(self.INTERVAL):
                return

    def check_once(self):
        repo = self.store.get_config("update_repo", "") or ""
        if not repo:
            return None
        try:
            info = check(repo)
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            return None
        if not info:
            return None
        self.latest = info
        if self.on_found and info["version"] not in self._announced:
            self._announced.add(info["version"])
            try:
                self.on_found(info)
            except Exception:
                pass
        return info

    def stop(self):
        self.stop_event.set()
