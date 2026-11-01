"""Copy user intent across files without copying concrete stream identities."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from video_converter.media.ffprobe_service import stream_label
from video_converter.models.conversion import SubtitleMode
from video_converter.models.job import ConversionJob
from video_converter.models.media import AudioStream, SubtitleStream
from video_converter.models.subtitle import EmbeddedSubtitleSource, ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for


def normalized_title(text: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def language(text: str) -> str:
    value = text.casefold().replace("_", "-")
    aliases = {"por": "pt", "eng": "en", "jpn": "ja", "spa": "es", "fra": "fr", "fre": "fr",
               "deu": "de", "ger": "de"}
    root, *region = value.split("-")
    root = aliases.get(root, root)
    return "-".join([root, *region]) if root not in {"und", "unknown", ""} else ""


def match_stream(source: AudioStream | SubtitleStream, candidates: tuple) -> tuple[object | None, str]:
    ranked = []
    src_lang, src_title = language(source.language), normalized_title(source.title)
    for candidate in candidates:
        dest_lang, dest_title = language(candidate.language), normalized_title(candidate.title)
        same_lang = bool(src_lang and dest_lang and (src_lang == dest_lang or (
            src_lang.split("-")[0] == dest_lang.split("-")[0] and ("-" not in src_lang or "-" not in dest_lang))))
        same_title = bool(src_title and src_title == dest_title)
        # Known contradictory languages are never resolved by title alone.
        if src_lang and dest_lang and not same_lang:
            continue
        if isinstance(source, SubtitleStream):
            # Full and Signs/Songs or forced subtitles are not interchangeable.
            if src_title and dest_title and not same_title:
                continue
            if candidate.forced != source.forced:
                continue
            rank = 4 if same_lang and same_title else 3 if same_title else 2 if same_lang else 0
            secondary = (candidate.codec == source.codec, candidate.default == source.default)
        else:
            rank = 4 if same_lang and same_title else 3 if same_lang else 2 if same_title else 0
            secondary = (candidate.channels == source.channels, candidate.layout == source.layout,
                         candidate.codec == source.codec)
        if rank:
            ranked.append(((rank, *secondary), candidate))
    if not ranked:
        return None, f"No safe match for {stream_label(source)}. Select a track explicitly."
    best = max(score for score, _ in ranked)
    matches = [candidate for score, candidate in ranked if score == best]
    if len(matches) != 1:
        return None, f"Ambiguous match for {stream_label(source)}. Select a track explicitly."
    return matches[0], ""


class BatchSettingsService:
    def apply_web_preset(self, job: ConversionJob) -> None:
        if not job.editable:
            return
        # Keep the job's output identity rather than propagating a source filename.
        job.settings = replace(settings_for(job.input_path), destination=job.settings.destination)
        job.stream_issues.clear()
        job.warnings = ()

    def copy(self, source: ConversionJob, destination: ConversionJob) -> None:
        if source.media is None or not destination.editable:
            return
        settings = source.settings
        issues: dict[str, str] = {}
        source_audio = source.media.audio_by_index(settings.audio_index) if settings.audio_index is not None else source.media.preferred_audio
        audio_index = None
        if source_audio is not None:
            matched, issue = match_stream(source_audio, destination.media.audios)
            if issue:
                issues["audio"] = issue
            elif matched:
                audio_index = matched.index
        subtitle_source = None
        if settings.subtitle_mode != SubtitleMode.NONE:
            selected = settings.subtitle_source
            if isinstance(selected, ExternalSubtitleSource):
                issues["subtitle"] = "External subtitle paths are not copied. Select this video's subtitle file."
            else:
                index = selected.stream_index if isinstance(selected, EmbeddedSubtitleSource) else settings.subtitle_index
                source_subtitle = source.media.subtitle_by_index(index) if index is not None else None
                if source_subtitle is None:
                    issues["subtitle"] = "Select a subtitle track for this video."
                else:
                    matched, issue = match_stream(source_subtitle, destination.media.subtitles)
                    if issue:
                        issues["subtitle"] = issue
                    elif matched:
                        subtitle_source = EmbeddedSubtitleSource(matched.index, matched.ordinal, matched.codec, stream_label(matched))
        # Frozen scalar settings may be reused by value; the settings record itself
        # is new and retains the destination's independent output filename/folder.
        destination.settings = replace(settings, destination=destination.settings.destination,
            audio_index=audio_index, subtitle_index=subtitle_source.stream_index if subtitle_source else None,
            subtitle_source=subtitle_source)
        destination.stream_issues = issues
        destination.warnings = tuple(issues.values())
