"""Audio-only first pass and parsing of loudnorm's mixed stderr diagnostics."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from video_converter.ffmpeg.audio_filters import build_audio_filters
from video_converter.models.conversion import ConversionPlan
from video_converter.models.loudness import LoudnessMeasurements, LoudnessResult

LOG = logging.getLogger(__name__)


def analysis_command(plan: ConversionPlan, ffmpeg: Path) -> list[str]:
    if plan.audio_index is None or plan.audio_processing.normalization_target is None:
        raise ValueError("Loudness analysis requires a selected audio track and normalization target.")
    # No preview seek/duration: measurements always describe the full selected track.
    return [str(ffmpeg), "-hide_banner", "-nostdin", "-i", str(plan.source),
            "-map", f"0:{plan.audio_index}", "-vn", "-sn", "-dn", "-af",
            build_audio_filters(plan.audio_processing, analysis=True),
            "-progress", "pipe:1", "-nostats", "-f", "null", "-"]


def _record(stderr: str, marker: str) -> dict:
    decoder = json.JSONDecoder()
    records = []
    # Logs and progress can surround JSON. raw_decode consumes exactly one object,
    # without relying on line numbers, log prefixes or a greedy brace expression.
    for index, char in enumerate(stderr):
        if char != "{":
            continue
        try:
            record, _ = decoder.raw_decode(stderr[index:])
        except ValueError:
            continue
        if isinstance(record, dict) and marker in record:
            records.append(record)
    if not records:
        raise ValueError("FFmpeg returned no complete loudness measurement payload.")
    return records[-1]


def _numeric(record: dict, name: str) -> float:
    try:
        value = record[name]
        if isinstance(value, bool):
            raise ValueError("Boolean is not a measurement")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Non-finite measurement (silent or unmeasurable audio)")
        return result
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"Invalid or missing loudnorm measurement: {name}.") from exc


def parse_measurements(stderr: str) -> LoudnessMeasurements:
    try:
        record = _record(stderr, "input_i")
        return LoudnessMeasurements(*(_numeric(record, key) for key in
            ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")))
    except ValueError:
        LOG.exception("Could not parse loudness measurements")
        raise


def parse_result(stderr: str) -> LoudnessResult:
    record = _record(stderr, "output_i")
    mode = record.get("normalization_type")
    if mode not in {"linear", "dynamic"}:
        raise ValueError("Invalid loudnorm result mode.")
    return LoudnessResult(*(_numeric(record, key) for key in
        ("output_i", "output_tp", "output_lra", "output_thresh")), mode)
