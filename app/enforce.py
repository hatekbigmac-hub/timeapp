"""Global low-level keyboard + mouse block via Win32 hooks.

A dedicated thread installs WH_KEYBOARD_LL / WH_MOUSE_LL hooks and runs a
message loop (required for low-level hooks to stay alive). While `block()` is
active every keyboard and mouse event is swallowed. Ctrl+Alt+Del (the Secure
Attention Sequence) is handled by Windows itself and cannot be hooked, so the
user always keeps that OS-level escape hatch.
"""

import ctypes
import threading
from ctypes import wintypes

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
HC_ACTION = 0
WM_QUIT = 0x0012

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.restype = wintypes.HANDLE
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
user32.GetMessageW.restype = ctypes.c_int
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


class InputBlocker:
    """Install once with start(); toggle with block()/unblock(); remove with stop()."""

    def __init__(self):
        self._active = threading.Event()
        self._run = False
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self._kb_hook = None
        self._mouse_hook = None
        self._kb_cb = None
        self._mouse_cb = None

    def _proc(self, n_code, w_param, l_param):
        if n_code == HC_ACTION and self._active.is_set():
            return 1  # swallow the event
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    def _loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        hmod = kernel32.GetModuleHandleW(None)
        # keep the CFUNCTYPE objects alive for the hook lifetime
        self._kb_cb = HOOKPROC(self._proc)
        self._mouse_cb = HOOKPROC(self._proc)
        self._kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_cb, hmod, 0)
        self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_cb, hmod, 0)
        self._ready.set()
        msg = wintypes.MSG()
        while self._run:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):  # WM_QUIT or error
                break
        if self._kb_hook:
            user32.UnhookWindowsHookEx(self._kb_hook)
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
        self._kb_hook = self._mouse_hook = None
        self._ready.clear()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._run = True
        self._ready.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="input-block")
        self._thread.start()
        self._ready.wait(2.0)

    def installed(self) -> bool:
        return bool(self._kb_hook) and bool(self._mouse_hook)

    def block(self):
        self._active.set()

    def unblock(self):
        self._active.clear()

    def is_blocking(self) -> bool:
        return self._active.is_set()

    def stop(self):
        self._run = False
        self._active.clear()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
