"""Ordered jobs and queue state, independent of widgets and media commands."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from video_converter.models.job import ACTIVE_STATUSES, ConversionJob, JobStatus
from video_converter.presets.web_kosmi import settings_for


class QueueState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"


class OutputPolicy(str, Enum):
    RENAME = "rename"
    SKIP_EXISTING = "skip_existing"
    REQUIRE_ATTENTION = "require_attention"


def path_identity(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


class ConversionQueue:
    def __init__(self) -> None:
        self._jobs: list[ConversionJob] = []
        self.state = QueueState.IDLE

    @property
    def jobs(self) -> tuple[ConversionJob, ...]:
        return tuple(self._jobs)

    def get(self, job_id: str | None) -> ConversionJob | None:
        return next((job for job in self._jobs if job.id == job_id), None)

    def add(self, path: Path) -> ConversionJob | None:
        resolved = path.expanduser().resolve()
        identity = path_identity(resolved)
        if any(path_identity(job.input_path) == identity for job in self._jobs):
            return None
        job = ConversionJob(resolved, settings_for(resolved))
        self._jobs.append(job)
        return job

    def remove(self, job_id: str) -> ConversionJob:
        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.status in ACTIVE_STATUSES:
            raise ValueError("Cancel the current job before removing it.")
        self._jobs.remove(job)
        return job

    def reorder(self, ordered_ids: list[str]) -> None:
        if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != {j.id for j in self._jobs}:
            raise ValueError("Reorder must contain every job exactly once.")
        for position, job in enumerate(self._jobs):
            if job.status in ACTIVE_STATUSES and ordered_ids[position] != job.id:
                raise ValueError("The active job's queue position is locked.")
        by_id = {job.id: job for job in self._jobs}
        self._jobs = [by_id[job_id] for job_id in ordered_ids]

    def next_runnable(self) -> ConversionJob | None:
        for job in self._jobs:
            # A faster probe must not let a later job overtake an earlier import.
            if job.status == JobStatus.ANALYZING:
                return None
            if job.status in {JobStatus.READY, JobStatus.WAITING}:
                return job
        return None

    def counts(self) -> dict[JobStatus, int]:
        return {status: sum(job.status == status for job in self._jobs) for status in JobStatus}
