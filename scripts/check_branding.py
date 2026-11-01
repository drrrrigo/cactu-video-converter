"""Portable branding smoke check; does not claim to build native release artifacts."""

from __future__ import annotations

import struct
import tempfile
import tomllib
from pathlib import Path

from branding_metadata import (
    ASSETS,
    EXECUTABLE_NAME,
    PRODUCT_NAME,
    PRODUCT_SLUG,
    ROOT,
    __version__,
    appimage_filename,
    desktop_entry,
    write_windows_metadata,
)


def check() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["name"] == PRODUCT_SLUG
    assert PRODUCT_SLUG in project["project"]["scripts"]
    assert (
        project["tool"]["setuptools"]["dynamic"]["version"]["attr"]
        == "video_converter.__package_version__"
    )
    assert (ROOT / "packaging/linux" / f"{PRODUCT_SLUG}.desktop").read_text() == desktop_entry()
    assert f'/usr/bin/{EXECUTABLE_NAME}"' in (ROOT / "packaging/linux/AppRun").read_text()
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        data = (ASSETS / f"{PRODUCT_SLUG}-{size}.png").read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == (size, size)
    icon = (ASSETS / f"{PRODUCT_SLUG}.ico").read_bytes()
    assert struct.unpack("<HHH", icon[:6]) == (0, 1, 7)
    for i in range(7):
        width, height, _, _, planes, depth, length, offset = struct.unpack(
            "<BBBBHHII", icon[6 + i * 16 : 22 + i * 16]
        )
        assert width == height and planes == 1 and depth == 32
        assert icon[offset : offset + length][:8] == b"\x89PNG\r\n\x1a\n"
    with tempfile.TemporaryDirectory() as temporary:
        version, include = write_windows_metadata(Path(temporary))
        compile(version.read_text(), str(version), "eval")
        assert PRODUCT_NAME in version.read_text()
        assert f"{EXECUTABLE_NAME}.exe" in version.read_text()
        assert 'LegacyAppId "Video Converter"' in include.read_text()
        assert f'AppVersion "{__version__}"' in include.read_text()
        assert "CompanyName" not in version.read_text()
    installer = (ROOT / "packaging/windows/CactuVideoConverter.iss").read_text()
    for text in (
        "AppId={#LegacyAppId}",
        "UsePreviousAppDir=yes",
        "SetupIconFile=",
        "UninstallDisplayIcon=",
        "OutputBaseFilename={#ExecutableName}-Setup-{#AppVersion}",
    ):
        assert text in installer
    spec = (ROOT / "packaging/video_converter.spec").read_text()
    assert "name=EXECUTABLE_NAME" in spec and '"assets/branding"' in spec
    assert "version=str(version_file)" in spec and "cactu-video-converter.ico" in spec
    assert appimage_filename() == f"CactuVideoConverter-{__version__}-x86_64.AppImage"
    print(f"{PRODUCT_NAME} {__version__}: Windows/Linux metadata, launcher and icon payloads OK")


if __name__ == "__main__":
    check()
