"""Immutable media records; ordinals and global indexes remain distinct."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoStream:
    index: int
    codec: str
    profile: str
    width: int
    height: int
    fps: float | None
    pixel_format: str
    bit_depth: int | None
    default: bool


@dataclass(frozen=True)
class AudioStream:
    index: int
    ordinal: int
    codec: str
    language: str
    title: str
    channels: int
    layout: str
    sample_rate: int | None
    bitrate: int | None
    default: bool


@dataclass(frozen=True)
class SubtitleStream:
    index: int
    ordinal: int
    codec: str
    language: str
    title: str
    default: bool
    forced: bool


@dataclass(frozen=True)
class AttachmentStream:
    index: int
    filename: str
    mimetype: str


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    container: str
    duration: float | None
    size: int | None
    videos: tuple[VideoStream, ...]
    audios: tuple[AudioStream, ...]
    subtitles: tuple[SubtitleStream, ...]
    attachments: tuple[AttachmentStream, ...]
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def video(self) -> VideoStream | None:
        return self.videos[0] if self.videos else None

    @property
    def preferred_audio(self) -> AudioStream | None:
        """Use FFprobe's default disposition when a track is not explicitly chosen."""
        return next((stream for stream in self.audios if stream.default),
                    self.audios[0] if self.audios else None)

    def audio_by_index(self, index: int) -> AudioStream | None:
        return next((s for s in self.audios if s.index == index), None)

    def subtitle_by_index(self, index: int) -> SubtitleStream | None:
        return next((s for s in self.subtitles if s.index == index), None)
