"""Keeps TimeApp running, and performs the admin-approved self-uninstall.

Honest scope: a single watchdog process waits for the app to disappear and
relaunches it — defeating "close the window", "End task", a crash or a stray
kill. It does NOT defeat a determined administrator (Task Manager can end any
process and the watchdog too). Parental-control grade deterrence, not
tamper-proofing.

Storm-proofing: only ONE watchdog ever runs (named mutex), and it relaunches at
most once before exiting, so a kill can never spawn a pile of processes. An
authorised shutdown (PIN quit, update, uninstall) drops a one-shot token the
watchdog checks, so legitimate exits are not fought.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

WATCHDOG_MUTEX = "TimeApp_Watchdog_Instance"
DETACHED = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW


def _state_dir():
    from storage import default_dir
    path = default_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return str(path)


def _flag_path():
    return os.path.join(_state_dir(), "allow_exit.flag")


def allow_exit():
    try:
        with open(_flag_path(), "w", encoding="utf-8") as fh:
            fh.write("1")
    except OSError:
        pass


def clear_allow_exit():
    try:
        os.remove(_flag_path())
    except OSError:
        pass


def allow_exit_set() -> bool:
    return os.path.exists(_flag_path())


def watchdog_enabled(store_dir=None) -> bool:
    store_dir = store_dir or _state_dir()
    try:
        with open(os.path.join(store_dir, "data.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return bool(data.get("config", {}).get("watchdog", True))
    except Exception:
        return True  # unknown -> keep protecting


def _spawn_watchdog():
    if not getattr(sys, "frozen", False):
        return None  # dev runs are not babysat
    try:
        return subprocess.Popen([sys.executable, "--watch", str(os.getpid())],
                                creationflags=DETACHED, close_fds=True)
    except OSError:
        return None


def run_watchdog(parent_pid):
    """Watchdog entry point (`TimeApp.exe --watch <pid>`)."""
    import winutil
    if not winutil.acquire_single_instance(WATCHDOG_MUTEX):
        return  # a watchdog is already running
    exe = sys.executable
    store_dir = _state_dir()
    while True:
        time.sleep(3)
        if allow_exit_set():
            return
        if not watchdog_enabled(store_dir):
            return
        if not winutil.pid_alive(parent_pid):
            if not allow_exit_set():
                try:
                    subprocess.Popen([exe], creationflags=DETACHED, close_fds=True)
                except OSError:
                    pass
            return  # one-shot: the relaunched app starts its own watchdog


def build_uninstall_script(exe, data_dir, pid, remove_data=True) -> str:
    lines = [
        "@echo off",
        f'set "EXE={exe}"',
        f'set "DATA={data_dir}"',
        ":wait",
        f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul',
        "if errorlevel 1 goto gone",
        "ping -n 2 127.0.0.1 >nul",
        "goto wait",
        ":gone",
        "ping -n 3 127.0.0.1 >nul",
    ]
    from winutil import APP_NAME, RUN_KEY
    lines.append(f'reg delete "HKCU\\{RUN_KEY}" /v {APP_NAME} /f >nul 2>&1')
    lines.append('if exist "%EXE%" del /F /Q "%EXE%" >nul 2>&1')
    if remove_data:
        lines.append('if exist "%DATA%" rmdir /S /Q "%DATA%" >nul 2>&1')
    lines.append('del "%~f0" >nul 2>&1')
    return "\n".join(lines) + "\n"


def uninstall(remove_data=True) -> bool:
    """Authorise exit, then run a detached script that deletes autostart/exe/data."""
    allow_exit()
    exe = sys.executable if getattr(sys, "frozen", False) else ""
    script = os.path.join(tempfile.gettempdir(), "timeapp_uninstall.bat")
    body = build_uninstall_script(exe, _state_dir(), os.getpid(), remove_data)
    try:
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(body)
        subprocess.Popen(["cmd", "/c", script], creationflags=DETACHED,
                         close_fds=True, cwd=tempfile.gettempdir())
        return True
    except OSError:
        return False


class Guard:
    """Owns the watchdog child from the main process side."""

    def __init__(self, store):
        self.store = store
        self.proc = None

    def _enabled(self) -> bool:
        return getattr(sys, "frozen", False) and bool(self.store.get_config("watchdog", True))

    def start(self):
        clear_allow_exit()
        self.ensure()

    def ensure(self):
        if not self._enabled():
            return
        if self.proc is None or self.proc.poll() is not None:
            self.proc = _spawn_watchdog()

    def set_enabled(self, on: bool):
        self.store.set_config("watchdog", bool(on))
        if on:
            clear_allow_exit()
            self.ensure()
        else:
            allow_exit()  # disarm the running watchdog (it exits within ~3s)

    def authorize_exit(self):
        allow_exit()
