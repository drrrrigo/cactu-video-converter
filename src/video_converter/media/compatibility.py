"""Broad browser compatibility guidance, not a playback guarantee."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from video_converter.models.media import MediaInfo


class State(str, Enum):
    COMPATIBLE = "Compatible"
    NEEDS_CONVERSION = "Needs conversion"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class Compatibility:
    container: State
    video: State
    pixel_format: State
    audio: State

    @property
    def message(self) -> str:
        if State.NEEDS_CONVERSION in (self.container, self.video, self.pixel_format, self.audio):
            return "This file is not ideal for browser playback."
        if State.UNKNOWN in (self.container, self.video, self.pixel_format, self.audio):
            return "Browser compatibility could not be fully determined."
        return "This file has broadly compatible media formats."


def analyze(media: MediaInfo) -> Compatibility:
    names = set(media.container.split(","))
    container = State.COMPATIBLE if names.intersection({"mp4", "mov"}) else State.NEEDS_CONVERSION
    video = media.video
    video_state = (State.UNKNOWN if video is None else
                   State.COMPATIBLE if video.codec == "h264" else State.NEEDS_CONVERSION)
    pixel_state = (State.UNKNOWN if video is None or video.pixel_format == "unknown" else
                   State.COMPATIBLE if video.pixel_format == "yuv420p" else State.NEEDS_CONVERSION)
    audio = media.preferred_audio
    audio_state = (State.UNKNOWN if audio is None else
                   State.COMPATIBLE if audio.codec == "aac" else State.NEEDS_CONVERSION)
    return Compatibility(container, video_state, pixel_state, audio_state)
