"""Reject predictable configuration errors before launching FFmpeg."""

from __future__ import annotations

from pathlib import Path

from video_converter.models.conversion import CodecChoice, ConversionSettings, SubtitleMode
from video_converter.models.audio import AudioProcessingMode, MAX_VOLUME_PERCENT, MIN_VOLUME_PERCENT
from video_converter.models.media import MediaInfo
from video_converter.models.encoder import EncoderBackend, HardwareEncoderCapability
from video_converter.models.subtitle import EmbeddedSubtitleSource, ExternalSubtitleSource


class ValidationError(ValueError):
    """A user correctable conversion configuration problem."""


def validate(media: MediaInfo, settings: ConversionSettings, *, overwrite: bool = False,
             capabilities: tuple[HardwareEncoderCapability, ...] = (),
             hardware_required: bool = True) -> None:
    if not media.path.is_file():
        raise ValidationError("Input file does not exist.")
    if not media.video:
        raise ValidationError("No video stream was found in this file.")
    if not settings.destination.parent.is_dir():
        raise ValidationError("Output directory does not exist.")
    if not settings.destination.parent.stat().st_mode & 0o222:
        raise ValidationError("Output directory is not writable.")
    if settings.destination.resolve() == media.path.resolve():
        raise ValidationError("Output file must be different from the input file.")
    if settings.destination.suffix.lower() != ".mp4":
        raise ValidationError("This version supports MP4 output only.")
    if settings.destination.exists() and not overwrite:
        raise ValidationError("Output file already exists. Choose another name or confirm overwrite.")
    if settings.crf not in range(0, 52):
        raise ValidationError("H.264 quality must be between 0 and 51.")
    if settings.preset not in {"veryfast", "fast", "medium", "slow", "slower"}:
        raise ValidationError("Unsupported H.264 encoding preset.")
    if settings.pixel_format not in {"auto", "yuv420p"}:
        raise ValidationError("Unsupported pixel format.")
    if settings.audio_bitrate_kbps not in {128, 192, 256, 320}:
        raise ValidationError("Unsupported AAC bitrate.")
    if settings.audio_channels not in {None, 2, 6}:
        raise ValidationError("Unsupported audio channel choice.")
    if (type(settings.volume_percent) is not int or
            not MIN_VOLUME_PERCENT <= settings.volume_percent <= MAX_VOLUME_PERCENT):
        raise ValidationError(f"Audio volume must be between {MIN_VOLUME_PERCENT}% and {MAX_VOLUME_PERCENT}%.")
    if type(settings.prevent_clipping) is not bool:
        raise ValidationError("Prevent clipping must be on or off.")
    if not isinstance(settings.audio_processing_mode, AudioProcessingMode):
        raise ValidationError("Invalid audio processing mode.")
    try:
        settings.loudness_target.validate()
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Invalid normalization target: {exc}") from exc
    if settings.audio_index is not None and media.audio_by_index(settings.audio_index) is None:
        raise ValidationError("Selected audio track was not found.")
    if settings.subtitle_mode != SubtitleMode.NONE:
        source = settings.subtitle_source
        if source is None and settings.subtitle_index is not None:
            selected = media.subtitle_by_index(settings.subtitle_index)
            if selected is not None:
                source = EmbeddedSubtitleSource(selected.index, selected.ordinal, selected.codec, "")
        if isinstance(source, ExternalSubtitleSource):
            if settings.subtitle_mode != SubtitleMode.BURN:
                raise ValidationError("External subtitle files currently support Burn into video only.")
            path = source.path
            if path.suffix.lower() != f".{source.format.value}":
                raise ValidationError("External subtitle format does not match its filename.")
            if not path.exists():
                raise ValidationError("External subtitle file could not be found.")
            if not path.is_file():
                raise ValidationError("External subtitle must be a regular file.")
            try:
                with path.open("rb") as handle:
                    if not handle.read(1):
                        raise ValidationError("External subtitle file is empty.")
            except OSError as exc:
                raise ValidationError(f"External subtitle file is not readable: {exc}") from exc
        elif isinstance(source, EmbeddedSubtitleSource):
            selected = media.subtitle_by_index(source.stream_index)
            if selected is None or selected.ordinal != source.ordinal or selected.codec != source.codec:
                raise ValidationError("Selected subtitle track was not found.")
            if settings.subtitle_mode == SubtitleMode.BURN and selected.codec not in {"ass", "ssa", "subrip"}:
                raise ValidationError(f"Burning {selected.codec.upper()} subtitles is not supported. Choose ASS, SSA, or SRT.")
            if settings.subtitle_mode == SubtitleMode.SELECTABLE and selected.codec not in {"ass", "ssa", "subrip", "mov_text"}:
                raise ValidationError("This subtitle format cannot be converted to selectable MP4 subtitles.")
        else:
            raise ValidationError("Select a subtitle track or external subtitle file.")
    if settings.subtitle_mode == SubtitleMode.BURN and settings.video_codec == CodecChoice.COPY:
        raise ValidationError("Burning subtitles requires video re-encoding. Select H.264 or Auto.")
    if settings.video_codec == CodecChoice.COPY and (media.video.codec != "h264" or media.video.pixel_format != "yuv420p"):
        raise ValidationError("Video Copy requires H.264 with yuv420p for this MP4 preset.")
    if hardware_required and settings.encoding_engine.backend != EncoderBackend.SOFTWARE_X264:
        if not any(cap.available and cap.selection == settings.encoding_engine for cap in capabilities):
            raise ValidationError(f"{settings.encoding_engine.backend.display_name} is currently unavailable. Choose Software — x264.")
    selected_audio = media.audio_by_index(settings.audio_index) if settings.audio_index is not None else media.preferred_audio
    normalizing = settings.audio_processing_mode == AudioProcessingMode.LOUDNESS_NORMALIZATION
    if normalizing and selected_audio is None:
        raise ValidationError("Select an audio track before enabling loudness normalization.")
    if normalizing and settings.audio_codec == CodecChoice.COPY:
        raise ValidationError("Audio must be re-encoded for loudness normalization. Choose AAC.")
    if selected_audio is None and settings.volume_percent != 100 and not normalizing:
        raise ValidationError("Select an audio track before changing volume.")
    if settings.audio_codec == CodecChoice.COPY and selected_audio and settings.volume_percent != 100 and not normalizing:
        raise ValidationError("Audio must be re-encoded when volume adjustment is enabled. Choose AAC.")
    if settings.audio_codec == CodecChoice.COPY and selected_audio and selected_audio.codec != "aac":
        raise ValidationError("Audio Copy requires an AAC source track for MP4.")
    if settings.audio_codec == CodecChoice.COPY and settings.audio_channels is not None:
        raise ValidationError("Audio channel changes require AAC encoding.")


def output_is_writable(path: Path) -> bool:
    """A lightweight preflight; FFmpeg errors still handle races and full disks."""
    return path.parent.is_dir() and bool(path.parent.stat().st_mode & 0o222)
