"""TimeApp entry point: single instance, tracker + policy + Telegram bot + GUI."""

import sys
import threading

# The bot token is a secret and must never live in the public source. A local,
# git-ignored secret_token.py can bake one in for your own builds; without it the
# app starts token-less and asks for the token once in Settings.
try:
    from secret_token import DEFAULT_TOKEN
except Exception:
    DEFAULT_TOKEN = ""


def run_selftest() -> int:
    import os
    import tempfile

    # --- storage + pairing ---
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TIMEAPP_DIR"] = tmp
        from storage import Store
        store = Store()
        store.add_time("2026-01-01", 10, 20)
        store.save()
        again = Store(tmp)
        assert again.day_stats("2026-01-01") == (10.0, 20.0), "storage roundtrip"
        code, _ = store.get_valid_code()
        assert len(code) == 6 and code.isdigit(), "code format"
        assert store.get_valid_code()[0] == code, "code stable while valid"
        assert store.try_pair(111, code), "pairing works"
        wrong = "000000" if code != "000000" else "999999"
        assert not store.try_pair(222, wrong), "wrong code rejected"
        # admins
        store.add_admin("@Alice")
        assert store.is_admin("alice") and store.is_admin("ALICE"), "admin case-insensitive"
        store.set_admin_chat("alice", 555)
        assert store.admin_chats().get("alice") == 555, "admin chat stored"
        store.remove_admin("alice")
        assert not store.is_admin("alice"), "admin removed"
        assert "alice" not in store.admin_chats(), "admin chat cleared"
        # commands + bonus
        store.push_command("breaknow", 10)
        drained = store.drain_commands()
        assert drained and drained[0]["type"] == "breaknow", "command queue"
        assert store.drain_commands() == [], "queue drains once"
        store.add_bonus("2026-01-01", 15)
        assert store.get_bonus("2026-01-01") == 15, "bonus stored"
        # per-app time + reset
        store.add_app_time("2026-01-01", "chrome.exe", 120)
        store.add_app_time("2026-01-01", "code.exe", 300)
        top = store.top_apps("2026-01-01", 5)
        assert top and top[0][0] == "code.exe", "top app ordering"
        store.reset_day("2026-01-01")
        assert store.day_stats("2026-01-01") == (0.0, 0.0) and not store.top_apps("2026-01-01"), "reset day"
        # blocklist + PIN
        store.add_block("YouTube.com/Shorts")
        assert "youtube.com/shorts" in store.get_blocklist(), "blocklist stored lowercased"
        store.remove_block("youtube.com/shorts")
        assert not store.get_blocklist(), "blocklist removed"
        assert store.check_pin("anything") is True, "no pin -> allow"
        store.set_pin("1234")
        assert store.has_pin() and store.check_pin("1234") and not store.check_pin("0000"), "pin verify"
        store.clear_pin()
        assert not store.has_pin(), "pin cleared"
        os.environ.pop("TIMEAPP_DIR", None)

    # --- version compare + update source validation ---
    import version as _v
    import updater as _u
    assert _v.parse("v1.2.3") == (1, 2, 3), "version parse"
    assert _v.is_newer("1.0.1", "1.0.0") and _v.is_newer("v2.0", "1.9.9"), "newer detected"
    assert not _v.is_newer("1.0.0", "1.0.0"), "same version is not newer"
    assert not _v.is_newer("0.9", "1.0.0"), "older is not newer"
    assert _u.normalize_repo("https://github.com/me/timeapp") == "me/timeapp", "repo from url"
    assert _u.normalize_repo(" me/timeapp ") == "me/timeapp", "repo plain"
    assert _u.normalize_repo("not a repo") == "", "bad repo rejected"
    assert _u._host_ok("https://github.com/a/b/releases/download/x/TimeApp.exe"), "github host ok"
    assert not _u._host_ok("http://github.com/a"), "http refused"
    assert not _u._host_ok("https://evil.com/TimeApp.exe"), "foreign host refused"
    assert not _u._host_ok("https://github.com.evil.com/x"), "lookalike host refused"

    # --- bot PIN gating ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        st = Store(tmp)
        st.add_admin("bob")
        assert st.is_admin_unlocked(7), "no bot pin -> unlocked"
        st.set_bot_pin("2468")
        assert not st.is_admin_unlocked(7), "bot pin set -> locked until entered"
        assert not st.check_bot_pin("0000") and st.check_bot_pin("2468"), "bot pin verify"
        st.unlock_admin(7)
        assert st.is_admin_unlocked(7), "unlocked after correct pin"
        st.set_bot_pin("1357")  # changing the PIN signs everyone out again
        assert not st.is_admin_unlocked(7), "re-setting pin revokes sessions"
        st.clear_bot_pin()
        assert st.is_admin_unlocked(7), "cleared pin -> open again"
        assert not st.check_bot_pin(""), "empty pin never authorises"

    # --- website blocklist matching (domain + path) ---
    from webrules import match
    assert match("https://www.youtube.com/shorts/abc", ["youtube.com/shorts"]), "path match"
    assert not match("https://www.youtube.com/watch?v=1", ["youtube.com/shorts"]), "other path not matched"
    assert match("https://m.youtube.com/feed", ["youtube.com"]), "subdomain domain match"
    assert not match("https://notyoutube.com/", ["youtube.com"]), "lookalike domain not matched"
    assert match("reddit.com/r/aww", ["reddit.com"]), "domain-only matches any path"

    # --- policy engine ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from policy import Policy
        st = Store(tmp)
        ev = threading.Event()
        clk = [1000.0]
        day = ["2026-02-02"]
        pol = Policy(st, ev, clock=lambda: clk[0], today_fn=lambda: day[0])

        # daily limit
        st.set_config("daily_limit_min", 1)  # 60s
        assert not pol.tick()["block"], "under limit -> no block"
        st.add_time(day[0], 70, 70)
        act = pol.tick()
        assert act["block"] and act["reason"] == "limit" and ev.is_set(), "limit blocks"
        st.add_bonus(day[0], 10)  # +600s -> now under limit
        assert not pol.tick()["block"] and not ev.is_set(), "bonus lifts limit block"
        st.set_config("daily_limit_min", 0)

        # work/break cycle
        st2dir = tmp + "_c"
        st2 = Store(st2dir)
        ev2 = threading.Event()
        clk2 = [500.0]
        pol2 = Policy(st2, ev2, clock=lambda: clk2[0], today_fn=lambda: "2026-02-02")
        st2.set_config("work_min", 1)
        st2.set_config("break_min", 1)
        st2.add_time("2026-02-02", 65, 65)  # streak 65s >= 60s
        act = pol2.tick()
        assert act["block"] and act["reason"] == "cycle", "cycle starts break"
        assert 0 < act["remaining"] <= 60, "cycle remaining sane"
        clk2[0] += 61  # break elapsed
        assert not pol2.tick()["block"] and not ev2.is_set(), "cycle break ends"

        # manual break + unlock via command queue
        st2.push_command("breaknow", 1)
        assert pol2.tick()["reason"] == "manual", "manual break"
        st2.push_command("unlock")
        assert not pol2.tick()["block"], "unlock ends break"

    # --- policy: warning before a block ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from policy import Policy
        st = Store(tmp)
        ev = threading.Event()
        st.set_config("daily_limit_min", 10)   # 600s limit
        st.set_config("warn_min", 5)            # warn within 300s
        pol = Policy(st, ev, clock=lambda: 0.0, today_fn=lambda: "d")
        st.add_time("d", 200, 200)              # remaining 400s -> outside warn window
        assert pol.tick().get("warn") is None, "no warn outside window"
        st.add_time("d", 150, 150)              # active 350s, remaining 250s -> warn
        w = pol.tick().get("warn")
        assert w and w["kind"] == "limit", "limit warning fires"
        assert pol.tick().get("warn") is None, "warning only fires once"

    # --- tracker: grace rollback ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from tracker import Tracker
        st = Store(tmp)
        st.set_config("idle_limit", 300)
        tr = Tracker(st, None)

        # short pause (<= limit) is KEPT: idle ramps 1..120s, never crosses 300
        for i in range(1, 121):
            tr.account(1.0, False, float(i), "d1")
        assert st.day_stats("d1")[0] == 120, "short pause kept"

        # real absence is REMOVED: 50s continuous activity, then walk away past 300s
        tr2 = Tracker(st, None)
        for _ in range(50):
            tr2.account(1.0, False, 0.0, "d2")          # idle=0 -> present, genuine
        assert st.day_stats("d2")[0] == 50, "genuine active counted"
        for i in range(1, 306):
            tr2.account(1.0, False, float(i), "d2")     # idle climbs past the 300s limit
        active2, screen2 = st.day_stats("d2")
        assert 50 <= active2 <= 52, f"absence grace removed (~50 genuine), got {active2}"
        assert screen2 >= 350, f"screen time kept counting on-but-idle, got {screen2}"

        # locked session credits nothing
        tr3 = Tracker(st, None)
        for _ in range(30):
            tr3.account(1.0, True, 0.0, "d3")
        assert st.day_stats("d3") == (0.0, 0.0), "locked -> nothing counted"

        # per-app time recorded while active
        tr4 = Tracker(st, None)
        for _ in range(10):
            tr4.account(1.0, False, 0.0, "d4", "chrome.exe")
        assert dict(st.top_apps("d4")).get("chrome.exe") == 10, "per-app time recorded"

    # --- reboot resilience: durable storage recovers a corrupt/empty file ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        st = Store(tmp)
        st.set_config("token", "TOKEN123")
        st.set_config("daily_limit_min", 42)
        st.path.write_text("{ this is broken json", encoding="utf-8")   # corrupt main
        st2 = Store(tmp)
        assert st2.get_config("token") == "TOKEN123", "config recovered from backup, not wiped"
        assert st2.get_config("daily_limit_min") == 42, "latest value recovered from backup"
        st.path.write_text("", encoding="utf-8")                        # empty (crash mid-write)
        st3 = Store(tmp)
        assert st3.get_config("token") == "TOKEN123", "empty main recovers from backup"

    # --- reboot resilience: in-progress break resumes after a restart ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from policy import Policy
        wall = [10_000.0]
        day = "2026-05-05"
        st = Store(tmp)
        st.set_config("work_min", 30)
        st.set_config("break_min", 15)
        ev = threading.Event()
        p = Policy(st, ev, clock=lambda: wall[0], today_fn=lambda: day)
        st.add_time(day, 30 * 60, 30 * 60)              # 30 min streak -> break starts
        assert p.tick()["reason"] == "cycle", "cycle break starts"
        # "reboot" 5 min into the 15-min break: fresh Policy + Event, same store
        wall[0] += 5 * 60
        ev2 = threading.Event()
        p2 = Policy(st, ev2, clock=lambda: wall[0], today_fn=lambda: day)
        assert ev2.is_set(), "resumed break re-blocks immediately after restart"
        r = p2.tick()
        assert r["block"] and r["reason"] == "cycle", "break still active after restart"
        assert 590 <= r["remaining"] <= 600, f"~10 min of the 15 left, got {r['remaining']}"
        # if the whole break elapsed while the PC was off, it is over on restart
        wall[0] += 20 * 60
        ev3 = threading.Event()
        p3 = Policy(st, ev3, clock=lambda: wall[0], today_fn=lambda: day)
        assert not ev3.is_set() and not p3.tick()["block"], "elapsed break is finished"

    # --- reboot resilience: daily-limit block + work-streak survive restart ---
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from policy import Policy
        st = Store(tmp)
        st.set_config("daily_limit_min", 10)            # 600s
        st.add_time("d", 700, 700)
        ev = threading.Event()
        assert Policy(st, ev, clock=lambda: 1.0, today_fn=lambda: "d").tick()["reason"] == "limit"
        ev2 = threading.Event()
        p2 = Policy(st, ev2, clock=lambda: 2.0, today_fn=lambda: "d")
        assert ev2.is_set() and p2.tick()["reason"] == "limit", "limit block persists across restart"

    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        from policy import Policy
        wall = [100.0]
        st = Store(tmp)
        st.set_config("work_min", 30)
        st.set_config("break_min", 15)
        ev = threading.Event()
        p = Policy(st, ev, clock=lambda: wall[0], today_fn=lambda: "d")
        st.add_time("d", 30 * 60, 30 * 60)              # 30 min -> break
        assert p.tick()["reason"] == "cycle"
        st.push_command("unlock")
        wall[0] += 1
        assert not p.tick()["block"]                    # break ended, baseline ~= 1800s
        # restart: the non-zero baseline must be restored so the streak keeps counting
        ev2 = threading.Event()
        p2 = Policy(st, ev2, clock=lambda: wall[0], today_fn=lambda: "d")
        st.add_time("d", 29 * 60, 29 * 60)              # 59 min total, streak 29 < 30
        assert not p2.tick()["block"], "streak baseline preserved -> no early break"
        st.add_time("d", 2 * 60, 2 * 60)                # 61 min total, streak 31 >= 30
        assert p2.tick()["reason"] == "cycle", "breaks again after another full work period"

    # --- i18n parity + formatting ---
    from i18n import STRINGS, fmt_duration, fmt_minutes, t
    assert set(STRINGS["en"]) == set(STRINGS["uk"]), "i18n key parity"
    assert fmt_duration(3725, "en").startswith("1 h"), "duration format"
    assert fmt_minutes(90, "uk").startswith("1 год"), "minutes format"
    assert "{date}" not in t("uk", "valid_until", date="x"), "placeholder subst"
    # every status_<x> the bot can emit must exist
    for state in ("starting", "ok", "network", "conflict", "unauthorized"):
        assert t("en", f"status_{state}") != f"status_{state}", f"status key {state}"

    # --- network setup + proxy config ---
    setup_network("")  # must never raise, even if truststore is unavailable
    with tempfile.TemporaryDirectory() as tmp:
        from storage import Store
        st = Store(tmp)
        assert st.get_config("proxy", "") == "", "proxy empty by default"
        st.set_config("proxy", "http://127.0.0.1:8080")
        assert Store(tmp).get_config("proxy") == "http://127.0.0.1:8080", "proxy persists"

    # --- winutil ---
    import winutil
    assert isinstance(winutil.get_idle_seconds(), float), "idle seconds"
    assert isinstance(winutil.is_locked(), bool), "lock state"
    assert winutil.pid_alive(os.getpid()), "own pid alive"
    assert not winutil.pid_alive(2 ** 31 - 1), "bogus pid not alive"
    assert not winutil.pid_alive(0) and not winutil.pid_alive("x"), "guarded pid inputs"

    # --- guardian: exit token, watchdog flag, uninstall script ---
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TIMEAPP_DIR"] = tmp
        import guardian
        from storage import Store
        st = Store(tmp)
        guardian.clear_allow_exit()
        assert not guardian.allow_exit_set(), "no exit token initially"
        guardian.allow_exit()
        assert guardian.allow_exit_set(), "exit token set"
        guardian.clear_allow_exit()
        assert not guardian.allow_exit_set(), "exit token cleared"
        assert guardian.watchdog_enabled(tmp), "watchdog enabled by default"
        st.set_config("watchdog", False)
        assert not guardian.watchdog_enabled(tmp), "watchdog flag read from data.json"
        script = guardian.build_uninstall_script(r"C:\x\TimeApp.exe", tmp, 4321, remove_data=True)
        assert "TimeApp.exe" in script and tmp in script and "rmdir" in script, "uninstall script"
        assert 'PID eq 4321' in script, "uninstall waits for the app pid"
        os.environ.pop("TIMEAPP_DIR", None)

    # --- input blocker installs/uninstalls (does NOT block during the test) ---
    from enforce import InputBlocker
    blk = InputBlocker()
    blk.start()
    assert blk.installed(), "hooks installed"
    assert not blk.is_blocking(), "not blocking by default"
    blk.stop()

    # --- Qt: svg + card render ---
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtSvg import QSvgRenderer
    _qt = QGuiApplication([])
    import icons
    for svg in (icons.LOGO_SVG, icons.FLAG_UA, icons.FLAG_GB):
        assert QSvgRenderer(svg.encode()).isValid(), "svg valid"
    for name in icons.names():
        assert QSvgRenderer(icons.svg(name)).isValid(), f"icon {name}"
    from render import render_today_card
    for lang in ("uk", "en"):
        png = render_today_card("2026-08-13", 3725, 5000, lang, "testbot")
        assert png[:8] == b"\x89PNG\r\n\x1a\n", f"card png {lang}"

    print("SELFTEST OK")
    return 0


def setup_network(proxy: str = ""):
    """Make HTTPS work on PCs where an antivirus/corporate proxy intercepts TLS.

    Injecting the OS (Windows) certificate store lets requests validate against
    the roots the machine already trusts — including the ones antivirus HTTPS
    scanners install — instead of only the bundled certifi roots, which is the
    usual reason a PC with working internet reports "can't reach Telegram".
    An optional manual proxy is applied via the environment so both the bot and
    the updater pick it up.
    """
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
    import os
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(key, None)
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy


def run_nettest() -> int:
    """`TimeApp.exe --nettest` — write a diagnostic of why Telegram is unreachable."""
    import os
    import tempfile
    import urllib.request

    import requests
    from storage import Store

    store = Store()
    token = store.get_config("token", "") or ""
    proxy = store.get_config("proxy", "") or ""
    url = f"https://api.telegram.org/bot{token}/getMe" if token else "https://api.telegram.org/"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    lines = [
        "TimeApp network diagnostic",
        "system proxies: " + str(urllib.request.getproxies()),
        "configured proxy: " + (proxy or "(none)"),
    ]

    def attempt(label):
        try:
            resp = requests.get(url, timeout=15, proxies=proxies)
            lines.append(f"{label}: OK (HTTP {resp.status_code})")
            return True
        except Exception as exc:  # noqa: BLE001 - diagnostic
            lines.append(f"{label}: FAIL {type(exc).__name__}: {str(exc)[:200]}")
            return False

    attempt("with bundled certs")     # what a plain requests call does today
    try:
        import truststore
        truststore.inject_into_ssl()
        lines.append("OS trust store: injected")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"OS trust store: inject failed: {exc}")
    attempt("with Windows trust store")

    out = os.path.join(tempfile.gettempdir(), "timeapp_nettest.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    os._exit(0)


def main() -> int:
    if "--selftest" in sys.argv:
        return run_selftest()

    if "--nettest" in sys.argv:
        return run_nettest()

    if "--urltest" in sys.argv:
        # 20s diagnostic: log what the address bar reports, to verify that
        # "typing" (editing=True) is told apart from "page opened".
        import os
        import tempfile
        import time
        import urlwatch
        out = os.path.join(tempfile.gettempdir(), "timeapp_urltest.txt")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(f"UIA_AVAILABLE={urlwatch._init()}\n")
            for _ in range(40):
                found = urlwatch.foreground_browser_url()
                if found:
                    _hwnd, url, editing = found
                    fh.write(f"editing={editing}\turl={url}\n")
                else:
                    fh.write("no-browser\n")
                fh.flush()
                time.sleep(0.5)
        os._exit(0)

    if "--watch" in sys.argv:
        # watchdog child: relaunch the app if the parent PID disappears
        import guardian
        idx = sys.argv.index("--watch")
        ppid = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 0
        guardian.run_watchdog(ppid)
        import os
        os._exit(0)

    if "--webtest" in sys.argv:
        # verify UI Automation (comtypes) initialises inside the frozen build
        import os
        import tempfile
        import urlwatch
        ok = urlwatch._init()
        out = os.path.join(tempfile.gettempdir(), "timeapp_webtest.txt")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(f"UIA_AVAILABLE={ok}")
        os._exit(0)  # COM keeps threads alive; leave immediately so no mutex is held

    import winutil
    if not winutil.acquire_single_instance():
        winutil.message_box(
            "TimeApp",
            "TimeApp вже запущено (іконка у треї).\nTimeApp is already running (check the tray).")
        return 0

    # autostart is always on, re-asserted on every launch
    try:
        winutil.set_autostart(True)
    except OSError:
        pass

    import guardian
    from storage import Store
    store = Store()
    # trust the OS certificate store + apply any manual proxy before any request
    setup_network(store.get_config("proxy", "") or "")
    token = store.get_config("token") or DEFAULT_TOKEN
    store.set_config("token", token)

    guard = guardian.Guard(store)
    guard.start()  # clears any stale exit token and spawns the watchdog

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("TimeApp")
    app.setQuitOnLastWindowClosed(False)

    from bot import TelegramBot
    from enforce import InputBlocker
    from policy import Policy
    from render import render_today_card
    from tracker import Tracker
    from webguard import WebGuard
    import updater
    from i18n import t as _t

    blocking_event = threading.Event()
    # Build the policy first: it restores a break that was in progress before a
    # reboot and sets blocking_event, so the tracker never counts that gap.
    policy = Policy(store, blocking_event)
    tracker = Tracker(store, blocking_event)
    tracker.start()

    def update_hook(chat_id, lang):
        """Serve /update from the bot thread: check, then install if allowed."""
        repo = store.get_config("update_repo", "") or ""
        if not repo:
            bot.send(chat_id, _t(lang, "cmd_update_off"))
            return
        try:
            info = updater.check(repo)
        except Exception as exc:
            bot.send(chat_id, _t(lang, "cmd_update_failed", value=str(exc)[:80]))
            return
        if not info:
            bot.send(chat_id, _t(lang, "cmd_update_none"))
            return
        bot.send(chat_id, _t(lang, "cmd_update_found", value=info["version"]))
        bot.send(chat_id, _t(lang, "cmd_update_installing"))
        try:
            path = updater.download(info["url"])
            if updater.apply_update(path):
                guard.authorize_exit()  # let the update swap the exe without a fight
                QApplication.instance().quit()
            else:
                bot.send(chat_id, _t(lang, "cmd_update_failed", value="not a frozen build"))
        except Exception as exc:
            bot.send(chat_id, _t(lang, "cmd_update_failed", value=str(exc)[:80]))

    def uninstall_hook():
        guardian.uninstall()
        QApplication.instance().quit()

    bot = TelegramBot(store, token, card_renderer=render_today_card,
                      update_hook=update_hook, uninstall_hook=uninstall_hook)
    bot.start()
    blocker = InputBlocker()
    policy.set_notifier(bot.notify)
    webguard = WebGuard(store)

    checker = updater.UpdateChecker(
        store, on_found=lambda info: bot.notify("notify_update", value=info["version"]))
    checker.start()

    from gui import MainWindow
    window = MainWindow(store, bot, blocking_event, blocker, policy, webguard, guard)
    window.show()

    exit_code = app.exec()

    tracker.stop()
    bot.stop()
    checker.stop()
    try:
        blocker.stop()
    except Exception:
        pass
    tracker.join(timeout=3)
    try:
        store.save()
    except OSError:
        pass
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
