"""Renders the app logo SVG into build/app.ico for the exe icon."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

import icons

app = QGuiApplication([])
renderer = QSvgRenderer(icons.LOGO_SVG.encode("utf-8"))
base = Path(__file__).resolve().parent

image = QImage(256, 256, QImage.Format_ARGB32)
image.fill(Qt.transparent)
painter = QPainter(image)
renderer.render(painter, QRectF(0, 0, 256, 256))
painter.end()
png_path = base / "app_256.png"
image.save(str(png_path))

from PIL import Image

Image.open(png_path).save(
    base / "app.ico",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("icon ok:", base / "app.ico")
