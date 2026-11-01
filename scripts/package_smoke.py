"""Launch an actual packaged executable with no system FFmpeg in PATH."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def smoke(executable: Path, *, destination: Path | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="cactu-package-smoke-") as folder:
        root = Path(folder)
        environment = os.environ.copy()
        environment.update(
            PATH=str(root / "empty-path"),
            QT_QPA_PLATFORM="offscreen",
            PYTHONNOUSERSITE="1",
            XDG_CONFIG_HOME=str(root / "config"),
            XDG_DATA_HOME=str(root / "data"),
            APPDATA=str(root / "config"),
            LOCALAPPDATA=str(root / "data"),
        )
        environment.pop("PYTHONPATH", None)
        # Type-2 AppImage extraction does not depend on FUSE on CI hosts.
        if executable.suffix == ".AppImage":
            environment["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        result = subprocess.run(
            [str(executable.resolve()), "--release-smoke", str(root / "result")],
            env=environment,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=150,
        )
        report_path = root / "result/smoke-result.json"
        if result.returncode or not report_path.is_file():
            raise RuntimeError(
                f"Packaged application smoke failed (exit {result.returncode}): {result.stderr[-3000:]}"
            )
        report = json.loads(report_path.read_text())
        if not all(
            report.get(key)
            for key in ("ok", "frozen", "runtime_bundled", "faststart", "original_unchanged")
        ):
            raise RuntimeError("Packaged smoke evidence is incomplete: " + str(report))
        # Do not export ephemeral private paths or environmental variables.
        report.pop("path", None)
        if destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


if __name__ == "__main__":
    smoke(Path(sys.argv[1]), destination=Path(sys.argv[2]) if len(sys.argv) > 2 else None)
