"""Own generated preview outputs for one desktop application session."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from video_converter.conversion.preview_planner import validate_preview_sources
from video_converter.conversion.validator import ValidationError
from video_converter.models.conversion import ConversionPlan
from video_converter.models.preview import PreviewPlan

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreviewArtifact:
    plan: PreviewPlan
    created_at: datetime

    def matches(self, current: ConversionPlan | None) -> bool:
        if current != self.plan.conversion_plan:
            return False
        try:
            validate_preview_sources(self.plan)
        except ValidationError:
            return False
        return True


class PreviewStore:
    def __init__(self) -> None:
        self._workspace = tempfile.TemporaryDirectory(prefix="video-converter-previews-",
                                                      ignore_cleanup_errors=True)
        self._candidate: Path | None = None
        self.latest: PreviewArtifact | None = None

    def allocate(self) -> Path:
        self.discard()
        self._candidate = Path(tempfile.mkdtemp(prefix="sample-", dir=self._workspace.name)) / "preview.mp4"
        return self._candidate

    def commit(self, plan: PreviewPlan) -> None:
        if self._candidate != plan.output_path or not plan.output_path.is_file():
            raise OSError("Preview output was not produced in the managed preview folder.")
        previous = self.latest
        self.latest = PreviewArtifact(plan, datetime.now(timezone.utc))
        self._candidate = None
        if previous is not None:
            self._remove(previous.plan.output_path)

    def discard(self) -> None:
        if self._candidate is not None:
            self._remove(self._candidate)
            self._candidate = None

    def _remove(self, path: Path) -> None:
        try:
            shutil.rmtree(path.parent)
        except OSError:
            LOG.warning("Could not remove generated preview folder %s", path.parent, exc_info=True)

    def cleanup(self) -> None:
        self._workspace.cleanup()
        self._candidate = None
        self.latest = None
