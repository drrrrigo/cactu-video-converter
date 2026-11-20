"""Packaged-environment smoke: existing Qt window, planner, runner and verifier."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QSslSocket

from video_converter import __version__
from video_converter.conversion.planner import plan
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.audio import AudioProcessingMode
from video_converter.models.job import JobStatus
from video_converter.models.queue import ConversionQueue, QueueState
from video_converter.models.preview import PreviewSettings
from video_converter.conversion.preview_planner import plan_preview
from video_converter.services.queue_controller import QueueController
from video_converter.models.subtitle import ExternalSubtitleSource
from video_converter.presets.web_kosmi import settings_for
from video_converter.services.startup import check_writable_environment
from video_converter.ui.main_window import MainWindow


def run_smoke(runtime, directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    report = {
        "version": __version__,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "frozen": bool(getattr(__import__("sys"), "frozen", False)),
        "ok": False,
    }
    try:
        check_writable_environment()
        report["qt_tls_backends"] = QSslSocket.availableBackends()
        if sys.platform == "win32":
            if "schannel" not in report["qt_tls_backends"] or not QSslSocket.supportsSsl():
                raise RuntimeError("Packaged native Windows TLS backend is unavailable")
            report["qt_tls_active_backend"] = QSslSocket.activeBackend()
            if report["qt_tls_active_backend"] != "schannel":
                raise RuntimeError("Unexpected Qt TLS backend in Windows package")
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
            "testsrc2=s=256x144:r=10:d=6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=6",
            "-i",
            str(subtitle),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:s",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "flac",
            "-c:s",
            "srt",
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
        if result.subtitles or result.duration is None or not 5.7 < result.duration < 6.4:
            raise RuntimeError("Output subtitle/duration check failed")
        preview = plan_preview(media, resolved, PreviewSettings(1, 5), directory / "preview.mp4")
        runner.start(media, preview.execution_plan, preview=preview)
        timer.start(60_000)
        loop.exec()
        timer.stop()
        if failure or not 4.7 < (probe(preview.output_path).duration or 0) < 5.4:
            raise RuntimeError("Packaged Quick Preview failed: " + "; ".join(failure))
        other = directory / "queue-second.mkv"
        shutil.copyfile(source, other)
        queue = ConversionQueue()
        controller = QueueController(queue, ConversionRunner(runtime), runtime)

        def wait_for(predicate):
            poll = QTimer()
            poll.timeout.connect(lambda: loop.quit() if predicate() else None)
            poll.start(20)
            timer.start(60_000)
            loop.exec()
            timer.stop()
            poll.stop()
            if failure or not predicate():
                raise RuntimeError("Packaged queue timed out or failed")

        try:
            jobs = controller.add_paths([source, other])
            wait_for(lambda: all(job.media for job in jobs))
            jobs[0].settings = jobs[0].settings.customized(
                subtitle_mode=SubtitleMode.BURN, subtitle_index=media.subtitles[0].index
            )
            jobs[1].settings = jobs[1].settings.customized(
                audio_processing_mode=AudioProcessingMode.LOUDNESS_NORMALIZATION
            )
            controller.start()
            wait_for(lambda: queue.state == QueueState.COMPLETED)
            if any(job.status != JobStatus.COMPLETED for job in jobs):
                raise RuntimeError(
                    "Packaged queue conversion failed: " + "; ".join(job.error for job in jobs)
                )
            if jobs[1].diagnostics.loudness is None:
                raise RuntimeError("Packaged loudness analysis did not run")
            for job in jobs:
                if probe(job.output_path).video.codec != "h264":
                    raise RuntimeError("Packaged queue output verification failed")
        finally:
            controller.probes.close()
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
            quick_preview=True,
            embedded_subtitle_queue=True,
            loudness_queue=True,
            sequential_queue_completed=2,
            physical_gpu_validation="not performed by frozen smoke; separate optional hardware tests required",
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
