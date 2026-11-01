"""Translate typed audio processing into one FFmpeg audio filter graph."""

from __future__ import annotations

from video_converter.models.audio import (
    AudioProcessingPlan, ChannelLayoutFilter, LimiterFilter, LoudnormFilter, ResampleFilter, VolumeFilter,
)


def volume_multiplier(percent: int) -> str:
    """Format hundredths exactly and retain one decimal for whole multipliers."""
    whole, fraction = divmod(percent, 100)
    return f"{whole}.{fraction:02d}".rstrip("0") if fraction else f"{whole}.0"


def number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def build_audio_filters(processing: AudioProcessingPlan, *, analysis: bool = False) -> str | None:
    chain: list[str] = []
    for item in processing.filters:
        if isinstance(item, VolumeFilter):
            chain.append(f"volume={volume_multiplier(item.percent)}")
        elif isinstance(item, LimiterFilter):
            # Disabling automatic makeup gain keeps the user's percentage
            # meaningful below the ceiling; latency compensates lookahead.
            chain.append(f"alimiter=limit={item.peak_limit:.2f}:level=false:latency=true")
        elif isinstance(item, ChannelLayoutFilter):
            # Match the signal measured in pass one to the signal normalized in pass two.
            layout = {2: "stereo", 6: "5.1"}.get(item.channels)
            if layout is None:
                raise ValueError("Unsupported normalized channel layout.")
            chain.append(f"aformat=channel_layouts={layout}")
        elif isinstance(item, LoudnormFilter):
            item.target.validate()
            target = item.target
            options = [f"I={number(target.integrated_lufs)}", f"LRA={number(target.loudness_range_lu)}",
                       f"TP={number(target.true_peak_dbtp)}"]
            if not analysis:
                measured = processing.loudness_measurements
                if measured is None:
                    raise ValueError("Loudness analysis is required before encoding.")
                options += [f"measured_I={number(measured.input_i)}",
                            f"measured_TP={number(measured.input_tp)}",
                            f"measured_LRA={number(measured.input_lra)}",
                            f"measured_thresh={number(measured.input_thresh)}",
                            f"offset={number(measured.target_offset)}", "linear=true"]
            # FFmpeg may fall back to dynamic normalization when linear constraints fail.
            chain.append("loudnorm=" + ":".join([*options, "print_format=json"]))
        elif isinstance(item, ResampleFilter):
            chain.append(f"aresample={item.sample_rate}")
        else:
            raise ValueError("Unknown audio filter.")
    return ",".join(chain) or None
