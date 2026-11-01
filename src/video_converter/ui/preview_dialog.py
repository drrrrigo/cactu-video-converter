"""Small segment chooser without a separate media-processing path."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QVBoxLayout, QWidget,
)

from video_converter.conversion.preview_planner import default_preview_start, effective_duration, parse_timestamp
from video_converter.conversion.validator import ValidationError
from video_converter.models.conversion import ConversionPlan
from video_converter.models.preview import PreviewSettings, format_timestamp, seconds_argument


class PreviewDialog(QDialog):
    def __init__(self, conversion: ConversionPlan, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quick Preview")
        self.setMinimumWidth(440)
        self.media_duration = conversion.duration
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.start_time = QLineEdit(format_timestamp(default_preview_start(conversion.duration)))
        self.start_time.setAccessibleName("Preview start time")
        self.start_time.setToolTip("Movie timestamp: HH:MM:SS or HH:MM:SS.mmm")
        self.duration = QComboBox()
        for value in (10, 30, 60):
            self.duration.addItem(f"{value} seconds", value)
        self.duration.setCurrentIndex(1)
        form.addRow("Start time", self.start_time)
        form.addRow("Duration", self.duration)
        layout.addLayout(form)
        self.auto_open = QCheckBox("Open when finished")
        self.auto_open.setChecked(True)
        layout.addWidget(self.auto_open)
        self.effective = QLabel()
        self.effective.setWordWrap(True)
        self.effective.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.effective)
        if conversion.video_copy or conversion.audio_copy:
            note = QLabel("Previews encode copied streams for accurate trimming. The full conversion keeps its copy decisions.")
            note.setWordWrap(True)
            layout.addWidget(note)
        if conversion.audio_processing.normalization_target:
            note = QLabel("Loudness normalization analyzes the full selected audio track on the first run. "
                          "Later previews and conversion reuse those measurements while the file, track and targets match.")
            note.setWordWrap(True)
            layout.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.create_button = self.buttons.addButton("Create Preview", QDialogButtonBox.ButtonRole.AcceptRole)
        self.create_button.setObjectName("primary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.start_time.textChanged.connect(self._refresh)
        self.duration.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def settings(self) -> PreviewSettings:
        return PreviewSettings(parse_timestamp(self.start_time.text()), self.duration.currentData(),
                               self.auto_open.isChecked())

    def _refresh(self, *_args: object) -> None:
        try:
            settings = self.settings()
            duration = effective_duration(self.media_duration, settings)
        except ValidationError as exc:
            self.effective.setText(str(exc))
            self.create_button.setEnabled(False)
            return
        end = settings.start_time_seconds + duration
        clipped = " (shortened at end of video)" if duration < settings.duration_seconds else ""
        self.effective.setText(f"{format_timestamp(settings.start_time_seconds)} → {format_timestamp(end)}\n"
                               f"Effective duration: {seconds_argument(duration)} seconds{clipped}")
        self.create_button.setEnabled(True)
