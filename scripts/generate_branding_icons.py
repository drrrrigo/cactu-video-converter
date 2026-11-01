"""Render the original SVG to PNG sizes and a multi-resolution PNG-backed ICO."""

from __future__ import annotations

import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def generate(directory: Path = ROOT / "assets" / "branding") -> None:
    _app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(str(directory / "cactu-video-converter.svg"))
    if not renderer.isValid():
        raise ValueError("Invalid Cactu SVG source")
    payloads = []
    for size in SIZES:
        canvas = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        renderer.render(painter)
        painter.end()
        payload = QByteArray()
        buffer = QBuffer(payload)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not canvas.save(buffer, "PNG"):
            raise OSError("Could not render icon PNG")
        data = bytes(payload)
        (directory / f"cactu-video-converter-{size}.png").write_bytes(data)
        if size == 256:
            (directory / "cactu-video-converter.png").write_bytes(data)
        if size <= 256:
            payloads.append((size, data))
    offset = 6 + 16 * len(payloads)
    entries, images = [], []
    for size, payload in payloads:
        entries.append(
            struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(payload), offset)
        )
        images.append(payload)
        offset += len(payload)
    (directory / "cactu-video-converter.ico").write_bytes(
        struct.pack("<HHH", 0, 1, len(payloads)) + b"".join(entries + images)
    )


if __name__ == "__main__":
    generate()
