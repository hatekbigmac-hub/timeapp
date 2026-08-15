"""English / Ukrainian strings for the bot and the desktop app."""

LANGS = ("uk", "en")

STRINGS = {
    "en": {
        # --- bot: onboarding ---
        "welcome": "\U0001F44B Hi! I'm <b>TimeApp</b> — I show how much time you spend at your PC.",
        "choose_lang": "\U0001F310 Choose your language:",
        "enter_code": "\U0001F511 Send me the 6-digit code from the TimeApp window on your PC.",
        "wrong_code": "❌ Wrong or expired code. Check the code in the TimeApp window and try again.",
        "paired": "✅ Done! Your PC is linked. Use the buttons below.",
        "hint": "Pick an action \U0001F447",
        "unlinked": "\U0001F513 This chat is unlinked. Send the code from the TimeApp window to link again.",
        "lang_set": "✅ Language: English",
        # --- bot: menus ---
        "menu_today": "\U0001F4CA Today",
        "menu_week": "\U0001F4C5 Week",
        "menu_lang": "\U0001F310 Language",
        "menu_status": "ℹ️ Status",
        "menu_break": "⛔ Break now",
        "menu_addtime": "➕ 15 min",
        "menu_unlock": "\U0001F513 Unlock",
        # --- bot: reports ---
        "today_caption": "\U0001F5D3 <b>{date}</b>\n⚡ Active time: <b>{active}</b>\n\U0001F5A5 Screen time: <b>{screen}</b>",
        "week_title": "\U0001F4C5 Last 7 days",
        "week_footer": "Total: <b>{total}</b> • Daily average: <b>{avg}</b>",
        # --- bot: admin commands ---
        "admin_only": "\U0001F512 This command is for admins of this PC only.",
        "cmd_limit_set": "✅ Daily limit: <b>{value}</b>",
        "cmd_limit_off": "✅ Daily limit turned off.",
        "cmd_cycle_set": "✅ Cycle: work <b>{work}</b> → break <b>{brk}</b>.",
        "cmd_cycle_off": "✅ Work/break cycle turned off.",
        "cmd_bonus_added": "✅ Added <b>{value}</b> to today's limit.",
        "cmd_break_started": "⛔ Break started: <b>{value}</b>. Mouse and keyboard are locked.",
        "cmd_unlocked": "\U0001F513 Unlocked.",
        "cmd_bad_number": "⚠️ Give a number of minutes, e.g. <code>{example}</code>",
        "help_admin": ("<b>Admin commands</b>\n"
                       "<code>/setlimit 120</code> — daily limit (0 = off)\n"
                       "<code>/setcycle 30 30</code> — work / break minutes (0 0 = off)\n"
                       "<code>/addtime 15</code> — add minutes to today\n"
                       "<code>/breaknow 10</code> — force a break now\n"
                       "<code>/unlock</code> — end the current block\n"
                       "<code>/resetday</code>, <code>/resetweek</code> — reset counted time\n"
                       "<code>/apps</code> — top apps today\n"
                       "<code>/block youtube.com/shorts</code>, <code>/unblock …</code>, <code>/blocklist</code>\n"
                       "<code>/setpin 1234</code>, <code>/clearpin</code> — protect the app\n"
                       "<code>/setbotpin 1234</code>, <code>/clearbotpin</code> — admin sign-in PIN\n"
                       "<code>/update</code>, <code>/version</code> — check for updates\n"
                       "<code>/uninstall</code> — remove TimeApp from the PC (needs PIN)\n"
                       "<code>/status</code> — current settings"),
        # --- bot: status report ---
        "st_title": "\U0001F5A5 <b>TimeApp — status</b>",
        "st_state": "State",
        "st_limit": "Daily limit",
        "st_cycle": "Work/break",
        "st_today": "Today active",
        "state_working": "working",
        "state_break": "break ({value} left)",
        "state_limit": "daily limit reached",
        # --- bot: notifications to admins ---
        "notify_limit": "\U0001F6AB This PC reached its daily limit — it is now locked.",
        "notify_break": "⛔ Break started on this PC.",
        "notify_break_over": "✅ Break is over on this PC.",
        # --- stat card ---
        "card_title": "Time at the PC today",
        "card_active": "Active time",
        "card_screen": "Screen time",
        # --- break overlay ---
        "overlay_break_title": "Time for a break",
        "overlay_limit_title": "Daily limit reached",
        "overlay_manual_title": "Break",
        "overlay_sub": "Mouse and keyboard are locked",
        "overlay_resume": "Resumes in",
        "overlay_until_tomorrow": "The PC unlocks tomorrow",
        "overlay_admin_unlock": "…or an admin can unlock it earlier",
        # --- desktop app ---
        "your_code": "Your code for the Telegram bot",
        "valid_until": "Valid until {date}",
        "today_at_pc": "Today at the PC",
        "open_bot": "Open bot in Telegram",
        "autostart_on": "Starts automatically with Windows",
        "manage": "Manage",
        "steps": "1) Open the bot in Telegram   2) Send it the code   3) Watch your stats",
        "tray_title": "TimeApp is running in the background",
        "tray_body": "Time tracking continues. The icon is in the tray near the clock.",
        "tray_open": "Open",
        "tray_quit": "Quit",
        "status_starting": "Connecting to Telegram…",
        "status_ok": "Bot is online",
        "status_network": "No internet — retrying…",
        "status_conflict": "This bot token is used on another PC",
        "status_unauthorized": "Bot token is invalid",
        "status_no_token": "Set the bot token in ⚙ Settings",
        "copied": "Copied!",
        # --- settings dialog ---
        "settings_title": "TimeApp — settings",
        "set_admins_label": "Admins (Telegram @username)",
        "set_admins_hint": "Admins control this PC from the bot: limits, breaks, unlock.",
        "set_add": "Add",
        "set_remove": "Remove",
        "set_none": "No admins yet",
        "set_limit_label": "Daily limit (minutes, 0 = off)",
        "set_cycle_work": "Work period (minutes)",
        "set_cycle_break": "Break period (minutes)",
        "set_cycle_hint": "0 in either field turns the work/break cycle off.",
        "set_metric_hint": "Limits count active time (mouse/keyboard used).",
        "set_token_label": "Bot token",
        "set_token_hint": "For a second PC, create another bot in @BotFather and paste its token here.",
        "set_apply": "Apply token",
        "set_saved": "Saved",
        "set_close": "Close",
        "set_min": "min",
        # --- v2 features ---
        "menu_apps": "\U0001F5C2 Apps",
        "menu_resetday": "♻️ Reset day",
        "cmd_reset_day": "♻️ Today's time has been reset.",
        "cmd_reset_week": "♻️ This week's time has been reset.",
        "cmd_block_added": "\U0001F6AB Blocked: <b>{value}</b>",
        "cmd_block_removed": "✅ Unblocked: <b>{value}</b>",
        "cmd_block_bad": "⚠️ Give a site, e.g. <code>{example}</code>",
        "blocklist_title": "\U0001F6AB <b>Blocked sites</b>",
        "blocklist_empty": "No blocked sites.",
        "cmd_pin_set": "\U0001F512 PIN set. Opening settings and quitting now ask for it.",
        "cmd_pin_cleared": "\U0001F513 PIN removed.",
        "cmd_pin_bad": "⚠️ Give a 4–8 digit PIN, e.g. <code>/setpin 1234</code>",
        "apps_title": "\U0001F5C2 <b>Top apps today</b>",
        "apps_empty": "No data yet.",
        "warn_limit_title": "⏰ Daily limit soon",
        "warn_cycle_title": "⏰ Break soon",
        "warn_body": "Time left: {value}",
        "web_blocked_title": "\U0001F6AB Site blocked",
        "web_blocked_body": "{value} is on the blocklist",
        "set_block_label": "Blocked sites (domain or path)",
        "set_block_hint": "e.g. youtube.com or youtube.com/shorts",
        "set_warn_label": "Warn before a block (minutes, 0 = off)",
        "set_pin_label": "Protection PIN",
        "set_pin_hint": "When set, opening settings and quitting require the PIN.",
        "set_pin_on": "PIN is on",
        "set_pin_off": "PIN is off",
        "set_pin_set_btn": "Set PIN",
        "set_pin_clear_btn": "Remove PIN",
        "pin_prompt_settings": "Enter PIN to open settings:",
        "pin_prompt_quit": "Enter PIN to quit:",
        "pin_set_prompt": "New PIN (4–8 digits):",
        "pin_wrong": "Wrong PIN.",
        # --- v3: reset week, bot PIN, auto-update ---
        "menu_resetweek": "♻️ Reset week",
        "enter_bot_pin": "\U0001F510 You are an admin of this PC. Send the bot PIN to sign in.",
        "admin_unlocked": "✅ Admin access granted.",
        "cmd_botpin_set": "\U0001F510 Bot PIN set. Everyone — including you — is signed out and must send this PIN to the bot to sign in.",
        "cmd_botpin_cleared": "\U0001F513 Bot PIN removed — admins are recognised by @username only.",
        "cmd_botpin_bad": "⚠️ Give a 4–8 digit PIN, e.g. <code>/setbotpin 1234</code>",
        "cmd_version": "TimeApp <b>v{value}</b>",
        "cmd_update_checking": "\U0001F504 Checking for updates…",
        "cmd_update_none": "✅ You are on the latest version.",
        "cmd_update_found": "\U0001F53C Update available: <b>v{value}</b>",
        "cmd_update_installing": "⬇️ Downloading and installing — the app will restart.",
        "cmd_update_failed": "⚠️ Update failed: {value}",
        "cmd_update_off": "⚠️ Auto-update is off: set the GitHub repository in the app settings.",
        "notify_update": "\U0001F53C TimeApp update available: <b>v{value}</b>",
        "set_botpin_label": "Bot PIN (admin sign-in)",
        "set_botpin_hint": "When set, admins must send this PIN to the bot before they get control.",
        "set_update_label": "Auto-update (GitHub repository)",
        "set_update_hint": "e.g. yourname/timeapp — the app checks Releases and updates itself.",
        "set_update_check": "Check now",
        "set_update_none": "Latest version",
        "set_update_found": "Update: v{value}",
        "set_update_bad_repo": "Enter the repository as owner/repo.",
        "set_version": "Version {value}",
        # --- v4: tamper resistance + uninstall from the bot ---
        "uninstall_warn": ("⚠️ <b>Remove TimeApp from this PC?</b>\n"
                           "Tracking stops, autostart is removed, and the app and its "
                           "data are deleted. This cannot be undone."),
        "uninstall_confirm_btn": "\U0001F5D1 Yes, remove",
        "uninstall_need_pin": "\U0001F510 Confirm with the PIN: send <code>/uninstall 1234</code>",
        "uninstall_done": "\U0001F5D1 Removing TimeApp. Goodbye!",
        "set_guard_label": "Keep running (relaunch if closed)",
        "set_guard_hint": "Relaunches the app if it is closed or killed. Removal is only via the bot.",
    },
    "uk": {
        # --- bot: onboarding ---
        "welcome": "\U0001F44B Привіт! Я <b>TimeApp</b> — показую, скільки часу ти проводиш за компʼютером.",
        "choose_lang": "\U0001F310 Обери мову:",
        "enter_code": "\U0001F511 Надішли мені 6-значний код з вікна TimeApp на твоєму компʼютері.",
        "wrong_code": "❌ Код невірний або застарів. Перевір код у вікні TimeApp і спробуй ще раз.",
        "paired": "✅ Готово! Компʼютер підключено. Користуйся кнопками нижче.",
        "hint": "Обери дію \U0001F447",
        "unlinked": "\U0001F513 Чат відвʼязано. Надішли код з вікна TimeApp, щоб підключити знову.",
        "lang_set": "✅ Мова: Українська",
        # --- bot: menus ---
        "menu_today": "\U0001F4CA Сьогодні",
        "menu_week": "\U0001F4C5 Тиждень",
        "menu_lang": "\U0001F310 Мова",
        "menu_status": "ℹ️ Стан",
        "menu_break": "⛔ Перерва зараз",
        "menu_addtime": "➕ 15 хв",
        "menu_unlock": "\U0001F513 Розблокувати",
        # --- bot: reports ---
        "today_caption": "\U0001F5D3 <b>{date}</b>\n⚡ Активний час: <b>{active}</b>\n\U0001F5A5 Час за екраном: <b>{screen}</b>",
        "week_title": "\U0001F4C5 Останні 7 днів",
        "week_footer": "Разом: <b>{total}</b> • В середньому за день: <b>{avg}</b>",
        # --- bot: admin commands ---
        "admin_only": "\U0001F512 Ця команда лише для адмінів цього компʼютера.",
        "cmd_limit_set": "✅ Ліміт на день: <b>{value}</b>",
        "cmd_limit_off": "✅ Ліміт на день вимкнено.",
        "cmd_cycle_set": "✅ Цикл: робота <b>{work}</b> → перерва <b>{brk}</b>.",
        "cmd_cycle_off": "✅ Цикл робота/перерва вимкнено.",
        "cmd_bonus_added": "✅ Додано <b>{value}</b> до ліміту на сьогодні.",
        "cmd_break_started": "⛔ Перерва почалась: <b>{value}</b>. Мишу та клавіатуру заблоковано.",
        "cmd_unlocked": "\U0001F513 Розблоковано.",
        "cmd_bad_number": "⚠️ Вкажи кількість хвилин, напр. <code>{example}</code>",
        "help_admin": ("<b>Команди адміна</b>\n"
                       "<code>/setlimit 120</code> — ліміт на день (0 = вимк)\n"
                       "<code>/setcycle 30 30</code> — хвилин роботи / перерви (0 0 = вимк)\n"
                       "<code>/addtime 15</code> — додати хвилин на сьогодні\n"
                       "<code>/breaknow 10</code> — примусова перерва зараз\n"
                       "<code>/unlock</code> — зняти блокування\n"
                       "<code>/resetday</code>, <code>/resetweek</code> — скинути враховане час\n"
                       "<code>/apps</code> — топ програм за сьогодні\n"
                       "<code>/block youtube.com/shorts</code>, <code>/unblock …</code>, <code>/blocklist</code>\n"
                       "<code>/setpin 1234</code>, <code>/clearpin</code> — захист застосунку\n"
                       "<code>/setbotpin 1234</code>, <code>/clearbotpin</code> — PIN входу адміна\n"
                       "<code>/update</code>, <code>/version</code> — перевірити оновлення\n"
                       "<code>/uninstall</code> — видалити TimeApp з ПК (потрібен PIN)\n"
                       "<code>/status</code> — поточні налаштування"),
        # --- bot: status report ---
        "st_title": "\U0001F5A5 <b>TimeApp — стан</b>",
        "st_state": "Стан",
        "st_limit": "Ліміт на день",
        "st_cycle": "Робота/перерва",
        "st_today": "Активно сьогодні",
        "state_working": "працює",
        "state_break": "перерва (лишилось {value})",
        "state_limit": "досягнуто ліміт на день",
        # --- bot: notifications to admins ---
        "notify_limit": "\U0001F6AB Цей компʼютер досяг ліміту на день — його заблоковано.",
        "notify_break": "⛔ На цьому компʼютері почалась перерва.",
        "notify_break_over": "✅ Перерва на цьому компʼютері закінчилась.",
        # --- stat card ---
        "card_title": "Час за компʼютером сьогодні",
        "card_active": "Активний час",
        "card_screen": "Час за екраном",
        # --- break overlay ---
        "overlay_break_title": "Час зробити перерву",
        "overlay_limit_title": "Досягнуто ліміт на день",
        "overlay_manual_title": "Перерва",
        "overlay_sub": "Мишу та клавіатуру заблоковано",
        "overlay_resume": "Продовження через",
        "overlay_until_tomorrow": "Компʼютер розблокується завтра",
        "overlay_admin_unlock": "…або адмін може розблокувати раніше",
        # --- desktop app ---
        "your_code": "Твій код для Telegram-бота",
        "valid_until": "Діє до {date}",
        "today_at_pc": "Сьогодні за компʼютером",
        "open_bot": "Відкрити бота в Telegram",
        "autostart_on": "Запускається автоматично з Windows",
        "manage": "Керування",
        "steps": "1) Відкрий бота в Telegram   2) Надішли йому код   3) Дивись свою статистику",
        "tray_title": "TimeApp працює у фоні",
        "tray_body": "Відлік часу триває. Іконка — у треї біля годинника.",
        "tray_open": "Відкрити",
        "tray_quit": "Вийти",
        "status_starting": "Підключення до Telegram…",
        "status_ok": "Бот на звʼязку",
        "status_network": "Немає інтернету — повторюю…",
        "status_conflict": "Токен цього бота вже зайнятий на іншому ПК",
        "status_unauthorized": "Токен бота недійсний",
        "status_no_token": "Встав токен бота у ⚙ Налаштуваннях",
        "copied": "Скопійовано!",
        # --- settings dialog ---
        "settings_title": "TimeApp — налаштування",
        "set_admins_label": "Адміни (Telegram @username)",
        "set_admins_hint": "Адміни керують цим ПК з бота: ліміти, перерви, розблокування.",
        "set_add": "Додати",
        "set_remove": "Прибрати",
        "set_none": "Ще немає адмінів",
        "set_limit_label": "Ліміт на день (хвилин, 0 = вимк)",
        "set_cycle_work": "Період роботи (хвилин)",
        "set_cycle_break": "Період перерви (хвилин)",
        "set_cycle_hint": "0 у будь-якому полі вимикає цикл робота/перерва.",
        "set_metric_hint": "Ліміти рахують активний час (є рух миші/клавіатури).",
        "set_token_label": "Токен бота",
        "set_token_hint": "Для другого ПК створи ще одного бота в @BotFather і встав його токен сюди.",
        "set_apply": "Застосувати токен",
        "set_saved": "Збережено",
        "set_close": "Закрити",
        "set_min": "хв",
        # --- v2 features ---
        "menu_apps": "\U0001F5C2 Програми",
        "menu_resetday": "♻️ Скинути день",
        "cmd_reset_day": "♻️ Час за сьогодні скинуто.",
        "cmd_reset_week": "♻️ Час за тиждень скинуто.",
        "cmd_block_added": "\U0001F6AB Заблоковано: <b>{value}</b>",
        "cmd_block_removed": "✅ Розблоковано: <b>{value}</b>",
        "cmd_block_bad": "⚠️ Вкажи сайт, напр. <code>{example}</code>",
        "blocklist_title": "\U0001F6AB <b>Заблоковані сайти</b>",
        "blocklist_empty": "Немає заблокованих сайтів.",
        "cmd_pin_set": "\U0001F512 PIN встановлено. Тепер налаштування та вихід питають його.",
        "cmd_pin_cleared": "\U0001F513 PIN прибрано.",
        "cmd_pin_bad": "⚠️ Вкажи PIN з 4–8 цифр, напр. <code>/setpin 1234</code>",
        "apps_title": "\U0001F5C2 <b>Топ програм за сьогодні</b>",
        "apps_empty": "Ще немає даних.",
        "warn_limit_title": "⏰ Скоро ліміт на день",
        "warn_cycle_title": "⏰ Скоро перерва",
        "warn_body": "Залишилось: {value}",
        "web_blocked_title": "\U0001F6AB Сайт заблоковано",
        "web_blocked_body": "{value} у списку блокування",
        "set_block_label": "Заблоковані сайти (домен або шлях)",
        "set_block_hint": "напр. youtube.com або youtube.com/shorts",
        "set_warn_label": "Попередження перед блоком (хвилин, 0 = вимк)",
        "set_pin_label": "PIN-захист",
        "set_pin_hint": "Коли встановлено, відкриття налаштувань і вихід питають PIN.",
        "set_pin_on": "PIN увімкнено",
        "set_pin_off": "PIN вимкнено",
        "set_pin_set_btn": "Встановити PIN",
        "set_pin_clear_btn": "Прибрати PIN",
        "pin_prompt_settings": "Введи PIN, щоб відкрити налаштування:",
        "pin_prompt_quit": "Введи PIN, щоб вийти:",
        "pin_set_prompt": "Новий PIN (4–8 цифр):",
        "pin_wrong": "Невірний PIN.",
        # --- v3: reset week, bot PIN, auto-update ---
        "menu_resetweek": "♻️ Скинути тиждень",
        "enter_bot_pin": "\U0001F510 Ти адмін цього ПК. Надішли PIN бота, щоб увійти.",
        "admin_unlocked": "✅ Доступ адміна надано.",
        "cmd_botpin_set": "\U0001F510 PIN бота встановлено. Усі — і ти теж — вийшли з бота й мають надіслати цей PIN, щоб знову увійти.",
        "cmd_botpin_cleared": "\U0001F513 PIN бота прибрано — адміни визначаються лише за @username.",
        "cmd_botpin_bad": "⚠️ Вкажи PIN з 4–8 цифр, напр. <code>/setbotpin 1234</code>",
        "cmd_version": "TimeApp <b>v{value}</b>",
        "cmd_update_checking": "\U0001F504 Перевіряю оновлення…",
        "cmd_update_none": "✅ У тебе найновіша версія.",
        "cmd_update_found": "\U0001F53C Доступне оновлення: <b>v{value}</b>",
        "cmd_update_installing": "⬇️ Завантажую і встановлюю — застосунок перезапуститься.",
        "cmd_update_failed": "⚠️ Оновлення не вдалося: {value}",
        "cmd_update_off": "⚠️ Автооновлення вимкнено: вкажи GitHub-репозиторій у налаштуваннях застосунку.",
        "notify_update": "\U0001F53C Доступне оновлення TimeApp: <b>v{value}</b>",
        "set_botpin_label": "PIN бота (вхід адмінів)",
        "set_botpin_hint": "Коли встановлено, адмін має надіслати цей PIN боту, щоб отримати керування.",
        "set_update_label": "Автооновлення (GitHub-репозиторій)",
        "set_update_hint": "напр. yourname/timeapp — застосунок дивиться Releases і оновлюється сам.",
        "set_update_check": "Перевірити зараз",
        "set_update_none": "Найновіша версія",
        "set_update_found": "Оновлення: v{value}",
        "set_update_bad_repo": "Вкажи репозиторій у форматі owner/repo.",
        "set_version": "Версія {value}",
        # --- v4: tamper resistance + uninstall from the bot ---
        "uninstall_warn": ("⚠️ <b>Видалити TimeApp з цього ПК?</b>\n"
                           "Відлік зупиниться, автозапуск прибереться, а застосунок і його "
                           "дані буде видалено. Це не можна скасувати."),
        "uninstall_confirm_btn": "\U0001F5D1 Так, видалити",
        "uninstall_need_pin": "\U0001F510 Надішли PIN, щоб підтвердити видалення.",
        "uninstall_done": "\U0001F5D1 Видаляю TimeApp. Бувай!",
        "set_guard_label": "Тримати запущеним (перезапуск при закритті)",
        "set_guard_hint": "Перезапускає застосунок, якщо його закрили чи завершили. Видалення лише через бота.",
    },
}

DOW = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "uk": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in STRINGS else "uk"
    text = STRINGS[lang].get(key) or STRINGS["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def fmt_duration(seconds: float, lang: str) -> str:
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if lang == "uk":
        if hours:
            return f"{hours} год {minutes:02d} хв"
        if minutes:
            return f"{minutes} хв"
        return f"{secs} с"
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min"
    return f"{secs} s"


def fmt_minutes(minutes: int, lang: str) -> str:
    return fmt_duration(int(minutes) * 60, lang)


def fmt_date(date_str: str, lang: str) -> str:
    year, month, day = date_str.split("-")
    return f"{day}.{month}.{year}"


def dow(lang: str, index: int) -> str:
    return DOW.get(lang, DOW["en"])[index]
