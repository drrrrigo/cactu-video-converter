"""Measured two-pass normalization, cache identity, and real media lifecycle."""

import array
import json
import math
import os
import subprocess
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QSettings, QTimer
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.conversion.preview_planner import plan_preview
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.audio_filters import build_audio_filters
from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.loudness import analysis_command, parse_measurements, parse_result
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.ffmpeg.progress import parse_progress
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.audio import AudioProcessingMode, AudioProcessingPlan, LoudnormFilter, VolumeFilter
from video_converter.models.conversion import CodecChoice, SubtitleMode
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.models.loudness import LoudnessMeasurements, LoudnessPreset, LoudnessTarget, target_for
from video_converter.models.preview import PreviewSettings
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for
from video_converter.services.loudness_cache import LoudnessCache, cache_key
from video_converter.ui.main_window import MainWindow

NORMALIZE = AudioProcessingMode.LOUDNESS_NORMALIZATION
MEASURED = LoudnessMeasurements(-30.1, -20.0, 2.3, -40.1, 0.1)
PAYLOAD = {"input_i": "-30.1", "input_tp": "-20.0", "input_lra": "2.3",
           "input_thresh": "-40.1", "target_offset": "0.1", "output_i": "-16.0",
           "output_tp": "-5.9", "output_lra": "2.3", "output_thresh": "-26.0",
           "normalization_type": "linear"}


class LoudnessUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "movie.mkv"
        self.source.write_bytes(b"fixture")
        self.binary = self.root / "ffmpeg"
        self.binary.write_bytes(b"runtime")
        self.runtime = FFmpegRuntime(self.binary, self.binary, "9.0.2", "9.0.2", True)
        self.media = parse_probe({"format": {"duration": "60", "format_name": "matroska"}, "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"index": 2, "codec_type": "audio", "codec_name": "aac", "channels": 6, "sample_rate": "48000"},
            {"index": 4, "codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "44100"},
            {"index": 5, "codec_type": "subtitle", "codec_name": "ass"},
        ]}, self.source)
        self.settings = settings_for(self.source).customized(audio_processing_mode=NORMALIZE)

    def test_presets_ranges_and_mutual_exclusion(self):
        for preset, integrated in ((LoudnessPreset.MOVIE_WEB, -16), (LoudnessPreset.LOUDER, -14),
                                   (LoudnessPreset.CONSERVATIVE, -18)):
            target = target_for(preset)
            target.validate()
            self.assertEqual((target.integrated_lufs, target.true_peak_dbtp, target.loudness_range_lu),
                             (integrated, -1.5, 11))
        for field, invalids in (("integrated_lufs", [-71, -4, float("nan"), True]),
                               ("true_peak_dbtp", [-10, 0.1, float("inf")]),
                               ("loudness_range_lu", [0, 51, "11"])):
            for value in invalids:
                with self.subTest(field=field, value=value):
                    self.assertRaises(ValidationError, plan, self.media,
                                      replace(self.settings, loudness_target=replace(LoudnessTarget(), **{field: value})))
        processing = plan(self.media, self.settings.customized(volume_percent=300)).audio_processing
        self.assertEqual(processing.volume_percent, 100)
        self.assertFalse(processing.limiter_active)
        self.assertFalse(processing.prevent_clipping)
        self.assertRaises(ValueError, AudioProcessingPlan, filters=(VolumeFilter(200), LoudnormFilter(LoudnessTarget())),
                          mode=NORMALIZE)
        self.assertRaises(ValueError, build_audio_filters, processing)
        graph = build_audio_filters(processing.with_measurements(MEASURED))
        self.assertIn("measured_I=-30.1", graph)
        self.assertIn("offset=0.1:linear=true", graph)
        self.assertTrue(graph.endswith("aresample=48000"))
        self.assertNotIn("volume=", graph)
        self.assertNotIn("alimiter", graph)

    def test_copy_selected_audio_and_preview_analysis(self):
        original = plan(self.media, settings_for(self.source))
        self.assertTrue(original.video_copy and original.audio_copy)
        selected = plan(self.media, self.settings.customized(audio_index=4))
        self.assertTrue(selected.video_copy)
        self.assertFalse(selected.audio_copy)
        self.assertRaises(ValidationError, plan, self.media, self.settings.customized(audio_codec=CodecChoice.COPY))
        self.assertRaises(ValidationError, plan, replace(self.media, audios=()), self.settings)
        command = build_command(selected, self.binary, self.root / "out.mp4",
                                audio_processing=selected.audio_processing.with_measurements(MEASURED))
        self.assertIn("0:4", command)
        self.assertEqual(command[command.index("-c:v") + 1], "copy")
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        self.assertIn("aresample=44100", command[command.index("-af") + 1])
        preview = plan_preview(self.media, selected, PreviewSettings(10, 5), self.root / "sample.mp4")
        command = analysis_command(preview.execution_plan, self.binary)
        self.assertIn("0:4", command)
        for flag in ("-vn", "-sn", "-dn"):
            self.assertIn(flag, command)
        for flag in ("-ss", "-t", "-vf", "-c:v"):
            self.assertNotIn(flag, command)
        self.assertEqual(command[-3:], ["-f", "null", "-"])
        mismatched = plan(self.media, self.settings.customized(audio_index=2)).audio_processing.with_measurements(MEASURED)
        self.assertRaises(ValueError, build_command, selected, self.binary, self.root / "out.mp4",
                          audio_processing=mismatched)

    def test_all_video_backends_and_channel_filter_order(self):
        for backend in EncoderBackend:
            selection = EncoderSelection(backend, "/dev/dri/renderD128" if backend in {
                EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV} else None)
            cap = HardwareEncoderCapability(selection, "", backend.display_name, "linux", None, True)
            conversion = plan(self.media, self.settings.customized(encoding_engine=selection,
                subtitle_mode=SubtitleMode.BURN, subtitle_index=5, audio_channels=2), capabilities=(cap,))
            self.assertFalse(conversion.video_copy or conversion.audio_copy)
            graph = build_audio_filters(conversion.audio_processing, analysis=True)
            self.assertTrue(graph.startswith("aformat=channel_layouts=stereo,loudnorm="))
            command = build_command(conversion, self.binary, self.root / "out.mp4", subtitle_file=Path("subtitle.ass"),
                                    audio_processing=conversion.audio_processing.with_measurements(MEASURED))
            self.assertIn("subtitles=subtitle.ass", command[command.index("-vf") + 1])
            self.assertIn("aformat=channel_layouts=stereo,loudnorm=", command[command.index("-af") + 1])

    def test_parser_noisy_json_and_invalid_payloads(self):
        noise = "ffmpeg version 9.0.2\n[audio] {not json}\n{\"other\": 1}\n[Parsed_loudnorm_0 @ 0xabcd]\n"
        self.assertEqual(parse_measurements(noise + json.dumps(PAYLOAD, indent=2) + "\ntrailing logs"), MEASURED)
        self.assertEqual(parse_result(json.dumps(PAYLOAD)).normalization_type, "linear")
        malformed = ["", "{\"input_i\": -30", "{\"other\": 0}"]
        for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
            missing = dict(PAYLOAD)
            del missing[key]
            malformed.append(json.dumps(missing))
            for value in ("NaN", "inf", "-inf", "bad", None, True):
                malformed.append(json.dumps({**PAYLOAD, key: value}))
        with self.assertLogs("video_converter.ffmpeg.loudness", level="ERROR"):
            for payload in malformed:
                self.assertRaises(ValueError, parse_measurements, payload)

    def test_cache_identity_and_bounded_storage(self):
        conversion = plan(self.media, self.settings)
        cache = LoudnessCache(2)
        key = cache_key(conversion, self.runtime)
        cache.put(key, MEASURED)
        self.assertEqual(cache.get(key), MEASURED)
        for changes in ({"audio_index": 4}, {"audio_channels": 2},
                        {"loudness_target": target_for(LoudnessPreset.LOUDER)},
                        {"loudness_target": replace(LoudnessTarget(), true_peak_dbtp=-2)},
                        {"loudness_target": replace(LoudnessTarget(), loudness_range_lu=12)}):
            self.assertNotEqual(key, cache_key(plan(self.media, self.settings.customized(**changes)), self.runtime))
        self.source.write_bytes(b"source changed")
        changed = cache_key(conversion, self.runtime)
        self.assertIsNone(cache.get(changed))
        cache.put(changed, MEASURED)
        runtime_key = cache_key(conversion, replace(self.runtime, ffmpeg_version="9.0.2 rebuild"))
        cache.put(runtime_key, MEASURED)
        self.assertEqual(len(cache), 2)
        self.assertIsNone(cache.get(key))
        other = self.root / "other.mkv"
        other.write_bytes(self.source.read_bytes())
        self.assertNotEqual(changed, cache_key(replace(conversion, source=other), self.runtime))

    def test_missing_filter_keeps_runtime_available(self):
        def command(args, **kwargs):
            if "-version" in args:
                output = "ffmpeg version 9.0.2\n"
            elif "-encoders" in args:
                output = " V libx264 video\n A aac audio\n"
            else:
                output = " ... subtitles V->V subtitles\n"
            return subprocess.CompletedProcess(args, 0, output, "")
        with patch.object(FFmpegRuntime, "bundled_directory", return_value=self.root), \
                patch("video_converter.ffmpeg.runtime.subprocess.run", side_effect=command), \
                patch("video_converter.ffmpeg.runtime.shutil.which", return_value=str(self.binary)), \
                self.assertLogs("video_converter.ffmpeg.runtime", level="ERROR"):
            runtime = FFmpegRuntime.locate(allow_system_development=True)
        self.assertFalse(runtime.loudnorm_available)


class LoudnessIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        if not cls.runtime.loudnorm_available:
            raise unittest.SkipTest("loudnorm unavailable")
        cls.temp = tempfile.TemporaryDirectory(prefix="video-converter-loudness-tests-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "quiet.mkv"
        # Separate frequencies identify channel order; a one-second silent lead
        # also detects timing shifts. The alternate track has a different level.
        tones = "|".join(f"if(lt(t\\,1)\\,0\\,0.01*sin(2*PI*{frequency}*t))" for frequency in (220, 330, 440, 55, 660, 770))
        cls._run([str(cls.runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
                  "color=c=black:s=256x144:r=10:d=12", "-f", "lavfi", "-i",
                  f"aevalsrc={tones}:s=48000:d=12:c=5.1", "-f", "lavfi", "-i",
                  "sine=frequency=1000:sample_rate=44100:duration=12,volume=0.5",
                  "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                  "-c:a", "flac", str(cls.source)])
        cls.media = cls._probe(cls.source)

    @classmethod
    def _run(cls, args):
        return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout

    @classmethod
    def _probe(cls, path):
        return parse_probe(cls._run([str(cls.runtime.ffprobe), "-v", "error", "-show_format",
                                   "-show_streams", "-of", "json", str(path)]).decode(), path)

    def _plan(self, name, **changes):
        return plan(self.media, settings_for(self.source).customized(destination=self.root / f"{name}.mp4",
                    audio_processing_mode=NORMALIZE, **changes))

    def _execute(self, runner, conversion, *, preview=None, cancel_stage=None, expect_error=False,
                 pause_stage=None):
        completed, failed, cancelled, stages, progress, commands = [], [], [], [], [], []
        def stage(label):
            stages.append(label)
            if runner.phase == cancel_stage:
                QTimer.singleShot(0, runner.cancel)
        connections = [(runner.completed, lambda path: (completed.append(path), self.app.quit())),
                       (runner.failed, lambda message, details: (failed.append(message + details), self.app.quit())),
                       (runner.cancelled, lambda: (cancelled.append(True), self.app.quit())),
                       (runner.stage_changed, stage),
                       (runner.progress_changed, lambda item: progress.append((runner.phase, item)))]
        for signal, callback in connections:
            signal.connect(callback)
        launch = runner._launch
        def record(command):
            commands.append(command)
            launch(command)
            if runner.phase == pause_stage:
                def pause():
                    runner.pause_or_resume()
                    self.assertTrue(runner.paused)
                    QTimer.singleShot(60, runner.pause_or_resume)
                runner.process.started.connect(pause)
        started = time.monotonic()
        with patch.object(runner, "_launch", side_effect=record):
            runner.start(self.media, conversion, preview=preview)
            workspace = Path(runner.workspace.name)
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(self.app.quit)
            timer.start(60_000)
            self.app.exec()
            timer.stop()
        for signal, callback in connections:
            signal.disconnect(callback)
        if not (completed or failed or cancelled):
            runner.cancel()
            self.fail("Loudness operation timed out")
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertFalse(workspace.exists())
        self.assertFalse(list(conversion.destination.parent.glob(".video-converter-*.mp4")))
        if expect_error:
            self.assertTrue(failed)
        else:
            self.assertFalse(failed, failed[0][-4000:] if failed else "")
            self.assertTrue(cancelled if cancel_stage else completed)
        return stages, progress, commands, time.monotonic() - started

    def _measure(self, source):
        args = [str(self.runtime.ffmpeg), "-hide_banner", "-i", str(source), "-map", "0:a:0", "-vn",
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]
        return parse_measurements(subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stderr)

    def _samples(self, source, channel=0):
        samples = array.array("f")
        samples.frombytes(self._run([str(self.runtime.ffmpeg), "-v", "error", "-i", str(source),
            "-map", "0:a:0", "-af", f"pan=mono|c0=c{channel}", "-ar", "48000", "-f", "f32le", "pipe:1"]))
        return samples

    def test_quiet_surround_loudness_channels_sample_rate_and_sync(self):
        runner = ConversionRunner(self.runtime)
        conversion = self._plan("surround")
        self.assertTrue(conversion.video_copy)
        stages, progress, commands, elapsed = self._execute(runner, conversion)
        self.assertIn("Analyzing Loudness", stages[0])
        self.assertIn("Step 2 of 2", stages[1])
        self.assertTrue(any(phase == "analyzing" for phase, _ in progress))
        self.assertTrue(any(phase == "converting" for phase, _ in progress))
        self.assertEqual(commands[0], analysis_command(conversion, self.runtime.ffmpeg))
        result = self._measure(conversion.destination)
        self.assertAlmostEqual(result.input_i, -16, delta=0.7)
        self.assertLessEqual(result.input_tp, -1.5 + 0.7)
        output = self._probe(conversion.destination)
        self.assertEqual((output.audios[0].channels, output.audios[0].sample_rate), (6, 48000))
        self.assertEqual(output.audios[0].layout, "5.1")
        self.assertAlmostEqual(output.duration, 12, delta=0.15)
        self.assertIsNotNone(runner.loudness_report.result)
        for channel, frequency in enumerate((220, 330, 440, 55, 660, 770)):
            samples = self._samples(conversion.destination, channel)
            self.assertLess(max(abs(x) for x in samples[4800:40000]), 0.001)
            segment = samples[96000:100800]
            strengths = [abs(sum(x * complex(math.cos(2*math.pi*f*i/48000),
                                              -math.sin(2*math.pi*f*i/48000))
                                 for i, x in enumerate(segment))) for f in (220, 330, 440, 55, 660, 770)]
            self.assertEqual(strengths.index(max(strengths)), channel, "Channel order changed")
        raw = json.loads(self._run([str(self.runtime.ffprobe), "-v", "error", "-show_streams", "-of", "json",
                                   str(conversion.destination)]))
        durations = [float(stream["duration"]) for stream in raw["streams"]]
        starts = [float(stream["start_time"]) for stream in raw["streams"]]
        self.assertLess(max(durations) - min(durations), 0.1)
        self.assertLess(max(starts) - min(starts), 0.05)
        print(f"\nLoudness fixture: 12s, analysis {runner.analysis_seconds:.2f}s "
              f"({12 / runner.analysis_seconds:.1f}x), two passes + verify {elapsed:.2f}s, "
              f"output {result.input_i} LUFS / {result.input_tp} dBTP")

    def test_preview_full_track_cache_reuse_and_invalidation(self):
        runner = ConversionRunner(self.runtime)
        base = self._plan("cached-full", audio_index=2)
        for number, start in enumerate((3, 6)):
            preview = plan_preview(self.media, base, PreviewSettings(start, 5, False), self.root / f"cache-{number}.mp4")
            stages, _, commands, _ = self._execute(runner, preview.execution_plan, preview=preview)
            if number == 0:
                self.assertNotIn("-ss", commands[0])
                self.assertNotIn("-t", commands[0])
                self.assertEqual(stages[0], "Step 1 of 2 — Analyzing Loudness...")
                self.assertFalse(runner.loudness_report.cache_hit)
            else:
                self.assertEqual(len(stages), 1)
                self.assertTrue(runner.loudness_report.cache_hit)
            self.assertEqual(self._probe(preview.output_path).audios[0].sample_rate, 44100)
            self.assertAlmostEqual(self._measure(preview.output_path).input_i, -16, delta=0.7)
        stages, _, _, _ = self._execute(runner, base)
        self.assertEqual(len(stages), 1)
        self.assertTrue(runner.loudness_report.cache_hit)
        for changed in (self._plan("changed-track", audio_index=1),
                        self._plan("changed-target", audio_index=2, loudness_target=target_for(LoudnessPreset.LOUDER))):
            stages, _, _, _ = self._execute(runner, changed)
            self.assertEqual(len(stages), 2)
            self.assertFalse(runner.loudness_report.cache_hit)
        stat = self.source.stat()
        try:
            os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            changed = self._plan("changed-file", audio_index=2)
            stages, _, _, _ = self._execute(runner, changed)
            self.assertEqual(len(stages), 2)
        finally:
            os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    def test_analysis_pause_resume_and_stage_progress_denominators(self):
        runner = ConversionRunner(self.runtime)
        base = self._plan("pause")
        preview = plan_preview(self.media, base, PreviewSettings(2, 5, False), self.root / "pause-preview.mp4")
        durations = []
        def progress(values, duration):
            durations.append((runner.phase, duration))
            return parse_progress(values, duration)
        with patch("video_converter.ffmpeg.runner.parse_progress", side_effect=progress):
            self._execute(runner, preview.execution_plan, preview=preview, pause_stage="analyzing")
        self.assertIn(("analyzing", 12), durations)
        self.assertIn(("converting", 5), durations)
        self.assertFalse(runner.paused)

    def test_missing_capability_fails_before_analysis_and_manual_still_works(self):
        runner = ConversionRunner(replace(self.runtime, loudnorm_available=False))
        self.assertRaisesRegex(ValueError, "unavailable", runner.start, self.media, self._plan("missing-filter"))
        self.assertIsNone(runner.workspace)
        conversion = plan(self.media, settings_for(self.source).customized(destination=self.root / "manual-no-loudnorm.mp4"))
        stages, _, commands, _ = self._execute(runner, conversion)
        self.assertEqual(len(stages), 1)
        self.assertFalse(any("loudnorm" in arg for command in commands for arg in command))

    def test_channel_conversion_matches_analysis_and_final_pass(self):
        runner = ConversionRunner(self.runtime)
        conversion = self._plan("stereo", audio_channels=2)
        self._execute(runner, conversion)
        output = self._probe(conversion.destination)
        self.assertEqual(output.audios[0].channels, 2)
        self.assertAlmostEqual(self._measure(conversion.destination).input_i, -16, delta=0.7)

    def test_true_peak_dynamic_fallback_and_subtitle_burn(self):
        source = self.root / "peaky.mkv"
        self._run([str(self.runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
                   "color=c=black:s=256x144:r=10:d=12", "-f", "lavfi", "-i",
                   "aevalsrc=0.02*sin(2*PI*440*t)+if(lt(mod(t\\,1)\\,0.005)\\,0.8*sin(2*PI*4000*t)\\,0):s=48000:d=12",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "flac", str(source)])
        subtitle = self.root / "Português.srt"
        subtitle.write_text("1\n00:00:01,000 --> 00:00:10,000\nLoudness test\n", encoding="utf-8")
        media = self._probe(source)
        conversion = plan(media, settings_for(source).customized(destination=self.root / "peaky-out.mp4",
            audio_processing_mode=NORMALIZE, subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(subtitle)))
        runner = ConversionRunner(self.runtime)
        original_media = self.media
        self.media = media
        try:
            self._execute(runner, conversion)
        finally:
            self.media = original_media
        self.assertEqual(runner.loudness_report.result.normalization_type, "dynamic")
        self.assertLessEqual(self._measure(conversion.destination).input_tp, -0.8)
        self.assertFalse(self._probe(conversion.destination).subtitles)
        frame = self._run([str(self.runtime.ffmpeg), "-v", "error", "-ss", "2", "-i", str(conversion.destination),
                           "-frames:v", "1", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"])
        self.assertGreater(sum(pixel > 80 for pixel in frame), 20)

    def test_cancel_analysis_and_encoding_cache_policy(self):
        runner = ConversionRunner(self.runtime)
        first = self._plan("cancel-analysis")
        _, _, commands, _ = self._execute(runner, first, cancel_stage="analyzing")
        self.assertEqual(len(commands), 1)
        self.assertEqual(len(runner.loudness_cache), 0)
        self.assertIsNone(runner.loudness_report)
        self.assertFalse(first.destination.exists())
        second = self._plan("cancel-pass-two")
        self._execute(runner, second, cancel_stage="converting")
        self.assertEqual(len(runner.loudness_cache), 1)
        self.assertFalse(second.destination.exists())
        final = self._plan("after-cancel")
        stages, _, _, _ = self._execute(runner, final)
        self.assertEqual(len(stages), 1)
        self.assertTrue(runner.loudness_report.cache_hit)

    def test_silent_measurements_fail_without_second_pass(self):
        source = self.root / "silent.mkv"
        self._run([str(self.runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
                   "color=c=black:s=256x144:r=10:d=5", "-f", "lavfi", "-i",
                   "anullsrc=r=48000:cl=stereo:d=5", "-c:v", "libx264", "-c:a", "flac", str(source)])
        media = self._probe(source)
        conversion = plan(media, settings_for(source).customized(audio_processing_mode=NORMALIZE))
        runner = ConversionRunner(self.runtime)
        self.media = media
        with self.assertLogs(level="ERROR"):
            _, _, commands, _ = self._execute(runner, conversion, expect_error=True)
        self.assertEqual(len(commands), 1)
        self.assertEqual(len(runner.loudness_cache), 0)
        self.assertFalse(conversion.destination.exists())


class LoudnessUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.runtime = FFmpegRuntime.locate(allow_system_development=True)

    def test_modes_presets_retained_gain_reset_and_missing_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "movie.mkv"
            source.write_bytes(b"fixture")
            media = parse_probe({"format": {"format_name": "matroska", "duration": "60"}, "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2}]}, source)
            for available in (True, False):
                with patch.object(MainWindow, "_detect_hardware"):
                    window = MainWindow(replace(self.runtime, loudnorm_available=available))
                    window.storage = QSettings(str(root / "ui.ini"), QSettings.Format.IniFormat)
                    window.media = media
                    window._populate_media(media)
                    self.assertEqual(window.settings.audio_processing_mode, AudioProcessingMode.MANUAL_VOLUME)
                    self.assertEqual(window.audio_mode.model().item(1).isEnabled(), available)
                    if available:
                        window.volume_slider.setValue(230)
                        window.audio_mode.setCurrentIndex(1)
                        self.assertFalse(window.volume_slider.isEnabled())
                        self.assertFalse(window.prevent_clipping.isEnabled())
                        self.assertEqual(window.current_plan.audio_processing.volume_percent, 100)
                        self.assertIn("Loudness: -16 LUFS", window.summary.text())
                        window.loudness_preset.setCurrentIndex(1)
                        self.assertEqual(window.settings.loudness_target.integrated_lufs, -14)
                        window.loudness_preset.setCurrentIndex(3)
                        window.loudness_lra.setValue(15)
                        self.assertEqual(window.settings.loudness_target.loudness_range_lu, 15)
                        window.audio_mode.setCurrentIndex(0)
                        self.assertTrue(window.volume_slider.isEnabled())
                        self.assertEqual(window.volume_slider.value(), 230)
                        window._populate_media(media)
                        self.assertEqual(window.volume_slider.value(), 100)
                        self.assertEqual(window.audio_mode.currentIndex(), 0)
                        window.runner.phase = "analyzing"
                        self.assertTrue(window._operation_busy())
                        window._on_state("Step 1 of 2 — Analyzing Loudness...")
                        self.assertTrue(window.pause_button.isEnabled())
                        window.runner.phase = "done"
                    window.close()
                    window.deleteLater()
                    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                    self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
