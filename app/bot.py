"""Telegram bot (long polling) running inside the app process.

Two roles:
  * paired users (owner) — see stats;
  * admins (recognised by @username, set in the app) — also control the PC:
    daily limit, work/break cycle, force break, unlock, add time.
"""

import datetime
import json
import queue
import re
import threading

import requests

import net
import version
from i18n import dow, fmt_date, fmt_duration, fmt_minutes, t

CODE_RE = re.compile(r"^\d{6}$")


class BotApiError(Exception):
    def __init__(self, code, description=""):
        super().__init__(f"{code}: {description}")
        self.code = code
        self.description = description


class TelegramBot(threading.Thread):
    POLL_TIMEOUT = 50

    def __init__(self, store, token, card_renderer=None, update_hook=None,
                 uninstall_hook=None):
        super().__init__(daemon=True, name="telegram-bot")
        self.store = store
        self.token = token
        self.card_renderer = card_renderer
        self.update_hook = update_hook       # hook(chat_id, lang) for /update
        self.uninstall_hook = uninstall_hook  # hook() -> removes the app, quits
        self.pending_uninstall = set()        # chats that pressed "confirm delete"
        self.stop_event = threading.Event()
        self.session = requests.Session()          # used by the polling thread only
        self.notify_session = requests.Session()    # used by the notify thread only
        self.transport = net.Transport()            # multi-strategy connectivity
        self.notify_q = queue.Queue()
        self.username = None
        self.status = "starting"
        self.last_error = ""
        self.offset = 0

    # -- low-level API ---------------------------------------------------
    CONNECT_TIMEOUT = 8  # fail a blocked route fast so fallbacks get their turn

    def api(self, method, params=None, files=None, http_timeout=20, session=None):
        session = session or self.session
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        params = params or {}
        timeout = (self.CONNECT_TIMEOUT, http_timeout)
        if files:
            data = {key: (json.dumps(value) if isinstance(value, (dict, list)) else value)
                    for key, value in params.items()}
            resp = self.transport.post(session, url, timeout, data=data, files=files)
        else:
            resp = self.transport.post(session, url, timeout, json=params)
        try:
            payload = resp.json()
        except ValueError:
            raise BotApiError(resp.status_code, "bad response")
        if not payload.get("ok"):
            raise BotApiError(payload.get("error_code", resp.status_code),
                              payload.get("description", ""))
        return payload.get("result")

    def send(self, chat_id, text, kb=None, session=None):
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if kb:
            params["reply_markup"] = {"inline_keyboard": kb}
        try:
            self.api("sendMessage", params, session=session)
        except (BotApiError, requests.RequestException):
            pass

    # -- notifications (called from the policy engine, any thread) -------
    def notify(self, key, **kwargs):
        self.notify_q.put((key, kwargs))

    def _notify_loop(self):
        while not self.stop_event.is_set():
            try:
                key, kwargs = self.notify_q.get(timeout=1.0)
            except queue.Empty:
                continue
            for _username, chat_id in self.store.admin_chats().items():
                lang = self.store.chat(chat_id).get("lang") or "uk"
                self.send(chat_id, t(lang, key, **kwargs), session=self.notify_session)

    # -- keyboards -------------------------------------------------------
    @staticmethod
    def lang_kb():
        return [[{"text": "\U0001F1EC\U0001F1E7 English", "callback_data": "lang:en"},
                 {"text": "\U0001F1FA\U0001F1E6 Українська", "callback_data": "lang:uk"}]]

    @staticmethod
    def menu_kb(lang, is_admin=False):
        rows = [[{"text": t(lang, "menu_today"), "callback_data": "today"},
                 {"text": t(lang, "menu_week"), "callback_data": "week"}],
                [{"text": t(lang, "menu_apps"), "callback_data": "apps"},
                 {"text": t(lang, "menu_status"), "callback_data": "status"}]]
        if is_admin:
            rows.append([{"text": t(lang, "menu_break"), "callback_data": "breaknow"},
                         {"text": t(lang, "menu_unlock"), "callback_data": "unlock"}])
            rows.append([{"text": t(lang, "menu_addtime"), "callback_data": "addtime:15"},
                         {"text": t(lang, "menu_resetday"), "callback_data": "resetday"}])
            rows.append([{"text": t(lang, "menu_resetweek"), "callback_data": "resetweek"}])
        rows.append([{"text": t(lang, "menu_lang"), "callback_data": "langmenu"}])
        return rows

    # -- main loop -------------------------------------------------------
    def run(self):
        if not self.token:
            self.status = "no_token"
            return  # a fresh bot is started by restart_bot once a token is entered
        while not self.stop_event.is_set():
            try:
                me = self.api("getMe")
                self.username = me.get("username")
                self.status = "ok"
                self.last_error = ""
                break
            except BotApiError as exc:
                if exc.code == 401:
                    self.status = "unauthorized"
                    return
                self.status = "network"
                self.last_error = str(exc)[:200]
            except Exception as exc:
                self.status = "network"
                self.last_error = str(exc)[:200]
            self.stop_event.wait(5)

        threading.Thread(target=self._notify_loop, daemon=True, name="tg-notify").start()

        while not self.stop_event.is_set():
            try:
                updates = self.api("getUpdates", {
                    "timeout": self.POLL_TIMEOUT,
                    "offset": self.offset,
                    "allowed_updates": ["message", "callback_query"],
                }, http_timeout=self.POLL_TIMEOUT + 10)
                self.status = "ok"
                self.last_error = ""
            except BotApiError as exc:
                self.status = {409: "conflict", 401: "unauthorized"}.get(exc.code, "network")
                if exc.code == 401:
                    return
                self.last_error = str(exc)[:200]
                self.stop_event.wait(5)
                continue
            except requests.RequestException as exc:
                self.status = "network"
                self.last_error = str(exc)[:200]
                self.stop_event.wait(5)
                continue
            for update in updates or []:
                self.offset = max(self.offset, update.get("update_id", 0) + 1)
                try:
                    self.dispatch(update)
                except Exception:
                    pass

    def stop(self):
        self.stop_event.set()

    # -- update handling -------------------------------------------------
    def dispatch(self, update):
        if "message" in update:
            self.on_message(update["message"])
        elif "callback_query" in update:
            self.on_callback(update["callback_query"])

    def _identify(self, sender, chat_id):
        """Return (lang, paired, is_admin).

        Being listed as an admin is necessary but, when a bot PIN is set, not
        sufficient: the chat must also have been unlocked with that PIN. The
        username itself is stored on the message by Telegram and cannot be
        forged by another user, but the PIN adds a second factor so a stolen or
        renamed account alone does not hand over control of the PC.
        """
        username = (sender or {}).get("username")
        info = self.store.chat(chat_id)
        lang = info.get("lang") or "uk"
        is_admin_user = self.store.is_admin(username)
        is_admin = is_admin_user and self.store.is_admin_unlocked(chat_id)
        if is_admin:
            self.store.set_admin_chat(username, chat_id)
            if not info.get("paired"):
                self.store.set_chat(chat_id, paired=True)
        paired = bool(self.store.chat(chat_id).get("paired"))
        return lang, paired, is_admin

    def _admin_listed(self, sender) -> bool:
        return self.store.is_admin((sender or {}).get("username"))

    def _locked_prompt(self, sender, lang) -> str:
        """What to ask an unauthorized chat for: the bot PIN, or the pairing code."""
        if self._admin_listed(sender) and self.store.has_bot_pin():
            return t(lang, "enter_bot_pin")
        return t(lang, "enter_code")

    def on_message(self, msg):
        chat_id = (msg.get("chat") or {}).get("id")
        if chat_id is None:
            return
        text = (msg.get("text") or "").strip()
        lang, paired, is_admin = self._identify(msg.get("from"), chat_id)
        authorized = paired or is_admin
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        args = text.split()[1:]

        if cmd == "/start":
            if self.store.chat(chat_id).get("lang"):
                self.send(chat_id, t(lang, "welcome"))
                if authorized and is_admin:
                    self.send(chat_id, t(lang, "hint"), kb=self.menu_kb(lang, True))
                elif self._admin_listed(msg.get("from")) and self.store.has_bot_pin():
                    self.send(chat_id, t(lang, "enter_bot_pin"))
                elif authorized:
                    self.send(chat_id, t(lang, "hint"), kb=self.menu_kb(lang, False))
                else:
                    self.send(chat_id, t(lang, "enter_code"))
            else:
                greeting = t("uk", "welcome") + "\n\n" + t("en", "welcome") + "\n\n" + t("uk", "choose_lang")
                self.send(chat_id, greeting, kb=self.lang_kb())
            return
        if cmd in ("/lang", "/language"):
            self.send(chat_id, t(lang, "choose_lang"), kb=self.lang_kb())
            return
        if cmd == "/unlink":
            self.store.unlink(chat_id)
            self.send(chat_id, t(lang, "unlinked"))
            return
        if cmd == "/help":
            self.send(chat_id, t(lang, "help_admin") if is_admin else t(lang, "hint"),
                      kb=self.menu_kb(lang, is_admin) if authorized else None)
            return
        if cmd == "/today":
            self._guard(chat_id, lang, authorized, is_admin, self.send_today)
            return
        if cmd == "/week":
            self._guard(chat_id, lang, authorized, is_admin, self.send_week)
            return
        if cmd == "/status":
            self._guard(chat_id, lang, authorized, is_admin, self.send_status)
            return
        if cmd == "/apps":
            self._guard(chat_id, lang, authorized, is_admin, self.send_apps)
            return

        # admin commands
        if cmd in ("/setlimit", "/setcycle", "/addtime", "/breaknow", "/unlock",
                   "/resetday", "/resetweek", "/block", "/unblock", "/blocklist",
                   "/setpin", "/clearpin", "/setbotpin", "/clearbotpin",
                   "/update", "/version", "/uninstall"):
            if not is_admin:
                self.send(chat_id, self._locked_prompt(msg.get("from"), lang)
                          if self._admin_listed(msg.get("from")) else t(lang, "admin_only"))
                return
            self.admin_command(chat_id, lang, cmd, args)
            return

        digits = text.replace(" ", "")

        # a pending uninstall is waiting for its PIN confirmation
        if chat_id in self.pending_uninstall and is_admin and digits.isdigit():
            self.uninstall_command(chat_id, lang, [digits])
            return

        if digits.isdigit() and 4 <= len(digits) <= 8:
            # a 6-digit pairing code, or the bot PIN that unlocks admin rights
            if CODE_RE.match(digits) and self.store.try_pair(chat_id, digits):
                self.send(chat_id, t(lang, "paired"), kb=self.menu_kb(lang, is_admin))
                return
            if (not is_admin and self._admin_listed(msg.get("from"))
                    and self.store.has_bot_pin() and self.store.check_bot_pin(digits)):
                self.store.unlock_admin(chat_id)
                self.store.set_admin_chat((msg.get("from") or {}).get("username"), chat_id)
                self.store.set_chat(chat_id, paired=True)
                self.send(chat_id, t(lang, "admin_unlocked"), kb=self.menu_kb(lang, True))
                return
            self.send(chat_id, t(lang, "wrong_code"))
            return

        if authorized:
            self.send(chat_id, t(lang, "hint"), kb=self.menu_kb(lang, is_admin))
        else:
            self.send(chat_id, self._locked_prompt(msg.get("from"), lang))

    def on_callback(self, cq):
        try:
            self.api("answerCallbackQuery", {"callback_query_id": cq.get("id")})
        except (BotApiError, requests.RequestException):
            pass
        chat_id = ((cq.get("message") or {}).get("chat") or {}).get("id")
        if chat_id is None:
            return
        data = cq.get("data") or ""
        lang, paired, is_admin = self._identify(cq.get("from"), chat_id)
        authorized = paired or is_admin

        if data.startswith("lang:"):
            lang = data[5:] if data[5:] in ("en", "uk") else "uk"
            self.store.set_chat(chat_id, lang=lang)
            self.send(chat_id, t(lang, "lang_set"))
            if authorized:
                self.send(chat_id, t(lang, "hint"), kb=self.menu_kb(lang, is_admin))
            else:
                self.send(chat_id, t(lang, "enter_code"))
        elif data == "langmenu":
            self.send(chat_id, t(lang, "choose_lang"), kb=self.lang_kb())
        elif data == "today":
            self._guard(chat_id, lang, authorized, is_admin, self.send_today)
        elif data == "week":
            self._guard(chat_id, lang, authorized, is_admin, self.send_week)
        elif data == "status":
            self._guard(chat_id, lang, authorized, is_admin, self.send_status)
        elif data == "apps":
            self._guard(chat_id, lang, authorized, is_admin, self.send_apps)
        elif data == "uninstall_yes":
            if not is_admin:
                self.send(chat_id, t(lang, "admin_only"))
                return
            self.pending_uninstall.add(chat_id)
            if self.store.has_bot_pin() or self.store.has_pin():
                self.send(chat_id, t(lang, "uninstall_need_pin"))
            else:
                self.uninstall_command(chat_id, lang, [])
        elif data in ("breaknow", "unlock", "resetday", "resetweek") or data.startswith("addtime:"):
            if not is_admin:
                self.send(chat_id, t(lang, "admin_only"))
                return
            if data == "breaknow":
                self.admin_command(chat_id, lang, "/breaknow", [])
            elif data == "unlock":
                self.admin_command(chat_id, lang, "/unlock", [])
            elif data == "resetday":
                self.admin_command(chat_id, lang, "/resetday", [])
            elif data == "resetweek":
                self.admin_command(chat_id, lang, "/resetweek", [])
            else:
                self.admin_command(chat_id, lang, "/addtime", [data.split(":", 1)[1]])

    def _guard(self, chat_id, lang, authorized, is_admin, action):
        if authorized:
            action(chat_id, lang, is_admin)
        else:
            self.send(chat_id, t(lang, "enter_code"))

    # -- admin actions ---------------------------------------------------
    def admin_command(self, chat_id, lang, cmd, args):
        def as_int(value):
            try:
                return max(0, int(value))
            except (TypeError, ValueError):
                return None

        if cmd == "/setlimit":
            value = as_int(args[0]) if args else None
            if value is None:
                self.send(chat_id, t(lang, "cmd_bad_number", example="/setlimit 120"))
                return
            self.store.set_config("daily_limit_min", value)
            if value == 0:
                self.send(chat_id, t(lang, "cmd_limit_off"))
            else:
                self.send(chat_id, t(lang, "cmd_limit_set", value=fmt_minutes(value, lang)))
        elif cmd == "/setcycle":
            work = as_int(args[0]) if len(args) >= 1 else None
            brk = as_int(args[1]) if len(args) >= 2 else None
            if work is None or brk is None:
                self.send(chat_id, t(lang, "cmd_bad_number", example="/setcycle 30 30"))
                return
            self.store.set_config("work_min", work)
            self.store.set_config("break_min", brk)
            if work == 0 or brk == 0:
                self.send(chat_id, t(lang, "cmd_cycle_off"))
            else:
                self.send(chat_id, t(lang, "cmd_cycle_set",
                                     work=fmt_minutes(work, lang), brk=fmt_minutes(brk, lang)))
        elif cmd == "/addtime":
            value = as_int(args[0]) if args else None
            if value is None or value == 0:
                self.send(chat_id, t(lang, "cmd_bad_number", example="/addtime 15"))
                return
            self.store.add_bonus(self.store.today_key(), value)
            self.send(chat_id, t(lang, "cmd_bonus_added", value=fmt_minutes(value, lang)))
        elif cmd == "/breaknow":
            value = as_int(args[0]) if args else None
            if value is None or value == 0:
                value = int(self.store.get_config("break_min", 0) or 0) or 5
            self.store.push_command("breaknow", value)
            self.send(chat_id, t(lang, "cmd_break_started", value=fmt_minutes(value, lang)))
        elif cmd == "/unlock":
            self.store.push_command("unlock")
            self.send(chat_id, t(lang, "cmd_unlocked"))
        elif cmd == "/resetday":
            self.store.reset_day()
            self.send(chat_id, t(lang, "cmd_reset_day"))
        elif cmd == "/resetweek":
            self.store.reset_week()
            self.send(chat_id, t(lang, "cmd_reset_week"))
        elif cmd == "/block":
            pattern = args[0].strip().lower() if args else ""
            if not pattern:
                self.send(chat_id, t(lang, "cmd_block_bad", example="/block youtube.com/shorts"))
                return
            self.store.add_block(pattern)
            self.send(chat_id, t(lang, "cmd_block_added", value=pattern))
        elif cmd == "/unblock":
            pattern = args[0].strip().lower() if args else ""
            if not pattern:
                self.send(chat_id, t(lang, "cmd_block_bad", example="/unblock youtube.com/shorts"))
                return
            self.store.remove_block(pattern)
            self.send(chat_id, t(lang, "cmd_block_removed", value=pattern))
        elif cmd == "/blocklist":
            items = self.store.get_blocklist()
            if items:
                text = t(lang, "blocklist_title") + "\n" + "\n".join(f"• <code>{p}</code>" for p in items)
            else:
                text = t(lang, "blocklist_title") + "\n" + t(lang, "blocklist_empty")
            self.send(chat_id, text)
        elif cmd == "/setpin":
            pin = args[0] if args else ""
            if not (pin.isdigit() and 4 <= len(pin) <= 8):
                self.send(chat_id, t(lang, "cmd_pin_bad"))
                return
            self.store.set_pin(pin)
            self.send(chat_id, t(lang, "cmd_pin_set"))
        elif cmd == "/clearpin":
            self.store.clear_pin()
            self.send(chat_id, t(lang, "cmd_pin_cleared"))
        elif cmd == "/setbotpin":
            pin = args[0] if args else ""
            if not (pin.isdigit() and 4 <= len(pin) <= 8):
                self.send(chat_id, t(lang, "cmd_botpin_bad"))
                return
            self.store.set_bot_pin(pin)  # revokes EVERY session, including this one
            self.send(chat_id, t(lang, "cmd_botpin_set"))
            self.send(chat_id, t(lang, "enter_bot_pin"))  # the setter must enter it too
        elif cmd == "/clearbotpin":
            self.store.clear_bot_pin()
            self.send(chat_id, t(lang, "cmd_botpin_cleared"))
        elif cmd == "/version":
            self.send(chat_id, t(lang, "cmd_version", value=version.APP_VERSION))
        elif cmd == "/update":
            self.send(chat_id, t(lang, "cmd_update_checking"))
            if self.update_hook:
                self.update_hook(chat_id, lang)
            else:
                self.send(chat_id, t(lang, "cmd_update_off"))
        elif cmd == "/uninstall":
            self.uninstall_command(chat_id, lang, args)

    # -- uninstall: confirm button, then PIN --------------------------------
    def _uninstall_pin_ok(self, pin: str) -> bool:
        """Check against the bot PIN, else the app PIN. No PIN set -> allowed."""
        if self.store.has_bot_pin():
            return self.store.check_bot_pin(pin)
        if self.store.has_pin():
            return self.store.check_pin(pin)
        return True

    def uninstall_command(self, chat_id, lang, args):
        needs_pin = self.store.has_bot_pin() or self.store.has_pin()
        if chat_id not in self.pending_uninstall:
            self.send(chat_id, t(lang, "uninstall_warn"),
                      kb=[[{"text": t(lang, "uninstall_confirm_btn"),
                            "callback_data": "uninstall_yes"}]])
            return
        if needs_pin:
            pin = args[0] if args else ""
            if not pin:
                self.send(chat_id, t(lang, "uninstall_need_pin"))
                return
            if not self._uninstall_pin_ok(pin):
                self.send(chat_id, t(lang, "pin_wrong"))
                return
        self.pending_uninstall.discard(chat_id)
        self.send(chat_id, t(lang, "uninstall_done"))
        if self.uninstall_hook:
            self.uninstall_hook()

    # -- reports ---------------------------------------------------------
    def send_today(self, chat_id, lang, is_admin=False):
        day = self.store.today_key()
        active, screen = self.store.day_stats(day)
        caption = t(lang, "today_caption", date=fmt_date(day, lang),
                    active=fmt_duration(active, lang), screen=fmt_duration(screen, lang))
        png = None
        if self.card_renderer:
            try:
                png = self.card_renderer(day, active, screen, lang, self.username or "")
            except Exception:
                png = None
        if png:
            try:
                self.api("sendPhoto",
                         {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML",
                          "reply_markup": {"inline_keyboard": self.menu_kb(lang, is_admin)}},
                         files={"photo": ("today.png", png, "image/png")})
                return
            except (BotApiError, requests.RequestException):
                pass
        self.send(chat_id, caption, kb=self.menu_kb(lang, is_admin))

    def send_week(self, chat_id, lang, is_admin=False):
        rows = self.store.last_days(7)
        max_active = max((active for _, active, _ in rows), default=0.0) or 1.0
        lines = []
        for day, active, _screen in rows:
            index = datetime.datetime.strptime(day, "%Y-%m-%d").weekday()
            blocks = int(round(active / max_active * 8))
            if active > 0 and blocks == 0:
                blocks = 1
            _, month, day_num = day.split("-")
            line = f"{dow(lang, index)} {day_num}.{month}  {'▇' * blocks} {fmt_duration(active, lang)}"
            lines.append(line.rstrip())
        total = sum(active for _, active, _ in rows)
        text = (f"<b>{t(lang, 'week_title')}</b>\n<pre>" + "\n".join(lines) + "</pre>\n" +
                t(lang, "week_footer", total=fmt_duration(total, lang),
                  avg=fmt_duration(total / 7, lang)))
        self.send(chat_id, text, kb=self.menu_kb(lang, is_admin))

    FRIENDLY = {
        "chrome.exe": "Google Chrome", "msedge.exe": "Microsoft Edge",
        "brave.exe": "Brave", "firefox.exe": "Firefox", "opera.exe": "Opera",
        "explorer.exe": "Explorer", "code.exe": "VS Code", "discord.exe": "Discord",
        "telegram.exe": "Telegram", "steam.exe": "Steam", "spotify.exe": "Spotify",
        "notepad.exe": "Notepad", "winword.exe": "Word", "excel.exe": "Excel",
    }

    @classmethod
    def _friendly(cls, name):
        if not name:
            return "?"
        return cls.FRIENDLY.get(name.lower(), name[:-4] if name.lower().endswith(".exe") else name)

    def send_apps(self, chat_id, lang, is_admin=False):
        day = self.store.today_key()
        top = self.store.top_apps(day, 8)
        if not top:
            text = t(lang, "apps_title") + "\n" + t(lang, "apps_empty")
        else:
            lines = [f"• {self._friendly(name)} — <b>{fmt_duration(sec, lang)}</b>"
                     for name, sec in top]
            text = t(lang, "apps_title") + "\n" + "\n".join(lines)
        self.send(chat_id, text, kb=self.menu_kb(lang, is_admin))

    def send_status(self, chat_id, lang, is_admin=False):
        day = self.store.today_key()
        active, _screen = self.store.day_stats(day)
        limit_min = int(self.store.get_config("daily_limit_min", 0) or 0)
        bonus = self.store.get_bonus(day)
        work = int(self.store.get_config("work_min", 0) or 0)
        brk = int(self.store.get_config("break_min", 0) or 0)

        if limit_min > 0:
            eff = limit_min + bonus
            limit_txt = fmt_minutes(eff, lang) + (f" (+{bonus})" if bonus else "")
            if active >= eff * 60:
                state = t(lang, "state_limit")
            else:
                state = t(lang, "state_working")
        else:
            limit_txt = "—"
            state = t(lang, "state_working")
        cycle_txt = (f"{fmt_minutes(work, lang)} / {fmt_minutes(brk, lang)}"
                     if work > 0 and brk > 0 else "—")

        text = (f"{t(lang, 'st_title')}\n"
                f"• {t(lang, 'st_state')}: <b>{state}</b>\n"
                f"• {t(lang, 'st_limit')}: <b>{limit_txt}</b>\n"
                f"• {t(lang, 'st_cycle')}: <b>{cycle_txt}</b>\n"
                f"• {t(lang, 'st_today')}: <b>{fmt_duration(active, lang)}</b>")
        if is_admin:
            text += "\n\n" + t(lang, "help_admin")
        self.send(chat_id, text, kb=self.menu_kb(lang, is_admin))
