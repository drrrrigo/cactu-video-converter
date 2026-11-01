"""Preview derivation and real nonzero-start subtitle/audio timing."""

import array
import math
import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.conversion.preview_planner import (
    default_preview_start, parse_duration, parse_timestamp, plan_preview, validate_preview_sources,
)
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.command_builder import build_command, extraction_command
from video_converter.ffmpeg.progress import parse_progress
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.models.preview import PreviewSettings
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for
from video_converter.services.preview_store import PreviewStore


class PreviewUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "movie.mkv"
        self.source.write_bytes(b"fixture")
        self.media = parse_probe({"format": {"duration": "60", "format_name": "matroska"}, "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"index": 2, "codec_type": "audio", "codec_name": "aac", "channels": 2},
            {"index": 3, "codec_type": "subtitle", "codec_name": "ass"},
            {"index": 4, "codec_type": "subtitle", "codec_name": "subrip"},
        ]}, self.source)

    def test_parsing_defaults_and_duration_boundaries(self) -> None:
        self.assertEqual(parse_timestamp("00:10:00"), 600)
        self.assertEqual(parse_timestamp("01:02:03.125"), 3723.125)
        for invalid in ("10", "00:60:00", "-01:00:00", "nan", "00:00:60", "00:00:01.1234"):
            self.assertRaises(ValidationError, parse_timestamp, invalid)
        for valid in ("5", "30", 120):
            self.assertEqual(parse_duration(valid), float(valid))
        for invalid in ("oops", -1, 4, 121, float("nan"), True):
            self.assertRaises(ValidationError, parse_duration, invalid)
        self.assertEqual(default_preview_start(20), 0)
        self.assertEqual(default_preview_start(3600), 360)
        self.assertEqual(default_preview_start(9000), 600)
        base = plan(self.media, settings_for(self.source))
        preview = plan_preview(self.media, base, PreviewSettings(50, 30), self.root / "preview.mp4")
        self.assertEqual(preview.duration_seconds, 10)
        tiny = plan_preview(self.media, base, PreviewSettings(59, 30), self.root / "tiny.mp4")
        self.assertEqual(tiny.duration_seconds, 1)
        for invalid in (-1, 60, float("inf")):
            self.assertRaises(ValidationError, plan_preview, self.media, base,
                              PreviewSettings(invalid), self.root / "invalid.mp4")
        self.assertRaises(ValidationError, plan_preview, replace(self.media, duration=None), base,
                          PreviewSettings(0), self.root / "unknown.mp4")

    def test_snapshot_copy_policy_and_all_backends(self) -> None:
        base = plan(self.media, settings_for(self.source))
        preview = plan_preview(self.media, base, PreviewSettings(10), self.root / "preview.mp4")
        self.assertTrue(base.video_copy)
        self.assertTrue(base.audio_copy)
        self.assertFalse(preview.execution_plan.video_copy)
        self.assertFalse(preview.execution_plan.audio_copy)
        self.assertEqual(preview.execution_plan.duration, 30)
        self.assertEqual(base.destination, settings_for(self.source).destination)
        self.assertEqual(preview.conversion_plan, base)
        command = build_command(preview.execution_plan, Path("ffmpeg"), preview.output_path, preview=preview)
        self.assertLess(command.index("-ss"), command.index("-i"))
        self.assertEqual(command[command.index("-t") + 1], "30")
        self.assertNotIn("-af", command)
        self.assertIn("0:2", command)
        self.assertEqual(parse_progress({"out_time_us": "15000000", "speed": "2x"},
                                        preview.execution_plan.duration).fraction, 0.5)
        for backend in EncoderBackend:
            selection = EncoderSelection(backend, "/dev/dri/renderD128" if backend in {
                EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV} else None)
            cap = HardwareEncoderCapability(selection, "", backend.display_name, "linux", None, True)
            for index in (3, 4):
                settings = settings_for(self.source).customized(
                    subtitle_mode=SubtitleMode.BURN, subtitle_index=index,
                    volume_percent=300, encoding_engine=selection)
                conversion = plan(self.media, settings, capabilities=(cap,))
                preview = plan_preview(self.media, conversion, PreviewSettings(10), self.root / "sample.mp4",
                                       capabilities=(cap,))
                self.assertEqual(preview.execution_plan.subtitle_source, conversion.subtitle_source)
                self.assertEqual(preview.execution_plan.audio_processing, conversion.audio_processing)
                suffix = "srt" if index == 4 else "ass"
                command = build_command(preview.execution_plan, Path("ffmpeg"), preview.output_path,
                                        subtitle_file=Path(f"subtitle.{suffix}"), preview=preview)
                graph = command[command.index("-vf") + 1]
                self.assertIn(f"setpts=PTS+10/TB,subtitles=subtitle.{suffix},setpts=PTS-10/TB", graph)
                self.assertIn("volume=3.0", command[command.index("-af") + 1])
                extract = extraction_command(Path("ffmpeg"), self.source, index, Path(f"subtitle.{suffix}"),
                                             preview=preview)
                self.assertIn("-copyts", extract)
                self.assertIn(f"0:{index}", extract)
        selected_gpu = plan(self.media, settings_for(self.source).customized(
            encoding_engine=EncoderSelection(EncoderBackend.NVIDIA_NVENC)))
        self.assertRaises(ValidationError, plan_preview, self.media, selected_gpu,
                          PreviewSettings(0), self.root / "no-gpu.mp4")

    def test_sources_snapshot_and_preview_store_lifecycle(self) -> None:
        subtitle = self.root / "Português [字幕].ass"
        subtitle.write_text("[Script Info]\n", encoding="utf-8")
        settings = settings_for(self.source).customized(
            subtitle_mode=SubtitleMode.BURN, subtitle_source=ExternalSubtitleSource.from_path(subtitle))
        base = plan(self.media, settings)
        store = PreviewStore()
        self.addCleanup(store.cleanup)
        preview = plan_preview(self.media, base, PreviewSettings(10), store.allocate())
        preview.output_path.write_bytes(b"preview")
        store.commit(preview)
        self.assertTrue(store.latest.matches(base))
        failed = store.allocate()
        failed.write_bytes(b"incomplete")
        store.discard()
        self.assertTrue(preview.output_path.exists())
        self.assertFalse(failed.parent.exists())
        next_preview = plan_preview(self.media, base, PreviewSettings(20), store.allocate())
        next_preview.output_path.write_bytes(b"new preview")
        store.commit(next_preview)
        self.assertFalse(preview.output_path.exists())
        subtitle.write_text("changed", encoding="utf-8")
        self.assertFalse(store.latest.matches(base))
        self.assertRaises(ValidationError, validate_preview_sources, next_preview)
        store.cleanup()
        self.assertFalse(next_preview.output_path.exists())
        self.assertTrue(self.source.is_file())
        self.assertTrue(subtitle.is_file())


class PreviewIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        try:
            cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        except RuntimeError as exc:
            raise unittest.SkipTest("FFmpeg 9.0.2 development runtime unavailable") from exc
        cls.temp = tempfile.TemporaryDirectory(prefix="video-converter-preview-tests-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.srt = cls.root / "External Português.srt"
        cls.srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nEARLY\n\n"
                           "2\n00:00:08,000 --> 00:00:12,000\nCROSSING\n\n"
                           "3\n00:00:12,000 --> 00:00:14,000\nRIGHT EVENT\n\n"
                           "4\n00:00:39,000 --> 00:00:42,000\nEND EVENT\n", encoding="utf-8")
        cls.ass = cls.root / "External [ASS].ass"
        cls.ssa = cls.root / "External.ssa"
        for output in (cls.ass, cls.ssa):
            cls._run([str(cls.runtime.ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(cls.srt), str(output)])
        cls.source = cls.root / "movie.mkv"
        cls._run([str(cls.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                  "-f", "lavfi", "-i", "color=c=black:s=256x144:r=10:d=60",
                  "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=60,volume=0.1",
                  "-f", "lavfi", "-i", "aevalsrc=if(lt(t\\,12)\\,0\\,0.02*sin(2*PI*880*t)):s=48000:d=60",
                  "-i", str(cls.ass), "-i", str(cls.srt),
                  "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:s", "-map", "4:s",
                  "-c:v", "libx264", "-preset", "ultrafast", "-g", "20", "-pix_fmt", "yuv420p",
                  "-c:a", "flac", "-c:s:0", "ass", "-c:s:1", "srt", str(cls.source)])
        cls.media = cls._probe(cls.source)

    @classmethod
    def _run(cls, args: list[str]) -> bytes:
        return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout

    @classmethod
    def _probe(cls, path: Path):
        return parse_probe(cls._run([str(cls.runtime.ffprobe), "-v", "error", "-show_streams",
                                    "-show_format", "-of", "json", str(path)]).decode(), path)

    def _execute(self, conversion, preview=None, *, cancel=False):
        runner = ConversionRunner(self.runtime)
        completed, errors, cancelled, progress = [], [], [], []
        runner.completed.connect(lambda path: (completed.append(path), self.app.quit()))
        runner.failed.connect(lambda message, details: (errors.append(message + details), self.app.quit()))
        runner.cancelled.connect(lambda: (cancelled.append(True), self.app.quit()))
        runner.progress_changed.connect(progress.append)
        runner.start(self.media, conversion, preview=preview)
        workspace = Path(runner.workspace.name)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.app.quit)
        timer.start(60_000)
        if cancel:
            QTimer.singleShot(0, runner.cancel)
        self.app.exec()
        timer.stop()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertFalse(workspace.exists())
        self.assertFalse(list(conversion.destination.parent.glob(".video-converter-*.mp4")))
        self.assertFalse(errors, errors[0][-3000:] if errors else "")
        self.assertTrue(cancelled if cancel else completed, "Preview timed out")
        return runner, progress

    def _frame(self, path: Path, seconds: float) -> bytes:
        return self._run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                          "-ss", str(seconds), "-i", str(path), "-frames:v", "1",
                          "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"])

    def test_thirty_seconds_audio_gain_duration_and_sync(self) -> None:
        previews = []
        for volume in (100, 300):
            settings = settings_for(self.source).customized(audio_index=2, volume_percent=volume,
                subtitle_mode=SubtitleMode.BURN, subtitle_source=ExternalSubtitleSource.from_path(self.ass))
            conversion = plan(self.media, settings)
            preview = plan_preview(self.media, conversion, PreviewSettings(10, 30, False),
                                   self.root / f"thirty-{volume}.mp4")
            runner, progress = self._execute(preview.execution_plan, preview)
            output = self._probe(preview.output_path)
            self.assertAlmostEqual(output.duration, 30, delta=0.15)
            self.assertEqual((output.video.codec, output.video.pixel_format, output.video.width, output.video.height),
                             ("h264", "yuv420p", 256, 144))
            self.assertEqual(output.audios[0].codec, "aac")
            self.assertFalse(output.subtitles)
            self.assertEqual(runner.plan.duration, 30)
            self.assertTrue(progress)
            self.assertGreaterEqual(progress[-1].fraction, 0.99)
            samples = array.array("f")
            samples.frombytes(self._run([str(self.runtime.ffmpeg), "-v", "error", "-i", str(preview.output_path),
                "-map", "0:a:0", "-ar", "48000", "-ac", "1", "-f", "f32le", "pipe:1"]))
            def rms(values):
                return math.sqrt(sum(x*x for x in values) / len(values))
            self.assertLess(rms(samples[4800:72000]), 0.0001, "Wrong audio track or cut timing")
            self.assertGreater(rms(samples[144000:192000]), 0.005)
            previews.append(rms(samples[144000:192000]))
        self.assertAlmostEqual(previews[1] / previews[0], 3, delta=0.15)

    def test_subtitle_movie_clock_for_embedded_and_external_sources(self) -> None:
        sources = [("embedded-ass", {"subtitle_index": 3}), ("embedded-srt", {"subtitle_index": 4})]
        sources += [(f"external-{path.suffix[1:]}", {"subtitle_source": ExternalSubtitleSource.from_path(path)})
                    for path in (self.ass, self.ssa, self.srt)]
        for name, selection in sources:
            with self.subTest(source=name):
                settings = settings_for(self.source).customized(destination=self.root / f"full-{name}.mp4",
                    subtitle_mode=SubtitleMode.BURN, **selection)
                conversion = plan(self.media, settings)
                self._execute(conversion)
                preview = plan_preview(self.media, conversion, PreviewSettings(10, 5, False),
                                       self.root / f"timing-{name}.mp4")
                self._execute(preview.execution_plan, preview)
                for moment in (0.5, 2.5, 4.5):
                    actual = self._frame(preview.output_path, moment)
                    expected = self._frame(conversion.destination, moment + 10)
                    self.assertEqual(len(actual), len(expected))
                    self.assertLess(sum(abs(a-b) for a, b in zip(actual, expected)) / len(actual), 2)
                    visible = sum(pixel > 60 for pixel in actual)
                    if moment < 4:
                        self.assertGreater(visible, 20, "Movie-time subtitle is missing")
                    else:
                        self.assertEqual(visible, 0, "Wrong-time subtitle was rendered")

    def test_end_of_file_and_cancellation(self) -> None:
        conversion = plan(self.media, settings_for(self.source))
        preview = plan_preview(self.media, conversion, PreviewSettings(50, 30, False), self.root / "eof.mp4")
        self._execute(preview.execution_plan, preview)
        self.assertAlmostEqual(self._probe(preview.output_path).duration, 10, delta=0.15)
        settings = settings_for(self.source).customized(subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(self.srt))
        conversion = plan(self.media, settings)
        preview = plan_preview(self.media, conversion, PreviewSettings(10, 30, False), self.root / "cancel.mp4")
        self._execute(preview.execution_plan, preview, cancel=True)
        self.assertFalse(preview.output_path.exists())
        self.assertTrue(self.srt.is_file())

    def test_selectable_subtitle_preview_clips_crossing_events(self) -> None:
        for index in (3, 4):
            conversion = plan(self.media, settings_for(self.source).customized(
                subtitle_mode=SubtitleMode.SELECTABLE, subtitle_index=index))
            preview = plan_preview(self.media, conversion, PreviewSettings(10, 5, False),
                                   self.root / f"selectable-{index}.mp4")
            self._execute(preview.execution_plan, preview)
            result = self._run([str(self.runtime.ffmpeg), "-v", "error", "-i", str(preview.output_path),
                                "-map", "0:s:0", "-f", "srt", "pipe:1"]).decode()
            self.assertIn("00:00:00,000 --> 00:00:02,000\nCROSSING", result)
            self.assertIn("00:00:02,000 --> 00:00:04,000\nRIGHT EVENT", result)
            self.assertNotIn("EARLY", result)
