"""External subtitle selection, staging, validation, and generated media tests."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.ffmpeg.subtitle_pipeline import prepare_subtitle, preflight_command
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import CodecChoice, SubtitleMode
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability
from video_converter.models.subtitle import ExternalSubtitleSource, SubtitleFormat
from video_converter.presets.web_kosmi import settings_for
from video_converter.ui.main_window import MainWindow


def run_event_loop(app: QApplication, timeout_ms: int) -> None:
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(app.quit)
    timer.start(timeout_ms)
    app.exec()
    timer.stop()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


class ExternalSubtitleTests(unittest.TestCase):
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
        self.video = self.root / "video.mkv"
        self.video.write_bytes(b"fixture")
        self.media = parse_probe({"format": {"format_name": "matroska"}, "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"}
        ]}, self.video)

    def test_formats_and_validation(self) -> None:
        for name in ("Português [Full].ASS", "movie.ssa", "movie.SRT"):
            path = self.root / name
            path.write_text("subtitle", encoding="utf-8")
            source = ExternalSubtitleSource.from_path(path)
            self.assertEqual(source.format.value, path.suffix.lower()[1:])
            settings = settings_for(self.video).customized(
                subtitle_mode=SubtitleMode.BURN, subtitle_source=source)
            resolved = plan(self.media, settings)
            self.assertFalse(resolved.video_copy)
            self.assertEqual(resolved.subtitle_source, source)
            with self.assertRaisesRegex(ValidationError, "Burn into video only"):
                plan(self.media, settings.customized(subtitle_mode=SubtitleMode.SELECTABLE))
            path.unlink()
            with self.assertRaisesRegex(ValidationError, "could not be found"):
                plan(self.media, settings)
        with self.assertRaisesRegex(ValueError, "Unsupported external subtitle format"):
            ExternalSubtitleSource.from_path(self.root / "movie.txt")
        empty = self.root / "empty.srt"
        empty.touch()
        with self.assertRaisesRegex(ValidationError, "empty"):
            plan(self.media, settings_for(self.video).customized(
                subtitle_mode=SubtitleMode.BURN,
                subtitle_source=ExternalSubtitleSource.from_path(empty)))

    def test_staging_uses_safe_basename_and_original_is_unchanged(self) -> None:
        source_path = self.root / "Vídeos 映画 'quotes' [PT-BR].ASS"
        content = b"[Script Info]\nTitle: Sample\n"
        source_path.write_bytes(content)
        source = ExternalSubtitleSource.from_path(source_path)
        workspace = self.root / "workspace"
        workspace.mkdir()
        prepared = prepare_subtitle(source, workspace, self.runtime.ffmpeg, self.video)
        self.assertEqual(prepared.path.name, "subtitle.ass")
        self.assertEqual(prepared.path.read_bytes(), content)
        self.assertEqual(source_path.read_bytes(), content)
        command = preflight_command(self.runtime.ffmpeg, prepared.path)
        self.assertIn("subtitles=subtitle.ass", command)
        self.assertNotIn(str(source_path), " ".join(command))
        windows_like = self.root / r"C:\Users\Test User\Vídeos\Português [Final].ass"
        windows_like.write_bytes(content)
        windows_staged = prepare_subtitle(ExternalSubtitleSource.from_path(windows_like),
                                          workspace, self.runtime.ffmpeg, self.video)
        self.assertEqual(windows_staged.path.name, "subtitle.ass")
        self.assertNotIn(str(windows_like), " ".join(preflight_command(
            self.runtime.ffmpeg, windows_staged.path)))
        settings = settings_for(self.video).customized(
            subtitle_mode=SubtitleMode.BURN, subtitle_source=source)
        resolved = plan(self.media, settings)
        self.assertFalse(resolved.video_copy)
        self.assertRaises(ValidationError, plan, self.media,
                          settings.customized(video_codec=CodecChoice.COPY))
        for backend in EncoderBackend:
            selection = EncoderSelection(backend, "/dev/dri/renderD128" if backend in
                                         {EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV} else None)
            cap = HardwareEncoderCapability(selection, "", backend.display_name, "linux", None, True)
            selected = settings.customized(encoding_engine=selection)
            resolved = plan(self.media, selected, capabilities=(cap,))
            command = build_command(resolved, self.runtime.ffmpeg, self.root / "out.mp4",
                                    subtitle_file=prepared.path)
            self.assertIn("subtitles=subtitle.ass", " ".join(command))
            self.assertIn("+faststart", command)
            self.assertNotIn(str(source_path), " ".join(command))

    def test_ui_external_choice_and_summary(self) -> None:
        path = self.root / "Português.srt"
        path.write_text("1\n00:00:00,000 --> 00:00:00,900\nHi\n", encoding="utf-8")
        window = MainWindow(self.runtime)
        window.media = self.media
        window._populate_media(self.media)
        window.external_subtitle_path = path
        window.subtitle_filename.setText(path.name)
        window.mode_burn.setChecked(True)
        window.subtitle_external.setChecked(True)
        self.assertEqual(window.current_plan.subtitle_source,
                         ExternalSubtitleSource(path, SubtitleFormat.SRT))
        self.assertIn("External: Português.srt", window.summary.text())
        self.assertFalse(window.subtitle_track.isEnabled())
        window.close()
        # Drain the startup detection callback before deleting this headless
        # window; otherwise it can outlive the next test's Qt event loop.
        self.app.processEvents()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()


class ExternalSubtitleIntegrationTests(unittest.TestCase):
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
        self.video = self.root / "source.mkv"
        subprocess.run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "testsrc2=size=256x144:rate=10:duration=1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(self.video)], check=True, capture_output=True, timeout=30)
        raw = subprocess.run([str(self.runtime.ffprobe), "-v", "error", "-show_streams",
                              "-show_format", "-of", "json", str(self.video)], check=True,
                             capture_output=True, text=True, timeout=15).stdout
        self.media = parse_probe(raw, self.video)

    def _convert(self, path: Path) -> tuple[list[str], list[str]]:
        settings = settings_for(self.video).customized(
            subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(path))
        resolved = plan(self.media, settings)
        runner = ConversionRunner(self.runtime)
        completed: list[str] = []
        failures: list[str] = []
        runner.completed.connect(lambda result: (completed.append(result), self.app.quit()))
        runner.failed.connect(lambda message, details: (failures.append(message + details), self.app.quit()))
        runner.start(self.media, resolved)
        workspace_path = Path(runner.workspace.name)
        run_event_loop(self.app, 15_000)
        self.assertFalse(list(self.root.glob(".video-converter-*.mp4")))
        self.assertFalse(workspace_path.exists(), "Staged subtitle workspace was not removed")
        return completed, failures

    def test_external_ass_ssa_and_srt_burn(self) -> None:
        srt = self.root / "Português 'test' [字幕].srt"
        srt.write_text("1\n00:00:00,100 --> 00:00:00,800\nExternal subtitle\n", encoding="utf-8")
        ass = self.root / "styled.ass"
        ssa = self.root / "styled.ssa"
        for path in (ass, ssa):
            subprocess.run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                            "-i", str(srt), str(path)], check=True, capture_output=True, timeout=15)
        for path in (srt, ass, ssa):
            with self.subTest(path=path.name):
                completed, failures = self._convert(path)
                self.assertFalse(failures, failures[0][-1200:] if failures else "")
                self.assertTrue(completed)
                raw = subprocess.run([str(self.runtime.ffprobe), "-v", "error", "-show_streams",
                                      "-show_format", "-of", "json", completed[0]], check=True,
                                     capture_output=True, text=True, timeout=15).stdout
                output = parse_probe(raw, Path(completed[0]))
                self.assertEqual(output.video.codec, "h264")
                self.assertEqual(output.video.pixel_format, "yuv420p")
                self.assertFalse(output.subtitles)
                self.assertTrue(path.is_file())
                if path == srt:
                    baseline = self.root / "baseline.mp4"
                    subprocess.run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                                    "-i", str(self.video), "-map", "0:v:0", "-c:v", "libx264",
                                    "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                                    "-an", str(baseline)], check=True, capture_output=True, timeout=30)
                    def frame_bytes(video: Path) -> bytes:
                        return subprocess.run(
                            [str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                             "-ss", "0.5", "-i", str(video), "-frames:v", "1",
                             "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"],
                            check=True, capture_output=True, timeout=15).stdout
                    burned = frame_bytes(Path(completed[0]))
                    plain = frame_bytes(baseline)
                    self.assertEqual(len(burned), len(plain))
                    self.assertGreater(sum(a != b for a, b in zip(burned, plain)), 100,
                                       "Subtitle burn did not visibly change the frame")
                Path(completed[0]).unlink()

    def test_malformed_subtitle_fails_before_conversion(self) -> None:
        bad = self.root / "broken.ass"
        bad.write_text("not an ASS file", encoding="utf-8")
        completed, failures = self._convert(bad)
        self.assertFalse(completed)
        self.assertTrue(failures)
        self.assertIn("External subtitle could not be rendered", failures[0])
        self.assertFalse((self.root / "source-Kosmi.mp4").exists())

    def test_cancel_external_burn_cleans_staged_copy(self) -> None:
        subtitle = self.root / "cancel.srt"
        subtitle.write_text("1\n00:00:00,100 --> 00:00:00,800\nCancel test\n", encoding="utf-8")
        long_video = self.root / "long.mkv"
        subprocess.run([str(self.runtime.ffmpeg), "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=8",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        str(long_video)], check=True, capture_output=True, timeout=30)
        raw = subprocess.run([str(self.runtime.ffprobe), "-v", "error", "-show_streams",
                              "-show_format", "-of", "json", str(long_video)], check=True,
                             capture_output=True, text=True, timeout=15).stdout
        media = parse_probe(raw, long_video)
        settings = settings_for(long_video).customized(
            subtitle_mode=SubtitleMode.BURN, subtitle_source=ExternalSubtitleSource.from_path(subtitle),
            preset="slower")
        resolved = plan(media, settings)
        runner = ConversionRunner(self.runtime)
        cancelled: list[bool] = []
        runner.cancelled.connect(lambda: (cancelled.append(True), self.app.quit()))
        runner.start(media, resolved)
        workspace = Path(runner.workspace.name)
        QTimer.singleShot(50, runner.cancel)
        run_event_loop(self.app, 15_000)
        self.assertTrue(cancelled)
        self.assertFalse(workspace.exists())
        self.assertTrue(subtitle.exists())
        self.assertFalse(resolved.destination.exists())
        self.assertFalse(list(self.root.glob(".video-converter-*.mp4")))


if __name__ == "__main__":
    unittest.main()
