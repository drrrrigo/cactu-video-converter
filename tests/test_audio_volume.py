"""Volume planning, FFmpeg syntax and synthetic audio behavior."""

import array
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_converter.conversion.planner import plan
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.audio_filters import build_audio_filters, volume_multiplier
from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.audio import plan_audio_processing
from video_converter.models.conversion import CodecChoice, SubtitleMode
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for


class AudioVolumeUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mkv"
        self.source.write_bytes(b"fixture")
        self.media = parse_probe({"format": {"format_name": "matroska"}, "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2},
            {"index": 2, "codec_type": "audio", "codec_name": "flac", "channels": 6},
        ]}, self.source)

    def test_percent_boundaries_and_filter_order(self) -> None:
        expected = {0: "0.0", 1: "0.01", 50: "0.5", 99: "0.99", 100: "1.0",
                    101: "1.01", 125: "1.25", 150: "1.5", 175: "1.75", 200: "2.0",
                    225: "2.25", 250: "2.5", 275: "2.75", 299: "2.99", 300: "3.0"}
        for percent, multiplier in expected.items():
            self.assertEqual(plan(self.media, settings_for(self.source).customized(
                volume_percent=percent)).audio_processing.volume_percent, percent)
            self.assertEqual(volume_multiplier(percent), multiplier)
            processing = plan_audio_processing(percent, True)
            chain = build_audio_filters(processing)
            if percent == 100:
                self.assertIsNone(chain)
                self.assertFalse(processing.requires_encoding)
            elif percent > 100:
                self.assertEqual(chain, f"volume={multiplier},alimiter=limit=0.85:level=false:latency=true")
                self.assertTrue(processing.limiter_active)
            else:
                self.assertEqual(chain, f"volume={multiplier}")
        self.assertEqual(build_audio_filters(plan_audio_processing(150, False)), "volume=1.5")
        self.assertEqual(build_audio_filters(plan_audio_processing(300, False)), "volume=3.0")

    def test_copy_rules_and_exact_selected_track(self) -> None:
        settings = settings_for(self.source)
        neutral = plan(self.media, settings)
        self.assertTrue(neutral.video_copy)
        self.assertTrue(neutral.audio_copy)
        neutral_args = build_command(neutral, Path("ffmpeg"), self.root / "neutral.mp4")
        self.assertNotIn("-af", neutral_args)
        self.assertEqual(neutral_args[neutral_args.index("-c:a") + 1], "copy")
        for percent in (0, 99, 101, 150, 200, 225, 250, 275, 299, 300):
            boosted = plan(self.media, settings.customized(volume_percent=percent))
            self.assertTrue(boosted.video_copy)
            self.assertFalse(boosted.audio_copy)
            args = build_command(boosted, Path("ffmpeg"), self.root / "boost.mp4")
            self.assertEqual(args[args.index("-c:v") + 1], "copy")
            self.assertEqual(args[args.index("-c:a") + 1], "aac")
            self.assertIn("-af", args)
            self.assertEqual(args[args.index("-map") + 1], "0:0")
            self.assertIn("0:1", args)
            self.assertNotIn("0:2", args)
            self.assertIn("+faststart", args)
        selected = plan(self.media, settings.customized(audio_index=2, volume_percent=300))
        args = build_command(selected, Path("ffmpeg"), self.root / "selected.mp4")
        self.assertIn("0:2", args)
        self.assertNotIn("0:1", args)
        self.assertFalse(selected.audio_copy)

    def test_validation_and_subtitle_hardware_independence(self) -> None:
        settings = settings_for(self.source)
        for invalid in (-1, 301, 400, 500, 150.0, True):
            with self.assertRaisesRegex(ValidationError, "between 0% and 300%"):
                plan(self.media, settings.customized(volume_percent=invalid))
        with self.assertRaisesRegex(ValidationError, "must be re-encoded"):
            plan(self.media, settings.customized(audio_codec=CodecChoice.COPY,
                                                volume_percent=300))
        for backend in EncoderBackend:
            selection = EncoderSelection(backend, "/dev/dri/renderD128" if backend in
                                         {EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV} else None)
            cap = HardwareEncoderCapability(selection, "", backend.display_name, "linux", None, True)
            media = parse_probe({"format": {"format_name": "matroska"}, "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "hevc", "pix_fmt": "yuv420p10le"},
                {"index": 1, "codec_type": "audio", "codec_name": "flac", "channels": 6},
            ]}, self.source)
            resolved = plan(media, settings.customized(encoding_engine=selection,
                                                       volume_percent=300), capabilities=(cap,))
            args = build_command(resolved, Path("ffmpeg"), self.root / "out.mp4")
            self.assertIn("-af", args)
            self.assertEqual(args[args.index("-af") + 1],
                             "volume=3.0,alimiter=limit=0.85:level=false:latency=true")
            subtitle = self.root / "external.ass"
            subtitle.write_text("[Script Info]\nTitle: Test\n", encoding="utf-8")
            burned = plan(media, settings.customized(
                encoding_engine=selection, volume_percent=300,
                subtitle_mode=SubtitleMode.BURN,
                subtitle_source=ExternalSubtitleSource.from_path(subtitle)), capabilities=(cap,))
            args = build_command(burned, Path("ffmpeg"), self.root / "burned.mp4",
                                 subtitle_file=Path("/tmp/subtitle.ass"))
            self.assertIn("subtitles=subtitle.ass", " ".join(args))
            self.assertIn("-af", args)
            self.assertFalse(burned.video_copy)


class AudioVolumeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        except RuntimeError as exc:
            raise unittest.SkipTest("FFmpeg 9.0.2 development runtime unavailable") from exc

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _run(self, args: list[str]) -> bytes:
        return subprocess.run(args, check=True, capture_output=True, timeout=30).stdout

    def _media(self, source: Path):
        raw = self._run([str(self.runtime.ffprobe), "-v", "error", "-show_streams",
                         "-show_format", "-of", "json", str(source)])
        return parse_probe(raw.decode(), source)

    def _samples(self, source: Path) -> array.array:
        raw = self._run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                         "-i", str(source), "-map", "0:a:0", "-f", "f32le", "-ac", "1",
                         "-ar", "48000", "pipe:1"])
        samples = array.array("f")
        samples.frombytes(raw)
        return samples

    def _convert(self, source: Path, percent: int, protect: bool) -> tuple[Path, object]:
        media = self._media(source)
        settings = settings_for(source).customized(
            destination=self.root / f"volume-{percent}-{protect}.mp4",
            volume_percent=percent, prevent_clipping=protect)
        resolved = plan(media, settings)
        args = build_command(resolved, self.runtime.ffmpeg, settings.destination)
        self._run(args)
        return settings.destination, resolved

    def test_linear_gain_video_copy_and_limiter_ceiling(self) -> None:
        quiet = self.root / "quiet.mkv"
        self._run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                   "-f", "lavfi", "-i", "color=c=black:s=256x144:r=10:d=2",
                   "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=2,volume=0.1",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "flac",
                   "-ac", "2", str(quiet)])
        original, neutral = self._convert(quiet, 100, True)
        boosted, increased = self._convert(quiet, 300, False)
        muted, muted_plan = self._convert(quiet, 0, True)
        self.assertTrue(neutral.video_copy)
        self.assertTrue(increased.video_copy)
        self.assertFalse(increased.audio_copy)
        normal_samples = self._samples(original)
        boosted_samples = self._samples(boosted)
        def rms(samples: array.array) -> float:
            return math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        ratio = rms(boosted_samples) / rms(normal_samples)
        self.assertGreater(ratio, 2.85)
        self.assertLess(ratio, 3.15)
        self.assertAlmostEqual(self._media(boosted).duration, self._media(original).duration, delta=0.03)
        self.assertLessEqual(abs(len(boosted_samples) - len(normal_samples)), 1024)
        self.assertTrue(all(math.isfinite(sample) for sample in boosted_samples))
        self.assertEqual(self._media(boosted).video.codec, "h264")
        self.assertEqual(self._media(boosted).audios[0].codec, "aac")
        self.assertEqual(self._media(boosted).audios[0].channels, 2)
        self.assertEqual(self._media(boosted).audios[0].sample_rate, 48000)
        self.assertFalse(muted_plan.audio_copy)
        self.assertEqual(self._media(muted).audios[0].codec, "aac")
        self.assertLess(max(abs(sample) for sample in self._samples(muted)), 0.001)

        loud = self.root / "loud.mkv"
        self._run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                   "-f", "lavfi", "-i", "color=c=black:s=256x144:r=10:d=2",
                   "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=2,volume=7",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "flac", str(loud)])
        limited, resolved = self._convert(loud, 300, True)
        self.assertTrue(resolved.audio_processing.limiter_active)
        limited_samples = self._samples(limited)
        self.assertTrue(all(math.isfinite(sample) for sample in limited_samples))
        peak = max(abs(sample) for sample in limited_samples)
        self.assertLess(peak, 1.02)
        self.assertGreater(peak, 0.5)
        self.assertAlmostEqual(self._media(limited).duration, 2.0, delta=0.15)
        self.assertEqual(self._media(limited).audios[0].channels, self._media(loud).audios[0].channels)

    def test_six_channel_layout_is_preserved(self) -> None:
        surround = self.root / "surround.mkv"
        self._run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                   "-f", "lavfi", "-i", "color=c=black:s=256x144:r=10:d=1",
                   "-f", "lavfi", "-i", "anullsrc=channel_layout=5.1:sample_rate=48000:d=1",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "flac", str(surround)])
        self.assertEqual(self._media(surround).audios[0].channels, 6)
        result, resolved = self._convert(surround, 300, True)
        self.assertTrue(resolved.video_copy)
        self.assertFalse(resolved.audio_copy)
        self.assertEqual(self._media(result).audios[0].channels, 6)
        self.assertEqual(self._media(result).audios[0].sample_rate, 48000)


if __name__ == "__main__":
    unittest.main()
