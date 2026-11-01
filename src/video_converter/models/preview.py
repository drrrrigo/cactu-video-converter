"""An immutable segment request and its original conversion snapshot."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from video_converter.models.conversion import ConversionPlan


@dataclass(frozen=True)
class PreviewSettings:
    start_time_seconds: float
    duration_seconds: float = 30
    auto_open: bool = True


@dataclass(frozen=True)
class PreviewPlan:
    conversion_plan: ConversionPlan
    settings: PreviewSettings
    duration_seconds: float
    output_path: Path
    source_signature: tuple[int, int]
    subtitle_signature: tuple[int, int] | None = None

    @property
    def execution_plan(self) -> ConversionPlan:
        # Exact cuts require decoding copied streams. Never alter the original
        # plan or substitute a different video backend for this exception.
        return replace(self.conversion_plan, destination=self.output_path,
                       duration=self.duration_seconds, video_copy=False, audio_copy=False)

    @property
    def end_time_seconds(self) -> float:
        return self.settings.start_time_seconds + self.duration_seconds


def seconds_argument(seconds: float) -> str:
    return f"{seconds:.6f}".rstrip("0").rstrip(".") or "0"


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole, fraction = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d}" + (f".{fraction:03d}" if fraction else "")
