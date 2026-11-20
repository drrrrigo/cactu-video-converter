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
