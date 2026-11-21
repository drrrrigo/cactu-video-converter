"""Map actual Qt binaries/plugins to the selected immutable source modules."""

import re
from pathlib import PurePosixPath


def qt_file_mapping(relative: str, lock: dict):
    name = PurePosixPath(relative).name
    match = re.match(r"(?:lib)?Qt6([A-Za-z0-9]+)\.(?:so|dll)", name)
    module = "Qt" + match[1] if match else None
    project = "qtbase"
    if module and ("Wayland" in module or "WlShell" in module):
        project = "qtwayland"
    elif module and "Svg" in module:
        project = "qtsvg"
    elif "/plugins/" in relative and "PySide6/" in relative:
        module = "Qt plugin: " + relative.split("/plugins/", 1)[1]
        if "wayland" in module.lower():
            project = "qtwayland"
        elif "svg" in name.lower():
            project = "qtsvg"
        elif "/imageformats/" in relative and re.match(
            r"(?:lib)?q(?:icns|tga|tiff|wbmp|webp)\.", name
        ):
            project = "qtimageformats"
    elif ("PySide6/" in relative and re.match(r"Qt\w+\.(?:abi3|pyd)", name)) or name.startswith(
        ("libpyside6", "libshiboken6")
    ):
        module = "Qt Python binding: " + name
        project = "pyside-pyside-setup"
    if not module:
        return None
    # Never map an unexpected leftover module to qtbase merely by its filename.
    if any(word in module for word in ["Pdf", "Qml", "Quick", "VirtualKeyboard"]):
        return {"module": module, "source_project": "UNRESOLVED", "review_status": "BLOCKED"}
    entry = next(x for x in lock["archives"] if x["project"] == project)
    return {
        "module": module,
        "source_project": project,
        "version": lock["version"],
        "source_commit": entry["commit"],
        "source_archive": entry["filename"],
        "source_url": entry["url"],
        "source_sha256": entry["sha256"],
        "license_option": "GPL-3.0-only for eligible module code; independent third-party terms retained",
        "packaged_notice_directory": "_internal/licenses/qt-6.11.2/" + project,
        "build_correspondence": "REVIEW_REQUIRED: wheel build configuration/third-party linkage",
    }
