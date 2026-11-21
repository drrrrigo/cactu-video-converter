"""Automated native Windows install/convert/uninstall smoke (not Win11 manual UX)."""

import subprocess
import sys
import tempfile
from pathlib import Path
from package_smoke import smoke
from release_common import ROOT, read_json
from windows_runtime import assert_no_runtime, microsoft_runtime


def test_installer(
    installer: Path, *, inventory_destination: Path | None = None, final_rc: bool = False
):
    if sys.platform != "win32":
        raise RuntimeError("Installer testing requires native Windows")
    with tempfile.TemporaryDirectory(prefix="cactu-installed-smoke-") as folder:
        target = Path(folder) / "application"
        # Simulate an earlier app-local installation using harmless placeholder
        # bytes. Any stale DLL left behind must fail the installed-payload guard.
        historical = read_json(
            ROOT
            / "release/evidence/rc1-qualification-3b19839/windows/packaging/windows-x86_64-portable-payload.json"
        )
        for record in historical["files"]:
            if microsoft_runtime(record["path"]):
                old = target / record["path"]
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_bytes(b"legacy application runtime test placeholder")
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
            assert_no_runtime(target)
            smoke(target / "CactuVideoConverter.exe")
            if inventory_destination:
                from payload_inventory import inventory

                inventory(
                    target,
                    installer,
                    payload_kind="installed-windows",
                    target="windows-x86_64",
                    destination=inventory_destination,
                    final_rc=final_rc,
                )
        finally:
            subprocess.run(
                [str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                check=True,
                timeout=120,
            )
        if any(
            (target / name).exists()
            for name in ("CactuVideoConverter.exe", "CactuVideoConverter-core.exe")
        ):
            raise RuntimeError("Uninstall left the application executable behind")


if __name__ == "__main__":
    test_installer(Path(sys.argv[1]))
