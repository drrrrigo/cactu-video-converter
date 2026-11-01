"""Locate the original icon in source, wheel and PyInstaller layouts."""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path
from PySide6.QtGui import QIcon
from video_converter.product import PRODUCT_SLUG


def branding_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "branding"
    source = Path(__file__).resolve().parents[3] / "assets" / "branding"
    if source.is_dir():
        return source
    return Path(sysconfig.get_path("data")) / "share" / PRODUCT_SLUG / "branding"


def application_icon() -> QIcon:
    return QIcon(str(branding_directory() / f"{PRODUCT_SLUG}.svg"))


def notices_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "THIRD_PARTY_NOTICES.md"
    source = Path(__file__).resolve().parents[3] / "THIRD_PARTY_NOTICES.md"
    if source.is_file():
        return source
    return Path(sysconfig.get_path("data")) / "share" / PRODUCT_SLUG / "THIRD_PARTY_NOTICES.md"


def about_dialog(runtime, parent=None):
    from PySide6.QtWidgets import QMessageBox
    from video_converter import __version__
    from video_converter.product import PRODUCT_NAME, PRODUCT_DESCRIPTION
    from video_converter.product import RELEASE_CHANNEL, REPOSITORY_URL, ISSUES_URL
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    box = QMessageBox(parent)
    box.setWindowTitle(f"About {PRODUCT_NAME}")
    box.setWindowIcon(application_icon())
    box.setIconPixmap(application_icon().pixmap(64, 64))
    box.setText(f"{PRODUCT_NAME} {__version__}\n{RELEASE_CHANNEL}\n{runtime.ffmpeg_version}\n{runtime.ffprobe_version}")
    box.setInformativeText(f"{PRODUCT_DESCRIPTION}.\nFFmpeg, Qt and other libraries retain their own licenses. "
                           "Web Compatibility / Kosmi is an independent compatibility preset.")
    for label,url in (("GitHub",REPOSITORY_URL),("Report Issue",ISSUES_URL)):
        button=box.addButton(label,QMessageBox.ButtonRole.ActionRole)
        button.clicked.connect(lambda checked=False,target=url:QDesktopServices.openUrl(QUrl(target)))
    licenses=box.addButton("Licenses",QMessageBox.ButtonRole.ActionRole)
    licenses.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(notices_path()))))
    return box


def settings_dialog(runtime, parent=None):
    """A grid keeps the application tools readable on narrow HiDPI desktops."""
    from PySide6.QtWidgets import (
        QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    )
    from video_converter import __version__
    from video_converter.product import PRODUCT_NAME
    box = QDialog(parent)
    box.setWindowTitle(f"{PRODUCT_NAME} — Settings")
    box.setWindowIcon(application_icon())
    box.selected_action = None
    layout = QVBoxLayout(box)
    heading = QHBoxLayout()
    icon = QLabel()
    icon.setPixmap(application_icon().pixmap(48, 48))
    heading.addWidget(icon)
    title = QLabel(f"{PRODUCT_NAME}\nVersion {__version__} · Public Beta")
    title.setWordWrap(True)
    heading.addWidget(title, 1)
    layout.addLayout(heading)
    versions = QLabel(f"{runtime.ffmpeg_version}\n{runtime.ffprobe_version}")
    versions.setWordWrap(True)
    layout.addWidget(versions)
    actions = QGridLayout()
    def choose(action):
        box.selected_action = action
        box.accept()
    for index, (key, label) in enumerate((
        ("diagnostics_general", "Diagnostics"), ("issue", "Report Issue"),
        ("hardware", "Hardware Acceleration"),
        ("logs", "Open Logs"), ("diagnostics", "Hardware Details"),
        ("redetect", "Re-detect Hardware"), ("notices", "Third-party Licenses"),
        ("reset", "Reset Settings"), ("about", "About"),
    )):
        button = QPushButton(label)
        button.clicked.connect(lambda checked=False, action=key: choose(action))
        if key == "reset":
            button.setObjectName("danger")
        actions.addWidget(button, index // 2, index % 2)
    layout.addLayout(actions)
    close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    close.rejected.connect(box.reject)
    layout.addWidget(close)
    return box
