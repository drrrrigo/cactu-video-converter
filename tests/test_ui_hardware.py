"""Headless UI checks for validated engine choices and plan summary."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent, QSettings, QTimer

from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.encoder import (
    EncoderBackend, EncoderSelection, HardwareEncoderCapability,
)
from video_converter.models.conversion import CodecChoice
from video_converter.ui.main_window import MainWindow


class HardwareUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("Video Converter Tests")
        cls.app.setApplicationName("Hardware UI Tests")
        cls.settings_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.settings_dir.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          cls.settings_dir.name)
        try:
            cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        except RuntimeError as exc:
            raise unittest.SkipTest("FFmpeg 9.0.2 development runtime unavailable") from exc

    def _close_window(self, window: MainWindow) -> None:
        window.close()
        self.app.processEvents()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_only_available_hardware_is_shown_and_summary_matches(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mkv"
            source.write_bytes(b"fixture")
            media = parse_probe({"format": {"format_name": "matroska"}, "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "hevc", "pix_fmt": "yuv420p10le"}
            ]}, source)
            window = MainWindow(self.runtime)
            window.media = media
            window._populate_media(media)
            selected = EncoderSelection(EncoderBackend.NVIDIA_NVENC)
            available = HardwareEncoderCapability(selected, "h264_nvenc", "NVIDIA NVENC",
                                                  "linux", "NVIDIA", True)
            unavailable = HardwareEncoderCapability(EncoderSelection(EncoderBackend.VAAPI),
                                                    "h264_vaapi", "VAAPI Hardware Encoder",
                                                    "linux", None, False, "No render device")
            window._hardware_detected((available, unavailable))
            self.assertEqual(window.engine_combo.count(), 2)
            window.engine_combo.setCurrentIndex(1)
            self.assertEqual(window.current_plan.encoding_engine, selected)
            self.assertIn("NVIDIA NVENC", window.summary.text())
            self.assertFalse(window.video_form.isRowVisible(window.crf))
            self.assertTrue(window.video_form.isRowVisible(window.hardware_quality))
            self._close_window(window)

    def test_hardware_detection_does_not_block_gui_timer(self) -> None:
        class SlowDetector:
            def detect(self, *, refresh=False):
                time.sleep(0.2)
                return ()

        window = MainWindow(self.runtime)
        window.hardware_detector = SlowDetector()
        window.show()
        ticks: list[bool] = []
        QTimer.singleShot(50, lambda: ticks.append(True))
        QTimer.singleShot(350, self.app.quit)
        self.app.exec()
        self.assertTrue(ticks, "The GUI event loop was blocked by hardware probing")
        self.assertIn("software", window.hardware_status.text().lower())
        self._close_window(window)

    def test_volume_slider_summary_warning_and_reset(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mkv"
            source.write_bytes(b"fixture")
            media = parse_probe({"format": {"format_name": "matroska"}, "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2},
            ]}, source)
            window = MainWindow(self.runtime)
            window.storage = QSettings(str(Path(folder) / "test.ini"), QSettings.Format.IniFormat)
            window.media = media
            window._populate_media(media)
            self.assertEqual(window.volume_slider.value(), 100)
            self.assertEqual(window.volume_slider.maximum(), 300)
            self.assertTrue(window.current_plan.audio_copy)
            window.volume_slider.setValue(300)
            self.assertEqual(window.volume_value.text(), "300%")
            self.assertTrue(window.current_plan.video_copy)
            self.assertFalse(window.current_plan.audio_copy)
            self.assertIn("Clipping protection enabled", window.summary.text())
            self.assertIn("Volume: 300%", window.summary.text())
            window.prevent_clipping.setChecked(False)
            self.assertIn("severe distortion", window.volume_note.text())
            window.audio_codec.setCurrentIndex(window.audio_codec.findData(CodecChoice.COPY))
            window.volume_slider.setValue(237)
            self.assertEqual(window.volume_value.text(), "237%")
            self.assertEqual(window.audio_codec.currentData(), CodecChoice.AAC)
            window.audio_codec.setCurrentIndex(window.audio_codec.findData(CodecChoice.AUTO))
            window.volume_reset.click()
            self.assertEqual(window.volume_slider.value(), 100)
            self.assertTrue(window.current_plan.audio_copy)
            self.assertNotIn("may cause distortion", window.volume_note.text())
            window.volume_slider.setValue(300)
            window._populate_media(media)
            self.assertEqual(window.volume_slider.value(), 100)
            self.assertTrue(window.prevent_clipping.isChecked())
            self.assertTrue(window.current_plan.audio_copy)
            self._close_window(window)
