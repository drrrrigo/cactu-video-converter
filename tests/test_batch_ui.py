"""Qt selection binding, bulk actions, file-drop MIME and per-job previews."""

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, QMimeData, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.models.job import JobStatus
from video_converter.models.preview import PreviewSettings
from video_converter.models.queue import QueueState, OutputPolicy
from video_converter.ui.main_window import MainWindow
from test_batch_queue import media_for
from qt_helpers import capture_qt_exceptions


class BatchUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        cls.runtime = FFmpegRuntime.locate(allow_system_development=True)

    def setUp(self):
        capture_qt_exceptions(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.window = MainWindow(self.runtime)
        self.window.storage = QSettings(str(self.root / "settings.ini"), QSettings.Format.IniFormat)
        self.addCleanup(self.delete)

    def delete(self):
        self.window.queue_controller.stop()
        if self.window.queue_controller.active:
            self.window.queue_controller._terminal(JobStatus.CANCELLED)
        self.window.runner.phase = "done"
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def add(self, name, **kwargs):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        with patch.object(self.window.queue_controller.probes, "submit"):
            self.window.add_files([path])
        job = self.window.queue.jobs[-1]
        self.window.queue_controller._analyzed(job.id, media_for(path, **kwargs))
        return job

    def select_many(self, jobs, source):
        selection = self.window.queue_list.selectionModel()
        selection.clearSelection()
        for job in jobs:
            index = self.window.queue_model.index(self.window.queue_model.ids.index(job.id))
            selection.select(index, QItemSelectionModel.SelectionFlag.Select)
        selection.setCurrentIndex(self.window.queue_model.index(self.window.queue_model.ids.index(source.id)),
                                  QItemSelectionModel.SelectionFlag.NoUpdate)
        self.window._bind_job(source)

    def test_preanalyzed_path_alias_reuses_existing_job(self):
        job = self.add("movie.mkv")
        nested = self.root / "nested"
        nested.mkdir()
        alias = nested / ".." / "movie.mkv"
        self.window._populate_media(replace(job.media, path=alias))
        self.assertEqual(len(self.window.queue.jobs), 1)
        self.assertEqual(self.window.selected_job_id, job.id)
        self.assertEqual(job.media.path, alias)

    def test_rapid_selection_preserves_every_setting_without_cross_writes(self):
        a, b = self.add("A.mkv"), self.add("B.mkv", reordered=True)
        self.window._select_job(a.id)
        self.window.volume_slider.setValue(175)
        self.window.audio_track.setCurrentIndex(self.window.audio_track.findData(2))
        self.window.mode_burn.setChecked(True)
        self.window.subtitle_track.setCurrentIndex(self.window.subtitle_track.findData(7))
        snapshot = a.settings
        self.window._select_job(b.id)
        self.window.volume_slider.setValue(250)
        self.window.prevent_clipping.setChecked(False)
        b_snapshot = b.settings
        for _ in range(12):
            self.window._select_job(a.id)
            self.assertEqual(self.window.volume_slider.value(), 175)
            self.assertEqual(self.window.subtitle_track.currentData(), 7)
            self.window._select_job(b.id)
            self.assertEqual(self.window.volume_slider.value(), 250)
            self.assertFalse(self.window.prevent_clipping.isChecked())
        self.assertEqual(a.settings, snapshot)
        self.assertEqual(b.settings, b_snapshot)
        self.assertIsNot(a.settings, b.settings)

    def test_multi_selection_bulk_copy_preset_and_directory(self):
        a, b = self.add("A.mkv"), self.add("B.mkv", reordered=True)
        self.window._select_job(a.id)
        self.window.volume_slider.setValue(200)
        self.window.audio_track.setCurrentIndex(self.window.audio_track.findData(2))
        self.window.mode_burn.setChecked(True)
        self.window.subtitle_track.setCurrentIndex(self.window.subtitle_track.findData(7))
        self.select_many([a, b], a)
        self.assertEqual(len(self.window._selected_ids()), 2)
        self.assertFalse(self.window.bulk_bar.isHidden())
        self.window.queue_list.selectionModel().setCurrentIndex(
            self.window.queue_model.index(self.window.queue_model.ids.index(b.id)),
            QItemSelectionModel.SelectionFlag.NoUpdate)
        self.assertEqual(self.window.selected_job_id, b.id)
        self.assertEqual(self.window.copy_source.currentData(), a.id)
        self.window._bulk_copy()
        self.assertEqual(b.settings.audio_index, 9)
        self.assertEqual(b.settings.subtitle_index, 12)
        self.assertEqual(b.settings.volume_percent, 200)
        folder = self.root / "Converted"
        folder.mkdir()
        with patch("video_converter.ui.queue_panel.QFileDialog.getExistingDirectory", return_value=str(folder)):
            self.window._bulk_folder()
        self.assertEqual(a.settings.destination.parent, folder)
        self.assertEqual(b.settings.destination.parent, folder)
        self.assertNotEqual(a.settings.destination.name, b.settings.destination.name)
        self.window._bulk_preset()
        self.assertEqual(a.settings.volume_percent, 100)
        self.assertEqual(b.settings.volume_percent, 100)
        self.assertIsNot(a.settings, b.settings)
        a.settings.destination.write_bytes(b"existing output")
        self.window.queue_controller.prepare(OutputPolicy.REQUIRE_ATTENTION)
        self.window._select_job(a.id)
        self.assertEqual(a.status, JobStatus.INVALID)
        self.window._restore_preset()
        self.assertFalse(a.output_issue)
        self.assertEqual(a.status, JobStatus.READY)

    def test_external_drop_and_native_multifile_browse(self):
        paths = [self.root / "日本語.mkv", self.root / "Film.mp4"]
        for path in paths:
            path.write_bytes(b"fixture")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
        event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        with patch.object(self.window.queue_controller.probes, "submit"):
            self.window.dropEvent(event)
        self.assertEqual(len(self.window.queue.jobs), 2)
        self.assertTrue(event.isAccepted())
        event2 = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        with patch.object(self.window.queue_controller.probes, "submit"):
            self.window.queue_list.dropEvent(event2)
        self.assertEqual(len(self.window.queue.jobs), 2)
        other = self.root / "Other.mov"
        other.write_bytes(b"fixture")
        with patch("video_converter.ui.main_window.QFileDialog.getOpenFileNames", return_value=([str(other)], "")), \
                patch.object(self.window.queue_controller.probes, "submit"):
            self.window._browse_input()
        self.assertEqual(len(self.window.queue.jobs), 3)
        self.assertEqual(self.window.storage.value("last_input_dir"), str(self.root))

    def test_active_locked_pending_editable_and_preview_disabled(self):
        a, b = self.add("A.mkv"), self.add("B.mkv")
        controller = self.window.queue_controller
        a.executed_plan = a.plan
        snapshot = a.executed_plan
        a.transition(JobStatus.RUNNING)
        controller.active_id = a.id
        self.window.queue.state = QueueState.RUNNING
        self.window._select_job(a.id)
        self.window._queue_changed()
        self.assertFalse(self.window.volume_slider.isEnabled())
        self.window._select_job(b.id)
        self.assertTrue(self.window.volume_slider.isEnabled())
        self.window.volume_slider.setValue(150)
        self.assertEqual(b.settings.volume_percent, 150)
        self.assertEqual(a.executed_plan, snapshot)
        self.assertFalse(self.window.preview_button.isEnabled())
        self.assertIn("queue is running", self.window.preview_button.toolTip())
        with patch.object(self.window.runner, "start") as launch:
            self.window._create_preview_with_settings(PreviewSettings(0, 5, False))
            launch.assert_not_called()
        self.window.queue.state = QueueState.STOPPING
        controller._terminal(JobStatus.COMPLETED)
        self.window._select_job(a.id)
        self.assertFalse(self.window.volume_slider.isEnabled())
        self.window.queue_controller.retry([a.id])
        self.window._queue_changed()
        self.assertTrue(self.window.volume_slider.isEnabled())

    def test_selected_preview_has_own_store_and_does_not_change_queue(self):
        a, b = self.add("A.mkv"), self.add("B.mkv")
        self.window._select_job(b.id)
        original = tuple(job.status for job in self.window.queue.jobs)
        def start(media, execution, **kwargs):
            self.assertEqual(media.path, b.input_path)
            self.window.runner.phase = "converting"
            self.window.runner.plan = execution
        with patch.object(self.window.runner, "start", side_effect=start):
            self.window._create_preview_with_settings(PreviewSettings(0, 5, False))
        self.assertEqual(self.window.queue.jobs, (a, b))
        self.assertEqual(tuple(job.status for job in self.window.queue.jobs), original)
        preview = self.window._active_preview
        preview.output_path.write_bytes(b"preview")
        self.window.runner.phase = "done"
        self.window._on_complete(str(preview.output_path))
        self.assertEqual(self.window.preview_store.latest.plan.conversion_plan.source, b.input_path)
        self.window._select_job(a.id)
        self.assertIsNone(self.window.preview_store.latest)
        self.window._select_job(b.id)
        self.assertIsNotNone(self.window.preview_store.latest)

    def test_stop_requires_confirmation_and_remove_keeps_files(self):
        job = self.add("A.mkv")
        self.window.queue.state = QueueState.PAUSED
        with patch("video_converter.ui.queue_panel.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            self.window._stop_queue()
        self.assertEqual(self.window.queue.state, QueueState.PAUSED)
        with patch("video_converter.ui.queue_panel.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window._stop_queue()
        self.assertEqual(self.window.queue.state, QueueState.IDLE)
        self.window._select_job(job.id)
        self.window._remove_selected()
        self.assertFalse(self.window.queue.jobs)
        self.assertTrue(job.input_path.is_file())



if __name__ == "__main__":
    unittest.main()
