"""Qt process lifecycle for extraction and conversion."""

from __future__ import annotations

import logging
import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from video_converter.services.output_commit import commit_output
from video_converter.services.diagnostics import record_error

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.progress import Progress, ProgressDecoder, parse_progress
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.ffmpeg.loudness import analysis_command, parse_measurements, parse_result
from video_converter.models.loudness import LoudnessReport, LoudnessMeasurements
from video_converter.services.loudness_cache import LoudnessCache, LoudnessCacheKey, cache_key
from video_converter.ffmpeg.subtitle_pipeline import prepare_subtitle, preflight_command, clip_selectable_subtitle
from video_converter.media.ffprobe_service import parse_probe, probe_arguments
from video_converter.models.conversion import ConversionPlan, SubtitleMode
from video_converter.models.media import MediaInfo
from video_converter.models.preview import PreviewPlan
from video_converter.conversion.preview_planner import validate_preview_sources

LOG = logging.getLogger(__name__)


class ConversionRunner(QObject):
    """Own one conversion and its temporary resources until it succeeds or exits."""

    progress_changed = Signal(object)
    state_changed = Signal(str)
    stage_changed = Signal(str)
    completed = Signal(str)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(self, runtime: FFmpegRuntime, parent: QObject | None = None, *,
                 loudness_cache: LoudnessCache | None = None) -> None:
        super().__init__(parent)
        self.runtime = runtime
        self.loudness_cache = loudness_cache if loudness_cache is not None else LoudnessCache()
        self.loudness_report: LoudnessReport | None = None
        self._analysis_key: LoudnessCacheKey | None = None
        self._phase_stderr = ""
        self.analysis_seconds: float | None = None
        self.process: QProcess | None = None
        self.plan: ConversionPlan | None = None
        self.preview: PreviewPlan | None = None
        self.last_command: list[str] = []
        self.commands: list[tuple[str, ...]] = []
        self.failure_phase: str | None = None
        self._operation_started = 0.0
        self.media: MediaInfo | None = None
        self.workspace: tempfile.TemporaryDirectory[str] | None = None
        self.partial: Path | None = None
        self.subtitle_file: Path | None = None
        self.decoder = ProgressDecoder()
        self.stderr = ""
        self.verification_output = bytearray()
        self.phase = "idle"
        self.paused = False
        self.cancelling = False
        self.overwrite = False
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self._kill_if_running)

    def start(self, media: MediaInfo, plan: ConversionPlan, *, overwrite: bool = False,
              preview: PreviewPlan | None = None) -> None:
        if self.phase not in {"idle", "done"}:
            raise RuntimeError("A conversion is already running.")
        if preview is not None:
            if plan != preview.execution_plan:
                raise ValueError("Preview execution plan does not match its configuration snapshot.")
            validate_preview_sources(preview)
            LOG.info("Preview requested: %r", preview)
        self.preview = preview
        self.commands = []
        self.failure_phase = None
        self._operation_started = time.monotonic()
        self.media, self.plan, self.overwrite = media, plan, overwrite
        self.resolved_audio_processing = plan.audio_processing.without_measurements()
        self.loudness_report = None
        self._analysis_key = None
        self.analysis_seconds = None
        if self.resolved_audio_processing.normalization_target and not self.runtime.loudnorm_available:
            raise ValueError("FFmpeg loudness normalization is unavailable in this runtime (loudnorm missing).")
        self.workspace = tempfile.TemporaryDirectory(prefix="video-converter-")
        self.stderr = ""
        self.verification_output.clear()
        self.decoder = ProgressDecoder()
        self.cancelling = False
        self.paused = False
        if self.resolved_audio_processing.normalization_target is not None:
            try:
                self._analysis_key = cache_key(plan, self.runtime)
            except (OSError, ValueError):
                self._cleanup()
                raise
            measurements = self.loudness_cache.get(self._analysis_key)
            if measurements is not None:
                LOG.info("Reusing full-track loudness measurements: %r", self._analysis_key)
                self._resolve_measurements(measurements, cache_hit=True)
            else:
                self.phase = "analyzing"
                self._analysis_started = time.monotonic()
                self._stage("Step 1 of 2 — Analyzing Loudness...")
                LOG.info("Loudness analysis started source=%s audio=%s target=%r", plan.source,
                         plan.audio_index, self.resolved_audio_processing.normalization_target)
                self._launch(analysis_command(plan, self.runtime.ffmpeg))
                return
        self._prepare_conversion()

    def _resolve_measurements(self, measurements: LoudnessMeasurements, *, cache_hit: bool) -> None:
        assert self.plan is not None and self.plan.audio_index is not None
        target = self.plan.audio_processing.normalization_target
        assert target is not None
        self.resolved_audio_processing = self.plan.audio_processing.with_measurements(measurements)
        self.loudness_report = LoudnessReport(str(self.plan.source), self.plan.audio_index,
                                             target, measurements, cache_hit)
        LOG.info("Loudness measurements (cache=%s): %r", cache_hit, measurements)

    def _prepare_conversion(self) -> None:
        assert self.plan is not None and self.workspace is not None
        plan, preview = self.plan, self.preview
        self.subtitle_file = None
        prepared = None
        self._clip_selectable = preview is not None and plan.subtitle_mode == SubtitleMode.SELECTABLE
        if plan.subtitle_mode == SubtitleMode.BURN or self._clip_selectable:
            assert plan.subtitle_source is not None
            try:
                prepared = prepare_subtitle(plan.subtitle_source, Path(self.workspace.name),
                                            self.runtime.ffmpeg, plan.source, preview=preview,
                                            selectable=self._clip_selectable)
            except OSError:
                self._cleanup()
                raise
            self.subtitle_file = prepared.path
        # Keep the partial file on the destination filesystem for atomic replace.
        # A unique hidden name avoids collisions with other conversions.
        try:
            descriptor, partial_name = tempfile.mkstemp(prefix=".video-converter-", suffix=".mp4",
                                                       dir=plan.destination.parent)
        except OSError:
            self._cleanup()
            raise
        os.close(descriptor)
        self.partial = Path(partial_name)
        if prepared is not None:
            if prepared.needs_preflight:
                self.phase = "subtitle_preflight"
                self.state_changed.emit("Checking subtitle file...")
                self._launch(preflight_command(self.runtime.ffmpeg, prepared.path))
                return
            self.phase = "extracting"
            self.state_changed.emit("Preparing subtitles...")
            assert prepared.extraction_command is not None
            self._launch(prepared.extraction_command)
        else:
            self._start_conversion()

    def _launch(self, command: list[str]) -> None:
        self.commands.append(tuple(command))
        self._phase_stderr = ""
        self.last_command = command
        LOG.info("Running media process: %r", command)
        if self.process and self.process.state() == QProcess.ProcessState.NotRunning:
            self.process.deleteLater()
        process = QProcess(self)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        if self.workspace:
            process.setWorkingDirectory(self.workspace.name)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._process_error)
        self.process = process
        process.start()

    def _start_conversion(self) -> None:
        assert self.plan is not None and self.partial is not None
        if self._analysis_key is not None:
            try:
                if cache_key(self.plan, self.runtime) != self._analysis_key:
                    raise ValueError("Source or runtime changed after loudness analysis. Reopen the source and try again.")
            except (OSError, ValueError) as exc:
                self._fail(str(exc))
                return
        self.phase = "converting"
        self._stage(self._encoding_label())
        LOG.info("%s started", "Loudness second pass" if self.loudness_report else "Conversion")
        command = build_command(self.plan, self.runtime.ffmpeg, self.partial,
                                subtitle_file=self.subtitle_file, preview=self.preview,
                                audio_processing=self.resolved_audio_processing)
        self._launch(command)

    def _encoding_label(self) -> str:
        return ("Step 2 of 2 — " if self.loudness_report else "") + (
            "Creating Preview..." if self.preview else "Converting...")

    def _stage(self, label: str) -> None:
        self.decoder = ProgressDecoder()
        self.stage_changed.emit(label)
        self.state_changed.emit(label)

    def _read_stdout(self) -> None:
        if self.process is None or self.plan is None:
            return
        raw = bytes(self.process.readAllStandardOutput())
        if self.phase == "verifying":
            self.verification_output.extend(raw)
            return
        if self.phase not in {"analyzing", "converting"}:
            return
        chunk = raw.decode("utf-8", "replace")
        for values in self.decoder.feed(chunk):
            duration = self.media.duration if self.phase == "analyzing" and self.media else self.plan.duration
            progress: Progress = parse_progress(values, duration)
            self.progress_changed.emit(progress)
            if progress.finalizing and self.phase == "converting":
                self.state_changed.emit("Finalizing output...")

    def _read_stderr(self) -> None:
        if self.process:
            chunk = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
            self.stderr += chunk
            self.stderr = self.stderr[-100_000:]
            self._phase_stderr = (self._phase_stderr + chunk)[-100_000:]

    def _process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._fail("FFprobe could not start." if self.phase == "verifying" else
                       "FFmpeg could not start.")

    def _finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.phase == "done":
            return
        self._read_stdout()
        self._read_stderr()
        LOG.info("FFmpeg phase=%s exit=%d", self.phase, exit_code)
        if self.cancelling:
            self._cleanup()
            self.cancelled.emit()
            return
        if exit_code != 0:
            message = {
                "converting": "FFmpeg could not encode this video.",
                "analyzing": "Loudness analysis failed. The selected audio track could not be analyzed.",
                "extracting": "The selected subtitle track could not be prepared.",
                "subtitle_preflight": "External subtitle could not be rendered. Check its format or text encoding.",
                "verifying": "FFprobe could not verify the output video.",
            }.get(self.phase, "The media process failed.")
            if self.phase == "converting" and self.loudness_report:
                message = "Audio normalization failed during final conversion. See Details for FFmpeg diagnostics."
            self._fail(message)
            return
        if self.phase == "analyzing":
            assert self.plan is not None and self._analysis_key is not None
            self.analysis_seconds = time.monotonic() - self._analysis_started
            LOG.info("Loudness analysis completed in %.3fs (media duration=%s)", self.analysis_seconds,
                     self.media.duration if self.media else None)
            try:
                measurements = parse_measurements(self._phase_stderr)
                if cache_key(self.plan, self.runtime) != self._analysis_key:
                    raise ValueError("The source file changed during loudness analysis. Reopen it and try again.")
            except (OSError, ValueError) as exc:
                self._fail(f"The normalization measurements returned by FFmpeg were invalid: {exc}")
                return
            self.loudness_cache.put(self._analysis_key, measurements)
            self._resolve_measurements(measurements, cache_hit=False)
            try:
                self._prepare_conversion()
            except (OSError, ValueError) as exc:
                self._fail(f"Could not prepare conversion after loudness analysis: {exc}")
            return
        if self.phase == "extracting":
            if self._clip_selectable:
                assert self.subtitle_file is not None and self.preview is not None
                try:
                    clip_selectable_subtitle(self.subtitle_file, self.preview)
                except (ValueError, OSError) as exc:
                    self._fail(f"Could not prepare selectable preview subtitles: {exc}")
                    return
            self._start_conversion()
            return
        if self.phase == "subtitle_preflight":
            self._start_conversion()
            return
        if self.phase == "converting":
            if self.loudness_report:
                try:
                    self.loudness_report = replace(self.loudness_report, result=parse_result(self._phase_stderr))
                    LOG.info("Loudness second-pass result: %r", self.loudness_report.result)
                except ValueError as exc:
                    # A preview segment can be silent although the full track is measurable.
                    LOG.warning("Second-pass loudness diagnostics unavailable: %s", exc)
            self.phase = "verifying"
            self.state_changed.emit("Verifying output...")
            assert self.partial is not None
            self._launch([str(self.runtime.ffprobe), *probe_arguments(self.partial)])
            return
        if self.phase == "verifying":
            assert self.partial is not None and self.plan is not None
            try:
                if not self.partial.is_file() or self.partial.stat().st_size == 0:
                    raise OSError("FFmpeg produced no output file.")
                output_media = parse_probe(self.verification_output.decode("utf-8", "replace"), self.partial)
                if "mp4" not in output_media.container.split(",") or not output_media.video or output_media.video.codec != "h264":
                    raise OSError("Output is not MP4/H.264.")
                if output_media.video.pixel_format != "yuv420p":
                    raise OSError("Output video is not 8-bit yuv420p.")
                if self.plan.audio_index is not None and (not output_media.audios or output_media.audios[0].codec != "aac"):
                    raise OSError("Output audio is not AAC.")
                if self.loudness_report and output_media.audios:
                    output_audio = output_media.audios[0]
                    source_audio = next(audio for audio in self.media.audios if audio.index == self.plan.audio_index)
                    expected_channels = self.plan.audio_channels or source_audio.channels
                    if expected_channels and output_audio.channels != expected_channels:
                        raise OSError("Normalized output channel count does not match the selected audio.")
                    if output_audio.sample_rate != self.resolved_audio_processing.output_sample_rate:
                        raise OSError("Normalized output sample rate does not match the audio plan.")
                if self.plan.subtitle_mode == SubtitleMode.BURN and output_media.subtitles:
                    raise OSError("Burned output unexpectedly contains a selectable subtitle stream.")
                if self.plan.subtitle_mode == SubtitleMode.SELECTABLE and len(output_media.subtitles) != 1:
                    raise OSError("Selected subtitle stream is missing from the output.")
                if self.preview is not None and (output_media.duration is None or
                        abs(output_media.duration - self.preview.duration_seconds) > 0.5):
                    raise OSError("Preview duration does not match the requested segment.")
                if self.plan.destination.exists() and not self.overwrite:
                    raise FileExistsError("Output appeared while conversion was running.")
                commit_output(self.partial, self.plan.destination, overwrite=self.overwrite)
                destination = str(self.plan.destination)
            except (OSError, ValueError) as exc:
                self._fail(f"Could not finalize output: {exc}")
                return
            self._cleanup()
            LOG.info("%s completed in %.2f seconds: %s", "Preview" if self.preview else "Conversion",
                     time.monotonic() - self._operation_started, destination)
            self.completed.emit(destination)

    def _fail(self, message: str) -> None:
        record_error("Conversion/" + self.phase)
        self.failure_phase = self.phase
        details = self.stderr[-20_000:]
        if self.preview is not None:
            details = f"Preview: {self.preview!r}\nCommand: {self.last_command!r}\n\n{details}"
        LOG.error("%s\n%s", message, details)
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        self._cleanup()
        self.failed.emit(message, details)

    def pause_or_resume(self) -> None:
        """Suspend the encoder process via psutil on supported desktop systems."""
        if self.phase not in {"analyzing", "converting"} or not self.process:
            return
        import psutil

        try:
            target = psutil.Process(self.process.processId())
            if self.paused:
                target.resume()
                self.paused = False
                self.state_changed.emit("Step 1 of 2 — Analyzing Loudness..." if self.phase == "analyzing"
                                        else self._encoding_label())
            else:
                target.suspend()
                self.paused = True
                self.state_changed.emit("Paused")
        except psutil.Error as exc:
            self.failed.emit("Could not change pause state.", str(exc))

    def cancel(self) -> None:
        if not self.process or self.phase not in {"analyzing", "subtitle_preflight", "extracting", "converting", "verifying"}:
            return
        self.cancelling = True
        self.state_changed.emit("Cancelling...")
        if self.paused:
            try:
                import psutil
                psutil.Process(self.process.processId()).resume()
            except psutil.Error:
                pass
            self.paused = False
        self.process.terminate()
        self.kill_timer.start(3000)

    def _kill_if_running(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _cleanup(self) -> None:
        self.phase = "done"
        self.kill_timer.stop()
        if self.process:
            self.process.deleteLater()
        self.process = None
        if self.partial:
            try:
                self.partial.unlink(missing_ok=True)
            except OSError:
                LOG.exception("Could not remove partial output %s", self.partial)
            self.partial = None
        if self.workspace:
            try:
                self.workspace.cleanup()
            except OSError:
                LOG.exception("Could not remove subtitle workspace")
            self.workspace = None
