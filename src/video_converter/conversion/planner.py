"""Decide whether each stream can be copied without unnecessary encoding."""

from video_converter.conversion.validator import ValidationError, validate
from video_converter.models.conversion import CodecChoice, ConversionPlan, ConversionSettings, SubtitleMode
from video_converter.models.media import MediaInfo
from video_converter.models.encoder import HardwareEncoderCapability
from video_converter.models.audio import plan_audio_processing
from video_converter.models.subtitle import EmbeddedSubtitleSource
from video_converter.media.ffprobe_service import stream_label


def plan(media: MediaInfo, settings: ConversionSettings, *, overwrite: bool = False,
         capabilities: tuple[HardwareEncoderCapability, ...] = ()) -> ConversionPlan:
    """Resolve selected *global* indexes and copy decisions into one immutable plan."""
    if media.video is None:
        raise ValidationError("No video stream was found in this file.")
    audio = media.audio_by_index(settings.audio_index) if settings.audio_index is not None else media.preferred_audio
    source = settings.subtitle_source
    if source is None and settings.subtitle_index is not None:
        selected = media.subtitle_by_index(settings.subtitle_index)
        if selected is not None:
            source = EmbeddedSubtitleSource(selected.index, selected.ordinal,
                                            selected.codec, stream_label(selected))
    subtitle = (media.subtitle_by_index(source.stream_index)
                if isinstance(source, EmbeddedSubtitleSource) else None)
    # A subtitle filter modifies pixels and therefore precludes stream copy.
    video_copy = settings.subtitle_mode != SubtitleMode.BURN and (
        settings.video_codec == CodecChoice.COPY or
        (settings.video_codec == CodecChoice.AUTO and media.video.codec == "h264" and
         media.video.pixel_format == "yuv420p" and settings.pixel_format in {"auto", "yuv420p"})
    )
    validate(media, settings, overwrite=overwrite, capabilities=capabilities,
             hardware_required=not video_copy)
    audio_processing = plan_audio_processing(settings.volume_percent, settings.prevent_clipping,
        mode=settings.audio_processing_mode, target=settings.loudness_target,
        sample_rate=audio.sample_rate if audio else None, channels=settings.audio_channels)
    audio_copy = audio is not None and not audio_processing.requires_encoding and (
        settings.audio_codec == CodecChoice.COPY or
        (settings.audio_codec == CodecChoice.AUTO and audio.codec == "aac" and settings.audio_channels is None)
    )
    return ConversionPlan(
        source=media.path, destination=settings.destination, video_index=media.video.index,
        audio_index=audio.index if audio else None,
        subtitle_index=subtitle.index if subtitle else None,
        subtitle_ordinal=subtitle.ordinal if subtitle else None,
        subtitle_mode=settings.subtitle_mode, subtitle_source=source,
        video_copy=video_copy, audio_copy=audio_copy, audio_processing=audio_processing,
        crf=settings.crf, preset=settings.preset, pixel_format=settings.pixel_format,
        encoding_engine=settings.encoding_engine, hardware_quality=settings.hardware_quality,
        audio_bitrate_kbps=settings.audio_bitrate_kbps,
        audio_channels=settings.audio_channels, faststart=settings.faststart,
        duration=media.duration,
    )
