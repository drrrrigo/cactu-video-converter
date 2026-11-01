"""Opt-in short conversion on real GPU hardware."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer, QEventLoop
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.conversion.preview_planner import plan_preview
from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.models.preview import PreviewSettings
from video_converter.models.audio import AudioProcessingMode
from video_converter.ffmpeg.loudness import parse_measurements
from video_converter.models.queue import ConversionQueue, QueueState
from video_converter.models.job import JobStatus
from video_converter.services.queue_controller import QueueController
from unittest.mock import patch
import shutil
from video_converter.presets.web_kosmi import settings_for

try:
    import pytest
    pytestmark = pytest.mark.hardware
except ImportError:
    pass


@unittest.skipUnless(os.environ.get("VIDEO_CONVERTER_HARDWARE_TEST") == "1",
                     "Set VIDEO_CONVERTER_HARDWARE_TEST=1 on a GPU machine")
class PhysicalHardwareTests(unittest.TestCase):
    def test_sequential_queue_with_fresh_gpu_preflight_per_job(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        runtime = FFmpegRuntime.locate(allow_system_development=True)
        capabilities = tuple(cap for cap in HardwareEncoderDetector(runtime.ffmpeg).detect() if cap.available)
        if not capabilities:
            self.skipTest("No working GPU encoder")
        _app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory(prefix="converter-gpu-queue-") as folder:
            root = Path(folder)
            srt = root / "Português.srt"
            srt.write_text("1\n00:00:00,500 --> 00:00:05,500\nFila de conversão\n", encoding="utf-8")
            ass = root / "Português.ass"
            subprocess.run([str(runtime.ffmpeg), "-v", "error", "-i", str(srt), str(ass)],
                           check=True, capture_output=True, timeout=15)
            source = root / "First.mkv"
            subprocess.run([str(runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=256x144:r=10:d=6", "-f", "lavfi", "-i",
                "sine=frequency=440:sample_rate=48000:duration=6,volume=0.1", "-i", str(ass),
                "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "libx265", "-pix_fmt", "yuv420p10le",
                "-x265-params", "log-level=error", "-c:a", "ac3", "-c:s", "ass", str(source)],
                check=True, capture_output=True, timeout=30)
            second = root / "Second.mkv"
            shutil.copyfile(source, second)
            queue = ConversionQueue()
            runner = ConversionRunner(runtime)
            controller = QueueController(queue, runner, runtime)
            controller.capabilities = capabilities
            jobs = controller.add_paths([source, second])
            loop, poll, timeout = QEventLoop(), QTimer(), QTimer()
            poll.timeout.connect(lambda: loop.quit() if all(job.media for job in jobs) else None)
            timeout.setSingleShot(True)
            timeout.timeout.connect(loop.quit)
            poll.start(10)
            timeout.start(15_000)
            loop.exec()
            poll.stop()
            self.assertTrue(all(job.media for job in jobs))
            for number, job in enumerate(jobs):
                job.settings = job.settings.customized(encoding_engine=capabilities[0].selection,
                    subtitle_mode=SubtitleMode.BURN, subtitle_index=job.media.subtitles[0].index if number else None,
                    subtitle_source=ExternalSubtitleSource.from_path(ass) if not number else None,
                    audio_processing_mode=AudioProcessingMode.LOUDNESS_NORMALIZATION if not number else AudioProcessingMode.MANUAL_VOLUME,
                    volume_percent=100 if not number else 150)
            controller.finished.connect(loop.quit)
            observed = []
            controller.active_changed.connect(lambda key: observed.append(key) if key else None)
            with patch.object(controller.detector, "probe_selection", wraps=controller.detector.probe_selection) as probe:
                controller.start()
                timeout.start(60_000)
                loop.exec()
                self.assertEqual(queue.state, QueueState.COMPLETED)
                self.assertEqual(probe.call_count, 2)
            timeout.stop()
            controller.probes.close()
            self.assertEqual(observed, [job.id for job in jobs])
            self.assertEqual([job.status for job in jobs], [JobStatus.COMPLETED, JobStatus.COMPLETED],
                             [job.error + job.diagnostics.logs[-2000:] for job in jobs])
            self.assertTrue(all(job.output_path.is_file() for job in jobs))
            self.assertIsNotNone(jobs[0].diagnostics.loudness)
            self.assertIsNone(jobs[1].diagnostics.loudness)
            self.assertFalse(list(root.glob(".video-converter-*.mp4")))
            self.assertIsNone(runner.workspace)

    def test_loudness_main10_ac3_surround_ass_and_preview(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        runtime = FFmpegRuntime.locate(allow_system_development=True)
        capabilities = tuple(cap for cap in HardwareEncoderDetector(runtime.ffmpeg).detect() if cap.available)
        if not capabilities:
            self.skipTest("No usable hardware H.264 encoder was detected")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory(prefix="video-converter-gpu-loudness-") as folder:
            root = Path(folder)
            srt = root / "Português.srt"
            srt.write_text("1\n00:00:00,500 --> 00:00:07,500\nNormalização de áudio\n", encoding="utf-8")
            ass = root / "Português.ass"
            subprocess.run([str(runtime.ffmpeg), "-v", "error", "-i", str(srt), str(ass)],
                           check=True, capture_output=True, timeout=15)
            source = root / "Movie.mkv"
            tones = "|".join(f"0.01*sin(2*PI*{frequency}*t)" for frequency in (220, 330, 440, 55, 660, 770))
            subprocess.run([str(runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=256x144:r=10:d=8", "-f", "lavfi", "-i",
                f"aevalsrc={tones}:s=48000:d=8:c=5.1", "-i", str(ass), "-map", "0:v", "-map", "1:a", "-map", "2:s",
                "-c:v", "libx265", "-pix_fmt", "yuv420p10le", "-x265-params", "log-level=error",
                "-c:a", "ac3", "-b:a", "384k", "-c:s", "ass", str(source)],
                check=True, capture_output=True, timeout=30)
            def probe(path):
                raw = subprocess.run([str(runtime.ffprobe), "-v", "error", "-show_streams", "-show_format",
                    "-of", "json", str(path)], check=True, capture_output=True, text=True, timeout=15).stdout
                return parse_probe(raw, path)
            media = probe(source)
            self.assertEqual(media.video.codec, "hevc")
            self.assertEqual(media.video.pixel_format, "yuv420p10le")
            self.assertEqual(media.audios[0].codec, "ac3")
            for number, capability in enumerate(capabilities):
                for external in (False, True):
                    with self.subTest(backend=capability.display_name, external=external):
                        settings = settings_for(source).customized(destination=root / f"normalized-{number}-{external}.mp4",
                            audio_processing_mode=AudioProcessingMode.LOUDNESS_NORMALIZATION,
                            encoding_engine=capability.selection, subtitle_mode=SubtitleMode.BURN,
                            subtitle_index=None if external else media.subtitles[0].index,
                            subtitle_source=ExternalSubtitleSource.from_path(ass) if external else None)
                        conversion = plan(media, settings, capabilities=capabilities)
                        runner = ConversionRunner(runtime)
                        completed, failures, stages = [], [], []
                        runner.completed.connect(lambda path: (completed.append(path), app.quit()))
                        runner.failed.connect(lambda message, details: (failures.append(message + details), app.quit()))
                        runner.stage_changed.connect(stages.append)
                        timeout = QTimer()
                        timeout.setSingleShot(True)
                        timeout.timeout.connect(app.quit)
                        def execute(conversion, preview=None):
                            completed.clear()
                            failures.clear()
                            stages.clear()
                            runner.start(media, conversion, preview=preview)
                            timeout.start(60_000)
                            app.exec()
                            timeout.stop()
                            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                            app.processEvents()
                            self.assertFalse(failures, failures[0][-4000:] if failures else "")
                            self.assertTrue(completed, "GPU loudness conversion timed out")
                            output = probe(Path(completed[0]))
                            self.assertEqual((output.video.codec, output.video.pixel_format), ("h264", "yuv420p"))
                            self.assertEqual((output.audios[0].codec, output.audios[0].channels,
                                              output.audios[0].sample_rate), ("aac", 6, 48000))
                            self.assertFalse(output.subtitles)
                            return output
                        execute(conversion)
                        self.assertEqual(len(stages), 2)
                        self.assertLess(runner.loudness_report.measurements.input_i, -25)
                        measured = subprocess.run([str(runtime.ffmpeg), "-hide_banner", "-i", str(conversion.destination),
                            "-map", "0:a:0", "-vn", "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json",
                            "-f", "null", "-"], check=True, capture_output=True, text=True, timeout=30)
                        result = parse_measurements(measured.stderr)
                        self.assertAlmostEqual(result.input_i, -16, delta=0.7)
                        self.assertLessEqual(result.input_tp, -0.8)
                        print(f"\nGPU loudness {capability.display_name}, external={external}: "
                              f"{result.input_i} LUFS, {result.input_tp} dBTP, analysis {runner.analysis_seconds:.2f}s")
                        frame = subprocess.run([str(runtime.ffmpeg), "-v", "error", "-ss", "2", "-i",
                            str(conversion.destination), "-frames:v", "1", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"],
                            check=True, capture_output=True, timeout=15).stdout
                        self.assertGreater(sum(pixel > 80 for pixel in frame), 20)
                        atoms = conversion.destination.read_bytes()
                        self.assertLess(atoms.index(b"moov"), atoms.index(b"mdat"))
                        preview = plan_preview(media, conversion, PreviewSettings(1, 5, False),
                            root / f"preview-{number}-{external}.mp4", capabilities=capabilities)
                        output = execute(preview.execution_plan, preview)
                        self.assertEqual(len(stages), 1)
                        self.assertTrue(runner.loudness_report.cache_hit)
                        self.assertAlmostEqual(output.duration, 5, delta=0.2)

    def test_short_subtitle_burn_on_available_encoders(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        runtime = FFmpegRuntime.locate(allow_system_development=True)
        capabilities = tuple(cap for cap in HardwareEncoderDetector(runtime.ffmpeg).detect()
                             if cap.available)
        if not capabilities:
            self.skipTest("No usable hardware H.264 encoder was detected")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory(prefix="video-converter-hardware-test-") as folder:
            root = Path(folder)
            subtitle = root / "subtitle.srt"
            subtitle.write_text("1\n00:00:00,100 --> 00:00:00,800\nGPU test\n", encoding="utf-8")
            external_ass = root / "External Português.ass"
            subprocess.run([str(runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                            "-i", str(subtitle), "-c:s", "ass", str(external_ass)],
                           check=True, capture_output=True, timeout=15)
            source = root / "source.mkv"
            subprocess.run([str(runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=256x144:rate=10:duration=1",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            "-i", str(subtitle), "-map", "0:v", "-map", "1:a", "-map", "2:s",
                            "-c:v", "libx265", "-pix_fmt", "yuv420p10le",
                            "-x265-params", "log-level=error", "-c:a", "flac",
                            "-c:s", "ass", "-shortest", str(source)], check=True,
                           capture_output=True, timeout=30)
            raw = subprocess.run([str(runtime.ffprobe), "-v", "error", "-show_format",
                                  "-show_streams", "-of", "json", str(source)], check=True,
                                 capture_output=True, text=True, timeout=15).stdout
            media = parse_probe(raw, source)
            for number, capability in enumerate(capabilities):
                for external in (False, True):
                    with self.subTest(capability=capability.display_name, external=external):
                        settings = settings_for(source).customized(
                            destination=root / f"hardware-{number}-{external}.mp4",
                            encoding_engine=capability.selection,
                            volume_percent=300,
                            prevent_clipping=True,
                            subtitle_mode=SubtitleMode.BURN,
                            subtitle_index=None if external else media.subtitles[0].index,
                            subtitle_source=ExternalSubtitleSource.from_path(external_ass) if external else None)
                        resolved = plan(media, settings, capabilities=capabilities)
                        self.assertFalse(resolved.audio_copy)
                        self.assertTrue(resolved.audio_processing.limiter_active)
                        runner = ConversionRunner(runtime)
                        completed: list[str] = []
                        failures: list[str] = []
                        runner.completed.connect(lambda path: (completed.append(path), app.quit()))
                        runner.failed.connect(lambda message, details: (failures.append(message + details), app.quit()))
                        runner.start(media, resolved)
                        timeout = QTimer()
                        timeout.setSingleShot(True)
                        timeout.timeout.connect(app.quit)
                        timeout.start(30_000)
                        app.exec()
                        timeout.stop()
                        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                        app.processEvents()
                        self.assertFalse(failures, failures[0][-3000:] if failures else "")
                        self.assertTrue(completed, "Hardware conversion timed out")
                        converted_raw = subprocess.run(
                            [str(runtime.ffprobe), "-v", "error", "-show_format", "-show_streams",
                             "-of", "json", completed[0]], check=True, capture_output=True,
                            text=True, timeout=15).stdout
                        converted = parse_probe(converted_raw, Path(completed[0]))
                        self.assertEqual(converted.video.codec, "h264")
                        self.assertEqual(converted.video.pixel_format, "yuv420p")
                        self.assertEqual(converted.audios[0].codec, "aac")
                        self.assertFalse(converted.subtitles)
                        preview = plan_preview(media, resolved, PreviewSettings(0.1, 5, False),
                            root / f"gpu-preview-{number}-{external}.mp4", capabilities=capabilities)
                        completed.clear()
                        failures.clear()
                        runner.start(media, preview.execution_plan, preview=preview)
                        timeout.start(30_000)
                        app.exec()
                        timeout.stop()
                        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                        app.processEvents()
                        self.assertFalse(failures, failures[0][-3000:] if failures else "")
                        self.assertTrue(completed, "Hardware preview timed out")
                        converted_raw = subprocess.run(
                            [str(runtime.ffprobe), "-v", "error", "-show_format", "-show_streams",
                             "-of", "json", completed[0]], check=True, capture_output=True,
                            text=True, timeout=15).stdout
                        converted = parse_probe(converted_raw, Path(completed[0]))
                        self.assertEqual(converted.video.codec, "h264")
                        self.assertEqual(converted.audios[0].codec, "aac")
                        self.assertAlmostEqual(converted.duration, preview.duration_seconds, delta=0.2)
