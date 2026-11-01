"""Bounded session cache; target-dependent offset must never cross targets."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.models.conversion import ConversionPlan
from video_converter.models.loudness import LoudnessMeasurements


@dataclass(frozen=True)
class LoudnessCacheKey:
    source: str
    size: int
    mtime_ns: int
    audio_index: int
    channels: int | None
    sample_rate: int
    targets: tuple[float, float, float]
    runtime: tuple[str, str, int, int]


def cache_key(plan: ConversionPlan, runtime: FFmpegRuntime) -> LoudnessCacheKey:
    target = plan.audio_processing.normalization_target
    rate = plan.audio_processing.output_sample_rate
    if target is None or rate is None or plan.audio_index is None:
        raise ValueError("A normalized audio plan is required for loudness caching.")
    source = plan.source.resolve(strict=True)
    stat = source.stat()
    binary = runtime.ffmpeg.resolve(strict=True)
    binary_stat = binary.stat()
    return LoudnessCacheKey(str(source), stat.st_size, stat.st_mtime_ns, plan.audio_index,
                            plan.audio_channels, rate,
                            (target.integrated_lufs, target.true_peak_dbtp, target.loudness_range_lu),
                            (str(binary), runtime.ffmpeg_version, binary_stat.st_size, binary_stat.st_mtime_ns))


class LoudnessCache:
    def __init__(self, capacity: int = 16) -> None:
        self.capacity = capacity
        self._items: OrderedDict[LoudnessCacheKey, LoudnessMeasurements] = OrderedDict()

    def get(self, key: LoudnessCacheKey) -> LoudnessMeasurements | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key: LoudnessCacheKey, value: LoudnessMeasurements) -> None:
        if not isinstance(value, LoudnessMeasurements):
            raise ValueError("Only validated loudness measurements can be cached.")
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
