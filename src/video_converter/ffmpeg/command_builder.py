"""Generate argument arrays from validated conversion plans."""

from __future__ import annotations

from pathlib import Path

from video_converter.ffmpeg.encoders import get_backend
from video_converter.ffmpeg.audio_filters import build_audio_filters
from video_converter.models.audio import AudioProcessingPlan
from video_converter.models.conversion import ConversionPlan, SubtitleMode
from video_converter.models.preview import PreviewPlan, seconds_argument


def build_command(plan: ConversionPlan, ffmpeg: Path, output: Path, *, subtitle_file: Path | None = None,
                  fonts_dir: Path | None = None, preview: PreviewPlan | None = None,
                  audio_processing: AudioProcessingPlan | None = None) -> list[str]:
    """Map exact global stream indexes; map no implicit streams or metadata tracks."""
    adapter = get_backend(plan.encoding_engine.backend)
    processing = audio_processing if audio_processing is not None else plan.audio_processing
    if processing.without_measurements() != plan.audio_processing.without_measurements():
        raise ValueError("Resolved audio processing must match the conversion plan.")
    setup = [] if plan.video_copy else adapter.setup_args(plan.encoding_engine)
    if preview is not None and plan != preview.execution_plan:
        raise ValueError("Preview command must use its derived execution plan.")
    seek = ["-ss", seconds_argument(preview.settings.start_time_seconds)] if preview else []
    args = [str(ffmpeg), "-hide_banner", "-nostdin", "-y", *setup, *seek, "-i", str(plan.source)]
    if preview is not None and plan.subtitle_mode == SubtitleMode.SELECTABLE:
        if subtitle_file is None or subtitle_file.name != "subtitle.srt":
            raise ValueError("Prepared preview subtitles are required for selectable output.")
        args += ["-i", subtitle_file.name]
    args += ["-map", f"0:{plan.video_index}"]
    if plan.audio_index is not None:
        args += ["-map", f"0:{plan.audio_index}"]
    if plan.subtitle_mode == SubtitleMode.SELECTABLE:
        assert plan.subtitle_index is not None
        args += ["-map", "1:0" if preview else f"0:{plan.subtitle_index}"]
    if plan.video_copy:
        args += ["-c:v", "copy"]
    else:
        subtitle_filter: str | None = None
        if plan.subtitle_mode == SubtitleMode.BURN:
            if subtitle_file is None:
                raise ValueError("Prepared subtitle file is required for burning.")
            # Preparation places files under a temporary ASCII-only cwd. The filter
            # receives a constant basename, avoiding path/colon/Unicode escaping.
            if subtitle_file.name not in {"subtitle.ass", "subtitle.ssa", "subtitle.srt"}:
                raise ValueError("Unexpected prepared subtitle filename.")
            subtitle_filter = f"subtitles={subtitle_file.name}"
            if fonts_dir is not None:
                subtitle_filter += ":fontsdir=fonts"
            if preview is not None and preview.settings.start_time_seconds:
                # Accurate input seek resets timestamps. libass needs the movie
                # clock to select events (including those crossing the cut),
                # then the encoder needs the segment clock again.
                offset = seconds_argument(preview.settings.start_time_seconds)
                subtitle_filter = f"setpts=PTS+{offset}/TB,{subtitle_filter},setpts=PTS-{offset}/TB"
        filter_chain = adapter.filter_chain(subtitle_filter, plan.encoding_engine)
        if filter_chain:
            args += ["-vf", filter_chain]
        args += adapter.encoding_args(plan.hardware_quality, crf=plan.crf,
                                      preset=plan.preset, pixel_format=plan.pixel_format)
    if plan.audio_index is None:
        args += ["-an"]
    elif plan.audio_copy:
        args += ["-c:a", "copy"]
    else:
        args += ["-c:a", "aac", "-b:a", f"{plan.audio_bitrate_kbps}k"]
        if plan.audio_channels is not None:
            args += ["-ac", str(plan.audio_channels)]
        audio_filters = build_audio_filters(processing)
        if audio_filters:
            args += ["-af", audio_filters]
    if plan.subtitle_mode == SubtitleMode.SELECTABLE:
        args += ["-c:s", "mov_text"]
    else:
        args += ["-sn"]
    if plan.faststart:
        args += ["-movflags", "+faststart"]
    if preview is not None:
        args += ["-t", seconds_argument(preview.duration_seconds)]
    args += ["-progress", "pipe:1", "-nostats", "-f", "mp4", str(output)]
    return args


def extraction_command(ffmpeg: Path, source: Path, global_index: int, output: Path,
                       *, preview: PreviewPlan | None = None) -> list[str]:
    """Extract exactly the selected embedded text subtitle stream."""
    seek = []
    end = []
    if preview is not None:
        # An event can start long before the cut and remain visible. Seeking
        # subtitle packets to the cut loses that event, so demux the prefix
        # (without decoding video) and stop at the preview end instead.
        seek = ["-t", seconds_argument(preview.end_time_seconds), "-copyts"]
        end = ["-to", seconds_argument(preview.end_time_seconds)]
    return [str(ffmpeg), "-hide_banner", "-nostdin", "-y", *seek, "-i", str(source),
            "-map", f"0:{global_index}", "-c:s", "ass" if output.suffix == ".ass" else "srt",
            *end, str(output)]
