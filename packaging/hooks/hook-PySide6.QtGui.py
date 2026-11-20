"""Use PyInstaller's pinned Qt analysis, minus two unused optional plugins."""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies
from scripts.qt_payload_policy import filter_gui_plugins

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = filter_gui_plugins(binaries)
