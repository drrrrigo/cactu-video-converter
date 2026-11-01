"""Default browser oriented settings."""

from pathlib import Path

from video_converter.models.conversion import ConversionSettings


NAME = "Web Compatibility / Kosmi"


def destination_for(source: Path) -> Path:
    """Use the source folder and append the preset suffix without overwriting input."""
    return source.with_name(f"{source.stem}-Kosmi.mp4")


def settings_for(source: Path) -> ConversionSettings:
    return ConversionSettings(destination=destination_for(source))
