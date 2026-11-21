"""Native launcher checks; hosted Windows is explicitly NOT clean-Windows proof."""

import json
import subprocess
import tempfile
from pathlib import Path

from release_common import ROOT
from windows_runtime import build_launcher


def main():
    work = ROOT / "build/windows-runtime"
    work.mkdir(parents=True, exist_ok=True)
    production = work / "production-check.exe"
    test = work / "test-check.exe"
    evidence = build_launcher(production)
    build_launcher(test, test=True)
    subprocess.run([str(production), "--check-prerequisites"], check=True, timeout=15)
    with tempfile.TemporaryDirectory(prefix="Cactu missing runtime ü ") as folder:
        result = subprocess.run([str(test), folder], timeout=15)
        if result.returncode != 10:
            raise RuntimeError("Missing-runtime check did not reject an empty directory")
        import PySide6
        import shutil

        for source in Path(PySide6.__file__).parent.glob("*.dll"):
            if source.name.lower().startswith(("vcruntime", "msvcp")):
                shutil.copy2(source, Path(folder) / source.name)
        result = subprocess.run([str(test), folder], timeout=15)
        if result.returncode != 10:
            raise RuntimeError("Older 14.44 runtime did not fail the 14.51 qualification floor")
    evidence.update(
        hosted_system_prerequisite="PASS",
        isolated_missing_directory="REJECTED",
        isolated_older_supplier_dlls="REJECTED",
        clean_windows_validation=False,
        no_runtime_installed_or_downloaded_by_test=True,
    )
    (work / "native-checks.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
