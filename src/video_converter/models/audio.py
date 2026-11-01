"""Typed audio processing decisions independent of FFmpeg syntax."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from video_converter.models.loudness import LoudnessMeasurements, LoudnessTarget

MIN_VOLUME_PERCENT = 0
MAX_VOLUME_PERCENT = 300


class AudioProcessingMode(str, Enum):
    MANUAL_VOLUME = "manual_volume"
    LOUDNESS_NORMALIZATION = "loudness_normalization"


@dataclass(frozen=True)
class VolumeFilter:
    percent: int


@dataclass(frozen=True)
class LimiterFilter:
    peak_limit: float = 0.85


@dataclass(frozen=True)
class LoudnormFilter:
    target: LoudnessTarget


@dataclass(frozen=True)
class ChannelLayoutFilter:
    channels: int


@dataclass(frozen=True)
class ResampleFilter:
    sample_rate: int


AudioFilter = VolumeFilter | LimiterFilter | LoudnormFilter | ChannelLayoutFilter | ResampleFilter


@dataclass(frozen=True)
class AudioProcessingPlan:
    volume_percent: int = 100
    prevent_clipping: bool = True
    filters: tuple[AudioFilter, ...] = ()
    mode: AudioProcessingMode = AudioProcessingMode.MANUAL_VOLUME
    loudness_measurements: LoudnessMeasurements | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, AudioProcessingMode):
            raise ValueError("Invalid audio processing mode.")
        normalizers = sum(isinstance(item, LoudnormFilter) for item in self.filters)
        if self.mode == AudioProcessingMode.LOUDNESS_NORMALIZATION:
            if normalizers != 1 or any(isinstance(item, (VolumeFilter, LimiterFilter)) for item in self.filters):
                raise ValueError("Normalization cannot be combined with manual volume or limiting.")
            if self.volume_percent != 100 or self.prevent_clipping:
                raise ValueError("Manual gain and clipping protection must be inactive during normalization.")
            self.normalization_target.validate()
        elif normalizers or self.loudness_measurements is not None:
            raise ValueError("Loudness measurements and filters require normalization mode.")

    @property
    def normalization_target(self) -> LoudnessTarget | None:
        return next((item.target for item in self.filters if isinstance(item, LoudnormFilter)), None)

    @property
    def output_sample_rate(self) -> int | None:
        return next((item.sample_rate for item in self.filters if isinstance(item, ResampleFilter)), None)

    def with_measurements(self, measurements: LoudnessMeasurements) -> AudioProcessingPlan:
        return replace(self, loudness_measurements=measurements)

    def without_measurements(self) -> AudioProcessingPlan:
        return replace(self, loudness_measurements=None)

    @property
    def requires_encoding(self) -> bool:
        return bool(self.filters)

    @property
    def limiter_active(self) -> bool:
        return any(isinstance(item, LimiterFilter) for item in self.filters)


def plan_audio_processing(volume_percent: int, prevent_clipping: bool, *,
                          mode: AudioProcessingMode = AudioProcessingMode.MANUAL_VOLUME,
                          target: LoudnessTarget = LoudnessTarget(),
                          sample_rate: int | None = None, channels: int | None = None) -> AudioProcessingPlan:
    """A neutral setting is a true no-op; limiting only applies to boosts."""
    filters: list[AudioFilter] = []
    if mode == AudioProcessingMode.LOUDNESS_NORMALIZATION:
        target.validate()
        if channels is not None:
            filters.append(ChannelLayoutFilter(channels))
        filters.append(LoudnormFilter(target))
        # Dynamic loudnorm can run at 192 kHz; choose a supported final AAC rate.
        supported_rates = {7350, 8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000}
        filters.append(ResampleFilter(sample_rate if sample_rate in supported_rates else 48000))
        return AudioProcessingPlan(100, False, tuple(filters), mode)
    if volume_percent != 100:
        filters.append(VolumeFilter(volume_percent))
        if volume_percent > 100 and prevent_clipping:
            filters.append(LimiterFilter())
    return AudioProcessingPlan(volume_percent, prevent_clipping, tuple(filters))
