"""Bounded asynchronous FFprobe import; callbacks carry stable job IDs."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from video_converter.media.ffprobe_service import parse_probe, probe_arguments

PROBE_CONCURRENCY = 2


class MediaProbePool(QObject):
    analyzed = Signal(str, object)
    rejected = Signal(str, str)

    def __init__(self, ffprobe: Path, parent: QObject | None = None, *, concurrency: int = PROBE_CONCURRENCY):
        super().__init__(parent)
        if concurrency < 1:
            raise ValueError("Probe concurrency must be positive.")
        self.ffprobe = ffprobe
        self.concurrency = concurrency
        self.pending: deque[tuple[str, Path]] = deque()
        self.active: dict[str, QProcess] = {}
        self.closed = False

    def submit(self, job_id: str, path: Path) -> None:
        self.pending.append((job_id, path))
        self._pump()

    def _pump(self) -> None:
        while not self.closed and self.pending and len(self.active) < self.concurrency:
            job_id, path = self.pending.popleft()
            try:
                if not path.is_file():
                    raise ValueError("Input is missing or is not a regular file.")
                with path.open("rb") as handle:
                    handle.read(1)
            except (OSError, ValueError) as exc:
                self.rejected.emit(job_id, str(exc))
                continue
            process = QProcess(self)
            process.setProgram(str(self.ffprobe))
            process.setArguments(probe_arguments(path))
            output, errors = bytearray(), bytearray()
            timer = QTimer(process)
            timer.setSingleShot(True)
            timer.timeout.connect(process.kill)
            timer.start(30_000)
            self.active[job_id] = process
            process.readyReadStandardOutput.connect(lambda p=process, data=output: data.extend(bytes(p.readAllStandardOutput())))
            process.readyReadStandardError.connect(lambda p=process, data=errors: data.extend(bytes(p.readAllStandardError())))
            def complete(code, _status=None, *, key=job_id, file=path, p=process, data=output, err=errors, timeout=timer):
                # The dict guard handles FailedToStart as well as finished, once.
                if self.active.get(key) is not p:
                    return
                timeout.stop()
                data.extend(bytes(p.readAllStandardOutput()))
                err.extend(bytes(p.readAllStandardError()))
                del self.active[key]
                p.deleteLater()
                if not self.closed:
                    try:
                        if code != 0:
                            raise ValueError("FFprobe could not read video: " + err.decode("utf-8", "replace")[-2000:])
                        media = parse_probe(data.decode("utf-8", "replace"), file)
                        if media.video is None:
                            raise ValueError("No video stream was found.")
                        self.analyzed.emit(key, media)
                    except (ValueError, KeyError, TypeError) as exc:
                        self.rejected.emit(key, str(exc))
                    QTimer.singleShot(0, self._pump)
            process.finished.connect(complete)
            process.errorOccurred.connect(lambda error, callback=complete: callback(-1) if error == QProcess.ProcessError.FailedToStart else None)
            process.start()

    def close(self) -> None:
        self.closed = True
        self.pending.clear()
        for process in list(self.active.values()):
            process.kill()
            process.waitForFinished(1000)
