"""Preview dialog, snapshot, job locking and session output ownership."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.preview import PreviewSettings
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.presets.web_kosmi import settings_for
from video_converter.ui.main_window import MainWindow
from video_converter.ui.preview_dialog import PreviewDialog


class PreviewUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        try:
            cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        except RuntimeError as exc:
            raise unittest.SkipTest("FFmpeg 9.0.2 development runtime unavailable") from exc

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "movie.mkv"
        self.source.write_bytes(b"fixture")
        self.media = parse_probe({"format": {"format_name": "matroska", "duration": "1000"}, "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2},
        ]}, self.source)

    def _delete(self, widget) -> None:
        widget.close()
        self.app.processEvents()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_dialog_defaults_and_effective_duration(self) -> None:
        conversion = plan(self.media, settings_for(self.source))
        dialog = PreviewDialog(conversion)
        self.assertEqual(dialog.settings(), PreviewSettings(100, 30, True))
        dialog.start_time.setText("00:16:39")
        self.assertTrue(dialog.create_button.isEnabled())
        self.assertIn("Effective duration: 1 seconds", dialog.effective.text())
        self.assertIn("shortened", dialog.effective.text())
        dialog.start_time.setText("00:16:40")
        self.assertFalse(dialog.create_button.isEnabled())
        dialog.start_time.setText("invalid")
        self.assertFalse(dialog.create_button.isEnabled())
        dialog.start_time.setText("00:00:00.125")
        self.assertTrue(dialog.create_button.isEnabled())
        self._delete(dialog)

    def test_preview_job_preserves_full_plan_and_marks_stale(self) -> None:
        window = MainWindow(self.runtime)
        window.storage = QSettings(str(self.root / "settings.ini"), QSettings.Format.IniFormat)
        window.media = self.media
        window._populate_media(self.media)
        original = window.current_plan

        def start(media, execution, **kwargs):
            window.runner.phase = "converting"
            window.runner.plan = execution
            window.runner.preview = kwargs["preview"]

        with patch.object(window.runner, "start", side_effect=start) as launch:
            window._create_preview_with_settings(PreviewSettings(10, 30, False))
            self.assertEqual(window.current_plan, original)
            self.assertFalse(window.preview_button.isEnabled())
            self.assertFalse(window.start_button.isEnabled())
            self.assertTrue(window.runner.plan.video_copy is False)
            self.assertEqual(window.runner.plan.duration, 30)
            window._start()
            window._create_preview_with_settings(PreviewSettings(0))
            self.assertEqual(launch.call_count, 1)
            candidate = window._active_preview.output_path
            candidate.write_bytes(b"test output")
            window.runner.phase = "done"
            window._on_complete(str(candidate))
            self.assertEqual(window.state.text(), "Preview ready")
            self.assertTrue(window.preview_store.latest.matches(original))
            self.assertTrue(window.start_button.isEnabled())
            window.volume_slider.setValue(150)
            self.assertIn("out of date", window.preview_status.text())
            window._create_preview_with_settings(PreviewSettings(20, 10, False))
            abandoned = window._active_preview.output_path
            window.runner.phase = "done"
            window._on_cancelled()
            self.assertFalse(abandoned.parent.exists())
            self.assertTrue(candidate.exists())
            self.assertEqual(window.state.text(), "Preview cancelled")
        with patch("video_converter.ui.main_window.QDesktopServices.openUrl", return_value=False), \
                patch("video_converter.ui.main_window.QMessageBox.warning") as warning:
            window._open_preview()
            warning.assert_called_once()
        self._delete(window)
        self.assertFalse(candidate.exists())
        self.assertTrue(self.source.exists())

    def test_cancel_during_hardware_preflight_never_launches(self) -> None:
        window = MainWindow(self.runtime)
        window.storage = QSettings(str(self.root / "preflight.ini"), QSettings.Format.IniFormat)
        window.media = self.media
        window._populate_media(self.media)
        selection = EncoderSelection(EncoderBackend.NVIDIA_NVENC)
        cap = HardwareEncoderCapability(selection, "h264_nvenc", "NVIDIA NVENC", "linux", None, True)
        window._hardware_detected((cap,))
        window.engine_combo.setCurrentIndex(1)
        with patch.object(window, "_run_hardware_worker"), patch.object(window.runner, "start") as launch:
            window._create_preview_with_settings(PreviewSettings(10, 30, False))
            candidate = window._active_preview.output_path
            self.assertTrue(window.cancel_button.isEnabled())
            self.assertFalse(window.preview_button.isEnabled())
            self.assertFalse(window.start_button.isEnabled())
            cancelled_plan = window._preflight_plan
            window._cancel_operation()
            self.assertIsNone(window._preflight_plan)
            self.assertFalse(candidate.parent.exists())
            self.assertTrue(window.preview_button.isEnabled())
            window._create_preview_with_settings(PreviewSettings(20, 30, False))
            pending_plan = window._preflight_plan
            window._hardware_preflight_done(cap, cancelled_plan)
            self.assertIs(window._preflight_plan, pending_plan)
            window._cancel_operation()
            window._hardware_preflight_done(cap, pending_plan)
            launch.assert_not_called()
        self._delete(window)
