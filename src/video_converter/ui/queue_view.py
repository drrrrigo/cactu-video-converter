"""Compact queue rows; file imports and stable-ID moves use separate MIME."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QByteArray, QMimeData, QModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QListView, QStyledItemDelegate

from video_converter.models.job import JobStatus, PENDING_STATUSES
from video_converter.models.queue import ConversionQueue
from video_converter.ui.theme import ACCENT, PROGRESS_TRACK

JOB_ROLE = Qt.ItemDataRole.UserRole + 1
MIME = "application/x-video-converter-job-ids"


class QueueListModel(QAbstractListModel):
    reordered = Signal()

    def __init__(self, queue: ConversionQueue, parent=None):
        super().__init__(parent)
        self.queue = queue
        self.ids: list[str] = []

    def refresh(self) -> None:
        ids = [job.id for job in self.queue.jobs]
        if ids != self.ids:
            self.beginResetModel()
            self.ids = ids
            self.endResetModel()
        elif ids:
            self.dataChanged.emit(self.index(0), self.index(len(ids) - 1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.ids)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.ids):
            return None
        job = self.queue.get(self.ids[index.row()])
        if job is None:
            return None
        if role == JOB_ROLE:
            return job.id
        if role == Qt.ItemDataRole.DisplayRole:
            percent = f" · {round(job.progress.fraction * 100)}%" if job.progress and job.progress.fraction is not None and job.status in {
                JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.FINALIZING} else ""
            warning = " ⚠" if job.warnings or job.stream_issues else ""
            return f"☰ {job.input_path.name}\n{job.status.label}{percent}{warning}"
        if role == Qt.ItemDataRole.ToolTipRole:
            return "\n".join(filter(None, [str(job.input_path), job.validation_error, job.error, *job.warnings]))
        if role == Qt.ItemDataRole.AccessibleTextRole:
            return f"{job.input_path.name}, {job.status.value}"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled
        job = self.queue.get(index.data(JOB_ROLE))
        if job and job.status in PENDING_STATUSES | {JobStatus.ANALYZING}:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        return flags

    def mimeTypes(self):
        return [MIME]

    def mimeData(self, indexes):
        mime = QMimeData()
        ids = list(dict.fromkeys(index.data(JOB_ROLE) for index in indexes if index.isValid()))
        mime.setData(MIME, QByteArray(json.dumps(ids).encode()))
        return mime

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def move_ids(self, ids: list[str], row: int) -> bool:
        if not ids or len(ids) != len(set(ids)) or any(job_id not in self.ids for job_id in ids):
            return False
        if any(self.queue.get(job_id).status not in PENDING_STATUSES | {JobStatus.ANALYZING} for job_id in ids):
            return False
        row = len(self.ids) if row < 0 else min(row, len(self.ids))
        before = sum(self.ids.index(job_id) < row for job_id in ids)
        moving = [job_id for job_id in self.ids if job_id in ids]
        remaining = [job_id for job_id in self.ids if job_id not in ids]
        destination = row - before
        ordered = remaining[:destination] + moving + remaining[destination:]
        try:
            self.queue.reorder(ordered)
        except ValueError:
            return False
        self.reordered.emit()
        return True

    def dropMimeData(self, mime, action, row, column, parent):
        if action != Qt.DropAction.MoveAction or not mime.hasFormat(MIME):
            return False
        try:
            ids = json.loads(bytes(mime.data(MIME)))
        except (ValueError, TypeError):
            return False
        if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
            return False
        return self.move_ids(ids, row if row >= 0 else parent.row())


class QueueDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(220, 68)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        job = index.model().queue.get(index.data(JOB_ROLE))
        if job and job.progress and job.progress.fraction is not None and job.status in {
                JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.FINALIZING}:
            rect = option.rect.adjusted(12, option.rect.height() - 8, -12, -4)
            painter.save()
            painter.fillRect(rect, QColor(PROGRESS_TRACK))
            rect.setWidth(round(rect.width() * job.progress.fraction))
            painter.fillRect(rect, QColor(ACCENT))
            painter.restore()


class QueueListView(QListView):
    files_dropped = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setItemDelegate(QueueDelegate(self))
        self.setSpacing(3)
        self.setAccessibleName("Conversion queue")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(MIME):
            self._drop_highlight(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()

    def _drop_highlight(self, active):
        self.setProperty("dropTarget", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.viewport().update()

    def dragLeaveEvent(self, event):
        self._drop_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._drop_highlight(False)
        if event.mimeData().hasUrls():
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        index = self.indexAt(event.position().toPoint())
        row = index.row() if index.isValid() else self.model().rowCount()
        if self.model().dropMimeData(event.mimeData(), Qt.DropAction.MoveAction, row, 0, QModelIndex()):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
