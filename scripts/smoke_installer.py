"""Automated native Windows install/convert/uninstall smoke (not Win11 manual UX)."""

import subprocess
import sys
import tempfile
from pathlib import Path
from package_smoke import smoke


def test_installer(installer: Path):
    if sys.platform != "win32":
        raise RuntimeError("Installer testing requires native Windows")
    with tempfile.TemporaryDirectory(prefix="cactu-installed-smoke-") as folder:
        target = Path(folder) / "application"
        subprocess.run(
            [
                str(installer.resolve()),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/SP-",
                f"/DIR={target}",
            ],
            check=True,
            timeout=120,
        )
        try:
            smoke(target / "CactuVideoConverter.exe")
        finally:
            subprocess.run(
                [str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                check=True,
                timeout=120,
            )
        if (target / "CactuVideoConverter.exe").exists():
            raise RuntimeError("Uninstall left the application executable behind")


if __name__ == "__main__":
    test_installer(Path(sys.argv[1]))
