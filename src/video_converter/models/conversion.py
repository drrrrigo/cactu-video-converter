"""User intent and resolved conversion decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from video_converter.models.encoder import EncoderSelection, HardwareQuality, EncoderBackend
from video_converter.models.audio import AudioProcessingMode, AudioProcessingPlan
from video_converter.models.loudness import LoudnessTarget
from video_converter.models.subtitle import SubtitleSource


class SubtitleMode(str, Enum):
    NONE = "none"
    SELECTABLE = "selectable"
    BURN = "burn"


class CodecChoice(str, Enum):
    AUTO = "auto"
    COPY = "copy"
    H264 = "h264"
    AAC = "aac"


@dataclass(frozen=True)
class ConversionSettings:
    destination: Path
    video_codec: CodecChoice = CodecChoice.AUTO
    crf: int = 18
    preset: str = "medium"
    pixel_format: str = "yuv420p"
    encoding_engine: EncoderSelection = EncoderSelection()
    hardware_quality: HardwareQuality = HardwareQuality.HIGH
    audio_codec: CodecChoice = CodecChoice.AUTO
    audio_bitrate_kbps: int = 256
    audio_channels: int | None = None
    audio_index: int | None = None
    volume_percent: int = 100
    prevent_clipping: bool = True
    audio_processing_mode: AudioProcessingMode = AudioProcessingMode.MANUAL_VOLUME
    loudness_target: LoudnessTarget = LoudnessTarget()
    subtitle_mode: SubtitleMode = SubtitleMode.NONE
    subtitle_index: int | None = None
    subtitle_source: SubtitleSource | None = None
    faststart: bool = True
    preset_name: str = "Web Compatibility / Kosmi"

    def customized(self, **changes: object) -> ConversionSettings:
        return replace(self, preset_name="Custom — based on Web Compatibility / Kosmi", **changes)


@dataclass(frozen=True)
class ConversionPlan:
    source: Path
    destination: Path
    video_index: int
    audio_index: int | None
    subtitle_index: int | None
    subtitle_ordinal: int | None
    subtitle_mode: SubtitleMode
    subtitle_source: SubtitleSource | None
    video_copy: bool
    audio_copy: bool
    audio_processing: AudioProcessingPlan
    crf: int
    preset: str
    pixel_format: str
    encoding_engine: EncoderSelection
    hardware_quality: HardwareQuality
    audio_bitrate_kbps: int
    audio_channels: int | None
    faststart: bool
    duration: float | None

    @property
    def description(self) -> str:
        if self.video_copy:
            video = "copy"
        elif self.encoding_engine.backend == EncoderBackend.SOFTWARE_X264:
            video = f"H.264 (Software x264, CRF {self.crf}, {self.preset})"
        else:
            video = f"H.264 ({self.encoding_engine.backend.display_name}, {self.hardware_quality.label})"
        audio = "none" if self.audio_index is None else ("copy" if self.audio_copy else f"AAC {self.audio_bitrate_kbps} kbps")
        if self.audio_index is not None and self.audio_processing.requires_encoding:
            target = self.audio_processing.normalization_target
            audio += (f" ({target.integrated_lufs:g} LUFS)" if target else
                      f" ({self.audio_processing.volume_percent}% volume)")
        return f"MP4 • Video: {video} • Audio: {audio}"
