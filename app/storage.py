"""Thread-safe JSON storage: usage, per-app time, pairing, chats, admins,
policy config, blocklist, PIN, and the imperative command queue."""

import hashlib
import json
import os
import secrets
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path

CODE_LIFETIME_DAYS = 30

_DEFAULT = {
    "days": {},      # "YYYY-MM-DD": {"active": s, "screen": s, "apps": {name: s}}
    "pair": None,
    "chats": {},
    "commands": [],
    "config": {
        "app_lang": "uk",
        "token": None,
        "idle_limit": 300,
        "daily_limit_min": 0,
        "work_min": 0,
        "break_min": 0,
        "warn_min": 5,          # warn this many minutes before a block
        "admins": [],
        "admin_chats": {},
        "bonus": {},
        "blocklist": [],        # website patterns: "youtube.com", "youtube.com/shorts"
        "pin": None,            # app PIN: {"salt": hex, "hash": hex} or None
        "bot_pin": None,        # bot admin PIN, same shape; None = admins by @username only
        "update_repo": "",      # GitHub "owner/repo" for auto-update ("" = off)
        "auto_update": True,    # install a found update automatically
        "watchdog": True,       # relaunch the app if it is closed/killed
    },
}


def default_dir() -> Path:
    override = os.environ.get("TIMEAPP_DIR")
    if override:
        return Path(override)
    return Path(os.environ.get("APPDATA", str(Path.home()))) / "TimeApp"


class Store:
    def __init__(self, directory=None):
        self.dir = Path(directory) if directory else default_dir()
        self.path = self.dir / "data.json"
        self.lock = threading.RLock()
        self.data = json.loads(json.dumps(_DEFAULT))
        self._load()

    @property
    def _bak(self):
        return self.path.with_suffix(".bak")

    @staticmethod
    def _read_json(path):
        try:
            text = path.read_text("utf-8")
        except OSError:
            return None
        if not text.strip():
            return None  # empty/truncated (e.g. a crash mid-write)
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _load(self):
        raw = self._read_json(self.path)
        if raw is None:
            raw = self._read_json(self._bak)  # main lost/corrupt -> recover the backup
        if raw is None:
            # Nothing parsed. If a non-empty main file exists it is corrupt: keep a
            # copy instead of silently overwriting it, then start from defaults.
            try:
                if self.path.exists() and self.path.stat().st_size > 0:
                    shutil.copy2(self.path, self.path.with_suffix(".corrupt"))
            except OSError:
                pass
            return
        for key, default in self.data.items():
            if key not in raw:
                continue
            if isinstance(default, dict) and isinstance(raw[key], dict):
                default.update(raw[key])
            else:
                self.data[key] = raw[key]

    def save(self):
        with self.lock:
            payload = json.dumps(self.data, ensure_ascii=False, indent=2)
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            # write + flush + fsync so the bytes really hit the disk before the
            # atomic rename — a power loss right after a reboot can otherwise leave
            # a zero-length file that wipes every setting.
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    pass
            os.replace(tmp, self.path)
            try:
                shutil.copy2(self.path, self._bak)  # keep a known-good backup
            except OSError:
                pass

    # -- time accounting ------------------------------------------------
    @staticmethod
    def today_key() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def add_time(self, day: str, active: float, screen: float):
        # active may be negative (grace rollback); clamp both metrics at zero.
        with self.lock:
            rec = self.data["days"].setdefault(day, {"active": 0.0, "screen": 0.0})
            rec["active"] = max(0.0, float(rec.get("active", 0.0)) + active)
            rec["screen"] = max(0.0, float(rec.get("screen", 0.0)) + screen)

    def add_app_time(self, day: str, app: str, seconds: float):
        if not app:
            return
        with self.lock:
            rec = self.data["days"].setdefault(day, {"active": 0.0, "screen": 0.0})
            apps = rec.setdefault("apps", {})
            apps[app] = float(apps.get(app, 0.0)) + seconds

    def day_stats(self, day: str = None):
        with self.lock:
            rec = self.data["days"].get(day or self.today_key()) or {}
            return float(rec.get("active", 0.0)), float(rec.get("screen", 0.0))

    def top_apps(self, day: str = None, count: int = 6):
        with self.lock:
            rec = self.data["days"].get(day or self.today_key()) or {}
            apps = rec.get("apps") or {}
            return sorted(apps.items(), key=lambda kv: kv[1], reverse=True)[:count]

    def last_days(self, count: int = 7):
        out = []
        now = datetime.now()
        with self.lock:
            for i in range(count - 1, -1, -1):
                day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                rec = self.data["days"].get(day) or {}
                out.append((day, float(rec.get("active", 0.0)), float(rec.get("screen", 0.0))))
        return out

    def reset_day(self, day: str = None):
        with self.lock:
            self.data["days"][day or self.today_key()] = {"active": 0.0, "screen": 0.0, "apps": {}}
            self.save()

    def reset_week(self):
        now = datetime.now()
        with self.lock:
            for i in range(7):
                day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                self.data["days"][day] = {"active": 0.0, "screen": 0.0, "apps": {}}
            self.save()

    # -- pairing code ---------------------------------------------------
    def get_valid_code(self):
        with self.lock:
            pair = self.data.get("pair")
            now = datetime.now()
            if isinstance(pair, dict):
                try:
                    expires = datetime.fromisoformat(pair["expires"])
                except (KeyError, TypeError, ValueError):
                    expires = now
                if expires > now and isinstance(pair.get("code"), str):
                    return pair["code"], expires
            code = f"{secrets.randbelow(900000) + 100000}"
            expires = now + timedelta(days=CODE_LIFETIME_DAYS)
            self.data["pair"] = {"code": code, "expires": expires.isoformat()}
            self.save()
            return code, expires

    def try_pair(self, chat_id, code: str) -> bool:
        with self.lock:
            valid, _ = self.get_valid_code()
            if code != valid:
                return False
            self.data["chats"].setdefault(str(chat_id), {})["paired"] = True
            self.save()
            return True

    # -- chats ----------------------------------------------------------
    def chat(self, chat_id) -> dict:
        with self.lock:
            return dict(self.data["chats"].get(str(chat_id)) or {})

    def set_chat(self, chat_id, **kwargs):
        with self.lock:
            self.data["chats"].setdefault(str(chat_id), {}).update(kwargs)
            self.save()

    def unlink(self, chat_id):
        self.set_chat(chat_id, paired=False)

    # -- admins ---------------------------------------------------------
    @staticmethod
    def _norm_user(username: str) -> str:
        return (username or "").lstrip("@").strip().lower()

    def get_admins(self):
        with self.lock:
            return list(self.data["config"].setdefault("admins", []))

    def is_admin(self, username) -> bool:
        if not username:
            return False
        return self._norm_user(username) in self.get_admins()

    def add_admin(self, username):
        name = self._norm_user(username)
        if not name:
            return False
        with self.lock:
            admins = self.data["config"].setdefault("admins", [])
            if name not in admins:
                admins.append(name)
                self.save()
            return True

    def remove_admin(self, username):
        name = self._norm_user(username)
        with self.lock:
            admins = self.data["config"].setdefault("admins", [])
            if name in admins:
                admins.remove(name)
            self.data["config"].setdefault("admin_chats", {}).pop(name, None)
            self.save()

    def set_admin_chat(self, username, chat_id):
        name = self._norm_user(username)
        if not name:
            return
        with self.lock:
            self.data["config"].setdefault("admin_chats", {})[name] = chat_id
            self.save()

    def admin_chats(self):
        with self.lock:
            return dict(self.data["config"].setdefault("admin_chats", {}))

    # -- policy commands + bonus ---------------------------------------
    def push_command(self, kind: str, value=None):
        with self.lock:
            self.data.setdefault("commands", []).append({"type": kind, "value": value})
            self.save()

    def drain_commands(self):
        with self.lock:
            cmds = self.data.get("commands") or []
            self.data["commands"] = []
            if cmds:
                self.save()
            return cmds

    def get_bonus(self, day: str) -> int:
        with self.lock:
            return int(self.data["config"].setdefault("bonus", {}).get(day, 0))

    def add_bonus(self, day: str, minutes: int):
        with self.lock:
            bonus = self.data["config"].setdefault("bonus", {})
            bonus[day] = int(bonus.get(day, 0)) + int(minutes)
            self.save()

    # -- website blocklist ---------------------------------------------
    def get_blocklist(self):
        with self.lock:
            return list(self.data["config"].setdefault("blocklist", []))

    def add_block(self, pattern: str) -> bool:
        p = (pattern or "").strip().lower()
        if not p:
            return False
        with self.lock:
            bl = self.data["config"].setdefault("blocklist", [])
            if p not in bl:
                bl.append(p)
                self.save()
            return True

    def remove_block(self, pattern: str):
        p = (pattern or "").strip().lower()
        with self.lock:
            bl = self.data["config"].setdefault("blocklist", [])
            if p in bl:
                bl.remove(p)
                self.save()

    # -- PINs (app PIN and bot admin PIN share this machinery) -----------
    def _has_pin(self, key) -> bool:
        with self.lock:
            return bool(self.data["config"].get(key))

    def _set_pin(self, key, pin: str):
        salt = secrets.token_hex(8)
        digest = hashlib.sha256((salt + str(pin)).encode("utf-8")).hexdigest()
        with self.lock:
            self.data["config"][key] = {"salt": salt, "hash": digest}
            self.save()

    def _clear_pin(self, key):
        with self.lock:
            self.data["config"][key] = None
            self.save()

    def _check_pin(self, key, pin: str, empty_ok=True) -> bool:
        with self.lock:
            rec = self.data["config"].get(key)
        if not rec:
            return empty_ok
        digest = hashlib.sha256((rec.get("salt", "") + str(pin)).encode("utf-8")).hexdigest()
        return secrets.compare_digest(digest, rec.get("hash", ""))

    # app PIN — guards opening settings and quitting
    def has_pin(self) -> bool:
        return self._has_pin("pin")

    def set_pin(self, pin: str):
        self._set_pin("pin", pin)

    def clear_pin(self):
        self._clear_pin("pin")

    def check_pin(self, pin: str) -> bool:
        return self._check_pin("pin", pin, empty_ok=True)

    # bot PIN — second factor for admins inside the bot
    def has_bot_pin(self) -> bool:
        return self._has_pin("bot_pin")

    def set_bot_pin(self, pin: str):
        self._set_pin("bot_pin", pin)
        self.revoke_all_admin_sessions()

    def clear_bot_pin(self):
        self._clear_pin("bot_pin")

    def check_bot_pin(self, pin: str) -> bool:
        # never let an empty/absent PIN authorise anything
        return self._check_pin("bot_pin", pin, empty_ok=False)

    # -- admin sessions in the bot (unlocked by the bot PIN) -------------
    def is_admin_unlocked(self, chat_id) -> bool:
        if not self.has_bot_pin():
            return True
        return bool(self.chat(chat_id).get("admin_ok"))

    def unlock_admin(self, chat_id):
        self.set_chat(chat_id, admin_ok=True)

    def revoke_all_admin_sessions(self):
        with self.lock:
            for chat in self.data["chats"].values():
                chat.pop("admin_ok", None)
            self.save()

    # -- config ---------------------------------------------------------
    def get_config(self, key, default=None):
        with self.lock:
            value = self.data["config"].get(key)
            return default if value is None else value

    def set_config(self, key, value):
        with self.lock:
            self.data["config"][key] = value
            self.save()
