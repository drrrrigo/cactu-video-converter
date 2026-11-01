"""Small generated media scenarios against a developer FFmpeg 9.0.2 pair."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication

from video_converter.conversion.planner import plan
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import CodecChoice, SubtitleMode
from video_converter.presets.web_kosmi import settings_for


def run_event_loop(app: QApplication, timeout_ms: int) -> None:
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(app.quit)
    timer.start(timeout_ms)
    app.exec()
    timer.stop()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.ffmpeg = shutil.which("ffmpeg")
        cls.ffprobe = shutil.which("ffprobe")
        if not cls.ffmpeg or not cls.ffprobe:
            raise unittest.SkipTest("FFmpeg/FFprobe not installed for development integration tests")
        try:
            cls.runtime = FFmpegRuntime.locate(allow_system_development=True)
        except RuntimeError as exc:
            raise unittest.SkipTest("FFmpeg 9.0.2 with required capabilities is unavailable") from exc
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def _run(self, args: list[str]) -> None:
        subprocess.run(args, check=True, capture_output=True, timeout=30)

    def _probe(self, path: Path):
        data = subprocess.run([self.ffprobe, "-v", "error", "-show_streams", "-show_format",
                               "-of", "json", str(path)], check=True, capture_output=True,
                              text=True, timeout=15).stdout
        return parse_probe(data, path)

    def _convert(self, source: Path, *, burn: bool = False) -> tuple[Path, list[object]]:
        media = self._probe(source)
        settings = settings_for(source)
        if burn:
            settings = settings.customized(subtitle_mode=SubtitleMode.BURN,
                                           subtitle_index=media.subtitles[0].index)
        resolved = plan(media, settings)
        runner = ConversionRunner(self.runtime)
        progress: list[object] = []
        result: list[str] = []
        failures: list[str] = []
        runner.progress_changed.connect(progress.append)
        runner.completed.connect(lambda path: (result.append(path), self.app.quit()))
        runner.failed.connect(lambda message, details: (failures.append(message + details), self.app.quit()))
        runner.start(media, resolved)
        run_event_loop(self.app, 30_000)
        self.assertFalse(failures, failures[0][-3000:] if failures else "")
        self.assertTrue(result, "Conversion did not complete within 30 seconds")
        return Path(result[0]), progress

    def test_copy_remux_unicode_path(self) -> None:
        source = self.folder / "Móvie 'sample' (1).mkv"
        self._run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                   "testsrc2=size=160x90:rate=10:duration=1", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", str(source)])
        media = self._probe(source)
        resolved = plan(media, settings_for(source))
        self.assertTrue(resolved.video_copy)
        self.assertTrue(resolved.audio_copy)
        output, progress = self._convert(source)
        self.assertTrue(output.is_file())
        self.assertEqual(self._probe(output).video.codec, "h264")
        self.assertTrue(progress)

    def test_hevc_flac_subtitle_burn(self) -> None:
        subtitle = self.folder / "captions.srt"
        subtitle.write_text("1\n00:00:00,100 --> 00:00:00,800\nHello browser\n", encoding="utf-8")
        source = self.folder / "hevc.mkv"
        self._run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                   "testsrc2=size=160x90:rate=10:duration=1", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=1", "-i", str(subtitle), "-map", "0:v",
                   "-map", "1:a", "-map", "2:s", "-c:v", "libx265", "-pix_fmt", "yuv420p10le",
                   "-x265-params", "log-level=error", "-c:a", "flac", "-c:s", "srt",
                   "-shortest", str(source)])
        media = self._probe(source)
        resolved = plan(media, settings_for(source).customized(
            subtitle_mode=SubtitleMode.BURN, subtitle_index=media.subtitles[0].index))
        self.assertFalse(resolved.video_copy)
        self.assertFalse(resolved.audio_copy)
        output, _ = self._convert(source, burn=True)
        converted = self._probe(output)
        self.assertEqual(converted.video.codec, "h264")
        self.assertEqual(converted.video.pixel_format, "yuv420p")
        self.assertEqual(converted.audios[0].codec, "aac")
        self.assertFalse(converted.subtitles)

    def test_selectable_subtitle_survives_output_verification(self) -> None:
        subtitle = self.folder / "captions.srt"
        subtitle.write_text("1\n00:00:00,100 --> 00:00:00,800\nHello browser\n", encoding="utf-8")
        source = self.folder / "selectable.mkv"
        self._run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                   "testsrc2=size=160x90:rate=10:duration=1", "-i", str(subtitle),
                   "-map", "0:v", "-map", "1:s", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:s", "srt", str(source)])
        media = self._probe(source)
        settings = settings_for(source).customized(
            subtitle_mode=SubtitleMode.SELECTABLE, subtitle_index=media.subtitles[0].index)
        resolved = plan(media, settings)
        runner = ConversionRunner(self.runtime)
        result: list[str] = []
        failures: list[str] = []
        runner.completed.connect(lambda path: (result.append(path), self.app.quit()))
        runner.failed.connect(lambda message, details: (failures.append(message + details), self.app.quit()))
        runner.start(media, resolved)
        run_event_loop(self.app, 30_000)
        self.assertFalse(failures, failures[0][-3000:] if failures else "")
        self.assertTrue(result, "Conversion did not complete within 30 seconds")
        converted = self._probe(Path(result[0]))
        self.assertEqual(len(converted.subtitles), 1)
        self.assertEqual(converted.subtitles[0].codec, "mov_text")

    def test_cancel_cleans_partial_output(self) -> None:
        source = self.folder / "long.mkv"
        self._run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                   "testsrc2=size=640x360:rate=30:duration=8", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=8", "-c:v", "libx264",
                   "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   "-shortest", str(source)])
        media = self._probe(source)
        settings = settings_for(source).customized(video_codec=CodecChoice.H264, preset="slower",
                                                  volume_percent=300)
        resolved = plan(media, settings)
        runner = ConversionRunner(self.runtime)
        cancelled: list[bool] = []
        completed: list[str] = []
        runner.cancelled.connect(lambda: (cancelled.append(True), self.app.quit()))
        runner.completed.connect(lambda path: (completed.append(path), self.app.quit()))
        runner.start(media, resolved)
        QTimer.singleShot(50, runner.cancel)
        run_event_loop(self.app, 15_000)
        self.assertTrue(cancelled)
        self.assertFalse(completed)
        self.assertFalse(resolved.destination.exists())
        self.assertFalse(list(self.folder.glob(".video-converter-*.mp4")))

    def test_pause_and_resume(self) -> None:
        source = self.folder / "pause.mkv"
        self._run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                   "testsrc2=size=640x360:rate=30:duration=8", "-f", "lavfi", "-i",
                   "sine=frequency=440:duration=8", "-c:v", "libx264",
                   "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   "-shortest", str(source)])
        media = self._probe(source)
        resolved = plan(media, settings_for(source).customized(
            video_codec=CodecChoice.H264, preset="slower", volume_percent=300))
        runner = ConversionRunner(self.runtime)
        states: list[str] = []
        completed: list[str] = []
        runner.state_changed.connect(states.append)
        runner.completed.connect(lambda path: (completed.append(path), self.app.quit()))
        runner.failed.connect(lambda message, details: (states.append(message + details), self.app.quit()))
        runner.start(media, resolved)
        QTimer.singleShot(50, runner.pause_or_resume)
        QTimer.singleShot(250, runner.pause_or_resume)
        run_event_loop(self.app, 15_000)
        self.assertIn("Paused", states)
        self.assertTrue(completed, states[-1] if states else "No process state")


if __name__ == "__main__":
    unittest.main()
