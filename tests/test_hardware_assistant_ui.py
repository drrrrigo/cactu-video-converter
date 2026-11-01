"""Qt re-test, warning dismissal, local copy and queue selection safeguards."""

import os
import subprocess
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.hardware.diagnosis import HardwareDiagnosisService
from video_converter.hardware.resources import RESOURCES
from video_converter.models.encoder import EncoderSelection, EncoderBackend
from video_converter.models.job import JobStatus
from video_converter.models.queue import QueueState
from video_converter.models.hardware_diagnosis import HardwareInventory
from video_converter.ui.hardware_assistant_panel import DISMISSAL_KEY
from video_converter.ui.main_window import MainWindow
from video_converter.ui.theme import apply_theme
from test_hardware_assistant import RUNTIME, AMD, ARCH, NODE, capability, diagnosis
from test_batch_queue import media_for
from qt_helpers import capture_qt_exceptions


class AssistantUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def setUp(self):
        capture_qt_exceptions(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.window = MainWindow(RUNTIME)
        self.window._startup_timer.stop()
        self.window.storage = QSettings(
            str(Path(self.temp.name) / "settings.ini"), QSettings.Format.IniFormat
        )
        self.addCleanup(self.delete)

    def delete(self):
        deadline = time.monotonic() + 4
        while self.window._hardware_testing() and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(10)
        self.window.queue.state = QueueState.IDLE
        if self.window.queue_controller.active:
            self.window.queue_controller._terminal(JobStatus.CANCELLED)
        self.window.runner.phase = "done"
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def wait_for_test(self):
        deadline = time.monotonic() + 5
        while self.window._hardware_thread is not None and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(10)
        self.assertIsNone(self.window._hardware_thread)
        self.app.processEvents()

    def add_job(self):
        source = Path(self.temp.name) / "movie.mkv"
        source.write_bytes(b"fixture")
        with patch.object(self.window.queue_controller.probes, "submit"):
            self.window.add_files([source])
        job = self.window.queue.jobs[-1]
        self.window.queue_controller._analyzed(job.id, media_for(source, codec="hevc"))
        return job

    def test_banner_dismissal_identity_change_recovery_and_explicit_software(self):
        window = self.window
        window.show()
        window._hardware_explained(diagnosis())
        self.assertFalse(window.hardware_banner.isHidden())
        window._dismiss_hardware_banner()
        self.assertEqual(window.storage.value(DISMISSAL_KEY), window.hardware_diagnosis.identity)
        window._hardware_explained(diagnosis())
        self.assertTrue(window.hardware_banner.isHidden())
        window._hardware_explained(diagnosis(devices=(replace(AMD, driver_version="new"),)))
        self.assertFalse(window.hardware_banner.isHidden())
        window._hardware_explained(diagnosis(caps=(capability(available=True),)))
        self.assertTrue(window.hardware_banner.isHidden())
        self.assertFalse(window.storage.contains(DISMISSAL_KEY))
        # Hardware works even if the user intentionally keeps x264.
        self.assertEqual(window.engine_combo.currentData(), EncoderSelection())
        window._hardware_explained(diagnosis(devices=(), caps=()))
        self.assertTrue(window.hardware_banner.isHidden())

    def test_opening_assistant_uses_cache_and_copy_is_sanitized_without_execution(self):
        self.window._hardware_explained(
            diagnosis(caps=(capability(error="Failed /home/alice/Private.mkv"),))
        )
        with (
            patch.object(self.window, "_detect_hardware") as detect,
            patch("subprocess.run", side_effect=AssertionError("No processes")),
        ):
            self.window._show_hardware_assistant()
            dialog = self.window._hardware_assistant
            dialog.copy_button.click()
            detect.assert_not_called()
            report = self.app.clipboard().text()
            self.assertIn("Cactu Video Converter", report)
            self.assertNotIn("alice", report)
            self.assertNotIn("Private.mkv", report)
            self.assertFalse(dialog.software_button.isEnabled())

    def test_only_registered_official_pages_can_open_and_failure_is_graceful(self):
        self.window._hardware_explained(diagnosis())
        self.window._show_hardware_assistant()
        dialog = self.window._hardware_assistant
        with patch(
            "video_converter.ui.hardware_assistant.QDesktopServices.openUrl", return_value=True
        ) as opening:
            dialog.open_resource(RESOURCES[0])
            self.assertEqual(opening.call_args.args[0].toString(), RESOURCES[0].url)
        with (
            patch("video_converter.ui.hardware_assistant.QDesktopServices.openUrl") as opening,
            patch("video_converter.ui.hardware_assistant.QMessageBox.warning") as warning,
        ):
            dialog.open_resource(replace(RESOURCES[0], url="https://evil.example/driver"))
            opening.assert_not_called()
            warning.assert_called_once()
        with (
            patch(
                "video_converter.ui.hardware_assistant.QDesktopServices.openUrl", return_value=False
            ),
            patch("video_converter.ui.hardware_assistant.QMessageBox.warning") as warning,
        ):
            dialog.open_resource(RESOURCES[0])
            warning.assert_called_once()

    def test_retest_updates_dropdown_pending_job_and_retains_explicit_selection(self):
        window = self.window
        usable = [False]
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            if "-encoders" in command:
                return subprocess.CompletedProcess(command, 0, " V..... h264_vaapi GPU\n", "")
            if "-filters" in command:
                return subprocess.CompletedProcess(
                    command, 0, " ... format V->V\n ... subtitles V->V\n ... hwupload V->V\n", ""
                )
            if "-hwaccels" in command:
                return subprocess.CompletedProcess(
                    command, 0, "Hardware acceleration methods:\nvaapi\n", ""
                )
            return subprocess.CompletedProcess(
                command, 0 if usable[0] else 1, "", "Initialization failed"
            )

        window.hardware_detector = HardwareEncoderDetector(
            RUNTIME.ffmpeg, platform="linux", devices=[Path(NODE.path)], run=run
        )
        window.hardware_diagnosis_service = HardwareDiagnosisService(
            RUNTIME, lambda: HardwareInventory("linux", "Linux", (AMD,), ARCH)
        )
        window.show()
        job = self.add_job()
        job.settings = job.settings.customized(
            encoding_engine=EncoderSelection(EncoderBackend.VAAPI, NODE.path)
        )
        window._bind_job(job)
        window._test_hardware_again()
        self.wait_for_test()
        self.assertFalse(window.hardware_diagnosis.available)
        self.assertEqual(job.status, JobStatus.INVALID)
        self.assertEqual(window.engine_combo.currentData(), job.settings.encoding_engine)
        before = len(commands)
        window._show_hardware_assistant()
        self.assertEqual(len(commands), before)
        usable[0] = True
        window._hardware_assistant.test_button.click()
        self.wait_for_test()
        self.assertTrue(window.hardware_diagnosis.available)
        self.assertEqual(job.status, JobStatus.READY)
        self.assertEqual(window.engine_combo.currentData(), job.settings.encoding_engine)
        self.assertFalse(window.hardware_banner.isVisible())
        window._hardware_assistant.software_button.click()
        self.assertEqual(job.settings.encoding_engine, EncoderSelection())
        self.assertIsNotNone(job.plan)

    def test_queue_and_preview_disable_retest_without_starting_any_process(self):
        self.window._hardware_explained(diagnosis())
        self.window._show_hardware_assistant()
        dialog = self.window._hardware_assistant
        for state in (
            QueueState.RUNNING,
            QueueState.PAUSED,
            QueueState.PAUSE_REQUESTED,
            QueueState.STOPPING,
        ):
            self.window.queue.state = state
            self.window._update_assistant_controls()
            self.assertFalse(dialog.test_button.isEnabled())
            self.assertIn("conversion is running", dialog.test_button.toolTip())
            with patch.object(self.window, "_detect_hardware") as detect:
                self.window._test_hardware_again()
                detect.assert_not_called()
        self.window.queue.state = QueueState.IDLE
        self.window.runner.phase = "converting"
        self.window._update_assistant_controls()
        self.assertFalse(dialog.test_button.isEnabled())
        self.window.runner.phase = "done"
        self.window._update_assistant_controls()
        self.assertTrue(dialog.test_button.isEnabled())

    def test_diagnosis_failure_does_not_disable_software_plans(self):
        job = self.add_job()
        self.window._hardware_explained(
            diagnosis(devices=(), caps=(), errors=("System APIs unavailable",))
        )
        self.assertEqual(job.status, JobStatus.READY)
        self.assertEqual(job.plan.encoding_engine, EncoderSelection())
        self.assertTrue(self.window.start_button.isEnabled())

    def test_preflight_failure_invalidates_pending_same_backend_without_switching(self):
        window = self.window
        job = self.add_job()
        second_path = Path(self.temp.name) / "second.mkv"
        second_path.write_bytes(b"fixture")
        with patch.object(window.queue_controller.probes, "submit"):
            window.add_files([second_path])
        second = window.queue.jobs[-1]
        window.queue_controller._analyzed(second.id, media_for(second_path, codec="hevc"))
        controller = window.queue_controller
        controller.capabilities = (capability(available=True),)
        for item in (job, second):
            item.settings = item.settings.customized(
                encoding_engine=EncoderSelection(EncoderBackend.VAAPI, NODE.path)
            )
            controller.validate_job(item)
        controller.active_id = job.id
        job.executed_plan = job.plan
        job.transition(JobStatus.RUNNING)
        controller._hardware_result = capability()
        controller._cancel_preflight = False
        controller._preflight_finished()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(second.status, JobStatus.INVALID)
        self.assertEqual(second.settings.encoding_engine.backend, EncoderBackend.VAAPI)
