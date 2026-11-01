"""Parse FFprobe JSON without exposing raw dictionaries to the rest of the app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_converter.models.media import (
    AttachmentStream, AudioStream, MediaInfo, SubtitleStream, VideoStream,
)


LANGUAGES = {"eng": "English", "en": "English", "por": "Portuguese", "pt": "Portuguese",
             "jpn": "Japanese", "ja": "Japanese", "spa": "Spanish", "es": "Spanish",
             "fra": "French", "fre": "French", "deu": "German", "ger": "German"}


def frame_rate(value: str | None) -> float | None:
    """Return a finite positive FPS, avoiding zero denominator and N/A values."""
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/") if "/" in value else (value, "1")
        result = float(numerator) / float(denominator)
        return result if 0 < result < 10000 else None
    except (ValueError, ZeroDivisionError):
        return None


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _duration(value: Any) -> float | None:
    try:
        duration = float(value)
        return duration if 0 < duration < float("inf") else None
    except (TypeError, ValueError):
        return None


def stream_label(stream: AudioStream | SubtitleStream) -> str:
    """Build a useful label while retaining stream identity in the model."""
    language = LANGUAGES.get(stream.language.lower(), stream.language)
    title = stream.title.strip()
    parts: list[str] = []
    if title:
        parts.append(title)
    if language and language.lower() not in {"und", "unknown"} and language.lower() not in title.lower():
        parts.append(language)
    if not parts:
        noun = "Audio" if isinstance(stream, AudioStream) else "Subtitle"
        parts.append(f"{noun} {stream.ordinal + 1}")
    codec = stream.codec.upper()
    if isinstance(stream, AudioStream):
        layout = "Stereo" if stream.channels == 2 else ("5.1" if stream.channels == 6 else stream.layout)
        codec += f" {layout}" if layout else ""
    parts.append(codec)
    return " — ".join(parts)


def parse_probe(data: str | dict[str, Any], path: Path) -> MediaInfo:
    """Convert FFprobe output into typed records with global and per-type indexes."""
    raw = json.loads(data) if isinstance(data, str) else data
    videos: list[VideoStream] = []
    audios: list[AudioStream] = []
    subtitles: list[SubtitleStream] = []
    attachments: list[AttachmentStream] = []
    for item in raw.get("streams", []):
        index = _integer(item.get("index"))
        if index is None:
            continue
        kind = item.get("codec_type")
        tags = item.get("tags") or {}
        disposition = item.get("disposition") or {}
        codec = str(item.get("codec_name") or "unknown")
        if kind == "video":
            videos.append(VideoStream(index, codec, str(item.get("profile") or ""),
                                      _integer(item.get("width")) or 0, _integer(item.get("height")) or 0,
                                      frame_rate(item.get("avg_frame_rate") or item.get("r_frame_rate")),
                                      str(item.get("pix_fmt") or "unknown"),
                                      _integer(item.get("bits_per_raw_sample")) or _integer(item.get("bits_per_sample")),
                                      bool(disposition.get("default"))))
        elif kind == "audio":
            audios.append(AudioStream(index, len(audios), codec, str(tags.get("language") or ""),
                                      str(tags.get("title") or ""), _integer(item.get("channels")) or 0,
                                      str(item.get("channel_layout") or ""), _integer(item.get("sample_rate")),
                                      _integer(item.get("bit_rate")), bool(disposition.get("default"))))
        elif kind == "subtitle":
            subtitles.append(SubtitleStream(index, len(subtitles), codec,
                                            str(tags.get("language") or ""), str(tags.get("title") or ""),
                                            bool(disposition.get("default")), bool(disposition.get("forced"))))
        elif kind == "attachment":
            attachments.append(AttachmentStream(index, str(tags.get("filename") or ""),
                                                str(tags.get("mimetype") or "")))
    fmt = raw.get("format") or {}
    return MediaInfo(path, str(fmt.get("format_name") or "unknown"), _duration(fmt.get("duration")),
                     _integer(fmt.get("size")), tuple(videos), tuple(audios), tuple(subtitles), tuple(attachments),
                     tuple((str(key), str(value)) for key, value in (fmt.get("tags") or {}).items()))


def probe_arguments(path: Path) -> list[str]:
    return ["-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)]
