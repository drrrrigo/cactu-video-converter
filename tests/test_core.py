"""Pure conversion and parser tests; no GUI or copyrighted media needed."""

import tempfile
import unittest
from pathlib import Path

from video_converter.conversion.planner import plan
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.command_builder import build_command, extraction_command
from video_converter.ffmpeg.progress import ProgressDecoder, parse_progress
from video_converter.media.compatibility import State, analyze
from video_converter.media.ffprobe_service import frame_rate, parse_probe, stream_label
from video_converter.models.conversion import CodecChoice, SubtitleMode
from video_converter.presets.web_kosmi import destination_for, settings_for


PROBE = {
    "format": {"format_name": "matroska,webm", "duration": "120.5", "size": "4000"},
    "streams": [
        {"index": 0, "codec_type": "video", "codec_name": "hevc", "profile": "Main 10",
         "width": 1920, "height": 1080, "avg_frame_rate": "24000/1001", "pix_fmt": "yuv420p10le"},
        {"index": 1, "codec_type": "audio", "codec_name": "flac", "channels": 6,
         "channel_layout": "5.1", "tags": {"language": "jpn"}},
        {"index": 2, "codec_type": "attachment", "tags": {"filename": "font.ttf", "mimetype": "application/x-truetype-font"}},
        {"index": 3, "codec_type": "subtitle", "codec_name": "ass", "tags": {"language": "por", "title": "Portuguese Full"}},
        {"index": 4, "codec_type": "audio", "codec_name": "aac", "channels": 2,
         "tags": {"language": "eng", "title": "English"}},
        {"index": 5, "codec_type": "subtitle", "codec_name": "ass", "tags": {"language": "eng", "title": "Signs & Songs"}},
    ],
}


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "Móvie 'sample' (1).mkv"
        self.source.write_bytes(b"fixture")
        self.media = parse_probe(PROBE, self.source)
        self.settings = settings_for(self.source)

    def test_probe_indexes_and_labels(self) -> None:
        self.assertEqual(self.media.audios[1].index, 4)
        self.assertEqual(self.media.audios[1].ordinal, 1)
        self.assertEqual(self.media.subtitles[1].index, 5)
        self.assertEqual(self.media.subtitles[1].ordinal, 1)
        self.assertEqual(stream_label(self.media.subtitles[1]), "Signs & Songs — English — ASS")
        self.assertEqual(self.media.video.profile, "Main 10")
        self.assertAlmostEqual(self.media.video.fps, 23.976, places=3)
        self.assertEqual(self.media.duration, 120.5)

    def test_default_audio_disposition(self) -> None:
        source = dict(PROBE)
        streams = [dict(item) for item in PROBE["streams"]]
        streams[4]["disposition"] = {"default": 1}
        source["streams"] = streams
        media = parse_probe(source, self.source)
        self.assertEqual(media.preferred_audio.index, 4)
        self.assertEqual(plan(media, self.settings).audio_index, 4)

    def test_bad_frame_rates(self) -> None:
        for value in (None, "N/A", "0/0", "1/0", "garbage"):
            self.assertIsNone(frame_rate(value))

    def test_compatibility_and_preset_filename(self) -> None:
        result = analyze(self.media)
        self.assertEqual(result.video, State.NEEDS_CONVERSION)
        self.assertEqual(result.audio, State.NEEDS_CONVERSION)
        self.assertEqual(destination_for(self.source).name, "Móvie 'sample' (1)-Kosmi.mp4")

    def test_hevc_subtitle_burn_exact_mapping(self) -> None:
        settings = self.settings.customized(subtitle_mode=SubtitleMode.BURN, subtitle_index=5)
        resolved = plan(self.media, settings)
        self.assertFalse(resolved.video_copy)
        self.assertFalse(resolved.audio_copy)
        self.assertEqual((resolved.subtitle_index, resolved.subtitle_ordinal), (5, 1))
        command = build_command(resolved, Path("/tmp/ffmpeg"), Path("/tmp/output.mp4"),
                                subtitle_file=Path("/tmp/subtitle.ass"))
        self.assertIn("subtitles=subtitle.ass", command)
        self.assertEqual(command.count("-map"), 2)
        self.assertEqual(command[command.index("-map") + 1], "0:0")
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        extract = extraction_command(Path("/tmp/ffmpeg"), self.source, 5, Path("/tmp/subtitle.ass"))
        self.assertEqual(extract[extract.index("-map") + 1], "0:5")

    def test_remux_and_audio_only_conversion(self) -> None:
        source = dict(PROBE)
        source["streams"] = [dict(PROBE["streams"][0], codec_name="h264", pix_fmt="yuv420p"),
                             dict(PROBE["streams"][1], codec_name="aac")]
        compatible = parse_probe(source, self.source)
        resolved = plan(compatible, self.settings)
        self.assertTrue(resolved.video_copy)
        self.assertTrue(resolved.audio_copy)
        source["streams"][1] = dict(source["streams"][1], codec_name="flac")
        audio_conversion = plan(parse_probe(source, self.source), self.settings)
        self.assertTrue(audio_conversion.video_copy)
        self.assertFalse(audio_conversion.audio_copy)

    def test_validation_and_overwrite(self) -> None:
        self.assertRaises(ValidationError, plan, self.media,
                          self.settings.customized(video_codec=CodecChoice.COPY))
        self.settings.destination.write_bytes(b"old")
        self.assertRaises(ValidationError, plan, self.media, self.settings)
        self.assertIsNotNone(plan(self.media, self.settings, overwrite=True))

    def test_progress_chunks_eta(self) -> None:
        decoder = ProgressDecoder()
        self.assertEqual(decoder.feed("out_time_us=30000000\nspe"), [])
        events = decoder.feed("ed=2.0x\nprogress=continue\n")
        progress = parse_progress(events[0], 120)
        self.assertEqual(progress.fraction, 0.25)
        self.assertEqual(progress.eta_seconds, 45)
        self.assertIsNone(parse_progress({"speed": "N/A"}, None).eta_seconds)


if __name__ == "__main__":
    unittest.main()
