"""Sequential orchestration around the existing single-plan media runner."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from video_converter.conversion.planner import plan
from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.models.audio import AudioProcessingMode
from video_converter.models.encoder import EncoderBackend
from video_converter.models.job import (
    ConversionJob, JobAttempt, JobDiagnostics, JobStatus, PENDING_STATUSES, ValidationState, now,
)
from video_converter.models.queue import ConversionQueue, OutputPolicy, QueueState, path_identity
from video_converter.services.probe_pool import MediaProbePool
from video_converter.ui.hardware_worker import HardwareDetectionWorker

LOG = logging.getLogger(__name__)


class QueueController(QObject):
    hardware_capability_changed = Signal(object)
    changed = Signal()
    job_changed = Signal(str)
    active_changed = Signal(object)
    message = Signal(str)
    finished = Signal()

    def __init__(self, queue: ConversionQueue, runner: ConversionRunner, runtime: FFmpegRuntime,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.queue, self.runner, self.runtime = queue, runner, runtime
        self.probes = MediaProbePool(runtime.ffprobe, self)
        self.probes.analyzed.connect(self._analyzed)
        self.probes.rejected.connect(self._rejected)
        self.capabilities = ()
        self.output_policy = OutputPolicy.RENAME
        self.active_id: str | None = None
        self.detector = HardwareEncoderDetector(runtime.ffmpeg)
        self._hardware_thread: QThread | None = None
        self._hardware_worker = None
        self._hardware_result = None
        self._cancel_preflight = False
        self._runner_owned = False
        runner.progress_changed.connect(self._progress)
        runner.state_changed.connect(self._state)
        runner.completed.connect(self._completed)
        runner.failed.connect(self._failed)
        runner.cancelled.connect(self._cancelled)
        if hasattr(runner, "stage_changed"):
            runner.stage_changed.connect(self._stage)

    @property
    def busy(self) -> bool:
        return self.queue.state in {QueueState.RUNNING, QueueState.PAUSE_REQUESTED, QueueState.PAUSED, QueueState.STOPPING}

    @property
    def active(self) -> ConversionJob | None:
        return self.queue.get(self.active_id)

    def add_paths(self, paths: list[Path]) -> list[ConversionJob]:
        if self.queue.state == QueueState.COMPLETED:
            self._queue_state(QueueState.IDLE)
        added = []
        for path in paths:
            try:
                job = self.queue.add(path)
            except (OSError, ValueError) as exc:
                self.message.emit(f"Could not add {path.name}: {exc}")
                continue
            if job is None:
                self.message.emit(f"{path.name} is already in the queue.")
                continue
            added.append(job)
            LOG.info("Job %s added input=%s queue_position=%d", job.id, job.input_path, len(self.queue.jobs))
        self.changed.emit()
        for job in added:
            self.probes.submit(job.id, job.input_path)
        return added

    def _analyzed(self, job_id, media) -> None:
        job = self.queue.get(job_id)
        if job is None:
            return
        job.media = media
        job.transition(JobStatus.READY)
        self.validate_job(job)
        self.job_changed.emit(job.id)
        self.changed.emit()
        if self.queue.state == QueueState.RUNNING:
            self._schedule()

    def _rejected(self, job_id, error) -> None:
        job = self.queue.get(job_id)
        if job is None:
            return
        job.validation_state, job.validation_error = ValidationState.INVALID, error
        job.error = error
        job.transition(JobStatus.INVALID)
        self.job_changed.emit(job.id)
        self.changed.emit()
        if self.queue.state == QueueState.RUNNING:
            self._schedule()

    def validate_job(self, job: ConversionJob, *, review_output: bool = True) -> bool:
        if job.media is None:
            return False
        try:
            if job.output_issue:
                raise ValueError(job.output_issue)
            if job.stream_issues:
                raise ValueError("\n".join(job.stream_issues.values()))
            if job.settings.audio_processing_mode == AudioProcessingMode.LOUDNESS_NORMALIZATION and not self.runtime.loudnorm_available:
                raise ValueError("FFmpeg loudness normalization is unavailable.")
            job.plan = plan(job.media, job.settings, overwrite=review_output, capabilities=self.capabilities)
            job.validation_state, job.validation_error = ValidationState.VALID, ""
            if job.status in PENDING_STATUSES:
                job.transition(JobStatus.WAITING if self.busy else JobStatus.READY)
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            job.plan = None
            job.validation_state, job.validation_error = ValidationState.INVALID, str(exc)
            if job.status in PENDING_STATUSES:
                job.transition(JobStatus.INVALID)
            return False

    def _output_error(self, job: ConversionJob, message: str) -> None:
        job.output_issue = message
        job.validation_state, job.validation_error, job.plan = ValidationState.INVALID, message, None
        job.transition(JobStatus.INVALID)

    def prepare(self, policy: OutputPolicy | None = None) -> tuple[int, int]:
        if policy is not None:
            self.output_policy = policy
        pending = [job for job in self.queue.jobs if job.status in PENDING_STATUSES and job.media]
        for job in pending:
            job.output_issue = ""
            self.validate_job(job)
        valid = [job for job in pending if job.plan is not None]
        destinations: dict[str, list[ConversionJob]] = {}
        for job in valid:
            destinations.setdefault(path_identity(job.settings.destination), []).append(job)
        reserved = {path_identity(job.settings.destination) for job in self.queue.jobs if job not in valid}
        inputs = {path_identity(job.input_path) for job in self.queue.jobs}
        for job in valid:
            destination = job.settings.destination
            identity = path_identity(destination)
            duplicate = len(destinations[identity]) > 1
            exists = destination.exists()
            if self.output_policy == OutputPolicy.REQUIRE_ATTENTION and (exists or duplicate or identity in reserved):
                self._output_error(job, "Output already exists or is shared by another job. Choose a unique filename.")
                continue
            if self.output_policy == OutputPolicy.SKIP_EXISTING and exists:
                self._output_error(job, "Skipped: output already exists. Choose another output or change output policy.")
                continue
            if identity in inputs:
                self._output_error(job, "Output would replace an input in this queue.")
                continue
            if exists or identity in reserved:
                if self.output_policy != OutputPolicy.RENAME:
                    self._output_error(job, "Output path is shared by another queue job.")
                    continue
                number = 2
                while True:
                    candidate = destination.with_name(f"{destination.stem}-{number}{destination.suffix}")
                    candidate_id = path_identity(candidate)
                    if (not candidate.exists() and candidate_id not in reserved and candidate_id not in inputs
                            and candidate_id not in destinations):
                        break
                    number += 1
                job.settings = replace(job.settings, destination=candidate)
                job.warnings = (*job.warnings, f"Output renamed to {candidate.name} to avoid a collision.")
                self.validate_job(job)
                identity = candidate_id
            reserved.add(identity)
        self.changed.emit()
        return (sum(job.status in {JobStatus.READY, JobStatus.WAITING} for job in self.queue.jobs),
                sum(job.status == JobStatus.INVALID for job in self.queue.jobs))

    def start(self, policy: OutputPolicy | None = None) -> None:
        if self.busy or self.runner.phase not in {"idle", "done"}:
            return
        for binary in (self.runtime.ffmpeg, self.runtime.ffprobe):
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise RuntimeError("FFmpeg runtime is unavailable. Restart with a valid runtime.")
        self.prepare(policy)
        self._queue_state(QueueState.RUNNING)
        self._schedule()

    def _queue_state(self, state: QueueState) -> None:
        LOG.info("Queue state=%s → %s", self.queue.state.value, state.value)
        self.queue.state = state
        self.changed.emit()

    def _schedule(self) -> None:
        QTimer.singleShot(0, self._advance)

    def _advance(self) -> None:
        if self.active_id is not None or self.queue.state != QueueState.RUNNING:
            return
        if self.runner.phase not in {"idle", "done"}:
            return
        job = self.queue.next_runnable()
        if job is None:
            if any(job.status == JobStatus.ANALYZING for job in self.queue.jobs):
                return
            self._queue_state(QueueState.COMPLETED)
            self.finished.emit()
            return
        # Recheck all current pending outputs, including edited or newly added jobs.
        self.prepare()
        job = self.queue.next_runnable()
        if job is None:
            self._schedule()
            return
        if not self.validate_job(job, review_output=False):
            self.job_changed.emit(job.id)
            self._schedule()
            return
        self.active_id = job.id
        self._runner_owned = False
        job.executed_plan = job.plan
        job.started_at, job.finished_at = now(), None
        job.attempts += 1
        job.error, job.progress = "", None
        job.diagnostics = JobDiagnostics(stage="Preparing…")
        job.transition(JobStatus.RUNNING)
        LOG.info("Job %s starting input=%s queue_position=%d output=%s time=%s", job.id, job.input_path,
                 self.queue.jobs.index(job) + 1, job.plan.destination, job.started_at)
        self.active_changed.emit(job.id)
        self.changed.emit()
        if not job.plan.video_copy and job.plan.encoding_engine.backend != EncoderBackend.SOFTWARE_X264:
            self._preflight(job)
        else:
            self._run(job)

    def _preflight(self, job: ConversionJob) -> None:
        job.diagnostics.stage = "Checking hardware encoder…"
        self._cancel_preflight = False
        self._hardware_result = None
        thread = QThread(self)
        worker = HardwareDetectionWorker(self.detector, job.executed_plan.encoding_engine)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.checked.connect(self._hardware_checked)
        worker.failed.connect(self._hardware_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._preflight_finished)
        thread.finished.connect(thread.deleteLater)
        self._hardware_thread, self._hardware_worker = thread, worker
        self.job_changed.emit(job.id)
        thread.start()

    def _hardware_checked(self, result, _request) -> None:
        self._hardware_result = result

    def _hardware_failed(self, error, _request) -> None:
        self._hardware_result = error

    def _preflight_finished(self) -> None:
        self._hardware_thread, self._hardware_worker = None, None
        job = self.active
        if job is None:
            return
        result = self._hardware_result
        if self._cancel_preflight:
            self._terminal(JobStatus.CANCELLED)
        elif result is None or isinstance(result, str) or not result.available:
            reason = result if isinstance(result, str) else getattr(result, "reason_unavailable", "Hardware preflight failed.")
            if result is not None and not isinstance(result, str):
                self.capabilities = tuple(c for c in self.capabilities if c.selection != result.selection) + (result,)
                for pending in self.queue.jobs:
                    if pending.editable:
                        self.validate_job(pending)
                self.hardware_capability_changed.emit(result)
            self._terminal(JobStatus.FAILED, f"Selected hardware encoder unavailable: {reason}")
        else:
            self._run(job)

    def _run(self, job: ConversionJob) -> None:
        self._runner_owned = True
        try:
            self.runner.start(job.media, job.executed_plan, overwrite=False)
        except (OSError, ValueError, RuntimeError) as exc:
            self._terminal(JobStatus.FAILED, str(exc))

    def _progress(self, progress) -> None:
        if self.active:
            self.active.progress = progress
            self.job_changed.emit(self.active.id)

    def _stage(self, label: str) -> None:
        if self.active:
            self.active.progress = None
            self.active.diagnostics.stage = label
            self.job_changed.emit(self.active.id)

    def _state(self, state: str) -> None:
        job = self.active
        if job is None:
            return
        job.diagnostics.stage = state
        status = JobStatus.PAUSED if state == "Paused" else (
            JobStatus.FINALIZING if self.runner.phase == "verifying" else JobStatus.RUNNING)
        job.transition(status)
        self.job_changed.emit(job.id)

    def _completed(self, output: str) -> None:
        if self.active:
            self.active.output_path = Path(output)
            self._terminal(JobStatus.COMPLETED)

    def _failed(self, message: str, details: str) -> None:
        if self.active:
            if self.runner.phase not in {"idle", "done"}:
                self.message.emit(message)
                return
            self._terminal(JobStatus.FAILED, message, details)

    def _cancelled(self) -> None:
        if self.active:
            self._terminal(JobStatus.CANCELLED)

    def _terminal(self, status: JobStatus, error: str = "", details: str = "") -> None:
        job = self.active
        if job is None:
            return
        job.finished_at, job.error = now(), error
        commands = getattr(self.runner, "commands", ()) if self._runner_owned else ()
        job.diagnostics.command = next((tuple(command) for command in reversed(commands)
                                       if command and command[0] == str(self.runtime.ffmpeg)), ())
        job.diagnostics.logs = details or (self.runner.stderr if self._runner_owned else error)
        job.diagnostics.loudness = self.runner.loudness_report if self._runner_owned else None
        job.diagnostics.recorded_at = now()
        job.transition(status)
        job.history = (*job.history, JobAttempt(job.attempts, job.executed_plan, status,
            job.output_path if status == JobStatus.COMPLETED else None, job.started_at, job.finished_at,
            error, replace(job.diagnostics)))
        LOG.info("Job %s finished status=%s output=%s time=%s failure=%s", job.id, status.value,
                 job.output_path, job.finished_at, error)
        if error:
            LOG.error("Job %s failed: %s", job.id, error)
        self.active_id = None
        self.job_changed.emit(job.id)
        self.active_changed.emit(None)
        if self.queue.state == QueueState.STOPPING:
            self._queue_state(QueueState.IDLE)
        elif self.queue.state == QueueState.PAUSE_REQUESTED:
            self._queue_state(QueueState.PAUSED)
        else:
            self.changed.emit()
            self._schedule()

    def pause_current(self) -> None:
        if self.active and self._hardware_thread is None:
            self.runner.pause_or_resume()

    def pause_queue(self) -> None:
        if self.queue.state == QueueState.RUNNING:
            self._queue_state(QueueState.PAUSE_REQUESTED if self.active else QueueState.PAUSED)

    def resume(self) -> None:
        if self.queue.state in {QueueState.PAUSED, QueueState.PAUSE_REQUESTED}:
            self._queue_state(QueueState.RUNNING)
            self._schedule()

    def cancel_current(self) -> None:
        if self.active:
            if self._hardware_thread:
                self._cancel_preflight = True
                self.active.diagnostics.stage = "Cancelling hardware check…"
                self.job_changed.emit(self.active.id)
            else:
                self.runner.cancel()

    def stop(self) -> None:
        if not self.busy:
            return
        self._queue_state(QueueState.STOPPING)
        if self.active:
            self.cancel_current()
        else:
            self._queue_state(QueueState.IDLE)

    def retry(self, job_ids: list[str]) -> None:
        if self.queue.state == QueueState.COMPLETED:
            self._queue_state(QueueState.IDLE)
        for job_id in job_ids:
            job = self.queue.get(job_id)
            if job and job.status in {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.COMPLETED}:
                job.transition(JobStatus.READY)
                job.error = ""
                self.validate_job(job)
                self.job_changed.emit(job.id)
        self.changed.emit()

    def remove(self, ids: list[str]) -> list[str]:
        removed = []
        for job_id in ids:
            try:
                self.queue.remove(job_id)
                removed.append(job_id)
            except (ValueError, KeyError):
                self.message.emit("Cancel the current job before removing it.")
        self.changed.emit()
        return removed
