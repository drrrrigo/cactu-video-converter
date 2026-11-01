"""Queue domain, safe settings transfer and deterministic sequential scheduling."""

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from video_converter.ffmpeg.progress import Progress
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.models.job import JobStatus
from video_converter.models.queue import ConversionQueue, OutputPolicy, QueueState
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.services.batch_settings import BatchSettingsService, match_stream
from video_converter.services.queue_controller import QueueController
from video_converter.ui.queue_view import QueueListModel, MIME
from qt_helpers import capture_qt_exceptions


def media_for(path, *, codec="h264", reordered=False, missing=False):
    path = path.resolve()
    return parse_probe({"format": {"format_name": "matroska", "duration": "10", "tags": {"title": "Movie"}},
        "streams": [{"index": 0, "codec_type": "video", "codec_name": codec, "pix_fmt": "yuv420p"},
            {"index": 9 if reordered else 2, "codec_type": "audio", "codec_name": "ac3", "channels": 6,
             "channel_layout": "5.1", "sample_rate": "48000", "tags": {"language": "por", "title": "Brazilian Portuguese"}},
            {"index": 2 if reordered else 9, "codec_type": "audio", "codec_name": "aac", "channels": 2,
             "tags": {"language": "eng", "title": "English"}, "disposition": {"default": 1}},
            {"index": 4, "codec_type": "subtitle", "codec_name": "ass", "tags": {"language": "eng", "title": "Full"}},
            {"index": 5, "codec_type": "subtitle", "codec_name": "ass", "tags": {"language": "por", "title": "Signs & Songs"}},
            *([] if missing else [{"index": 12 if reordered else 7, "codec_type": "subtitle", "codec_name": "ass",
                                  "tags": {"language": "por", "title": "Portuguese Full"}}])]}, path)


class FakeRunner(QObject):
    progress_changed = Signal(object)
    state_changed = Signal(str)
    completed = Signal(str)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.phase = "idle"
        self.calls = []
        self.commands = []
        self.stderr = ""
        self.loudness_report = None
        self.paused = False

    def start(self, media, plan, **kwargs):
        if self.phase not in {"idle", "done"}:
            raise AssertionError("More than one conversion started")
        self.phase = "converting"
        self.plan = plan
        self.calls.append(plan.source)
        self.state_changed.emit("Converting...")

    def finish(self, *, fail=False):
        self.phase = "done"  # terminal signal follows cleanup, as in the real runner
        self.stderr = f"logs for {self.plan.source.name}"
        if fail:
            self.failed.emit("Synthetic failure", self.stderr)
        else:
            self.completed.emit(str(self.plan.destination))

    def cancel(self):
        self.phase = "done"
        self.cancelled.emit()

    def pause_or_resume(self):
        self.paused = not self.paused
        self.state_changed.emit("Paused" if self.paused else "Converting...")


class BatchQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.runtime = FFmpegRuntime.locate(allow_system_development=True)

    def setUp(self):
        capture_qt_exceptions(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.queue = ConversionQueue()
        self.runner = FakeRunner()
        self.controller = QueueController(self.queue, self.runner, self.runtime)
        self.addCleanup(self.controller.probes.close)

    def job(self, name, **media_options):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        job = self.queue.add(path)
        job.media = media_for(path, **media_options)
        job.transition(JobStatus.READY)
        self.controller.validate_job(job)
        return job

    def drain(self):
        for _ in range(6):
            self.app.processEvents()

    def test_ids_duplicate_paths_independence_and_transitions(self):
        a, b = self.job("one/Movie.mkv"), self.job("two/Movie.mkv")
        self.assertNotEqual(a.id, b.id)
        self.assertIsNone(self.queue.add(a.input_path.parent / "." / a.input_path.name))
        a.settings = a.settings.customized(volume_percent=175)
        a.stream_issues["audio"] = "review"
        self.assertEqual(b.settings.volume_percent, 100)
        self.assertFalse(b.stream_issues)
        self.assertRaises(ValueError, b.transition, JobStatus.COMPLETED)
        self.assertRaises(ValueError, a.transition, "running")
        self.assertEqual(b.media.metadata, (("title", "Movie"),))

    def test_reordering_changes_execution_and_active_anchor_is_locked(self):
        a, b, c = (self.job(f"{name}.mkv") for name in "ABC")
        model = QueueListModel(self.queue)
        model.refresh()
        self.assertTrue(model.move_ids([c.id], 1))
        self.assertEqual(self.queue.jobs, (a, c, b))
        self.controller.start()
        self.drain()
        self.assertRaises(ValueError, self.queue.remove, a.id)
        self.assertFalse(model.move_ids([a.id], 3))
        self.assertFalse(model.move_ids([c.id], 0))
        for job in (a, c, b):
            self.assertEqual(self.controller.active_id, job.id)
            self.runner.finish()
            self.drain()
        self.assertEqual(self.runner.calls, [a.input_path, c.input_path, b.input_path])

    def test_bulk_preset_per_media_plans_and_independent_destinations(self):
        a, b = self.job("A.mkv"), self.job("B.mkv", codec="hevc")
        service = BatchSettingsService()
        for job in (a, b):
            job.settings = job.settings.customized(volume_percent=250)
            service.apply_web_preset(job)
            self.controller.validate_job(job)
        self.assertIsNot(a.settings, b.settings)
        self.assertNotEqual(a.plan.destination, b.plan.destination)
        self.assertTrue(a.plan.video_copy)
        self.assertFalse(b.plan.video_copy)
        self.assertEqual(a.settings.volume_percent, 100)

    def test_semantic_copy_reordered_streams_and_missing_subtitle(self):
        a, b, c = self.job("A.mkv"), self.job("B.mkv", reordered=True), self.job("C.mkv", missing=True)
        a.settings = a.settings.customized(audio_index=2, subtitle_mode=SubtitleMode.BURN, subtitle_index=7,
                                           volume_percent=175)
        service = BatchSettingsService()
        service.copy(a, b)
        self.assertEqual(b.settings.audio_index, 9)
        self.assertEqual(b.settings.subtitle_index, 12)
        self.assertEqual(b.settings.volume_percent, 175)
        self.assertNotEqual(b.settings.destination, a.settings.destination)
        self.assertTrue(self.controller.validate_job(b))
        service.copy(a, c)
        self.assertIn("subtitle", c.stream_issues)
        self.assertFalse(self.controller.validate_job(c))
        self.assertEqual(c.status, JobStatus.INVALID)
        self.assertIsNone(c.settings.subtitle_source)

    def test_ambiguous_or_missing_audio_and_title_language_safety(self):
        a, b = self.job("A.mkv"), self.job("B.mkv")
        audio = a.media.audios[0]
        duplicate = replace(audio, index=99, ordinal=9)
        result, error = match_stream(audio, (audio, duplicate))
        self.assertIsNone(result)
        self.assertIn("Ambiguous", error)
        self.assertIsNone(match_stream(audio, (b.media.audios[1],))[0])
        subtitle = a.media.subtitles[-1]
        self.assertIsNone(match_stream(subtitle, (a.media.subtitles[0], a.media.subtitles[1]))[0])
        self.assertIsNone(match_stream(subtitle, (replace(subtitle, forced=True),))[0])
        a.settings = a.settings.customized(audio_index=2)
        b.media = replace(b.media, audios=(b.media.audios[1],))
        BatchSettingsService().copy(a, b)
        self.assertIn("audio", b.stream_issues)
        self.assertFalse(self.controller.validate_job(b))

    def test_external_subtitle_is_never_copied(self):
        a, b = self.job("A.mkv"), self.job("B.mkv")
        subtitle = self.root / "Movie01.pt-BR.ass"
        subtitle.write_text("[Script Info]", encoding="utf-8")
        a.settings = a.settings.customized(subtitle_mode=SubtitleMode.BURN,
                                           subtitle_source=ExternalSubtitleSource.from_path(subtitle))
        BatchSettingsService().copy(a, b)
        self.assertIsNone(b.settings.subtitle_source)
        self.assertIn("not copied", b.stream_issues["subtitle"])
        self.assertFalse(self.controller.validate_job(b))

    def test_continue_after_failure_and_retained_snapshots_diagnostics(self):
        a, b, c = (self.job(f"{name}.mkv") for name in "ABC")
        self.controller.start()
        self.drain()
        for job, fails in ((a, False), (b, True), (c, False)):
            self.assertEqual(self.controller.active, job)
            self.runner.progress_changed.emit(Progress(5, .5, 2, 2.5, False))
            self.assertEqual(job.progress.fraction, .5)
            self.runner.finish(fail=fails)
            self.drain()
        self.assertEqual([j.status for j in self.queue.jobs], [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.COMPLETED])
        self.assertEqual(self.queue.state, QueueState.COMPLETED)
        self.assertIn("B.mkv", b.diagnostics.logs)
        self.assertNotEqual(b.diagnostics.logs, c.diagnostics.logs)
        self.assertIsNotNone(a.executed_plan)
        self.assertIsNotNone(a.started_at)
        self.assertIsNotNone(a.finished_at)
        self.assertEqual(a.output_path, a.executed_plan.destination)
        self.assertEqual(b.attempts, 1)

    def test_cancel_current_continues_and_stop_preserves_pending(self):
        a, b, c = (self.job(f"{name}.mkv") for name in "ABC")
        self.controller.start()
        self.drain()
        self.controller.cancel_current()
        self.drain()
        self.assertEqual(a.status, JobStatus.CANCELLED)
        self.assertEqual(self.controller.active, b)
        self.controller.stop()
        self.drain()
        self.assertEqual(b.status, JobStatus.CANCELLED)
        self.assertEqual(c.status, JobStatus.WAITING)
        self.assertEqual(self.queue.state, QueueState.IDLE)
        self.assertEqual(len(self.runner.calls), 2)
        self.controller.start()
        self.drain()
        self.assertEqual(self.controller.active, c)
        self.runner.finish()
        self.drain()

    def test_queue_pause_after_current_and_process_pause_are_distinct(self):
        a, b = self.job("A.mkv"), self.job("B.mkv")
        self.controller.start()
        self.drain()
        self.controller.pause_current()
        self.assertEqual(a.status, JobStatus.PAUSED)
        self.assertEqual(self.queue.state, QueueState.RUNNING)
        self.assertEqual(len(self.runner.calls), 1)
        self.controller.pause_current()
        self.assertEqual(a.status, JobStatus.RUNNING)
        self.controller.pause_queue()
        self.assertEqual(self.queue.state, QueueState.PAUSE_REQUESTED)
        self.assertFalse(self.runner.paused)
        self.runner.finish()
        self.drain()
        self.assertEqual(self.queue.state, QueueState.PAUSED)
        self.assertEqual(len(self.runner.calls), 1)
        self.controller.resume()
        self.drain()
        self.assertEqual(self.controller.active, b)
        self.runner.finish()
        self.drain()

    def test_retry_failed_is_explicit_once_and_invalid_revalidation_blocks(self):
        job = self.job("A.mkv")
        self.controller.start()
        self.drain()
        self.runner.finish(fail=True)
        self.drain()
        self.assertEqual(len(self.runner.calls), 1)
        job.settings = job.settings.customized(volume_percent=999)
        self.controller.retry([job.id])
        self.assertEqual(job.status, JobStatus.INVALID)
        job.settings = job.settings.customized(volume_percent=150)
        self.controller.validate_job(job)
        self.controller.start()
        self.drain()
        self.runner.finish()
        self.drain()
        self.assertEqual(len(self.runner.calls), 2)
        self.assertEqual(job.executed_plan.audio_processing.volume_percent, 150)
        self.assertEqual(len(job.history), 2)
        self.assertEqual(job.history[0].status, JobStatus.FAILED)
        self.assertEqual(job.history[0].plan.audio_processing.volume_percent, 100)
        self.assertEqual(job.history[1].status, JobStatus.COMPLETED)

    def test_output_collisions_policies_and_input_protection(self):
        a, b = self.job("one/Movie.mkv"), self.job("two/Movie.mkv")
        output = self.root / "Movie.mp4"
        for job in (a, b):
            job.settings = replace(job.settings, destination=output)
        self.assertEqual(self.controller.prepare(OutputPolicy.REQUIRE_ATTENTION), (0, 2))
        self.assertEqual(a.status, JobStatus.INVALID)

        self.assertEqual(b.status, JobStatus.INVALID)
        self.assertEqual(self.controller.prepare(OutputPolicy.RENAME), (2, 0))
        self.assertEqual(a.settings.destination, output)
        self.assertEqual(b.settings.destination.name, "Movie-2.mp4")
        output.write_bytes(b"existing output")
        self.controller.prepare(OutputPolicy.SKIP_EXISTING)
        self.assertEqual(a.status, JobStatus.INVALID)
        self.assertEqual(output.read_bytes(), b"existing output")
        a.settings = replace(a.settings, destination=a.input_path)
        self.controller.prepare(OutputPolicy.RENAME)
        self.assertEqual(a.status, JobStatus.INVALID)

    def test_unwritable_output_and_existing_output_are_resolved_before_start(self):
        job = self.job("A.mkv")
        folder = self.root / "ReadOnly"
        folder.mkdir()
        job.settings = replace(job.settings, destination=folder / "Movie.mp4")
        folder.chmod(0o555)
        try:
            self.assertEqual(self.controller.prepare(), (0, 1))
        finally:
            folder.chmod(0o755)
        destination = job.settings.destination
        destination.write_bytes(b"keep existing bytes")
        self.controller.prepare(OutputPolicy.RENAME)
        self.assertEqual(job.settings.destination.name, "Movie-2.mp4")
        self.assertEqual(destination.read_bytes(), b"keep existing bytes")

    def test_language_aliases_and_known_regional_conflicts(self):
        job = self.job("A.mkv")
        source = job.media.audios[0]
        matched, error = match_stream(source, (replace(source, index=99, language="pt-BR"),))
        self.assertEqual(matched.index, 99)
        self.assertFalse(error)
        self.assertIsNone(match_stream(replace(source, language="pt-BR"),
                                       (replace(source, language="pt-PT"),))[0])
    def test_removed_probe_result_and_internal_mime_do_not_import(self):
        job = self.job("A.mkv")
        media = job.media
        self.controller.remove([job.id])
        self.controller._analyzed(job.id, media)
        self.assertFalse(self.queue.jobs)
        a, b = self.job("one/A.mkv"), self.job("B.mkv")
        model = QueueListModel(self.queue)
        model.refresh()
        mime = model.mimeData([model.index(1)])
        self.assertTrue(mime.hasFormat(MIME))
        self.assertFalse(mime.hasUrls())
        self.assertTrue(model.dropMimeData(mime, model.supportedDropActions(), 0, 0, model.index(-1)))
        self.assertEqual(self.queue.jobs, (b, a))

    def test_added_analysis_while_running_is_appended_and_waits(self):
        a = self.job("A.mkv")
        self.controller.start()
        self.drain()
        path = self.root / "Unicode 日本語.mkv"
        path.write_bytes(b"fixture")
        with patch.object(self.controller.probes, "submit"):
            added = self.controller.add_paths([path, a.input_path, path])
        self.assertEqual(len(added), 1)
        self.controller._analyzed(added[0].id, media_for(path))
        self.assertEqual(added[0].status, JobStatus.WAITING)
        self.assertEqual(len(self.runner.calls), 1)
        self.runner.finish()
        self.drain()
        self.assertEqual(self.controller.active, added[0])
        self.runner.finish()
        self.drain()

    def test_slow_first_probe_does_not_change_execution_order(self):
        a, b = self.job("A.mkv"), self.job("B.mkv")
        a.status = JobStatus.ANALYZING
        a.media = None
        self.controller.start()
        self.drain()
        self.assertFalse(self.runner.calls)
        self.controller._analyzed(a.id, media_for(a.input_path))
        self.drain()
        self.assertEqual(self.controller.active, a)
        self.runner.finish()
        self.drain()
        self.assertEqual(self.controller.active, b)
        self.runner.finish()
        self.drain()

    def test_hardware_preflight_failure_and_cancellation_do_not_start_encoder(self):
        a, b = self.job("A.mkv", codec="hevc"), self.job("B.mkv")
        selection = EncoderSelection(EncoderBackend.NVIDIA_NVENC)
        capability = HardwareEncoderCapability(selection, "h264_nvenc", "NVIDIA", "linux", None, True)
        self.controller.capabilities = (capability,)
        a.settings = a.settings.customized(encoding_engine=selection)
        with patch.object(self.controller, "_preflight"):
            self.controller.start()
            self.drain()
        self.assertFalse(self.runner.calls)
        self.controller._hardware_result = "Device disappeared"
        with self.assertLogs("video_converter.services.queue_controller", level="ERROR"):
            self.controller._preflight_finished()
        self.drain()
        self.assertEqual(a.status, JobStatus.FAILED)
        self.assertEqual(self.controller.active, b)
        self.runner.finish()
        self.drain()
        self.controller.retry([a.id])
        with patch.object(self.controller, "_preflight"):
            self.controller.start()
            self.drain()
        self.controller._cancel_preflight = True
        self.controller.queue.state = QueueState.STOPPING
        self.controller._preflight_finished()
        self.drain()
        self.assertEqual(a.status, JobStatus.CANCELLED)
        self.assertEqual(len(self.runner.calls), 1)


if __name__ == "__main__":
    unittest.main()
