"""Sanitized opt-in bug-report snapshots; no network or media/job export."""

from __future__ import annotations

import platform
import struct
from video_converter import __version__
from video_converter.product import PRODUCT_NAME, RELEASE_CHANNEL
from video_converter.hardware.report import diagnostic_report, sanitize

_recent_error_category = "None recorded"


def record_error(category: str) -> None:
    global _recent_error_category
    _recent_error_category = category[:100]


def report(runtime, hardware=None) -> str:
    header = [
        f"{PRODUCT_NAME} {__version__} ({RELEASE_CHANNEL})",
        f"OS: {platform.system()} {platform.release()}",
        f"Architecture: {platform.machine()} / {struct.calcsize('P') * 8}-bit",
        f"FFmpeg: {runtime.ffmpeg_version}",
        f"FFprobe: {runtime.ffprobe_version}",
        "Base capability checks: x264 / AAC / subtitles; full release tables checked in frozen builds",
        f"Loudness normalization available: {runtime.loudnorm_available}",
        f"Recent error category: {_recent_error_category}",
        "Network: offline conversion; no telemetry or automatic uploads",
    ]
    if hardware is not None:
        header += ["", diagnostic_report(hardware)]
    else:
        header += ["Hardware: detection not completed; Software x264 remains available"]
    return sanitize("\n".join(header))[:60000]
