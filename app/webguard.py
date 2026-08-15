"""Enforces the website blocklist.

Only reacts to a page that was actually OPENED. While the address bar has
keyboard focus the user is still typing, and the half-typed text must be
ignored — otherwise typing "youtube.com/shorts" would close the tab mid-word.
A blocked address must also stay put for CONFIRM_TICKS consecutive samples, so
transient values during navigation never trigger a close.
"""

import time

import urlwatch
import webrules
import winutil


class WebGuard:
    COOLDOWN = 3.0      # seconds between actions, so one navigation closes one tab
    CONFIRM_TICKS = 2   # the same blocked URL must be seen this many times in a row

    def __init__(self, store, clock=time.monotonic):
        self.store = store
        self.clock = clock
        self._last_action = None
        self._pending = None   # (normalized_url, seen_count)

    def _reset(self):
        self._pending = None

    def tick(self):
        """Return the matched pattern if a blocked tab was just closed, else None."""
        patterns = self.store.get_blocklist()
        if not patterns:
            self._reset()
            return None
        found = urlwatch.foreground_browser_url()
        if not found:
            self._reset()
            return None
        _hwnd, url, editing = found
        if editing:
            self._reset()   # user is typing in the address bar — not an open page
            return None
        matched = webrules.match(url, patterns)
        if not matched:
            self._reset()
            return None

        norm = webrules.normalize_url(url)
        if self._pending and self._pending[0] == norm:
            count = self._pending[1] + 1
        else:
            count = 1
        self._pending = (norm, count)
        if count < self.CONFIRM_TICKS:
            return None

        now = self.clock()
        if self._last_action is not None and now - self._last_action < self.COOLDOWN:
            return None
        self._last_action = now
        self._reset()
        try:
            winutil.send_ctrl_w()
        except Exception:
            pass
        return matched
