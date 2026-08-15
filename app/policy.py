"""Screen-time policy engine: daily limit + work/break cycle + manual breaks.

Pure state machine driven by tick(). It reads settings/usage from the Store,
toggles a shared blocking Event (read by the tracker so it stops counting), and
returns an action dict the GUI uses to show/hide the fullscreen break overlay.

Clocks are injectable so the whole thing is unit-testable without real time:
  clock()    -> monotonic seconds (break countdowns)
  today_fn() -> "YYYY-MM-DD" (day rollover / bonus lookup)
"""

import time


class Policy:
    def __init__(self, store, blocking_event, clock=time.monotonic,
                 today_fn=None, notifier=None):
        self.store = store
        self.blocking = blocking_event
        self.clock = clock
        self.today_fn = today_fn or store.today_key
        self.notifier = notifier
        self.mode = "work"          # "work" | "break"
        self.reason = None          # "cycle" | "manual" | "limit"
        self.break_end = None       # monotonic deadline, or None for open-ended (limit)
        self.baseline_active = 0.0  # active-seconds mark at the start of this work streak
        self.current_day = self.today_fn()
        self._warned = False        # emitted the "block approaching" warning already?

    def set_notifier(self, notifier):
        self.notifier = notifier

    def _notify(self, key):
        if self.notifier:
            try:
                self.notifier(key)
            except Exception:
                pass

    def _limit_seconds(self, day):
        limit_min = int(self.store.get_config("daily_limit_min", 0) or 0)
        if limit_min <= 0:
            return None
        bonus_min = int(self.store.get_bonus(day))
        return (limit_min + bonus_min) * 60

    def _over_limit(self, day, active):
        limit = self._limit_seconds(day)
        return limit is not None and active >= limit

    def _start_break(self, now, duration, reason):
        self.mode = "break"
        self.reason = reason
        self.break_end = now + duration
        self.blocking.set()
        self._notify("notify_break")

    def _start_limit_block(self):
        self.mode = "break"
        self.reason = "limit"
        self.break_end = None
        self.blocking.set()
        self._notify("notify_limit")

    def _end_break(self, active_today):
        was_break = self.mode == "break"
        self.mode = "work"
        self.reason = None
        self.break_end = None
        self.baseline_active = active_today
        self._warned = False
        self.blocking.clear()
        if was_break:
            self._notify("notify_break_over")

    def _warning(self, day, active):
        """Return {'kind','seconds'} once when a block is < warn_min away, else None."""
        warn_sec = int(self.store.get_config("warn_min", 5) or 0) * 60
        if warn_sec <= 0:
            return None
        approaching = None
        limit = self._limit_seconds(day)
        if limit is not None:
            remaining = limit - active
            if 0 < remaining <= warn_sec:
                approaching = ("limit", remaining)
        if approaching is None:
            work_min = int(self.store.get_config("work_min", 0) or 0)
            break_min = int(self.store.get_config("break_min", 0) or 0)
            if work_min > 0 and break_min > 0:
                remaining = work_min * 60 - (active - self.baseline_active)
                if 0 < remaining <= warn_sec:
                    approaching = ("cycle", remaining)
        if approaching is None:
            self._warned = False
            return None
        if self._warned:
            return None
        self._warned = True
        return {"kind": approaching[0], "seconds": approaching[1]}

    def tick(self):
        now = self.clock()
        day = self.today_fn()
        if day != self.current_day:
            self.current_day = day
            self.baseline_active = 0.0
            if self.mode == "break" and self.reason == "limit":
                self._end_break(0.0)

        active, _screen = self.store.day_stats(day)

        # imperative commands from admins (via the bot thread)
        for cmd in self.store.drain_commands():
            kind = cmd.get("type")
            if kind == "unlock" and self.mode == "break":
                self._end_break(active)
            elif kind == "breaknow":
                minutes = cmd.get("value") or self.store.get_config("break_min", 5) or 5
                self._start_break(now, float(minutes) * 60, "manual")

        if self.mode == "break":
            if self.reason == "limit":
                if not self._over_limit(day, active):
                    self._end_break(active)  # bonus granted -> back under the limit
                    return {"block": False}
                return {"block": True, "reason": "limit", "remaining": None}
            remaining = (self.break_end - now) if self.break_end is not None else 0
            if remaining <= 0:
                self._end_break(active)
                return {"block": False}
            return {"block": True, "reason": self.reason, "remaining": remaining}

        # working
        if self._over_limit(day, active):
            self._start_limit_block()
            return {"block": True, "reason": "limit", "remaining": None}

        work_min = int(self.store.get_config("work_min", 0) or 0)
        break_min = int(self.store.get_config("break_min", 0) or 0)
        if work_min > 0 and break_min > 0:
            streak = active - self.baseline_active
            if streak >= work_min * 60:
                self._start_break(now, break_min * 60, "cycle")
                return {"block": True, "reason": "cycle", "remaining": break_min * 60}

        return {"block": False, "warn": self._warning(day, active)}
