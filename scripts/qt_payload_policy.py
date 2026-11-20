"""Remove only optional Qt plugins that introduce unused document/QML engines."""

from pathlib import Path

# Cactu uses QWidget controls and PNG/ICO/SVG branding, not QML or PDF rendering.
# Keep desktop platform plugins, native input methods, styles and image codecs.
EXCLUDED_PLUGIN_STEMS = {"qpdf", "qtvirtualkeyboardplugin"}


def filter_gui_plugins(binaries):
    kept = []
    for source, destination in binaries:
        name = Path(source).stem.removeprefix("lib")
        if name not in EXCLUDED_PLUGIN_STEMS:
            kept.append((source, destination))
    return kept


def windows_network_plugins(binaries):
    # Qt's documented native Windows TLS backend avoids unrelated host OpenSSL DLLs.
    if not any(Path(source).name.lower() == "qschannelbackend.dll" for source, _ in binaries):
        raise RuntimeError("Native Windows Qt Schannel TLS plugin is required")
    return [
        (source, destination)
        for source, destination in binaries
        if Path(source).name.lower() != "qopensslbackend.dll"
    ]
