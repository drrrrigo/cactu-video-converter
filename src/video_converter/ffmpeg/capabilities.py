"""Essential release capability checks; physical GPUs are deliberately optional."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REQUIRED = {
    "-encoders": {"libx264", "aac", "ass", "srt", "mov_text"},
    "-decoders": {"h264", "hevc", "ass", "ssa", "subrip"},
    "-filters": {"subtitles", "loudnorm", "alimiter", "aresample", "format"},
    "-muxers": {"mp4", "matroska"},
    "-demuxers": {"matroska", "srt", "ass"},
}


def table_names(output: str) -> set[str]:
    result = set()
    for line in output.splitlines():
        match = re.match(r"^\s*[.A-Z|]{1,6}\s+([a-zA-Z0-9_,]+)\s", line)
        if match:
            result.update(match[1].split(","))
    return result


def capability_tables(binary: Path) -> dict[str, set[str]]:
    tables = {}
    for flag in REQUIRED:
        result = subprocess.run(
            [str(binary), "-hide_banner", flag],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        tables[flag] = table_names(result.stdout)
    return tables


def require_capabilities(tables: dict[str, set[str]]) -> None:
    missing = [
        f"{flag}: {', '.join(sorted(names - tables.get(flag, set())))}"
        for flag, names in REQUIRED.items()
        if not names <= tables.get(flag, set())
    ]
    if missing:
        raise RuntimeError("Essential FFmpeg capabilities are missing: " + "; ".join(missing))
