"""Screen-time policy engine: daily limit + work/break cycle + manual breaks.

State machine driven by tick(). It reads settings/usage from the Store, toggles
a shared blocking Event (read by the tracker so it stops counting), and returns
an action dict the GUI uses to show/hide the fullscreen break overlay.

Persistence: the runtime state (mode, break deadline, work-streak baseline) is
saved to the Store and restored on start, using a WALL clock so it survives a
reboot. Without this, a restart would drop an in-progress break and reset the
time-until-break to zero. Break deadlines are absolute wall timestamps, so a
break that elapsed while the PC was off is correctly treated as finished, and a
break interrupted by a reboot resumes with the right time left.

Clocks are injectable for testing:
  clock()    -> wall-clock seconds (time.time); break deadlines are stored in it
  today_fn() -> "YYYY-MM-DD" (day rollover / bonus lookup)
"""

import time


class Policy:
    def __init__(self, store, blocking_event, clock=time.time,
                 today_fn=None, notifier=None):
        self.store = store
        self.blocking = blocking_event
        self.clock = clock
        self.today_fn = today_fn or store.today_key
        self.notifier = notifier
        self.current_day = self.today_fn()
        self._warned = False
        self.mode = "work"          # "work" | "break"
        self.reason = None          # "cycle" | "manual" | "limit"
        self.break_end = None       # absolute wall deadline, or None (open-ended limit)
        self.baseline_active = 0.0  # active-seconds mark at the start of this work streak
        self._restore()

    # -- persistence ----------------------------------------------------
    def _restore(self):
        st = self.store.get_config("policy_state", {}) or {}
        mode = st.get("mode")
        self.mode = mode if mode in ("work", "break") else "work"
        self.reason = st.get("reason")
        end = st.get("break_end")
        self.break_end = float(end) if isinstance(end, (int, float)) else None
        try:
            self.baseline_active = float(st.get("baseline_active", 0.0) or 0.0)
        except (TypeError, ValueError):
            self.baseline_active = 0.0

        now = self.clock()
        active, _screen = self.store.day_stats(self.current_day)
        if st.get("baseline_day") != self.current_day:
            self.baseline_active = 0.0  # a new day resets the work streak
            if self.mode == "break" and self.reason == "limit":
                self.mode, self.reason, self.break_end = "work", None, None

        if self.mode == "break":
            if self.reason == "limit":
                self.blocking.set()   # tick() re-checks the limit and clears if under
            elif self.break_end is not None and (self.break_end - now) > 0:
                self.blocking.set()   # timed break still has time left -> resume it
            else:
                self._end_break(active, notify=False)  # elapsed while the PC was off
        else:
            self.blocking.clear()
        self._save_state()

    def _save_state(self):
        self.store.set_config("policy_state", {
            "mode": self.mode,
            "reason": self.reason,
            "break_end": self.break_end,
            "baseline_active": self.baseline_active,
            "baseline_day": self.current_day,
        })

    # -- helpers --------------------------------------------------------
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
        return (limit_min + int(self.store.get_bonus(day))) * 60

    def _over_limit(self, day, active):
        limit = self._limit_seconds(day)
        return limit is not None and active >= limit

    def _start_break(self, now, duration, reason):
        self.mode = "break"
        self.reason = reason
        self.break_end = now + duration
        self.blocking.set()
        self._save_state()
        self._notify("notify_break")

    def _start_limit_block(self):
        self.mode = "break"
        self.reason = "limit"
        self.break_end = None
        self.blocking.set()
        self._save_state()
        self._notify("notify_limit")

    def _end_break(self, active_today, notify=True):
        was_break = self.mode == "break"
        self.mode = "work"
        self.reason = None
        self.break_end = None
        self.baseline_active = active_today
        self._warned = False
        self.blocking.clear()
        self._save_state()
        if was_break and notify:
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

    # -- main tick ------------------------------------------------------
    def tick(self):
        now = self.clock()
        day = self.today_fn()
        if day != self.current_day:
            self.current_day = day
            self.baseline_active = 0.0
            if self.mode == "break" and self.reason == "limit":
                self._end_break(0.0)
            else:
                self._save_state()

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
