"""Loudness targets and validated FFmpeg measurements."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class LoudnessPreset(str, Enum):
    MOVIE_WEB = "movie_web"
    LOUDER = "louder"
    CONSERVATIVE = "conservative"
    CUSTOM = "custom"

    @property
    def label(self) -> str:
        return {self.MOVIE_WEB: "Movie / Web", self.LOUDER: "Louder",
                self.CONSERVATIVE: "Conservative", self.CUSTOM: "Custom"}[self]


def finite_range(value: float, minimum: float, maximum: float, name: str) -> None:
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or not minimum <= value <= maximum):
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}.")


@dataclass(frozen=True)
class LoudnessTarget:
    integrated_lufs: float = -16
    true_peak_dbtp: float = -1.5
    loudness_range_lu: float = 11
    preset: LoudnessPreset = LoudnessPreset.MOVIE_WEB

    def validate(self) -> None:
        finite_range(self.integrated_lufs, -70, -5, "Target loudness (LUFS)")
        finite_range(self.true_peak_dbtp, -9, 0, "True peak target (dBTP)")
        finite_range(self.loudness_range_lu, 1, 50, "Loudness range target (LU)")
        if not isinstance(self.preset, LoudnessPreset):
            raise ValueError("Invalid loudness preset.")


def target_for(preset: LoudnessPreset) -> LoudnessTarget:
    integrated = {LoudnessPreset.MOVIE_WEB: -16, LoudnessPreset.LOUDER: -14,
                  LoudnessPreset.CONSERVATIVE: -18, LoudnessPreset.CUSTOM: -16}[preset]
    return LoudnessTarget(integrated, -1.5, 11, preset)


@dataclass(frozen=True)
class LoudnessMeasurements:
    input_i: float
    input_tp: float
    input_lra: float
    input_thresh: float
    target_offset: float

    def __post_init__(self) -> None:
        # loudnorm cannot use infinities (e.g. silent audio) in a measured pass.
        for value, low, high, name in (
            (self.input_i, -99, 0, "Measured loudness"),
            (self.input_tp, -99, 99, "Measured true peak"),
            (self.input_lra, 0, 99, "Measured loudness range"),
            (self.input_thresh, -99, 0, "Measured threshold"),
            (self.target_offset, -99, 99, "Measured target offset"),
        ):
            finite_range(value, low, high, name)


@dataclass(frozen=True)
class LoudnessResult:
    output_i: float
    output_tp: float
    output_lra: float
    output_thresh: float
    normalization_type: str


@dataclass(frozen=True)
class LoudnessReport:
    source: str
    audio_index: int
    target: LoudnessTarget
    measurements: LoudnessMeasurements
    cache_hit: bool
    result: LoudnessResult | None = None
