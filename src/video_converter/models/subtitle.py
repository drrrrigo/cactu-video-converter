"""A selected subtitle's identity, independent of how it is prepared."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SubtitleFormat(str, Enum):
    ASS = "ass"
    SSA = "ssa"
    SRT = "srt"

    @classmethod
    def from_path(cls, path: Path) -> SubtitleFormat:
        try:
            return cls(path.suffix.lower().removeprefix("."))
        except ValueError as exc:
            raise ValueError("Unsupported external subtitle format. Choose ASS, SSA, or SRT.") from exc


@dataclass(frozen=True)
class EmbeddedSubtitleSource:
    stream_index: int
    ordinal: int
    codec: str
    display_name: str


@dataclass(frozen=True)
class ExternalSubtitleSource:
    path: Path
    format: SubtitleFormat

    @classmethod
    def from_path(cls, path: Path) -> ExternalSubtitleSource:
        return cls(path=path, format=SubtitleFormat.from_path(path))

    @property
    def display_name(self) -> str:
        return self.path.name


SubtitleSource = EmbeddedSubtitleSource | ExternalSubtitleSource
