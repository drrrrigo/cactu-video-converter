"""Session job records, with stable identity and immutable execution history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from video_converter.ffmpeg.progress import Progress
from video_converter.models.conversion import ConversionPlan, ConversionSettings
from video_converter.models.loudness import LoudnessReport
from video_converter.models.media import MediaInfo

LOG = logging.getLogger(__name__)


def now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    ANALYZING = "analyzing"
    READY = "ready"
    WAITING = "waiting"
    RUNNING = "running"
    PAUSED = "paused"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INVALID = "invalid"

    @property
    def label(self) -> str:
        return {self.ANALYZING: "◌ Analyzing…", self.READY: "○ Ready", self.WAITING: "◷ Waiting",
                self.RUNNING: "▶ Running", self.PAUSED: "Ⅱ Paused", self.FINALIZING: "◌ Finalizing…",
                self.COMPLETED: "✓ Completed", self.FAILED: "✕ Failed", self.CANCELLED: "■ Cancelled",
                self.INVALID: "⚠ Requires attention"}[self]


ACTIVE_STATUSES = {JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.FINALIZING}
TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
PENDING_STATUSES = {JobStatus.READY, JobStatus.WAITING, JobStatus.INVALID}


class ValidationState(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class JobDiagnostics:
    command: tuple[str, ...] = ()
    logs: str = ""
    loudness: LoudnessReport | None = None
    stage: str = ""
    recorded_at: datetime = field(default_factory=now)


@dataclass(frozen=True)
class JobAttempt:
    number: int
    plan: ConversionPlan
    status: JobStatus
    output_path: Path | None
    started_at: datetime
    finished_at: datetime
    error: str
    diagnostics: JobDiagnostics


@dataclass
class ConversionJob:
    input_path: Path
    settings: ConversionSettings
    id: str = field(default_factory=lambda: str(uuid4()))
    media: MediaInfo | None = None
    plan: ConversionPlan | None = None
    executed_plan: ConversionPlan | None = None
    output_path: Path | None = None
    status: JobStatus = JobStatus.ANALYZING
    validation_state: ValidationState = ValidationState.PENDING
    validation_error: str = ""
    output_issue: str = ""
    stream_issues: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    progress: Progress | None = None
    error: str = ""
    created_at: datetime = field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    diagnostics: JobDiagnostics = field(default_factory=JobDiagnostics)
    preview_diagnostics: JobDiagnostics = field(default_factory=JobDiagnostics)
    attempts: int = 0
    history: tuple[JobAttempt, ...] = ()

    @property
    def editable(self) -> bool:
        return self.media is not None and self.status in PENDING_STATUSES

    def transition(self, status: JobStatus) -> None:
        if not isinstance(status, JobStatus):
            raise ValueError("Invalid job status.")
        if self.status == status:
            return
        allowed = {
            JobStatus.ANALYZING: PENDING_STATUSES,
            JobStatus.READY: PENDING_STATUSES | {JobStatus.RUNNING},
            JobStatus.WAITING: PENDING_STATUSES | {JobStatus.RUNNING},
            JobStatus.INVALID: PENDING_STATUSES | {JobStatus.ANALYZING},
            JobStatus.RUNNING: ACTIVE_STATUSES | TERMINAL_STATUSES,
            JobStatus.PAUSED: ACTIVE_STATUSES | TERMINAL_STATUSES,
            JobStatus.FINALIZING: ACTIVE_STATUSES | TERMINAL_STATUSES,
            JobStatus.COMPLETED: PENDING_STATUSES,
            JobStatus.FAILED: PENDING_STATUSES,
            JobStatus.CANCELLED: PENDING_STATUSES,
        }
        if status not in allowed[self.status]:
            raise ValueError(f"Invalid job transition: {self.status.value} → {status.value}")
        LOG.info("Job %s input=%s status=%s → %s", self.id, self.input_path, self.status.value, status.value)
        self.status = status
