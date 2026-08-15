"""Background thread that accumulates per-day active/screen seconds.

Active time is credited while the session is unlocked and input idle time is
below `idle_limit` (a grace window so short reading pauses still count). The
moment idle actually crosses the limit — i.e. you really stepped away — the
grace seconds that were provisionally credited during THIS absence are removed
again, so walking away never inflates active time. Screen time keeps counting
the whole on-and-unlocked period regardless.
"""

import threading
import time

import winutil


class Tracker(threading.Thread):
    TICK = 1.0          # seconds between samples
    SAVE_EVERY = 15.0    # flush to disk this often
    GAP_LIMIT = 5.0      # a bigger gap means sleep/hibernate -> don't credit it
    ACTIVE_RESET = 2.0   # idle below this = actively present -> no pending grace

    def __init__(self, store, blocking_event=None):
        super().__init__(daemon=True, name="tracker")
        self.store = store
        self.blocking_event = blocking_event
        self.stop_event = threading.Event()
        self.idle_limit = float(store.get_config("idle_limit", 300) or 300)
        self._grace = 0.0      # active secs provisionally credited during the current absence
        self._rolled = False   # already rolled the grace back for this absence?

    def _reset_grace(self):
        self._grace = 0.0
        self._rolled = False

    @staticmethod
    def _app_name():
        try:
            name, _title = winutil.get_foreground_app()
            return name
        except Exception:
            return ""

    def account(self, delta, locked, idle, day, app=None):
        """Apply one sample. Pure w.r.t. time/OS so it is unit-testable."""
        if locked:
            self._reset_grace()
            return
        if idle < self.ACTIVE_RESET:
            self._reset_grace()          # user is present right now
        if idle < self.idle_limit:
            self.store.add_time(day, delta, delta)   # active + screen
            if app:
                self.store.add_app_time(day, app, delta)
            if idle >= self.ACTIVE_RESET:
                self._grace += delta      # at-risk if this turns into an absence
        else:
            self.store.add_time(day, 0.0, delta)      # screen only
            if not self._rolled:
                self.store.add_time(day, -self._grace, 0.0)  # remove the grace from active
                self._rolled = True
                self._grace = 0.0

    def run(self):
        last = time.monotonic()
        last_save = last
        while not self.stop_event.wait(self.TICK):
            now = time.monotonic()
            delta = now - last
            last = now
            if delta <= 0 or delta > self.GAP_LIMIT:
                self._reset_grace()
                continue
            if self.blocking_event is not None and self.blocking_event.is_set():
                self._reset_grace()
                continue
            try:
                locked = winutil.is_locked()
                idle = winutil.get_idle_seconds()
                app = "" if locked else self._app_name()
            except Exception:
                continue
            self.account(delta, locked, idle, self.store.today_key(), app)
            if now - last_save >= self.SAVE_EVERY:
                last_save = now
                try:
                    self.store.save()
                except OSError:
                    pass
        try:
            self.store.save()
        except OSError:
            pass

    def stop(self):
        self.stop_event.set()
