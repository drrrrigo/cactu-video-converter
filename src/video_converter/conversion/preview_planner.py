"""Resolve bounded preview execution from an already validated full plan."""

from __future__ import annotations

import math
import re
from pathlib import Path

from video_converter.conversion.validator import ValidationError
from video_converter.models.conversion import ConversionPlan
from video_converter.models.encoder import EncoderBackend, HardwareEncoderCapability
from video_converter.models.media import MediaInfo
from video_converter.models.preview import PreviewPlan, PreviewSettings
from video_converter.models.subtitle import ExternalSubtitleSource


def parse_timestamp(value: str) -> float:
    match = re.fullmatch(r"(\d+):([0-5]\d):([0-5]\d(?:\.\d{1,3})?)", value.strip())
    if not match:
        raise ValidationError("Enter preview start as HH:MM:SS or HH:MM:SS.mmm.")
    hours, minutes, seconds = match.groups()
    try:
        result = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, OverflowError) as exc:
        raise ValidationError("Invalid preview start time.") from exc
    if not math.isfinite(result):
        raise ValidationError("Invalid preview start time.")
    return result


def parse_duration(value: str | float) -> float:
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValidationError("Preview duration must be between 5 and 120 seconds.") from exc
    if isinstance(value, bool) or not math.isfinite(result) or not 5 <= result <= 120:
        raise ValidationError("Preview duration must be between 5 and 120 seconds.")
    return result


def effective_duration(media_duration: float | None, settings: PreviewSettings) -> float:
    requested = parse_duration(settings.duration_seconds)
    if media_duration is None or not math.isfinite(media_duration) or media_duration <= 0:
        raise ValidationError("Preview requires a video with a known duration. Analyze the file again.")
    start = settings.start_time_seconds
    if isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start) or not 0 <= start < media_duration:
        raise ValidationError("Selected preview start time is outside the video duration.")
    return min(requested, media_duration - start)


def default_preview_start(duration: float | None) -> float:
    if duration is None or not math.isfinite(duration) or duration <= 60:
        return 0
    return float(int(min(duration * 0.1, 600, max(0, duration - 30))))


def file_signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def validate_preview_sources(preview: PreviewPlan) -> None:
    try:
        source = preview.conversion_plan.source
        if not source.is_file() or file_signature(source) != preview.source_signature:
            raise ValidationError("Source video changed or is missing. Open it again before creating a preview.")
        with source.open("rb") as handle:
            handle.read(1)
        subtitle = preview.conversion_plan.subtitle_source
        if isinstance(subtitle, ExternalSubtitleSource):
            if file_signature(subtitle.path) != preview.subtitle_signature:
                raise ValidationError("External subtitle changed. Select it again before creating a preview.")
            with subtitle.path.open("rb") as handle:
                handle.read(1)
    except OSError as exc:
        raise ValidationError(f"Preview source could not be read: {exc}") from exc


def plan_preview(media: MediaInfo, conversion: ConversionPlan, settings: PreviewSettings,
                 output_path: Path, *, capabilities: tuple[HardwareEncoderCapability, ...] = ()) -> PreviewPlan:
    duration = effective_duration(media.duration, settings)
    if conversion.source != media.path:
        raise ValidationError("Preview source does not match the analyzed video.")
    if output_path.suffix.lower() != ".mp4" or not output_path.parent.is_dir():
        raise ValidationError("Preview requires an existing temporary output directory and an MP4 filename.")
    if output_path.resolve() in {conversion.source.resolve(), conversion.destination.resolve()} or output_path.exists():
        raise ValidationError("Preview output must be a new file separate from the movie and final output.")
    if conversion.encoding_engine.backend != EncoderBackend.SOFTWARE_X264 and not any(
            cap.available and cap.selection == conversion.encoding_engine for cap in capabilities):
        raise ValidationError("The selected hardware encoder is unavailable for preview encoding.")
    try:
        signature = file_signature(media.path)
        if media.size is not None and media.size != signature[0]:
            raise ValidationError("Source video changed since analysis. Open it again before creating a preview.")
        subtitle = conversion.subtitle_source
        subtitle_signature = file_signature(subtitle.path) if isinstance(subtitle, ExternalSubtitleSource) else None
    except OSError as exc:
        raise ValidationError(f"Preview source could not be read: {exc}") from exc
    result = PreviewPlan(conversion, settings, duration, output_path, signature, subtitle_signature)
    validate_preview_sources(result)
    return result
