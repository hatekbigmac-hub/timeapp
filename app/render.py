"""Renders the daily stat card (SVG logo + painted text) into PNG bytes.

Uses only QImage/QPainter, which are safe to use from the bot's worker thread
as long as a Q(Gui)Application exists in the process.
"""

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from PySide6.QtSvg import QSvgRenderer

import icons
from i18n import fmt_date, fmt_duration, t

WIDTH, HEIGHT = 900, 440


def _font(pixel_size: int, weight=QFont.Weight.Normal) -> QFont:
    font = QFont("Segoe UI")
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def render_today_card(day: str, active: float, screen: float, lang: str,
                      bot_name: str = "") -> bytes:
    img = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    try:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # card background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, WIDTH, HEIGHT), 28, 28)
        grad = QLinearGradient(0, 0, WIDTH, HEIGHT)
        grad.setColorAt(0, QColor("#161D2E"))
        grad.setColorAt(1, QColor("#0D1220"))
        painter.fillPath(path, QBrush(grad))
        painter.setPen(QPen(QColor(255, 255, 255, 26), 2))
        painter.drawPath(path)

        # logo
        QSvgRenderer(icons.LOGO_SVG.encode("utf-8")).render(painter, QRectF(48, 48, 84, 84))

        # title + date
        painter.setPen(QColor("#AEB9CE"))
        painter.setFont(_font(27, QFont.Weight.DemiBold))
        painter.drawText(QRectF(156, 54, 660, 40), Qt.AlignLeft | Qt.AlignVCenter, t(lang, "card_title"))
        painter.setPen(QColor("#66738C"))
        painter.setFont(_font(20))
        painter.drawText(QRectF(156, 96, 660, 32), Qt.AlignLeft | Qt.AlignVCenter, fmt_date(day, lang))

        # big active time
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(_font(64, QFont.Weight.Bold))
        painter.drawText(QRectF(48, 178, WIDTH - 96, 90), Qt.AlignLeft | Qt.AlignVCenter,
                         fmt_duration(active, lang))
        painter.setPen(QColor("#8A94A8"))
        painter.setFont(_font(18))
        painter.drawText(QRectF(48, 274, WIDTH - 96, 28), Qt.AlignLeft | Qt.AlignVCenter,
                         t(lang, "card_active"))

        # progress bar: active as a share of screen time
        bar = QRectF(48, 330, WIDTH - 96, 14)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(bar, 7, 7)
        painter.fillPath(bar_path, QColor(255, 255, 255, 26))
        fraction = 0.0 if screen <= 0 else max(0.0, min(1.0, active / screen))
        if fraction > 0:
            fill = QRectF(bar.x(), bar.y(), max(14.0, bar.width() * fraction), bar.height())
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill, 7, 7)
            fill_grad = QLinearGradient(fill.topLeft(), fill.topRight())
            fill_grad.setColorAt(0, QColor(icons.ACCENT))
            fill_grad.setColorAt(1, QColor(icons.ACCENT2))
            painter.fillPath(fill_path, QBrush(fill_grad))

        # legend
        painter.setBrush(QColor(icons.ACCENT))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(48, 366, 10, 10))
        painter.setPen(QColor("#C6CFE0"))
        painter.setFont(_font(16))
        painter.drawText(QRectF(66, 358, 420, 26), Qt.AlignLeft | Qt.AlignVCenter,
                         f"{t(lang, 'card_active')}: {fmt_duration(active, lang)}")
        painter.setPen(QColor("#8A94A8"))
        painter.drawText(QRectF(430, 358, 422, 26), Qt.AlignRight | Qt.AlignVCenter,
                         f"{t(lang, 'card_screen')}: {fmt_duration(screen, lang)}")

        # footer
        painter.setPen(QColor("#55607A"))
        painter.setFont(_font(15))
        painter.drawText(QRectF(48, 398, WIDTH - 96, 24), Qt.AlignLeft | Qt.AlignVCenter, "TimeApp")
        if bot_name:
            painter.drawText(QRectF(48, 398, WIDTH - 96, 24), Qt.AlignRight | Qt.AlignVCenter,
                             f"@{bot_name}")
    finally:
        painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data
