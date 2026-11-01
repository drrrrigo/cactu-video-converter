"""Prepare either subtitle source for the existing libass burn filter."""

from __future__ import annotations

import logging
import shutil
import re
from dataclasses import dataclass
from pathlib import Path

from video_converter.ffmpeg.command_builder import extraction_command
from video_converter.models.subtitle import EmbeddedSubtitleSource, ExternalSubtitleSource, SubtitleSource
from video_converter.models.preview import PreviewPlan

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedSubtitle:
    path: Path
    extraction_command: list[str] | None
    needs_preflight: bool


def prepare_subtitle(source: SubtitleSource, workspace: Path, ffmpeg: Path,
                     video: Path, *, preview: PreviewPlan | None = None,
                     selectable: bool = False) -> PreparedSubtitle:
    """Return one safe basename; only preparation depends on source origin."""
    if isinstance(source, EmbeddedSubtitleSource):
        suffix = ".srt" if selectable or source.codec == "subrip" else ".ass"
        path = workspace / f"subtitle{suffix}"
        LOG.info("Preparing embedded subtitle stream %d as %s", source.stream_index, path)
        return PreparedSubtitle(path, extraction_command(ffmpeg, video, source.stream_index, path,
                                                          preview=preview), False)
    if isinstance(source, ExternalSubtitleSource):
        path = workspace / f"subtitle.{source.format.value}"
        try:
            # Copy bytes unchanged. A stable snapshot also avoids a file changing
            # while a long video conversion is in progress.
            shutil.copyfile(source.path, path)
        except OSError as exc:
            raise OSError(f"External subtitle file could not be read: {exc}") from exc
        if path.stat().st_size == 0:
            raise OSError("External subtitle file is empty.")
        LOG.info("External subtitle validated and staged: source=%s format=%s staged=%s",
                 source.path, source.format.value.upper(), path)
        return PreparedSubtitle(path, None, True)
    raise TypeError("Unknown subtitle source")


def clip_selectable_subtitle(staged: Path, preview: PreviewPlan) -> None:
    """Clip FFmpeg's canonical SRT output for a standalone selectable sample.

    Full MP4 selectable conversion already drops advanced ASS styling. Let
    FFmpeg convert text to SRT, then adjust only event times, including an event
    crossing the cut. This avoids muxing negative timestamps into mov_text.
    """
    def milliseconds(value: str) -> int:
        match = re.fullmatch(r"(\d+):([0-5]\d):([0-5]\d),(\d{3})", value)
        if match is None:
            raise ValueError("FFmpeg produced invalid subtitle timestamps.")
        h, m, s, ms = map(int, match.groups())
        return ((h * 60 + m) * 60 + s) * 1000 + ms

    def timestamp(value: int) -> str:
        h, rest = divmod(value, 3_600_000)
        m, rest = divmod(rest, 60_000)
        s, ms = divmod(rest, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    offset = round(preview.settings.start_time_seconds * 1000)
    duration = round(preview.duration_seconds * 1000)
    # Anchor the text input at zero even if its first visible event is later.
    # A zero-width space creates no visible subtitle in the first millisecond.
    result = ["1\n00:00:00,000 --> 00:00:00,001\n\u200b\n"]
    content = staged.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        timing = re.fullmatch(r"(\d+:\d\d:\d\d,\d{3}) --> (\d+:\d\d:\d\d,\d{3})", lines[1])
        if timing is None:
            raise ValueError("FFmpeg produced an invalid selectable subtitle file.")
        start = max(0, milliseconds(timing[1]) - offset)
        end = min(duration, milliseconds(timing[2]) - offset)
        if end > start:
            result.append(f"{len(result) + 1}\n{timestamp(start)} --> {timestamp(end)}\n" + "\n".join(lines[2:]) + "\n")
    staged.write_text("\n".join(result), encoding="utf-8")
    LOG.info("Prepared selectable preview subtitles: %s", staged)


def preflight_command(ffmpeg: Path, staged: Path) -> list[str]:
    """Ask libass to render a frame before committing to a long conversion."""
    if staged.name not in {"subtitle.ass", "subtitle.ssa", "subtitle.srt"}:
        raise ValueError("Unexpected staged subtitle name.")
    return [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=256x144:r=1:d=1",
            "-vf", f"subtitles={staged.name}", "-frames:v", "1", "-f", "null", "-"]
