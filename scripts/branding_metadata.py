"""Derive native packaging metadata from the application's product/version source."""

from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from video_converter import __version__  # noqa: E402
from video_converter.product import (  # noqa: E402
    EXECUTABLE_NAME,
    LEGACY_INSTALLER_APP_ID,
    PRODUCT_DESCRIPTION,
    PRODUCT_NAME,
    PRODUCT_SLUG,
)

ASSETS = ROOT / "assets" / "branding"


def desktop_entry() -> str:
    return (
        "[Desktop Entry]\nType=Application\n"
        f"Name={PRODUCT_NAME}\nComment={PRODUCT_DESCRIPTION}\n"
        f"Exec={EXECUTABLE_NAME}\nIcon={PRODUCT_SLUG}\n"
        "Terminal=false\nCategories=AudioVideo;Video;\n"
    )


def write_windows_metadata(destination: Path) -> tuple[Path, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?", __version__)
    if not match:
        raise ValueError("Unsupported release version")
    version = tuple(int(part or 0) for part in match.groups())
    strings = {
        "ProductName": PRODUCT_NAME,
        "FileDescription": PRODUCT_NAME,
        "InternalName": EXECUTABLE_NAME,
        "OriginalFilename": f"{EXECUTABLE_NAME}.exe",
        "ProductVersion": __version__,
        "FileVersion": __version__,
    }
    version_file = destination / "windows-version.txt"
    version_file.write_text(
        "VSVersionInfo(\n"
        f" ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, "
        "mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),\n"
        " kids=[StringFileInfo([StringTable('040904B0', [\n"
        + ",\n".join(f"  StringStruct({key!r}, {value!r})" for key, value in strings.items())
        + "])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n",
        encoding="utf-8",
    )
    include = destination / "windows-branding.iss"
    include.write_text(
        "\n".join(
            f'#define {key} "{value}"'
            for key, value in {
                "ProductName": PRODUCT_NAME,
                "AppVersion": __version__,
                "ExecutableName": EXECUTABLE_NAME,
                "LegacyAppId": LEGACY_INSTALLER_APP_ID,
                "NumericVersion": ".".join(map(str, version)),
            }.items()
        )
        + "\n",
        encoding="utf-8",
    )
    return version_file, include


def appimage_filename() -> str:
    return f"{EXECUTABLE_NAME}-{__version__}-x86_64.AppImage"


if __name__ == "__main__":
    write_windows_metadata(ROOT / "build" / "branding")
