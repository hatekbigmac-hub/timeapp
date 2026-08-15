"""Read the current URL from the foreground browser via UI Automation.

Best-effort and fully defensive: if comtypes / UI Automation is unavailable or
anything fails, every call returns None and website blocking simply stays off.
Works for Chromium browsers (Chrome, Edge, Brave, Opera, Vivaldi) and Firefox —
their address bar is an Edit control whose value is the full URL including path.
"""

import ctypes
from ctypes import wintypes

import winutil

BROWSERS = ("chrome", "msedge", "brave", "firefox", "opera", "vivaldi", "chromium")
TreeScope_Descendants = 4

_uia = None
_edit_cond = None
_gen = None
_available = None  # None = not tried yet, True/False after first attempt


def _init():
    global _uia, _edit_cond, _gen, _available
    if _available is not None:
        return _available
    try:
        import comtypes
        import comtypes.client
        comtypes.client.gen_dir = None  # generate wrappers in memory (frozen-safe)
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as gen
        _gen = gen
        _uia = comtypes.client.CreateObject(gen.CUIAutomation, interface=gen.IUIAutomation)
        _edit_cond = _uia.CreatePropertyCondition(
            gen.UIA_ControlTypePropertyId, gen.UIA_EditControlTypeId)
        _available = True
    except Exception:
        _available = False
    return _available


def _looks_like_url(value: str) -> bool:
    if not value or " " in value.strip():
        return False
    v = value.strip().lower()
    return "." in v or v.startswith("http") or "/" in v


def foreground_browser_url():
    """Return (hwnd, url, editing) for the foreground browser, else None.

    `editing` is True while the address bar holds keyboard focus — i.e. the user
    is typing in it. The value there is a half-typed string, not a page that was
    actually opened, so callers must not act on it.
    """
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    name, _title = winutil.get_foreground_app()
    if not any(b in name for b in BROWSERS) or "webview" in name:
        return None
    if not _init():
        return None
    try:
        element = _uia.ElementFromHandle(hwnd)
        edit = element.FindFirst(TreeScope_Descendants, _edit_cond)
        if not edit:
            return None
        pattern = edit.GetCurrentPattern(_gen.UIA_ValuePatternId)
        if not pattern:
            return None
        value = pattern.QueryInterface(_gen.IUIAutomationValuePattern).CurrentValue
        try:
            editing = bool(edit.CurrentHasKeyboardFocus)
        except Exception:
            editing = True  # unknown -> assume typing, never act on a guess
        if _looks_like_url(value):
            return hwnd, value, editing
    except Exception:
        return None
    return None
