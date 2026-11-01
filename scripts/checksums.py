"""Generate strict SHA256SUMS for the three final artifacts, never a hand-written list."""

from pathlib import Path
import sys
from branding_metadata import EXECUTABLE_NAME, __version__, appimage_filename
from release_common import sha256


def expected_names():
    return (
        f"{EXECUTABLE_NAME}-Setup-{__version__}.exe",
        f"{EXECUTABLE_NAME}-Portable-{__version__}.zip",
        appimage_filename(),
    )


def generate(directory: Path) -> Path:
    rows = []
    for name in expected_names():
        file = directory / name
        if not file.is_file():
            raise RuntimeError("Required final artifact missing: " + name)
        rows.append(f"{sha256(file)}  {name}")
    target = directory / "SHA256SUMS.txt"
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
