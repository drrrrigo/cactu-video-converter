"""Preserve native Windows TLS without collecting a second host OpenSSL pair."""

import sys
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info
from scripts.qt_payload_policy import windows_network_plugins

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
if sys.platform == "win32":
    binaries = windows_network_plugins(binaries)
else:
    binaries += pyside6_library_info.collect_qtnetwork_files()
