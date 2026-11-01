"""Essential writable workspace checks before enabling beta conversion UI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from PySide6.QtCore import QStandardPaths


def check_writable_environment(config: Path | None = None) -> None:
    directory = config or Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    )
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=directory) as stream:
            stream.write(b"Cactu startup check")
            stream.flush()
    except OSError as exc:
        raise RuntimeError(
            "Cactu cannot write its configuration directory. Check your account permissions and available disk space."
        ) from exc
    try:
        with tempfile.TemporaryDirectory(prefix="cactu-startup-") as temporary:
            (Path(temporary) / "check").write_bytes(b"temporary workspace")
    except OSError as exc:
        raise RuntimeError(
            "Cactu cannot create a temporary workspace. Check temporary-directory permissions and available disk space."
        ) from exc
