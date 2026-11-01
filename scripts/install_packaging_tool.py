"""Build-time-only native packager acquisition with fixed archive hashes."""

import os
import subprocess
import sys
from release_common import ROOT, download, read_json


def install():
    config = read_json(ROOT / "release/toolchain.json")
    if sys.platform == "win32":
        entry = config["inno_setup"]
        archive = download(entry["url"], entry["sha256"], ROOT / "build/tools/inno-setup.exe")
        destination = ROOT / "build/tools/inno"
        subprocess.run(
            [
                str(archive),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/CURRENTUSER",
                f"/DIR={destination}",
            ],
            check=True,
        )
        print(destination / "ISCC.exe")
    else:
        entry = config["appimagetool"]
        target = download(entry["url"], entry["sha256"], ROOT / "build/tools/appimagetool.AppImage")
        target.chmod(0o755)
        runtime = config["appimage_runtime"]
        download(runtime["url"], runtime["sha256"], ROOT / "build/tools/runtime-x86_64")
        environment = os.environ.copy()
        environment["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        subprocess.run([str(target), "--version"], env=environment, check=True)
        print(target)


if __name__ == "__main__":
    install()
