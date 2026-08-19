"""PySide6 UI: main window, settings dialog, and the fullscreen break overlay."""

from PySide6.QtCore import QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import (QAction, QDesktopServices, QFont, QGuiApplication,
                           QIcon, QPainter, QPixmap)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QSpinBox, QSystemTrayIcon,
                               QToolButton, QVBoxLayout, QWidget)

import icons
import updater
import version
import winutil
from i18n import fmt_duration, t

STYLE = """
QWidget#root, QDialog { background: #0F1420; }
QLabel { color: #E8ECF4; font-family: 'Segoe UI'; font-size: 14px; }
QLabel[cls="muted"] { color: #8A94A8; font-size: 12px; }
QLabel[cls="title"] { font-size: 19px; font-weight: 600; }
QLabel[cls="section"] { color: #AEB9CE; font-size: 13px; font-weight: 600; }
QFrame[cls="card"] { background: #161D2E; border: 1px solid #232D42; border-radius: 16px; }
QPushButton {
  background: #1B2436; color: #E8ECF4; border: 1px solid #2A3550;
  border-radius: 10px; padding: 10px 14px; font-family: 'Segoe UI'; font-size: 14px;
}
QPushButton:hover { background: #232D45; }
QPushButton:disabled { color: #5A6478; }
QPushButton[cls="accent"] { background: #244; border-color: #2A6; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 4px; }
QToolButton:hover { border-color: #2A3550; background: #1B2436; }
QToolButton:checked { border-color: #4F8CFF; background: #1B2436; }
QLineEdit, QSpinBox {
  background: #141B2B; color: #E8ECF4; border: 1px solid #2A3550;
  border-radius: 8px; padding: 6px 8px; font-family: 'Segoe UI'; font-size: 13px;
}
QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
"""

STATUS_COLORS = {"ok": "#3DDC84", "starting": "#F5B942", "network": "#F5B942",
                 "conflict": "#F56262", "unauthorized": "#F56262", "no_token": "#F5B942"}


def svg_pixmap(data, size: int) -> QPixmap:
    if isinstance(data, str):
        data = data.encode("utf-8")
    renderer = QSvgRenderer(data)
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def svg_icon(data, size: int = 20) -> QIcon:
    return QIcon(svg_pixmap(data, size))


class BreakOverlay(QWidget):
    """Fullscreen, always-on-top block screen shown during breaks/limits."""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setObjectName("root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: #080B12;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(svg_pixmap(icons.LOGO_SVG, 96))
        layout.addWidget(logo)

        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color:#FFFFFF; font-family:'Segoe UI'; font-size:40px; font-weight:700;")
        layout.addWidget(self.title)

        self.countdown = QLabel()
        self.countdown.setAlignment(Qt.AlignCenter)
        self.countdown.setStyleSheet(f"color:{icons.ACCENT}; font-family:'Consolas'; font-size:88px; font-weight:700;")
        layout.addWidget(self.countdown)

        self.sub = QLabel()
        self.sub.setAlignment(Qt.AlignCenter)
        self.sub.setStyleSheet("color:#8A94A8; font-family:'Segoe UI'; font-size:18px;")
        layout.addWidget(self.sub)

    def update_view(self, reason, remaining, lang):
        titles = {"cycle": "overlay_break_title", "limit": "overlay_limit_title",
                  "manual": "overlay_manual_title"}
        self.title.setText(t(lang, titles.get(reason, "overlay_manual_title")))
        if remaining is None:
            self.countdown.setText("∞")
            self.sub.setText(t(lang, "overlay_until_tomorrow") + "\n" + t(lang, "overlay_admin_unlock"))
        else:
            total = max(0, int(remaining))
            self.countdown.setText(f"{total // 60:02d}:{total % 60:02d}")
            self.sub.setText(t(lang, "overlay_resume") + " …\n" + t(lang, "overlay_sub"))

    def show_block(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())
        self.show()
        self.raise_()
        self.activateWindow()


class SettingsDialog(QDialog):
    def __init__(self, parent, store, on_token_apply, guard=None):
        super().__init__(parent)
        self.store = store
        self.on_token_apply = on_token_apply
        self.guard = guard
        self.lang = store.get_config("app_lang", "uk")
        self.setStyleSheet(STYLE)
        self.setWindowTitle(t(self.lang, "settings_title"))
        self.setWindowIcon(svg_icon(icons.LOGO_SVG, 64))
        self.setMinimumWidth(440)
        self._build()

    def _section(self, layout, key):
        label = QLabel(t(self.lang, key))
        label.setProperty("cls", "section")
        layout.addWidget(label)

    def _hint(self, layout, key):
        label = QLabel(t(self.lang, key))
        label.setProperty("cls", "muted")
        label.setWordWrap(True)
        layout.addWidget(label)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        body.setObjectName("root")
        scroll.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)

        # --- admins ---
        self._section(root, "set_admins_label")
        self._hint(root, "set_admins_hint")
        add_row = QHBoxLayout()
        self.admin_input = QLineEdit()
        self.admin_input.setPlaceholderText("@username")
        self.admin_input.returnPressed.connect(self._add_admin)
        add_row.addWidget(self.admin_input, 1)
        btn_add = QPushButton(t(self.lang, "set_add"))
        btn_add.clicked.connect(self._add_admin)
        add_row.addWidget(btn_add)
        root.addLayout(add_row)
        self.admins_box = QVBoxLayout()
        self.admins_box.setSpacing(6)
        root.addLayout(self.admins_box)
        self._reload_admins()

        root.addSpacing(8)

        # --- daily limit ---
        self._section(root, "set_limit_label")
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(0, 1440)
        self.spin_limit.setSuffix(" " + t(self.lang, "set_min"))
        self.spin_limit.setValue(int(self.store.get_config("daily_limit_min", 0) or 0))
        self.spin_limit.valueChanged.connect(
            lambda v: self.store.set_config("daily_limit_min", int(v)))
        root.addWidget(self.spin_limit)

        # --- work / break cycle ---
        self._section(root, "set_cycle_work")
        self.spin_work = QSpinBox()
        self.spin_work.setRange(0, 600)
        self.spin_work.setSuffix(" " + t(self.lang, "set_min"))
        self.spin_work.setValue(int(self.store.get_config("work_min", 0) or 0))
        self.spin_work.valueChanged.connect(lambda v: self.store.set_config("work_min", int(v)))
        root.addWidget(self.spin_work)
        self._section(root, "set_cycle_break")
        self.spin_break = QSpinBox()
        self.spin_break.setRange(0, 600)
        self.spin_break.setSuffix(" " + t(self.lang, "set_min"))
        self.spin_break.setValue(int(self.store.get_config("break_min", 0) or 0))
        self.spin_break.valueChanged.connect(lambda v: self.store.set_config("break_min", int(v)))
        root.addWidget(self.spin_break)
        self._hint(root, "set_cycle_hint")
        self._hint(root, "set_metric_hint")

        # --- warning before a block ---
        self._section(root, "set_warn_label")
        self.spin_warn = QSpinBox()
        self.spin_warn.setRange(0, 60)
        self.spin_warn.setSuffix(" " + t(self.lang, "set_min"))
        self.spin_warn.setValue(int(self.store.get_config("warn_min", 5) or 0))
        self.spin_warn.valueChanged.connect(lambda v: self.store.set_config("warn_min", int(v)))
        root.addWidget(self.spin_warn)

        root.addSpacing(8)

        # --- blocked sites ---
        self._section(root, "set_block_label")
        self._hint(root, "set_block_hint")
        block_row = QHBoxLayout()
        self.block_input = QLineEdit()
        self.block_input.setPlaceholderText("youtube.com/shorts")
        self.block_input.returnPressed.connect(self._add_block)
        block_row.addWidget(self.block_input, 1)
        btn_block = QPushButton(t(self.lang, "set_add"))
        btn_block.clicked.connect(self._add_block)
        block_row.addWidget(btn_block)
        root.addLayout(block_row)
        self.blocks_box = QVBoxLayout()
        self.blocks_box.setSpacing(6)
        root.addLayout(self.blocks_box)
        self._reload_blocks()

        root.addSpacing(8)

        # --- protection PIN ---
        self._section(root, "set_pin_label")
        self._hint(root, "set_pin_hint")
        pin_row = QHBoxLayout()
        self.pin_status = QLabel()
        self.pin_status.setProperty("cls", "muted")
        pin_row.addWidget(self.pin_status, 1)
        self.btn_pin_set = QPushButton(t(self.lang, "set_pin_set_btn"))
        self.btn_pin_set.clicked.connect(self._set_pin)
        pin_row.addWidget(self.btn_pin_set)
        self.btn_pin_clear = QPushButton(t(self.lang, "set_pin_clear_btn"))
        self.btn_pin_clear.clicked.connect(self._clear_pin)
        pin_row.addWidget(self.btn_pin_clear)
        root.addLayout(pin_row)
        self._refresh_pin()

        # --- bot PIN (admin sign-in) ---
        self._section(root, "set_botpin_label")
        self._hint(root, "set_botpin_hint")
        botpin_row = QHBoxLayout()
        self.botpin_status = QLabel()
        self.botpin_status.setProperty("cls", "muted")
        botpin_row.addWidget(self.botpin_status, 1)
        self.btn_botpin_set = QPushButton(t(self.lang, "set_pin_set_btn"))
        self.btn_botpin_set.clicked.connect(self._set_bot_pin)
        botpin_row.addWidget(self.btn_botpin_set)
        self.btn_botpin_clear = QPushButton(t(self.lang, "set_pin_clear_btn"))
        self.btn_botpin_clear.clicked.connect(self._clear_bot_pin)
        botpin_row.addWidget(self.btn_botpin_clear)
        root.addLayout(botpin_row)
        self._refresh_bot_pin()

        root.addSpacing(8)

        # --- auto-update ---
        self._section(root, "set_update_label")
        self._hint(root, "set_update_hint")
        upd_row = QHBoxLayout()
        self.repo_input = QLineEdit(self.store.get_config("update_repo", "") or "")
        self.repo_input.setPlaceholderText("owner/repo")
        self.repo_input.editingFinished.connect(self._save_repo)
        upd_row.addWidget(self.repo_input, 1)
        self.btn_update = QPushButton(t(self.lang, "set_update_check"))
        self.btn_update.clicked.connect(self._check_update)
        upd_row.addWidget(self.btn_update)
        root.addLayout(upd_row)
        # prominent one-click update button (checks + downloads + installs)
        self.btn_do_update = QPushButton(t(self.lang, "set_update_now"))
        self.btn_do_update.setProperty("cls", "accent")
        self.btn_do_update.setCursor(Qt.PointingHandCursor)
        self.btn_do_update.clicked.connect(self._check_update)
        root.addWidget(self.btn_do_update)
        self.update_status = QLabel(t(self.lang, "set_version", value=version.APP_VERSION))
        self.update_status.setProperty("cls", "muted")
        root.addWidget(self.update_status)

        root.addSpacing(8)

        # --- keep-running watchdog ---
        self._section(root, "set_guard_label")
        self.chk_guard = QCheckBox(t(self.lang, "set_guard_label"))
        self.chk_guard.setChecked(bool(self.store.get_config("watchdog", True)))
        self.chk_guard.toggled.connect(self._toggle_guard)
        root.addWidget(self.chk_guard)
        self._hint(root, "set_guard_hint")

        root.addSpacing(8)

        # --- token ---
        self._section(root, "set_token_label")
        self._hint(root, "set_token_hint")
        token_row = QHBoxLayout()
        self.token_input = QLineEdit(self.store.get_config("token", "") or "")
        token_row.addWidget(self.token_input, 1)
        btn_token = QPushButton(t(self.lang, "set_apply"))
        btn_token.clicked.connect(self._apply_token)
        token_row.addWidget(btn_token)
        root.addLayout(token_row)
        self.saved_label = QLabel("")
        self.saved_label.setStyleSheet(f"color:{icons.ACCENT2}; font-size:12px;")
        root.addWidget(self.saved_label)

        root.addSpacing(8)

        # --- proxy (for PCs where Telegram is blocked / behind a proxy) ---
        self._section(root, "set_proxy_label")
        self._hint(root, "set_proxy_hint")
        self.proxy_input = QLineEdit(self.store.get_config("proxy", "") or "")
        self.proxy_input.setPlaceholderText("http://host:port")
        self.proxy_input.editingFinished.connect(self._save_proxy)
        root.addWidget(self.proxy_input)

        root.addStretch(1)
        btn_close = QPushButton(t(self.lang, "set_close"))
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close)

    def _reload_admins(self):
        while self.admins_box.count():
            item = self.admins_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        admins = self.store.get_admins()
        if not admins:
            empty = QLabel(t(self.lang, "set_none"))
            empty.setProperty("cls", "muted")
            self.admins_box.addWidget(empty)
            return
        for name in admins:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel("@" + name)
            layout.addWidget(label, 1)
            btn = QToolButton()
            btn.setText("✕")
            btn.clicked.connect(lambda _=False, n=name: self._remove_admin(n))
            layout.addWidget(btn)
            self.admins_box.addWidget(row)

    def _add_admin(self):
        name = self.admin_input.text()
        if name.strip():
            self.store.add_admin(name)
            self.admin_input.clear()
            self._reload_admins()

    def _remove_admin(self, name):
        self.store.remove_admin(name)
        self._reload_admins()

    def _apply_token(self):
        token = self.token_input.text().strip()
        if token:
            self.on_token_apply(token)
            self.saved_label.setText(t(self.lang, "set_saved"))
            QTimer.singleShot(1500, lambda: self.saved_label.setText(""))

    def _save_proxy(self):
        proxy = self.proxy_input.text().strip()
        self.store.set_config("proxy", proxy)
        # apply live so the bot and updater pick it up on the next request
        import os
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(key, None)
        if proxy:
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy

    def _reload_blocks(self):
        while self.blocks_box.count():
            item = self.blocks_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        blocks = self.store.get_blocklist()
        if not blocks:
            empty = QLabel(t(self.lang, "blocklist_empty"))
            empty.setProperty("cls", "muted")
            self.blocks_box.addWidget(empty)
            return
        for pattern in blocks:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(pattern)
            layout.addWidget(label, 1)
            btn = QToolButton()
            btn.setText("✕")
            btn.clicked.connect(lambda _=False, p=pattern: self._remove_block(p))
            layout.addWidget(btn)
            self.blocks_box.addWidget(row)

    def _add_block(self):
        pattern = self.block_input.text().strip()
        if pattern:
            self.store.add_block(pattern)
            self.block_input.clear()
            self._reload_blocks()

    def _remove_block(self, pattern):
        self.store.remove_block(pattern)
        self._reload_blocks()

    def _refresh_pin(self):
        on = self.store.has_pin()
        self.pin_status.setText(t(self.lang, "set_pin_on" if on else "set_pin_off"))
        self.btn_pin_clear.setEnabled(on)

    def _set_pin(self):
        pin, ok = QInputDialog.getText(self, "TimeApp", t(self.lang, "pin_set_prompt"),
                                       QLineEdit.EchoMode.Password)
        if not ok:
            return
        if pin.isdigit() and 4 <= len(pin) <= 8:
            self.store.set_pin(pin)
            self._refresh_pin()
        else:
            QMessageBox.warning(self, "TimeApp", t(self.lang, "cmd_pin_bad").replace("<code>", "").replace("</code>", ""))

    def _clear_pin(self):
        self.store.clear_pin()
        self._refresh_pin()

    def _refresh_bot_pin(self):
        on = self.store.has_bot_pin()
        self.botpin_status.setText(t(self.lang, "set_pin_on" if on else "set_pin_off"))
        self.btn_botpin_clear.setEnabled(on)

    def _set_bot_pin(self):
        pin, ok = QInputDialog.getText(self, "TimeApp", t(self.lang, "pin_set_prompt"),
                                       QLineEdit.EchoMode.Password)
        if not ok:
            return
        if pin.isdigit() and 4 <= len(pin) <= 8:
            self.store.set_bot_pin(pin)
            self._refresh_bot_pin()
        else:
            QMessageBox.warning(self, "TimeApp", t(self.lang, "cmd_botpin_bad")
                                .replace("<code>", "").replace("</code>", ""))

    def _clear_bot_pin(self):
        self.store.clear_bot_pin()
        self._refresh_bot_pin()

    def _toggle_guard(self, on):
        if self.guard:
            self.guard.set_enabled(on)
        else:
            self.store.set_config("watchdog", bool(on))

    def _save_repo(self):
        text = self.repo_input.text().strip()
        repo = updater.normalize_repo(text)
        if text and not repo:
            self.update_status.setText(t(self.lang, "set_update_bad_repo"))
            return
        self.store.set_config("update_repo", repo)
        self.repo_input.setText(repo)

    def _update_buttons(self, enabled):
        for name in ("btn_update", "btn_do_update"):
            btn = getattr(self, name, None)
            if btn:
                btn.setEnabled(enabled)

    def _check_update(self):
        self._save_repo()
        repo = self.store.get_config("update_repo", "") or ""
        if not repo:
            self.update_status.setText(t(self.lang, "set_update_bad_repo"))
            return
        self._update_buttons(False)
        self.update_status.setText(t(self.lang, "cmd_update_checking")
                                   .replace("\U0001F504 ", ""))
        QApplication.processEvents()
        try:
            info = updater.check(repo)
        except Exception as exc:
            self.update_status.setText(t(self.lang, "cmd_update_failed", value=str(exc)[:80]))
            self._update_buttons(True)
            return
        self._update_buttons(True)
        if not info:
            self.update_status.setText(t(self.lang, "set_update_none"))
            return
        self.update_status.setText(t(self.lang, "set_update_found", value=info["version"]))
        if QMessageBox.question(self, "TimeApp",
                                t(self.lang, "set_update_found", value=info["version"]) + "\n\n" +
                                t(self.lang, "cmd_update_installing").replace("⬇️ ", "")
                                ) == QMessageBox.StandardButton.Yes:
            self._install_update(info)

    def _install_update(self, info):
        try:
            path = updater.download(info["url"])
            if updater.apply_update(path):
                if self.guard:
                    self.guard.authorize_exit()
                QApplication.instance().quit()
            else:
                self.update_status.setText(t(self.lang, "cmd_update_failed", value="not frozen"))
        except Exception as exc:
            self.update_status.setText(t(self.lang, "cmd_update_failed", value=str(exc)[:80]))


class MainWindow(QWidget):
    def __init__(self, store, bot, blocking_event, blocker, policy, webguard=None, guard=None):
        super().__init__()
        self.store = store
        self.bot = bot
        self.blocking_event = blocking_event
        self.blocker = blocker
        self.policy = policy
        self.webguard = webguard
        self.guard = guard
        self._guard_counter = 0
        self.lang = store.get_config("app_lang", "uk")
        self._tray_hint_shown = False
        self._blocker_started = False
        from render import render_today_card
        self._card_renderer = render_today_card
        self._build_ui()
        self._build_tray()
        self.retranslate()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    # -- UI construction -------------------------------------------------
    def _build_ui(self):
        self.setObjectName("root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(STYLE)
        self.setWindowTitle("TimeApp")
        self.setWindowIcon(svg_icon(icons.LOGO_SVG, 64))
        self.setFixedSize(440, 580)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(13)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(svg_pixmap(icons.LOGO_SVG, 38))
        header.addWidget(logo)
        title = QLabel("TimeApp")
        title.setProperty("cls", "title")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_settings = QToolButton()
        self.btn_settings.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_settings.setText("⚙")
        self.btn_settings.setStyleSheet("QToolButton{font-size:20px;color:#AEB9CE;padding:2px 6px;}")
        self.btn_settings.clicked.connect(self._open_settings)
        header.addWidget(self.btn_settings)
        self.btn_flag_en = QToolButton()
        self.btn_flag_en.setIcon(svg_icon(icons.FLAG_GB, 24))
        self.btn_flag_en.setCheckable(True)
        self.btn_flag_en.clicked.connect(lambda: self.set_lang("en"))
        self.btn_flag_uk = QToolButton()
        self.btn_flag_uk.setIcon(svg_icon(icons.FLAG_UA, 24))
        self.btn_flag_uk.setCheckable(True)
        self.btn_flag_uk.clicked.connect(lambda: self.set_lang("uk"))
        header.addWidget(self.btn_flag_en)
        header.addWidget(self.btn_flag_uk)
        root.addLayout(header)

        self.steps_label = QLabel()
        self.steps_label.setProperty("cls", "muted")
        self.steps_label.setWordWrap(True)
        root.addWidget(self.steps_label)

        # pairing code card
        code_card = QFrame()
        code_card.setProperty("cls", "card")
        code_layout = QVBoxLayout(code_card)
        code_layout.setContentsMargins(18, 14, 18, 14)
        code_layout.setSpacing(6)
        self.code_title = QLabel()
        self.code_title.setProperty("cls", "muted")
        code_layout.addWidget(self.code_title)
        code_row = QHBoxLayout()
        self.code_label = QLabel("--- ---")
        font = QFont("Consolas", 30, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        self.code_label.setFont(font)
        self.code_label.setStyleSheet("color:#FFFFFF;")
        code_row.addWidget(self.code_label)
        code_row.addStretch(1)
        self.copied_label = QLabel("")
        self.copied_label.setStyleSheet(f"color:{icons.ACCENT2}; font-size:12px;")
        code_row.addWidget(self.copied_label)
        self.btn_copy = QToolButton()
        self.btn_copy.setIcon(svg_icon(icons.svg("copy"), 22))
        self.btn_copy.clicked.connect(self._copy_code)
        code_row.addWidget(self.btn_copy)
        code_layout.addLayout(code_row)
        valid_row = QHBoxLayout()
        cal = QLabel()
        cal.setPixmap(svg_pixmap(icons.svg("calendar", icons.MUTED), 14))
        valid_row.addWidget(cal)
        self.valid_label = QLabel()
        self.valid_label.setProperty("cls", "muted")
        valid_row.addWidget(self.valid_label)
        valid_row.addStretch(1)
        code_layout.addLayout(valid_row)
        root.addWidget(code_card)

        # today card
        today_card = QFrame()
        today_card.setProperty("cls", "card")
        today_layout = QVBoxLayout(today_card)
        today_layout.setContentsMargins(18, 14, 18, 14)
        today_layout.setSpacing(6)
        today_head = QHBoxLayout()
        clock = QLabel()
        clock.setPixmap(svg_pixmap(icons.svg("clock", icons.MUTED), 16))
        today_head.addWidget(clock)
        self.today_title = QLabel()
        self.today_title.setProperty("cls", "muted")
        today_head.addWidget(self.today_title)
        today_head.addStretch(1)
        today_layout.addLayout(today_head)
        self.today_value = QLabel("0")
        self.today_value.setStyleSheet(
            f"color:{icons.ACCENT}; font-family:'Segoe UI'; font-size:27px; font-weight:700;")
        today_layout.addWidget(self.today_value)
        root.addWidget(today_card)

        # bot status
        status_row = QHBoxLayout()
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        status_row.addWidget(self.status_dot)
        self.status_label = QLabel()
        self.status_label.setProperty("cls", "muted")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        root.addLayout(status_row)

        self.btn_bot = QPushButton()
        self.btn_bot.setIcon(svg_icon(icons.svg("send"), 18))
        self.btn_bot.setCursor(Qt.PointingHandCursor)
        self.btn_bot.clicked.connect(self._open_bot)
        root.addWidget(self.btn_bot)

        autostart_row = QHBoxLayout()
        check = QLabel()
        check.setPixmap(svg_pixmap(icons.svg("check", "#3DDC84"), 16))
        autostart_row.addWidget(check)
        self.autostart_label = QLabel()
        self.autostart_label.setProperty("cls", "muted")
        autostart_row.addWidget(self.autostart_label)
        autostart_row.addStretch(1)
        self.btn_manage = QPushButton()
        self.btn_manage.clicked.connect(self._open_settings)
        autostart_row.addWidget(self.btn_manage)
        root.addLayout(autostart_row)

        root.addStretch(1)
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def _build_tray(self):
        self.tray = QSystemTrayIcon(svg_icon(icons.LOGO_SVG, 32), self)
        self.tray.setToolTip("TimeApp")
        self.tray_menu = QMenu()
        self.act_open = QAction(self.tray_menu)
        self.act_open.triggered.connect(self._show_window)
        self.act_quit = QAction(self.tray_menu)
        self.act_quit.triggered.connect(self._request_quit)
        self.tray_menu.addAction(self.act_open)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.act_quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self.overlay = BreakOverlay()

    # -- language --------------------------------------------------------
    def set_lang(self, lang):
        self.lang = lang
        self.store.set_config("app_lang", lang)
        self.retranslate()
        self._tick()

    def retranslate(self):
        lang = self.lang
        self.btn_flag_en.setChecked(lang == "en")
        self.btn_flag_uk.setChecked(lang == "uk")
        self.steps_label.setText(t(lang, "steps"))
        self.code_title.setText(t(lang, "your_code"))
        self.today_title.setText(t(lang, "today_at_pc"))
        self.btn_bot.setText("  " + t(lang, "open_bot"))
        self.autostart_label.setText(t(lang, "autostart_on"))
        self.btn_manage.setText(t(lang, "manage"))
        self.act_open.setText(t(lang, "tray_open"))
        self.act_quit.setText(t(lang, "tray_quit"))

    # -- periodic tick (stats + policy enforcement) ----------------------
    def _tick(self):
        code, expires = self.store.get_valid_code()
        self.code_label.setText(f"{code[:3]} {code[3:]}")
        self.valid_label.setText(t(self.lang, "valid_until", date=expires.strftime("%d.%m.%Y")))
        active, _screen = self.store.day_stats()
        self.today_value.setText(fmt_duration(active, self.lang))

        status = self.bot.status
        self.status_dot.setStyleSheet(
            f"background:{STATUS_COLORS.get(status, '#F5B942')}; border-radius:5px;")
        self.status_label.setText(t(self.lang, f"status_{status}"))
        # surface the real reason behind a failed connection for diagnosis
        self.status_label.setToolTip(getattr(self.bot, "last_error", "") if status == "network" else "")
        self.btn_bot.setEnabled(bool(self.bot.username))
        if self.bot.username:
            self.btn_bot.setToolTip(f"https://t.me/{self.bot.username}")

        self._enforce()
        self._guard_web()
        self._guard_counter += 1
        if self.guard and self._guard_counter >= 20:  # ~20s: keep the watchdog alive
            self._guard_counter = 0
            self.guard.ensure()

    def _enforce(self):
        action = self.policy.tick()
        if action.get("block"):
            if not self._blocker_started:
                self.blocker.start()
                self._blocker_started = True
            self.blocker.block()
            self.overlay.update_view(action.get("reason"), action.get("remaining"), self.lang)
            if not self.overlay.isVisible():
                self.overlay.show_block()
            else:
                self.overlay.raise_()
        else:
            self.blocker.unblock()
            if self.overlay.isVisible():
                self.overlay.hide()
            warn = action.get("warn")
            if warn:
                title = "warn_limit_title" if warn.get("kind") == "limit" else "warn_cycle_title"
                body = t(self.lang, "warn_body", value=fmt_duration(warn.get("seconds", 0), self.lang))
                self.tray.showMessage(t(self.lang, title), body,
                                      QSystemTrayIcon.Information, 6000)

    def _guard_web(self):
        if not self.webguard:
            return
        try:
            matched = self.webguard.tick()
        except Exception:
            matched = None
        if matched:
            self.tray.showMessage(t(self.lang, "web_blocked_title"),
                                  t(self.lang, "web_blocked_body", value=matched),
                                  QSystemTrayIcon.Information, 4000)

    # -- actions ---------------------------------------------------------
    def _copy_code(self):
        code, _ = self.store.get_valid_code()
        QApplication.clipboard().setText(code)
        self.copied_label.setText(t(self.lang, "copied"))
        QTimer.singleShot(1500, lambda: self.copied_label.setText(""))

    def _open_bot(self):
        if self.bot.username:
            QDesktopServices.openUrl(QUrl(f"https://t.me/{self.bot.username}"))

    def _ask_pin(self, prompt_key) -> bool:
        if not self.store.has_pin():
            return True
        text, ok = QInputDialog.getText(self, "TimeApp", t(self.lang, prompt_key),
                                        QLineEdit.EchoMode.Password)
        if not ok:
            return False
        if self.store.check_pin(text):
            return True
        QMessageBox.warning(self, "TimeApp", t(self.lang, "pin_wrong"))
        return False

    def _open_settings(self):
        if not self._ask_pin("pin_prompt_settings"):
            return
        dialog = SettingsDialog(self, self.store, self.restart_bot, self.guard)
        dialog.exec()

    def _request_quit(self):
        if not self._ask_pin("pin_prompt_quit"):
            return
        if self.guard:
            self.guard.authorize_exit()  # tell the watchdog this exit is allowed
        QApplication.instance().quit()

    def restart_bot(self, token):
        self.store.set_config("token", token)
        try:
            self.bot.stop()
        except Exception:
            pass
        from bot import TelegramBot
        self.bot = TelegramBot(self.store, token, card_renderer=self._card_renderer)
        self.bot.start()
        self.policy.set_notifier(self.bot.notify)

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.showMessage(t(self.lang, "tray_title"), t(self.lang, "tray_body"),
                                  QSystemTrayIcon.Information, 4000)
