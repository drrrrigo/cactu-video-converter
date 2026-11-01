"""Real bounded probing and multiple verified conversions through one runner."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.audio import AudioProcessingMode
from video_converter.models.conversion import SubtitleMode
from video_converter.models.job import JobStatus
from video_converter.models.queue import ConversionQueue, QueueState
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.services.probe_pool import MediaProbePool
from video_converter.services.queue_controller import QueueController
from qt_helpers import capture_qt_exceptions


class BatchIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="converter-batch-tests-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.fixture = cls.root / "fixture.mkv"
        cls.run_command([str(cls.runtime.ffmpeg), "-v", "error", "-f", "lavfi", "-i",
            "color=c=black:s=256x144:r=10:d=8", "-f", "lavfi", "-i",
            "sine=frequency=440:sample_rate=48000:duration=8,volume=0.1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.fixture)])

    @classmethod
    def run_command(cls, args):
        return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout

    def setUp(self):
        capture_qt_exceptions(self)

    def wait_for(self, predicate, timeout=30_000):
        if predicate():
            return
        loop, poll, deadline = QEventLoop(), QTimer(), QTimer()
        poll.timeout.connect(lambda: loop.quit() if predicate() else None)
        poll.start(10)
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        deadline.start(timeout)
        loop.exec()
        poll.stop()
        deadline.stop()
        self.assertTrue(predicate(), "Batch operation timed out")

    def test_bounded_probes_unicode_content_validation_and_bad_candidates(self):
        pool = MediaProbePool(self.runtime.ffprobe, concurrency=2)
        self.addCleanup(pool.close)
        successes, failures, max_active = [], [], 0
        pool.analyzed.connect(lambda key, media: successes.append((key, media)))
        pool.rejected.connect(lambda key, error: failures.append((key, error)))
        candidates = []
        for index in range(5):
            path = self.root / f"Unicode 日本語 {index}.data"
            shutil.copyfile(self.fixture, path)
            candidates.append(path)
        invalid = self.root / "unsupported.txt"
        invalid.write_text("not a video", encoding="utf-8")
        candidates += [invalid, self.root / "missing.mkv", self.root]
        for index, path in enumerate(candidates):
            pool.submit(str(index), path)
            max_active = max(max_active, len(pool.active))
            self.assertLessEqual(len(pool.active), 2)
        self.wait_for(lambda: len(successes) + len(failures) == len(candidates))
        self.assertEqual(len(successes), 5)
        self.assertEqual(len(failures), 3)
        self.assertEqual(max_active, 2)
        self.assertFalse(pool.active)

    def test_real_queue_copy_failed_subtitle_loudness_and_gain_continue(self):
        queue = ConversionQueue()
        runner = ConversionRunner(self.runtime)
        controller = QueueController(queue, runner, self.runtime)
        self.addCleanup(controller.probes.close)
        sources = []
        for index in range(4):
            path = self.root / f"queue-{index}.mkv"
            shutil.copyfile(self.fixture, path)
            sources.append(path)
        jobs = controller.add_paths(sources)
        self.wait_for(lambda: all(job.media is not None for job in jobs))
        broken = self.root / "bad.ass"
        broken.write_text("not valid ASS", encoding="utf-8")
        valid = self.root / "external.srt"
        valid.write_text("1\n00:00:01,000 --> 00:00:07,000\nBatch test\n", encoding="utf-8")
        jobs[1].settings = jobs[1].settings.customized(subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(broken))
        jobs[2].settings = jobs[2].settings.customized(audio_processing_mode=AudioProcessingMode.LOUDNESS_NORMALIZATION)
        jobs[3].settings = jobs[3].settings.customized(volume_percent=150, subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(valid))
        order = []
        def changed(key):
            if key:
                self.assertEqual(runner.phase, "done" if order else "idle")
                self.assertEqual(len([job for job in queue.jobs if job.status in {
                    JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.FINALIZING}]), 1)
                order.append(key)
        controller.active_changed.connect(changed)
        controller.start()
        self.wait_for(lambda: queue.state == QueueState.COMPLETED, 60_000)
        self.assertEqual(order, [job.id for job in jobs])
        self.assertEqual([job.status for job in jobs], [JobStatus.COMPLETED, JobStatus.FAILED,
                                                     JobStatus.COMPLETED, JobStatus.COMPLETED])
        self.assertTrue(jobs[0].executed_plan.video_copy and jobs[0].executed_plan.audio_copy)
        self.assertTrue(jobs[2].executed_plan.video_copy)
        self.assertFalse(jobs[2].executed_plan.audio_copy)
        self.assertIsNotNone(jobs[2].diagnostics.loudness)
        self.assertIsNone(jobs[3].diagnostics.loudness)
        self.assertIn("Unable to open", jobs[1].diagnostics.logs)
        self.assertFalse(jobs[1].settings.destination.exists())
        self.assertFalse(list(self.root.glob(".video-converter-*.mp4")))
        self.assertIsNone(runner.workspace)
        for job in (jobs[0], jobs[2], jobs[3]):
            raw = self.run_command([str(self.runtime.ffprobe), "-v", "error", "-show_format",
                                   "-show_streams", "-of", "json", str(job.output_path)])
            media = parse_probe(raw.decode(), job.output_path)
            self.assertEqual((media.video.codec, media.video.pixel_format, media.audios[0].codec),
                             ("h264", "yuv420p", "aac"))
            self.assertAlmostEqual(media.duration, 8, delta=.2)
        self.assertTrue(all(job.diagnostics.command for job in jobs))

    def test_real_cancel_current_cleans_partial_before_next_job(self):
        queue = ConversionQueue()
        runner = ConversionRunner(self.runtime)
        controller = QueueController(queue, runner, self.runtime)
        self.addCleanup(controller.probes.close)
        paths = []
        for number in range(2):
            path = self.root / f"cancel-{number}.mkv"
            shutil.copyfile(self.fixture, path)
            paths.append(path)
        jobs = controller.add_paths(paths)
        self.wait_for(lambda: all(job.media for job in jobs))
        def active(key):
            if key == jobs[0].id:
                QTimer.singleShot(0, controller.cancel_current)
            elif key == jobs[1].id:
                self.assertIsNone(runner.workspace)
                self.assertFalse(list(self.root.glob(".video-converter-*.mp4")))
        controller.active_changed.connect(active)
        controller.start()
        self.wait_for(lambda: queue.state == QueueState.COMPLETED)
        self.assertEqual(jobs[0].status, JobStatus.CANCELLED)
        self.assertEqual(jobs[1].status, JobStatus.COMPLETED)
        self.assertFalse(jobs[0].settings.destination.exists())


if __name__ == "__main__":
    unittest.main()
