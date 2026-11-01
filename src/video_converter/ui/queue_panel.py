"""Queue presentation and selected-job binding; scheduling stays in the controller."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGridLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from video_converter.models.conversion import SubtitleMode
from video_converter.models.job import JobStatus, JobDiagnostics, TERMINAL_STATUSES
from video_converter.models.queue import OutputPolicy, QueueState
from video_converter.models.subtitle import EmbeddedSubtitleSource, ExternalSubtitleSource
from video_converter.services.preview_store import PreviewStore
from video_converter.ui.queue_view import JOB_ROLE, QueueListModel, QueueListView


def label(text, name=""):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    return widget


class QueuePanelMixin:
    def _build_queue_sidebar(self):
        sidebar = QWidget()
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(460)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.addWidget(label("Queue", "section"))
        self.add_files_button = QPushButton("+ Add Files")
        self.add_files_button.clicked.connect(self._browse_input)
        layout.addWidget(self.add_files_button)
        self.empty_queue = label("Drop videos here\nMKV, MP4, MOV and more", "muted")
        layout.addWidget(self.empty_queue)
        self.queue_list = QueueListView()
        self.queue_model = QueueListModel(self.queue, self)
        self.queue_list.setModel(self.queue_model)
        self.queue_list.files_dropped.connect(self.add_files)
        self.queue_model.reordered.connect(self._queue_changed)
        self.queue_list.selectionModel().currentChanged.connect(self._selection_changed)
        self.queue_list.selectionModel().selectionChanged.connect(lambda *_: self._update_bulk_bar())
        layout.addWidget(self.queue_list, 1)
        self.bulk_bar = QWidget()
        bulk = QGridLayout(self.bulk_bar)
        bulk.setContentsMargins(0, 0, 0, 0)
        self.bulk_count = label("")
        bulk.addWidget(self.bulk_count, 0, 0)
        bulk.addWidget(label("Copy from"), 0, 1)
        self.copy_source = QComboBox()
        self.copy_source.setAccessibleName("Copy settings source job")
        bulk.addWidget(self.copy_source, 0, 2)
        self._last_single_job_id = None
        self._bulk_was_multi = False
        self.bulk_preset_button = QPushButton("Apply Web Preset")
        self.bulk_preset_button.setObjectName("primary")
        self.bulk_preset_button.clicked.connect(self._bulk_preset)
        self.bulk_copy_button = QPushButton("Copy Settings")
        self.bulk_copy_button.clicked.connect(self._bulk_copy)
        self.bulk_folder_button = QPushButton("Output Folder")
        self.bulk_folder_button.clicked.connect(self._bulk_folder)
        bulk.addWidget(self.bulk_preset_button, 1, 0)
        bulk.addWidget(self.bulk_copy_button, 1, 1)
        bulk.addWidget(self.bulk_folder_button, 1, 2)
        actions = QGridLayout()
        self.remove_button = QPushButton("Remove")
        self.remove_button.setObjectName("danger")
        self.remove_button.clicked.connect(self._remove_selected)
        self.requeue_button = QPushButton("Retry / Requeue")
        self.requeue_button.clicked.connect(lambda: self.queue_controller.retry(self._selected_ids()))
        self.retry_failed_button = QPushButton("Retry Failed")
        self.retry_failed_button.clicked.connect(self._retry_failed)
        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.setObjectName("danger")
        self.clear_completed_button.clicked.connect(self._clear_completed)
        actions.addWidget(self.remove_button, 0, 0)
        actions.addWidget(self.requeue_button, 0, 1)
        actions.addWidget(self.retry_failed_button, 1, 0)
        actions.addWidget(self.clear_completed_button, 1, 1)
        layout.addLayout(actions)
        self.output_policy = QComboBox()
        self.output_policy.setAccessibleName("Output collision policy")
        self.output_policy.setToolTip("Policy for existing outputs and duplicate destination paths.")
        for title, value in [("Rename automatically", OutputPolicy.RENAME),
                             ("Skip existing", OutputPolicy.SKIP_EXISTING),
                             ("Require attention", OutputPolicy.REQUIRE_ATTENTION)]:
            self.output_policy.addItem(title, value)
        layout.addWidget(self.output_policy)
        self.job_output_button = QPushButton("Open Output Folder")
        self.job_output_button.clicked.connect(self._open_job_output)
        return sidebar

    def _selected_ids(self):
        return [index.data(JOB_ROLE) for index in self.queue_list.selectionModel().selectedIndexes()]

    def _select_job(self, job_id):
        if job_id not in self.queue_model.ids:
            return
        index = self.queue_model.index(self.queue_model.ids.index(job_id))
        self.queue_list.selectionModel().setCurrentIndex(index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def _selection_changed(self, current, _previous):
        if current.isValid():
            self._bind_job(self.queue.get(current.data(JOB_ROLE)))

    def _queue_changed(self):
        if not hasattr(self, "queue_model"):
            return
        selected = self._selected_ids()
        current = self.selected_job_id
        selection = self.queue_list.selectionModel()
        with QSignalBlocker(selection):
            self.queue_model.refresh()
            for job_id in selected:
                if job_id in self.queue_model.ids:
                    selection.select(self.queue_model.index(self.queue_model.ids.index(job_id)),
                                     QItemSelectionModel.SelectionFlag.Select)
            if current in self.queue_model.ids:
                selection.setCurrentIndex(self.queue_model.index(self.queue_model.ids.index(current)),
                                          QItemSelectionModel.SelectionFlag.NoUpdate)
        job = self.queue.get(current)
        if job is None:
            if self.queue.jobs:
                self._select_job(self.queue.jobs[0].id)
            else:
                self.selected_job_id = None
                self.media = self.settings = self.current_plan = None
                self.input_path.clear()
                self.source_summary.setText("Drop videos into the queue to begin.")
                self.summary.setText("Select a job to see its output plan.")
                self.validation.setText("")
        elif job.media is not self.media or job.settings is not self.settings:
            self._bind_job(job)
        counts = self.queue.counts()
        total = len(self.queue.jobs)
        state = self.queue.state
        prefix = {QueueState.IDLE: "Queue", QueueState.RUNNING: "Queue running",
                  QueueState.PAUSE_REQUESTED: "Queue will pause after current file",
                  QueueState.PAUSED: "Queue paused", QueueState.STOPPING: "Stopping queue…",
                  QueueState.COMPLETED: "Queue completed"}[state]
        self.queue_summary.setText(f"{prefix} · {counts[JobStatus.COMPLETED]} / {total} completed · "
            f"{counts[JobStatus.FAILED]} failed · {counts[JobStatus.CANCELLED]} cancelled · "
            f"{counts[JobStatus.INVALID]} require attention")
        self.empty_queue.setVisible(total == 0)
        self._update_queue_controls()

    def _job_changed(self, job_id):
        self.queue_model.refresh()
        job = self.queue.get(job_id)
        if job_id == self.selected_job_id and job and job.media is not self.media:
            self._bind_job(job)
        if self.queue_controller.active_id == job_id:
            self.current_job_label.setText(f"Current: {job.input_path.name} → {job.executed_plan.destination.name}")
            self.state.setText(job.diagnostics.stage)
        self._update_queue_controls()

    def _active_job_changed(self, job_id):
        if job_id:
            self._job_changed(job_id)
            self._on_stage("")
        self._queue_changed()

    def _queue_message(self, message):
        self.footer.setText(message)

    def _queue_finished(self):
        self.state.setText("Queue completed")
        self.current_job_label.setText("All runnable jobs finished")
        if self._queued_capabilities is not None:
            queued, self._queued_capabilities = self._queued_capabilities, None
            self._hardware_detected(queued)
        self._queue_changed()

    def _bind_job(self, job):
        if job is None:
            return
        self._loading = True
        self.selected_job_id = job.id
        self.media, self.settings, self.current_plan = job.media, job.settings, job.plan
        self.preview_store = self._store_for_job(job.id)
        self.input_path.setText(str(job.input_path))
        if job.media:
            self._populate_media(job.media, restore=False)
            self._loading = True
            self._load_job_settings(job)
        else:
            self.source_summary.setText(f"{job.input_path.name}\n{job.status.label}")
            self.summary.setText("Media analysis is pending or unavailable.")
            self.validation.setText(job.validation_error)
        self._loading = False
        if job.media:
            self._refresh_plan()
        self._refresh_preview_status()
        self._update_queue_controls()

    def _store_for_job(self, job_id):
        store = self._preview_stores.get(job_id)
        if store is None:
            store = self._unbound_preview_store or PreviewStore()
            self._unbound_preview_store = None
            self._preview_stores[job_id] = store
        return store

    def _capture_preview_diagnostics(self, stage):
        job = self.queue.get(self.selected_job_id)
        if job:
            commands = self.runner.commands
            command = next((command for command in reversed(commands) if command[0] == str(self.runtime.ffmpeg)), ())
            job.preview_diagnostics = JobDiagnostics(tuple(command), self.runner.stderr,
                self.runner.loudness_report, stage)

    def _load_job_settings(self, job):
        settings = job.settings
        self.destination_folder.setText(str(settings.destination.parent))
        self.filename.setText(settings.destination.name)
        for combo, value in [(self.video_codec, settings.video_codec), (self.encode_preset, settings.preset),
                (self.pixel_format, settings.pixel_format), (self.hardware_quality, settings.hardware_quality),
                (self.audio_codec, settings.audio_codec), (self.bitrate, settings.audio_bitrate_kbps),
                (self.channels, settings.audio_channels), (self.audio_mode, settings.audio_processing_mode),
                (self.loudness_preset, settings.loudness_target.preset)]:
            combo.setCurrentIndex(combo.findData(value))
        engine_index = next((index for index in range(self.engine_combo.count())
                             if self.engine_combo.itemData(index) == settings.encoding_engine), -1)
        if engine_index < 0:
            self.engine_combo.addItem(settings.encoding_engine.backend.display_name + " (unavailable)", settings.encoding_engine)
            engine_index = self.engine_combo.count() - 1
        self.engine_combo.setCurrentIndex(engine_index)
        self.crf.setValue(settings.crf)
        audio = settings.audio_index
        if audio is None and "audio" not in job.stream_issues and job.media.preferred_audio:
            audio = job.media.preferred_audio.index
        self.audio_track.setCurrentIndex(self.audio_track.findData(audio))
        self.volume_slider.setValue(settings.volume_percent)
        self.volume_value.setText(f"{settings.volume_percent}%")
        self.prevent_clipping.setChecked(settings.prevent_clipping)
        self.loudness_i.setValue(settings.loudness_target.integrated_lufs)
        self.loudness_tp.setValue(settings.loudness_target.true_peak_dbtp)
        self.loudness_lra.setValue(settings.loudness_target.loudness_range_lu)
        self.mode_none.setChecked(settings.subtitle_mode == SubtitleMode.NONE)
        self.mode_selectable.setChecked(settings.subtitle_mode == SubtitleMode.SELECTABLE)
        self.mode_burn.setChecked(settings.subtitle_mode == SubtitleMode.BURN)
        source = settings.subtitle_source
        external = isinstance(source, ExternalSubtitleSource)
        self.external_subtitle_path = source.path if external else None
        self.subtitle_filename.setText(source.path.name if external else "")
        self.subtitle_filename.setToolTip(str(source.path) if external else "")
        self.subtitle_external.setChecked(external)
        self.subtitle_embedded.setChecked(not external)
        index = source.stream_index if isinstance(source, EmbeddedSubtitleSource) else settings.subtitle_index
        self.subtitle_track.setCurrentIndex(self.subtitle_track.findData(index))
        self.preset_combo.setCurrentIndex(0 if settings.preset_name == "Web Compatibility / Kosmi" else 1)
        self._update_quality_controls()
        self._update_audio_controls()
        self._update_subtitle_controls()
        self._update_volume_note()

    def _update_queue_controls(self):
        if not hasattr(self, "queue_pause_button"):
            return
        job = self.queue.get(self.selected_job_id)
        preview_busy = self._active_preview is not None or self._preflight_plan is not None
        runner_busy = self.runner.phase not in {"idle", "done"}
        busy = self.queue_controller.busy or preview_busy or runner_busy or self._hardware_testing()
        self._set_config_enabled(bool(job and job.editable) and not preview_busy)
        self.queue_list.setEnabled(not preview_busy)
        self.start_button.setEnabled(not busy and any(j.status in {JobStatus.READY, JobStatus.WAITING, JobStatus.ANALYZING} for j in self.queue.jobs))
        self.preview_button.setEnabled(not busy and bool(self.current_plan and job and job.editable))
        self.preview_button.setToolTip("Preview is unavailable while the conversion queue is running." if self.queue_controller.busy else
                                       "Create a preview for the selected job.")
        active = self.queue_controller.active
        self.pause_button.setEnabled((active is not None or preview_busy) and self.runner.phase in {"analyzing", "converting"})
        self.cancel_button.setEnabled(active is not None or preview_busy or runner_busy)
        self.queue_pause_button.setEnabled(self.queue_controller.busy and self.queue.state != QueueState.STOPPING)
        self.queue_pause_button.setText("Resume Queue" if self.queue.state in {QueueState.PAUSE_REQUESTED, QueueState.PAUSED} else "Pause Queue")
        self.queue_stop_button.setEnabled(self.queue_controller.busy)
        self.output_policy.setEnabled(not busy)
        self.requeue_button.setEnabled(not preview_busy and any(self.queue.get(key).status in TERMINAL_STATUSES for key in self._selected_ids() if self.queue.get(key)))
        self.retry_failed_button.setEnabled(not busy and any(j.status == JobStatus.FAILED for j in self.queue.jobs))
        self.clear_completed_button.setEnabled(not preview_busy and any(j.status == JobStatus.COMPLETED for j in self.queue.jobs))
        self.job_output_button.setEnabled(bool(job and job.output_path))
        self._update_bulk_bar()
        self._update_assistant_controls()

    def _update_bulk_bar(self):
        ids = self._selected_ids()
        multiple = len(ids) > 1
        if len(ids) == 1:
            self._last_single_job_id = ids[0]
        desired = self.copy_source.currentData() if self._bulk_was_multi else self._last_single_job_id
        sources = [job for job in self.queue.jobs if job.media]
        with QSignalBlocker(self.copy_source):
            self.copy_source.clear()
            for job in sources:
                self.copy_source.addItem(f"{job.input_path.name} — {job.input_path.parent}", job.id)
            index = self.copy_source.findData(desired)
            fallback = self.copy_source.findData(self.selected_job_id)
            self.copy_source.setCurrentIndex(index if index >= 0 else fallback if fallback >= 0 else 0 if sources else -1)
        self._bulk_was_multi = multiple
        self.bulk_bar.setVisible(multiple)
        self.bulk_count.setText(f"{len(ids)} selected")
        editable = [self.queue.get(key) for key in ids if self.queue.get(key) and self.queue.get(key).editable]
        for button in (self.bulk_preset_button, self.bulk_copy_button, self.bulk_folder_button):
            button.setEnabled(bool(editable) and self._active_preview is None)
        source = self.queue.get(self.copy_source.currentData())
        self.bulk_copy_button.setToolTip(f"Copy from {source.input_path.name} to the other selected jobs." if source else "Select a source job.")
        self.remove_button.setEnabled(self._active_preview is None and any(self.queue.get(key).status not in {
            JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.FINALIZING} for key in ids if self.queue.get(key)))

    def _bulk_preset(self):
        for key in self._selected_ids():
            job = self.queue.get(key)
            self.batch_settings.apply_web_preset(job)
            self.queue_controller.validate_job(job)
        self._bind_job(self.queue.get(self.selected_job_id))
        self._queue_changed()

    def _bulk_copy(self):
        source = self.queue.get(self.copy_source.currentData())
        if source is None:
            return
        for key in self._selected_ids():
            destination = self.queue.get(key)
            if destination is not source:
                self.batch_settings.copy(source, destination)
                self.queue_controller.validate_job(destination)
        self._queue_changed()

    def _bulk_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Output Folder for Selected Jobs",
                                                  str(self.storage.value("bulk_output_dir", str(Path.home()))))
        if not folder:
            return
        self.storage.setValue("bulk_output_dir", folder)
        for key in self._selected_ids():
            job = self.queue.get(key)
            if job.editable:
                job.output_issue = ""
                job.settings = replace(job.settings, destination=Path(folder) / job.settings.destination.name)
                self.queue_controller.validate_job(job)
        self._queue_changed()

    def _remove_selected(self):
        self._remove_jobs(self._selected_ids())

    def _remove_jobs(self, ids):
        removed = self.queue_controller.remove(ids)
        for key in removed:
            store = self._preview_stores.pop(key, None)
            if store:
                store.cleanup()
        self._queue_changed()

    def _clear_completed(self):
        self._remove_jobs([j.id for j in self.queue.jobs if j.status == JobStatus.COMPLETED])

    def _retry_failed(self):
        self.queue_controller.retry([j.id for j in self.queue.jobs if j.status == JobStatus.FAILED])
        self._queue_changed()

    def _pause_current(self):
        if self.queue_controller.active:
            self.queue_controller.pause_current()
        else:
            self.runner.pause_or_resume()

    def _pause_queue(self):
        if self.queue.state in {QueueState.PAUSED, QueueState.PAUSE_REQUESTED}:
            self.queue_controller.resume()
        else:
            self.queue_controller.pause_queue()

    def _stop_queue(self):
        result = QMessageBox.question(self, "Stop conversion queue?",
            "The current conversion will be cancelled.\nRemaining jobs will stay in the queue.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.queue_controller.stop()

    def _show_media_details(self):
        if self.media:
            box = QMessageBox(QMessageBox.Icon.Information, "Media Details", self.media.path.name,
                              QMessageBox.StandardButton.Ok, self)
            box.setInformativeText("Cached source analysis — expand Details for streams, attachments and metadata.")
            box.setDetailedText(json.dumps(asdict(self.media), indent=2, default=str, ensure_ascii=False))
            box.exec()

    def _show_job_details(self):
        job = self.queue.get(self.selected_job_id)
        if job:
            box = QMessageBox(QMessageBox.Icon.Information, "Job Details",
                f"{job.input_path.name}\n{job.status.label}\n{job.validation_error or job.error}",
                QMessageBox.StandardButton.Ok, self)
            details = asdict(job)
            details["diagnostics"].pop("logs", None)
            details["preview_diagnostics"].pop("logs", None)
            box.setDetailedText(json.dumps(details, indent=2, default=str, ensure_ascii=False) +
                "\n\nFFmpeg conversion logs:\n" + job.diagnostics.logs +
                "\n\nFFmpeg preview logs:\n" + job.preview_diagnostics.logs)
            box.exec()

    def _open_job_output(self):
        job = self.queue.get(self.selected_job_id)
        if job and job.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(job.output_path.parent)))
