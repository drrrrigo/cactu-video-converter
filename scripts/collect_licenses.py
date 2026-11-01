"""Collect exact Python/wheel notices. Completeness approval is a separate gate."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from release_common import ROOT, sha256

PACKAGES = (
    "PySide6",
    "PySide6_Essentials",
    "PySide6_Addons",
    "shiboken6",
    "psutil",
    "PyInstaller",
    "pyinstaller-hooks-contrib",
    "altgraph",
    "packaging",
)


def collect(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", destination / "Cactu-GPL-3.0.txt")
    inventory = {"python": sys.version, "components": [], "redistribution_approval": False}
    for name in PACKAGES:
        dist = importlib.metadata.distribution(name)
        target = destination / name
        target.mkdir(exist_ok=True)
        copied = []
        for file in dist.files or ():
            lower = str(file).lower()
            if any(token in lower for token in ("license", "copying", "copyright")):
                source = Path(dist.locate_file(file))
                if source.is_file() and source.suffix.lower() not in {
                    ".pyc",
                    ".so",
                    ".dll",
                    ".dylib",
                    ".exe",
                }:
                    relative = Path(str(file).replace("..", "_"))
                    out = target / relative
                    out.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, out)
                    copied.append(
                        {"file": out.relative_to(destination).as_posix(), "sha256": sha256(out)}
                    )
        inventory["components"].append(
            {
                "name": name,
                "version": dist.version,
                "license_expression": dist.metadata.get("License-Expression")
                or dist.metadata.get("License", "Not declared"),
                "source": dist.metadata.get("Home-page", ""),
                "files": copied,
            }
        )
    for source in (ROOT / "licenses").rglob("*"):
        if source.is_file():
            target = destination / source.relative_to(ROOT / "licenses")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (destination / "component-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


if __name__ == "__main__":
    collect(ROOT / "build/licenses")
