"""Packaged-environment smoke: existing Qt window, planner, runner and verifier."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from video_converter import __version__
from video_converter.conversion.planner import plan
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for
from video_converter.services.startup import check_writable_environment
from video_converter.ui.main_window import MainWindow


def run_smoke(runtime, directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    report = {
        "version": __version__,
        "frozen": bool(getattr(__import__("sys"), "frozen", False)),
        "ok": False,
    }
    try:
        check_writable_environment()
        # An actual configuration window starts; cloud runners need no physical GPU.
        window = MainWindow(runtime)
        window._startup_timer.stop()
        window.show()
        QApplication.processEvents()
        report["window_title"] = window.windowTitle()
        window.close()
        window.deleteLater()
        source = directory / "synthetic.mkv"
        subtitle = directory / "synthetic.srt"
        subtitle.write_text(
            "1\n00:00:00,100 --> 00:00:01,800\nCactu beta smoke\n", encoding="utf-8"
        )
        command = [
            str(runtime.ffmpeg),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=s=256x144:r=10:d=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "flac",
            "-shortest",
            "-y",
            str(source),
        ]
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        original = hashlib.sha256(source.read_bytes()).hexdigest()

        def probe(path):
            raw = subprocess.run(
                [
                    str(runtime.ffprobe),
                    "-v",
                    "error",
                    "-show_streams",
                    "-show_format",
                    "-of",
                    "json",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            ).stdout
            return parse_probe(raw, path)

        media = probe(source)
        output = directory / "converted.mp4"
        settings = settings_for(source).customized(
            destination=output,
            subtitle_mode=SubtitleMode.BURN,
            subtitle_source=ExternalSubtitleSource.from_path(subtitle),
            volume_percent=150,
        )
        resolved = plan(media, settings)
        runner = ConversionRunner(runtime)
        loop = QEventLoop()
        failure = []
        runner.completed.connect(lambda _: loop.quit())
        runner.failed.connect(lambda message, details: (failure.append(message), loop.quit()))
        runner.cancelled.connect(lambda: (failure.append("Cancelled"), loop.quit()))
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: (failure.append("Timed out"), runner.cancel(), loop.quit()))
        runner.start(media, resolved)
        timer.start(60_000)
        loop.exec()
        timer.stop()
        if failure:
            raise RuntimeError("; ".join(failure))
        result = probe(output)
        data = output.read_bytes()
        if (
            not result.video
            or result.video.codec != "h264"
            or not result.audios
            or result.audios[0].codec != "aac"
        ):
            raise RuntimeError("Packaged conversion did not produce H.264/AAC")
        if (
            result.video.pixel_format != "yuv420p"
            or data.find(b"moov") < 0
            or data.find(b"moov") > data.find(b"mdat")
        ):
            raise RuntimeError("Output pixel format / Faststart check failed")
        if result.subtitles or result.duration is None or not 1.7 < result.duration < 2.4:
            raise RuntimeError("Output subtitle/duration check failed")
        if hashlib.sha256(source.read_bytes()).hexdigest() != original:
            raise RuntimeError("Original media changed")
        report.update(
            ok=True,
            ffmpeg=runtime.ffmpeg_version,
            ffprobe=runtime.ffprobe_version,
            runtime_bundled=str(runtime.ffmpeg).startswith(str(runtime.bundled_directory())),
            path=os.environ.get("PATH", ""),
            video=result.video.codec,
            audio=result.audios[0].codec,
            faststart=True,
            original_unchanged=True,
            output_sha256=hashlib.sha256(data).hexdigest(),
        )
        code = 0
    except Exception as exc:
        from video_converter.hardware.report import sanitize

        report["error"] = sanitize(str(exc))
        code = 1
    (directory / "smoke-result.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return code
