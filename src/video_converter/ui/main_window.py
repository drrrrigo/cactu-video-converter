"""Main desktop workflow; conversion decisions remain in the service layer."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QSettings, QThread, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSlider, QSpinBox, QDoubleSpinBox, QVBoxLayout, QWidget, QSplitter,
)

from video_converter.conversion.planner import plan
from video_converter.conversion.preview_planner import plan_preview
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.ffmpeg.progress import Progress
from video_converter.ffmpeg.runner import ConversionRunner
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.media.compatibility import analyze
from video_converter.media.ffprobe_service import stream_label
from video_converter.models.conversion import CodecChoice, ConversionPlan, ConversionSettings, SubtitleMode
from video_converter.models.audio import MAX_VOLUME_PERCENT, MIN_VOLUME_PERCENT, AudioProcessingMode
from video_converter.models.loudness import LoudnessTarget, LoudnessPreset, target_for
from video_converter.ffmpeg.loudness import analysis_command
from video_converter.services.loudness_cache import cache_key
from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareEncoderCapability, HardwareQuality
from video_converter.models.media import MediaInfo
from video_converter.models.subtitle import EmbeddedSubtitleSource, ExternalSubtitleSource, SubtitleFormat
from video_converter.models.preview import PreviewPlan, PreviewSettings, format_timestamp, seconds_argument
from video_converter.presets.web_kosmi import NAME, settings_for
from video_converter.services.logging import log_directory
from video_converter.ui.hardware_worker import HardwareDetectionWorker
from video_converter.ui.preview_dialog import PreviewDialog
from video_converter.services.preview_store import PreviewStore

from video_converter.models.job import JobStatus
from video_converter.models.queue import ConversionQueue, OutputPolicy, path_identity
from video_converter.services.queue_controller import QueueController
from video_converter.services.batch_settings import BatchSettingsService
from video_converter.ui.queue_panel import QueuePanelMixin
from video_converter.ui.branding import application_icon, about_dialog, notices_path, settings_dialog
from video_converter.services.settings_migration import reset_preferences
from video_converter.product import PRODUCT_NAME, TAGLINE
from video_converter.hardware.diagnosis import HardwareDiagnosisService
from video_converter.ui.hardware_assistant_panel import HardwareAssistantMixin

LOG = logging.getLogger(__name__)


def _label(text: str, *, object_name: str = "") -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    if object_name:
        label.setObjectName(object_name)
    label.setWordWrap(True)
    return label


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    layout.addWidget(_label(title, object_name="section"))
    return frame, layout


def _combo(items: list[tuple[str, object]]) -> QComboBox:
    combo = QComboBox()
    for text, value in items:
        combo.addItem(text, value)
    return combo


def _time(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    value = max(0, int(seconds))
    return f"{value // 3600:02d}:{value // 60 % 60:02d}:{value % 60:02d}"


class MainWindow(HardwareAssistantMixin, QueuePanelMixin, QMainWindow):
    """Present the source, editable settings, resolved plan, and process state."""

    def __init__(self, runtime: FFmpegRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.media: MediaInfo | None = None
        self.settings: ConversionSettings | None = None
        self.current_plan: ConversionPlan | None = None
        self.runner = ConversionRunner(runtime, self)
        self.queue = ConversionQueue()
        self.queue_controller = QueueController(self.queue, self.runner, runtime, self)
        self.batch_settings = BatchSettingsService()
        self.selected_job_id: str | None = None
        self._preview_stores: dict[str, PreviewStore] = {}
        self.queue_controller.changed.connect(self._queue_changed)
        self.queue_controller.job_changed.connect(self._job_changed)
        self.queue_controller.active_changed.connect(self._active_job_changed)
        self.queue_controller.message.connect(self._queue_message)
        self.queue_controller.finished.connect(self._queue_finished)
        self.runner.progress_changed.connect(self._on_progress)
        self.runner.state_changed.connect(self._on_state)
        self.runner.stage_changed.connect(self._on_stage)
        self.runner.completed.connect(self._on_complete)
        self.runner.failed.connect(self._on_failure)
        self.runner.cancelled.connect(self._on_cancelled)
        self.storage = QSettings()
        self.hardware_detector = HardwareEncoderDetector(runtime.ffmpeg)
        self.hardware_diagnosis_service = HardwareDiagnosisService(runtime)
        self.hardware_diagnosis = None
        self._hardware_assistant = None
        self._queued_diagnosis = None
        self.queue_controller.hardware_capability_changed.connect(self._hardware_capability_changed)
        self.hardware_capabilities: tuple[HardwareEncoderCapability, ...] = ()
        self._queued_capabilities: tuple[HardwareEncoderCapability, ...] | None = None
        self._hardware_thread: QThread | None = None
        self._hardware_worker: HardwareDetectionWorker | None = None
        self._preflight_plan: ConversionPlan | None = None
        self._preflight_overwrite = False
        self._close_after_probe = False
        self._loading = False
        self._started_at: float | None = None
        self.preview_store = PreviewStore()
        self._unbound_preview_store = self.preview_store
        self._active_preview: PreviewPlan | None = None
        self.external_subtitle_path: Path | None = None
        self.setWindowTitle(PRODUCT_NAME)
        self.setWindowIcon(application_icon())
        self.resize(1480, 900)
        self.setMinimumSize(860, 620)
        self.setAcceptDrops(True)
        self._build_ui()
        saved = self.storage.value("geometry")
        if saved:
            self.restoreGeometry(saved)
        sizes = self.storage.value("queue_splitter")
        if sizes:
            self.splitter.setSizes([int(value) for value in sizes])
        self.footer.setText("● FFmpeg ready (v9.0.2)")
        self._queue_changed()
        self._startup_timer = QTimer(self)
        self._startup_timer.setSingleShot(True)
        self._startup_timer.timeout.connect(self._detect_hardware)
        self._startup_timer.start(0)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 14, 20, 8)
        outer.setSpacing(12)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(application_icon().pixmap(44, 44))
        logo.setAccessibleName(f"{PRODUCT_NAME} icon")
        header.addWidget(logo)
        brand = QVBoxLayout()
        brand.addWidget(_label(PRODUCT_NAME, object_name="title"))
        tagline = _label(TAGLINE, object_name="muted")
        tagline.setWordWrap(False)
        brand.addWidget(tagline)
        header.addLayout(brand)
        header.addStretch()
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self._show_settings)
        help_button = QPushButton("Help")
        help_button.clicked.connect(self._show_help)
        header.addWidget(settings_button)
        header.addWidget(help_button)
        outer.addLayout(header)

        self.hardware_banner = self._build_hardware_banner()
        outer.addWidget(self.hardware_banner)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        sidebar = self._build_queue_sidebar()
        self.splitter.addWidget(sidebar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        body = QVBoxLayout(content)
        body.setSpacing(14)
        body.addWidget(self.bulk_bar)
        self.selected_scroll = scroll
        self.splitter.addWidget(scroll)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 1180])
        outer.addWidget(self.splitter, 1)

        input_row = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Select a job from the queue")
        self.input_path.setReadOnly(True)
        self.input_path.returnPressed.connect(lambda: self.open_file(Path(self.input_path.text())))
        self.browse_button = QPushButton("Add Files")
        self.browse_button.clicked.connect(self._browse_input)
        self.hevc_badge = _label("")
        input_row.addWidget(self.input_path, 1)
        input_row.addWidget(self.browse_button)
        input_row.addWidget(self.hevc_badge)
        # The sidebar is the sole import control. Retain the path binding for
        # internal callers; full paths are available in cached Media Details.
        input_binding = QWidget(content)
        input_binding.setLayout(input_row)
        input_binding.hide()

        columns = QVBoxLayout()
        columns.setSpacing(14)
        left = QVBoxLayout()
        right = QHBoxLayout()
        columns.addLayout(left)
        body.addLayout(columns)

        source_card, source_layout = _card("Selected Job")
        source_title = source_layout.takeAt(0).widget()
        source_layout.setContentsMargins(12, 10, 12, 10)
        source_layout.setSpacing(6)
        self.source_fields = {name: _label("—") for name in
                              ["Container", "Video", "Resolution", "FPS", "Pixel Format", "Audio", "Subtitles"]}
        self.source_summary = _label("Drop videos into the queue to begin.")
        source_layout.addWidget(self.source_summary)
        details_row = QHBoxLayout()
        details_row.addWidget(source_title)
        details_row.addStretch()
        media_details = QPushButton("Media Details")
        media_details.clicked.connect(self._show_media_details)
        job_details = QPushButton("Job Details")
        job_details.clicked.connect(self._show_job_details)
        details_row.addWidget(media_details)
        details_row.addWidget(job_details)
        details_row.addWidget(self.job_output_button)
        source_layout.insertLayout(0, details_row)
        self.compatibility = _label("", object_name="warningText")
        source_layout.addWidget(self.compatibility)
        left.addWidget(source_card)
        left.addLayout(right)

        left.addWidget(_label("Conversion Settings", object_name="section"))
        setting_grid = QGridLayout()
        setting_grid.setSpacing(12)
        self.setting_grid = setting_grid
        left.addLayout(setting_grid)
        self._build_output_card(setting_grid)
        self._build_video_card(setting_grid)
        self._build_audio_card(setting_grid)
        self._build_subtitle_card(setting_grid)

        preset_card, preset_layout = _card("★  Output Preset")
        self.preset_card = preset_card
        self.preset_combo = _combo([(NAME, NAME), ("Custom — based on Web Compatibility / Kosmi", "custom")])
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(_label("Converts to MP4 + H.264 + AAC + YUV420P + Faststart.", object_name="muted"))
        restore = QPushButton("Restore Preset Defaults")
        restore.clicked.connect(self._restore_preset)
        preset_layout.addWidget(restore)
        right.addWidget(preset_card)

        summary_card, summary_layout = _card("Output Summary")
        self.summary_head = _label("MP4 + H.264 + AAC + YUV420P", object_name="successText")
        summary_layout.addWidget(self.summary_head)
        self.summary = _label("Select a file to see the conversion plan.")
        summary_layout.addWidget(self.summary)
        self.validation = _label("", object_name="warningText")
        summary_layout.addWidget(self.validation)
        preview = QPushButton("Command Preview")
        preview.clicked.connect(self._show_command)
        summary_layout.addWidget(preview)
        right.addWidget(summary_card)

        progress_card, progress_layout = _card("Conversion Progress")
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(6)
        progress_row = QHBoxLayout()
        self.current_job_label = _label("No active conversion")
        progress_layout.addWidget(self.current_job_label)
        self.queue_summary = _label("Queue: 0 jobs", object_name="muted")
        queue_row = QHBoxLayout()
        queue_row.addWidget(self.queue_summary, 1)
        self.queue_pause_button = QPushButton("Pause Queue")
        self.queue_pause_button.clicked.connect(self._pause_queue)
        self.queue_stop_button = QPushButton("Stop Queue")
        self.queue_stop_button.setObjectName("danger")
        self.queue_stop_button.clicked.connect(self._stop_queue)
        queue_row.addWidget(self.queue_pause_button)
        queue_row.addWidget(self.queue_stop_button)
        progress_layout.addLayout(queue_row)
        self.state = _label("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)  # Separate percent label stays legible over any fill.
        self.progress_bar.setValue(0)
        self.percent = _label("0%")
        progress_row.addWidget(self.state)
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.percent)
        progress_layout.addLayout(progress_row)
        metrics = QHBoxLayout()
        self.elapsed = _label("Elapsed: —", object_name="muted")
        self.remaining = _label("Remaining: —", object_name="muted")
        self.speed = _label("Speed: —", object_name="muted")
        metrics.addWidget(self.elapsed)
        metrics.addWidget(self.remaining)
        metrics.addWidget(self.speed)
        metrics.addStretch()
        progress_layout.addLayout(metrics)
        preview_row = QHBoxLayout()
        self.preview_status = _label("", object_name="muted")
        self.preview_status.setVisible(False)
        self.open_preview_button = QPushButton("Open Preview")
        self.open_preview_button.clicked.connect(self._open_preview)
        self.open_preview_folder_button = QPushButton("Open Preview Folder")
        self.open_preview_folder_button.clicked.connect(self._open_preview_folder)
        self.open_preview_button.setVisible(False)
        self.open_preview_folder_button.setVisible(False)
        preview_row.addWidget(self.preview_status, 1)
        preview_row.addWidget(self.open_preview_button)
        preview_row.addWidget(self.open_preview_folder_button)
        progress_layout.addLayout(preview_row)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.preview_button = QPushButton("Create Preview")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self._create_preview)
        self.start_button = QPushButton("Start Queue")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self._pause_current)
        self.cancel_button = QPushButton("Cancel Current")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_operation)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.cancel_button)
        progress_layout.addLayout(buttons)
        outer.addWidget(progress_card)
        self.footer = _label("Checking FFmpeg...", object_name="successText")
        outer.addWidget(self.footer)
        for editor in self.findChildren(QLineEdit):
            editor.setAcceptDrops(False)

    def _build_output_card(self, grid: QGridLayout) -> None:
        card, layout = _card("Output")
        form = QFormLayout()
        self.destination_folder = QLineEdit()
        self.destination_folder.editingFinished.connect(self._edited)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.destination_folder)
        folder_button = QPushButton("…")
        folder_button.setFixedWidth(38)
        folder_button.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_button)
        self.filename = QLineEdit()
        self.filename.editingFinished.connect(self._edited)
        form.addRow("Container", _label("MP4"))
        form.addRow("Destination", folder_row)
        form.addRow("File name", self.filename)
        layout.addLayout(form)
        grid.addWidget(card, 0, 0)

    def _build_video_card(self, grid: QGridLayout) -> None:
        card, layout = _card("Video")
        form = QFormLayout()
        self.video_form = form
        self.video_codec = _combo([("Auto (copy when compatible)", CodecChoice.AUTO),
                                   ("H.264 / AVC", CodecChoice.H264), ("Copy", CodecChoice.COPY)])
        self.engine_combo = _combo([("Software — x264", EncoderSelection())])
        self.crf = QSpinBox()
        self.crf.setRange(0, 51)
        self.crf.setValue(18)
        self.encode_preset = _combo([(x, x) for x in ["veryfast", "fast", "medium", "slow", "slower"]])
        self.encode_preset.setCurrentText("medium")
        self.pixel_format = _combo([("yuv420p", "yuv420p"), ("Auto", "auto")])
        self.hardware_quality = _combo([(quality.label, quality) for quality in HardwareQuality])
        form.addRow("Video codec", self.video_codec)
        form.addRow("Encoding engine", self.engine_combo)
        form.addRow("Quality (CRF)", self.crf)
        form.addRow("Encoding preset", self.encode_preset)
        form.addRow("Hardware quality", self.hardware_quality)
        form.addRow("Pixel format", self.pixel_format)
        self.hardware_status = _label("Detecting hardware encoders...", object_name="muted")
        layout.addLayout(form)
        layout.addWidget(self.hardware_status)
        grid.addWidget(card, 0, 1)
        self._update_quality_controls()
        for widget in (self.video_codec, self.engine_combo, self.crf, self.encode_preset,
                       self.hardware_quality, self.pixel_format):
            widget.currentIndexChanged.connect(self._edited) if isinstance(widget, QComboBox) else widget.valueChanged.connect(self._edited)

    def _build_audio_card(self, grid: QGridLayout) -> None:
        card, layout = _card("Audio")
        form = QFormLayout()
        self.audio_track = QComboBox()
        self.audio_codec = _combo([("Auto (copy AAC)", CodecChoice.AUTO), ("AAC", CodecChoice.AAC),
                                   ("Copy", CodecChoice.COPY)])
        self.bitrate = _combo([(f"{x} kbps", x) for x in (128, 192, 256, 320)])
        self.bitrate.setCurrentIndex(2)
        self.channels = _combo([("Source / Preserve", None), ("Stereo", 2), ("5.1 Surround", 6)])
        form.addRow("Audio track", self.audio_track)
        form.addRow("Audio codec", self.audio_codec)
        form.addRow("Bitrate", self.bitrate)
        form.addRow("Channels", self.channels)
        self.audio_mode = _combo([("Manual Volume", AudioProcessingMode.MANUAL_VOLUME),
                                 ("Loudness Normalization", AudioProcessingMode.LOUDNESS_NORMALIZATION)])
        if not self.runtime.loudnorm_available:
            self.audio_mode.model().item(1).setEnabled(False)
            self.audio_mode.setToolTip("Loudness normalization is unavailable: this FFmpeg runtime lacks loudnorm.")
        form.addRow("Audio processing", self.audio_mode)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(MIN_VOLUME_PERCENT, MAX_VOLUME_PERCENT)
        self.volume_slider.setSingleStep(1)
        self.volume_slider.setValue(100)
        self.volume_slider.setAccessibleName("Output Volume")
        self.volume_slider.setToolTip("Adjust output volume from 0% to 300%. 100% preserves the original level.")
        self.volume_value = _label("100%")
        self.volume_value.setMinimumWidth(42)
        self.volume_reset = QPushButton("Reset")
        self.volume_reset.setToolTip("Restore original volume (100%).")
        self.volume_reset.clicked.connect(lambda: self.volume_slider.setValue(100))
        volume_row = QHBoxLayout()
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_value)
        volume_row.addWidget(self.volume_reset)
        form.addRow("Volume", volume_row)
        layout.addLayout(form)
        self.prevent_clipping = QCheckBox("Prevent clipping")
        self.prevent_clipping.setChecked(True)
        self.prevent_clipping.setToolTip("Limits peaks after amplification to reduce distortion.")
        self.volume_note = _label("", object_name="muted")
        layout.addWidget(self.prevent_clipping)
        layout.addWidget(self.volume_note)
        self.loudness_panel = QWidget()
        self.loudness_panel.setObjectName("loudnessPanel")
        loudness_form = QFormLayout(self.loudness_panel)
        loudness_form.setContentsMargins(0, 0, 0, 0)
        self.loudness_preset = _combo([(preset.label, preset) for preset in LoudnessPreset])
        self.loudness_i = QDoubleSpinBox()
        self.loudness_i.setRange(-70, -5)
        self.loudness_i.setDecimals(1)
        self.loudness_i.setValue(-16)
        self.loudness_i.setSuffix(" LUFS")
        self.loudness_tp = QDoubleSpinBox()
        self.loudness_tp.setRange(-9, 0)
        self.loudness_tp.setDecimals(1)
        self.loudness_tp.setValue(-1.5)
        self.loudness_tp.setSuffix(" dBTP")
        self.loudness_lra = QDoubleSpinBox()
        self.loudness_lra.setRange(1, 50)
        self.loudness_lra.setDecimals(1)
        self.loudness_lra.setValue(11)
        self.loudness_lra.setSuffix(" LU")
        loudness_form.addRow("Preset", self.loudness_preset)
        loudness_form.addRow("Target loudness", self.loudness_i)
        loudness_form.addRow("Maximum true peak", self.loudness_tp)
        loudness_form.addRow("Loudness range", self.loudness_lra)
        self.loudness_form = loudness_form
        layout.addWidget(self.loudness_panel)
        details = QPushButton("Loudness Details")
        details.clicked.connect(self._show_loudness_details)
        layout.addWidget(details)
        grid.addWidget(card, 1, 0)
        for widget in (self.audio_track, self.audio_codec, self.bitrate, self.channels):
            widget.currentIndexChanged.connect(self._edited)
        self.volume_slider.valueChanged.connect(self._volume_changed)
        self.prevent_clipping.toggled.connect(self._edited)
        self.audio_mode.currentIndexChanged.connect(self._audio_mode_changed)
        self.loudness_preset.currentIndexChanged.connect(self._loudness_preset_changed)
        for widget in (self.loudness_i, self.loudness_tp, self.loudness_lra):
            widget.valueChanged.connect(self._edited)
        self._update_audio_controls()

    def _audio_mode_changed(self) -> None:
        if (not self._loading and self.audio_mode.currentData() == AudioProcessingMode.LOUDNESS_NORMALIZATION
                and self.audio_codec.currentData() == CodecChoice.COPY):
            self.audio_codec.setCurrentIndex(self.audio_codec.findData(CodecChoice.AAC))
        self._edited()

    def _loudness_preset_changed(self) -> None:
        preset = LoudnessPreset(self.loudness_preset.currentData())
        if preset != LoudnessPreset.CUSTOM:
            target = target_for(preset)
            loading = self._loading
            self._loading = True
            self.loudness_i.setValue(target.integrated_lufs)
            self.loudness_tp.setValue(target.true_peak_dbtp)
            self.loudness_lra.setValue(target.loudness_range_lu)
            self._loading = loading
        self._edited()

    def _loudness_target(self) -> LoudnessTarget:
        return LoudnessTarget(self.loudness_i.value(), self.loudness_tp.value(),
                              self.loudness_lra.value(), LoudnessPreset(self.loudness_preset.currentData()))

    def _update_audio_controls(self) -> None:
        normalizing = self.audio_mode.currentData() == AudioProcessingMode.LOUDNESS_NORMALIZATION
        available = bool(self.media and self.media.audios)
        self.audio_mode.setEnabled(available)
        self.loudness_panel.setVisible(normalizing)
        custom = self.loudness_preset.currentData() == LoudnessPreset.CUSTOM
        self.loudness_i.setEnabled(custom)
        self.loudness_tp.setEnabled(custom)
        self.loudness_form.setRowVisible(self.loudness_lra, custom)
        for widget in (self.volume_slider, self.volume_reset, self.prevent_clipping):
            widget.setEnabled(available and not normalizing)

    def _volume_changed(self, value: int) -> None:
        self.volume_value.setText(f"{value}%")
        if self._loading:
            return
        if value != 100 and self.audio_codec.currentData() == CodecChoice.COPY:
            self.audio_codec.setCurrentIndex(self.audio_codec.findData(CodecChoice.AAC))
        self._edited()

    def _update_volume_note(self) -> None:
        value = self.volume_slider.value()
        if self.audio_mode.currentData() == AudioProcessingMode.LOUDNESS_NORMALIZATION:
            self.volume_note.setText("Analyzes the full selected audio track before encoding. Previews reuse measurements. Manual volume is inactive.")
        elif not self.runtime.loudnorm_available:
            self.volume_note.setText("Loudness normalization unavailable: FFmpeg lacks loudnorm. Manual volume is available.")
        elif value >= 250 and not self.prevent_clipping.isChecked():
            self.volume_note.setText("High amplification without clipping protection may cause severe distortion.")
        elif value > 100 and not self.prevent_clipping.isChecked():
            self.volume_note.setText("Boosting audio without clipping protection may cause distortion.")
        elif value != 100:
            self.volume_note.setText("Audio will be re-encoded to adjust volume.")
        else:
            self.volume_note.setText("")

    def _build_subtitle_card(self, grid: QGridLayout) -> None:
        card, layout = _card("Subtitles")
        self.mode_none = QRadioButton("None")
        self.mode_selectable = QRadioButton("Keep selectable")
        self.mode_burn = QRadioButton("Burn into video")
        mode_group = QButtonGroup(self)
        for mode in (self.mode_none, self.mode_selectable, self.mode_burn):
            mode_group.addButton(mode)
        self.subtitle_embedded = QRadioButton("Embedded track")
        self.subtitle_external = QRadioButton("External file")
        source_group = QButtonGroup(self)
        source_group.addButton(self.subtitle_embedded)
        source_group.addButton(self.subtitle_external)
        self.subtitle_embedded.setChecked(True)
        self.mode_none.setChecked(True)
        self.subtitle_track = QComboBox()
        for mode in (self.mode_none, self.mode_selectable, self.mode_burn):
            layout.addWidget(mode)
            mode.toggled.connect(self._edited)
        layout.addWidget(_label("Subtitle source", object_name="muted"))
        for source in (self.subtitle_embedded, self.subtitle_external):
            layout.addWidget(source)
            source.toggled.connect(self._edited)
        layout.addWidget(_label("Subtitle track", object_name="muted"))
        layout.addWidget(self.subtitle_track)
        self.subtitle_track.currentIndexChanged.connect(self._edited)
        subtitle_row = QHBoxLayout()
        self.subtitle_filename = QLineEdit()
        self.subtitle_filename.setReadOnly(True)
        self.subtitle_filename.setPlaceholderText("Choose an ASS, SSA, or SRT file")
        self.subtitle_browse = QPushButton("Browse")
        self.subtitle_browse.clicked.connect(self._browse_subtitle)
        subtitle_row.addWidget(self.subtitle_filename, 1)
        subtitle_row.addWidget(self.subtitle_browse)
        layout.addLayout(subtitle_row)
        self._update_subtitle_controls()
        grid.addWidget(card, 1, 1)

    def _update_subtitle_controls(self) -> None:
        burning = self.mode_burn.isChecked()
        selectable = self.mode_selectable.isChecked()
        self.subtitle_embedded.setEnabled(burning)
        self.subtitle_external.setEnabled(burning)
        self.subtitle_track.setEnabled(selectable or (burning and self.subtitle_embedded.isChecked()))
        self.subtitle_filename.setEnabled(burning and self.subtitle_external.isChecked())
        self.subtitle_browse.setEnabled(burning and self.subtitle_external.isChecked())

    def _browse_subtitle(self) -> None:
        initial = str(self.storage.value("last_subtitle_dir", str(Path.home())))
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", initial,
            "All Supported Subtitles (*.ass *.ssa *.srt *.ASS *.SSA *.SRT);;"
            "ASS (*.ass *.ASS);;SSA (*.ssa *.SSA);;SubRip (*.srt *.SRT);;All Files (*)")
        if not filename:
            return
        path = Path(filename)
        try:
            SubtitleFormat.from_path(path)
        except ValueError as exc:
            QMessageBox.warning(self, "Subtitle file", str(exc))
            return
        self.external_subtitle_path = path
        self.subtitle_filename.setText(path.name)
        self.subtitle_filename.setToolTip(str(path))
        self.storage.setValue("last_subtitle_dir", str(path.parent))
        LOG.info("External subtitle selected: %s", path)
        self.subtitle_external.setChecked(True)
        self.mode_burn.setChecked(True)
        self._edited()

    def _browse_input(self) -> None:
        initial = str(self.storage.value("last_input_dir", str(Path.home())))
        filenames, _ = QFileDialog.getOpenFileNames(self, "Add Videos", initial,
            "Video files (*.mkv *.mp4 *.mov *.m4v *.webm *.avi *.ts *.m2ts);;All files (*)")
        if filenames:
            self.storage.setValue("last_input_dir", str(Path(filenames[0]).parent))
            self.add_files([Path(name) for name in filenames])

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.destination_folder.text())
        if folder:
            self.destination_folder.setText(folder)
            self._edited()

    def open_file(self, path: Path) -> None:
        self.add_files([path])

    def add_files(self, paths: list[Path]) -> None:
        added = self.queue_controller.add_paths(paths)
        if added and self.selected_job_id is None:
            self._select_job(added[0].id)

    def _populate_media(self, media: MediaInfo, *, restore: bool = True) -> None:
        # Also supports programmatic loading of already analyzed media without a re-probe.
        if restore:
            identity = path_identity(media.path)
            job = next((job for job in self.queue.jobs
                        if path_identity(job.input_path) == identity), None)
            if job is None:
                job = self.queue.add(media.path)
            job.media = media
            if job.status == JobStatus.ANALYZING:
                job.transition(JobStatus.READY)
            self.selected_job_id = job.id
            self.preview_store = self._store_for_job(job.id)
        self.media = media
        video = media.video
        assert video is not None
        container = media.container.split(",")[0]
        self.source_fields["Container"].setText({"matroska": "MKV", "mov": "MP4"}.get(container, container.upper()))
        self.source_fields["Video"].setText(f"{video.codec.upper()} {video.profile}".strip())
        self.source_fields["Resolution"].setText(f"{video.width} × {video.height}")
        self.source_fields["FPS"].setText(f"{video.fps:.3f}" if video.fps else "—")
        self.source_fields["Pixel Format"].setText(video.pixel_format)
        audio = media.preferred_audio
        self.source_fields["Audio"].setText(f"{audio.codec.upper()} {audio.layout}" if audio else "None")
        self.source_fields["Subtitles"].setText(f"{len(media.subtitles)} tracks")
        self.hevc_badge.setText("⚠ HEVC detected" if video.codec == "hevc" else "")
        self.compatibility.setText(analyze(media).message)
        self._loading = True
        self.audio_track.clear()
        for track in media.audios:
            self.audio_track.addItem(stream_label(track), track.index)
        if audio:
            self.audio_track.setCurrentIndex(next(i for i, track in enumerate(media.audios)
                                                 if track.index == audio.index))
        self.volume_slider.setEnabled(bool(media.audios))
        self.volume_reset.setEnabled(bool(media.audios))
        self.prevent_clipping.setEnabled(bool(media.audios))
        self.subtitle_track.clear()
        for track in media.subtitles:
            self.subtitle_track.addItem(stream_label(track), track.index)
        self.source_summary.setText(
            f"{media.path.name}\n{container.upper()} • {video.codec.upper()} {video.profile} • "
            f"{video.width} × {video.height} • {video.fps:.3f} FPS\n"
            f"{audio.codec.upper() + ' ' + audio.layout if audio else 'No audio'} • "
            f"{len(media.subtitles)} subtitles • {_time(media.duration)} • "
            f"{media.size / 1_000_000_000:.2f} GB" if video.fps and media.size else
            f"{media.path.name}\n{container.upper()} • {video.codec.upper()} {video.profile} • "
            f"{video.width} × {video.height} • {len(media.subtitles)} subtitles • {_time(media.duration)}")
        self.input_path.setText(str(media.path))
        self._loading = False
        if restore:
            self._restore_preset()
            self._queue_changed()

    def _restore_preset(self) -> None:
        if self.media is None:
            return
        job = self.queue.get(self.selected_job_id)
        if job is not None and not job.editable:
            return
        if job:
            job.stream_issues.clear()
            job.warnings = ()
        self._loading = True
        self.settings = settings_for(self.media.path)
        if job and job.settings.destination != self.settings.destination:
            job.output_issue = ""
        selection = self.engine_combo.currentData()
        if isinstance(selection, EncoderSelection) and selection.backend != EncoderBackend.SOFTWARE_X264:
            self.settings = self.settings.customized(encoding_engine=selection)
        self.destination_folder.setText(str(self.settings.destination.parent))
        self.filename.setText(self.settings.destination.name)
        self.video_codec.setCurrentIndex(0)
        self.crf.setValue(18)
        self.encode_preset.setCurrentText("medium")
        self.pixel_format.setCurrentIndex(0)
        self.hardware_quality.setCurrentIndex(0)
        self.audio_codec.setCurrentIndex(0)
        self.bitrate.setCurrentIndex(2)
        self.channels.setCurrentIndex(0)
        self.audio_mode.setCurrentIndex(0)
        self.loudness_preset.setCurrentIndex(0)
        self.loudness_i.setValue(-16)
        self.loudness_tp.setValue(-1.5)
        self.loudness_lra.setValue(11)
        self.volume_slider.setValue(100)
        self.prevent_clipping.setChecked(True)
        self._update_volume_note()
        self.mode_none.setChecked(True)
        self.subtitle_embedded.setChecked(True)
        self.external_subtitle_path = None
        self.subtitle_filename.clear()
        self.subtitle_filename.setToolTip("")
        self.preset_combo.setCurrentIndex(
            0 if self.settings.encoding_engine.backend == EncoderBackend.SOFTWARE_X264 else 1)
        self._loading = False
        self._update_quality_controls()
        self._update_audio_controls()
        self._refresh_plan()

    def _preset_changed(self) -> None:
        if not self._loading and self.preset_combo.currentIndex() == 0:
            self._restore_preset()

    def _edited(self, *_args: object) -> None:
        if self._loading:
            return
        job = self.queue.get(self.selected_job_id)
        if job is not None and not job.editable:
            return
        self._update_quality_controls()
        self._update_subtitle_controls()
        self._update_audio_controls()
        self._update_volume_note()
        if self._loading or self.media is None or self.settings is None:
            return
        folder = Path(self.destination_folder.text()).expanduser()
        filename = self.filename.text().strip()
        mode = SubtitleMode.BURN if self.mode_burn.isChecked() else (SubtitleMode.SELECTABLE if self.mode_selectable.isChecked() else SubtitleMode.NONE)
        subtitle_source = None
        if mode != SubtitleMode.NONE:
            if mode == SubtitleMode.BURN and self.subtitle_external.isChecked() and self.external_subtitle_path:
                subtitle_source = ExternalSubtitleSource.from_path(self.external_subtitle_path)
            elif mode == SubtitleMode.SELECTABLE or self.subtitle_embedded.isChecked():
                selected = self.media.subtitle_by_index(self.subtitle_track.currentData()) if self.subtitle_track.currentData() is not None else None
                if selected is not None:
                    subtitle_source = EmbeddedSubtitleSource(selected.index, selected.ordinal,
                                                             selected.codec, stream_label(selected))
        previous_settings = self.settings
        self.settings = self.settings.customized(
            destination=folder / filename, video_codec=CodecChoice(self.video_codec.currentData()),
            crf=self.crf.value(), preset=self.encode_preset.currentData(),
            pixel_format=self.pixel_format.currentData(),
            encoding_engine=self.engine_combo.currentData(),
            hardware_quality=HardwareQuality(self.hardware_quality.currentData()),
            audio_codec=CodecChoice(self.audio_codec.currentData()),
            audio_bitrate_kbps=self.bitrate.currentData(), audio_channels=self.channels.currentData(),
            volume_percent=self.volume_slider.value(), prevent_clipping=self.prevent_clipping.isChecked(),
            audio_processing_mode=AudioProcessingMode(self.audio_mode.currentData()),
            loudness_target=self._loudness_target(),
            audio_index=self.audio_track.currentData(), subtitle_mode=mode,
            subtitle_index=subtitle_source.stream_index if isinstance(subtitle_source, EmbeddedSubtitleSource) else None,
            subtitle_source=subtitle_source,
        )
        if job:
            if self.settings.destination != previous_settings.destination:
                job.output_issue = ""
            if self.settings.audio_index != previous_settings.audio_index:
                job.stream_issues.pop("audio", None)
            if (self.settings.subtitle_source != previous_settings.subtitle_source or
                    self.settings.subtitle_mode == SubtitleMode.NONE):
                job.stream_issues.pop("subtitle", None)
            job.warnings = tuple(job.stream_issues.values())
            job.settings = self.settings
        self._loading = True
        self.preset_combo.setCurrentIndex(1)
        self._loading = False
        selected = self.engine_combo.currentData()
        if isinstance(selected, EncoderSelection):
            self.storage.setValue("preferred_encoder_backend", selected.backend.value)
        self._refresh_plan()

    def _refresh_plan(self) -> None:
        self.current_plan = None
        job = self.queue.get(self.selected_job_id)
        if job is not None and self.settings is not None:
            if job.editable:
                job.settings = self.settings
            self.queue_controller.capabilities = self.hardware_capabilities
            self.queue_controller.validate_job(job)
        if self.media is None or self.settings is None:
            self.preview_button.setEnabled(False)
            self._refresh_preview_status()
            return
        try:
            # The queue resolves output policy up front; review can still show
            # an existing destination without authorizing its replacement.
            if job and job.validation_error:
                raise ValidationError(job.validation_error)
            if job and job.stream_issues:
                raise ValidationError("\n".join(job.stream_issues.values()))
            resolved = plan(self.media, self.settings, overwrite=self.settings.destination.exists(),
                            capabilities=self.hardware_capabilities)
        except ValidationError as exc:
            self.validation.setText(str(exc))
            self.summary_head.setText("Configuration needs attention")
            self.summary.setText("Adjust the settings to see an output plan.")
            self.preview_button.setEnabled(False)
            self._refresh_preview_status()
            self._queue_changed()
            return
        self.current_plan = resolved
        self.validation.setText("")
        self.summary_head.setText(resolved.description)
        subtitle_desc = "None"
        if resolved.subtitle_mode != SubtitleMode.NONE and resolved.subtitle_source is not None:
            label = resolved.subtitle_source.display_name
            origin = "External" if isinstance(resolved.subtitle_source, ExternalSubtitleSource) else "Embedded"
            subtitle_desc = f"{resolved.subtitle_mode.value.title()} — {origin}: {label}"
        if resolved.audio_index is None:
            volume_desc = ""
        elif (target := resolved.audio_processing.normalization_target) is not None:
            volume_desc = f"\nLoudness: {target.integrated_lufs:g} LUFS\nTrue Peak: {target.true_peak_dbtp:g} dBTP"
        elif resolved.audio_processing.volume_percent == 100:
            volume_desc = "\nVolume: Original (100%)\nNo normalization"
        else:
            protected = " — Clipping protection enabled" if resolved.audio_processing.limiter_active else ""
            volume_desc = f"\nVolume: {resolved.audio_processing.volume_percent}%{protected}\nNo normalization"
        self.summary.setText(
            f"Container: MP4\nVideo: {self._video_summary(resolved)}\n"
            f"Audio: {'None' if resolved.audio_index is None else ('Copy without re-encoding' if resolved.audio_copy else f'AAC, {resolved.audio_bitrate_kbps} kbps')}{volume_desc}\n"
            f"Subtitles: {subtitle_desc}\nFaststart: {'Enabled' if resolved.faststart else 'Disabled'}")
        self.start_button.setEnabled(not self._operation_busy())
        self.preview_button.setEnabled(not self._operation_busy())
        if job:
            job.plan = resolved
        self.queue_model.refresh()
        self._refresh_preview_status()
        self._queue_changed()

    def _operation_busy(self) -> bool:
        return self.queue_controller.busy or self._preflight_plan is not None or self.runner.phase in {
            "analyzing", "subtitle_preflight", "extracting", "converting", "verifying"}

    def _create_preview(self) -> None:
        if self._operation_busy() or self.current_plan is None:
            return
        dialog = PreviewDialog(self.current_plan, self)
        if dialog.exec() == PreviewDialog.DialogCode.Accepted:
            self._create_preview_with_settings(dialog.settings())

    def _create_preview_with_settings(self, settings: PreviewSettings) -> None:
        if self._operation_busy() or self._hardware_testing() or self.media is None or self.settings is None:
            return
        try:
            base = plan(self.media, self.settings, overwrite=self.settings.destination.exists(),
                        capabilities=self.hardware_capabilities)
            output = self.preview_store.allocate()
            preview = plan_preview(self.media, base, settings, output,
                                   capabilities=self.hardware_capabilities)
        except (OSError, ValueError, RuntimeError) as exc:
            self.preview_store.discard()
            QMessageBox.warning(self, "Preview could not be created", str(exc))
            return
        self._prepare_launch(preview.execution_plan, False, preview=preview)

    def _refresh_preview_status(self) -> None:
        if self._active_preview is not None:
            preview = self._active_preview
            self.preview_status.setText(
                f"Preview: {format_timestamp(preview.settings.start_time_seconds)} → "
                f"{format_timestamp(preview.end_time_seconds)} ({seconds_argument(preview.duration_seconds)} s)")
        elif self.preview_store.latest is not None:
            current = self.preview_store.latest.matches(self.current_plan)
            self.preview_status.setText("Preview ready" if current else "Preview out of date — source or settings changed")
        else:
            self.preview_status.setText("")
        available = self.preview_store.latest is not None
        self.open_preview_button.setVisible(available)
        self.open_preview_folder_button.setVisible(available)
        self.preview_status.setVisible(bool(self.preview_status.text()))

    def _open_preview(self) -> None:
        latest = self.preview_store.latest
        if latest is not None:
            self._open_preview_path(latest.plan.output_path)

    def _open_preview_folder(self) -> None:
        latest = self.preview_store.latest
        if latest is not None:
            self._open_preview_path(latest.plan.output_path.parent)

    def _open_preview_path(self, path: Path) -> None:
        if not path.exists() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Preview could not be opened", f"Could not open {path}. Check the system's default video player.")

    def _start(self) -> None:
        if self._hardware_testing():
            return
        if self._operation_busy():
            return
        self.queue_controller.capabilities = self.hardware_capabilities
        policy = OutputPolicy(self.output_policy.currentData())
        ready, invalid = self.queue_controller.prepare(policy)
        self._queue_changed()
        if not ready and not any(job.status == JobStatus.ANALYZING for job in self.queue.jobs):
            self._queue_message(f"No ready jobs. {invalid} require attention.")
            return
        if invalid:
            answer = QMessageBox.question(self, "Start Queue", f"{ready} ready · {invalid} require attention.\n"
                "Run valid jobs and leave the others for review?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.queue_controller.start(policy)
        except RuntimeError as exc:
            QMessageBox.warning(self, "Cannot start queue", str(exc))

    def _prepare_launch(self, resolved: ConversionPlan, overwrite: bool,
                        *, preview: PreviewPlan | None = None) -> None:
        self._active_preview = preview
        self._refresh_preview_status()
        if not resolved.video_copy and resolved.encoding_engine.backend != EncoderBackend.SOFTWARE_X264:
            self._preflight_plan, self._preflight_overwrite = resolved, overwrite
            self._set_config_enabled(False)
            self.start_button.setEnabled(False)
            self.preview_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.state.setText("Checking hardware encoder...")
            self._run_hardware_worker(selection=resolved.encoding_engine, request_plan=resolved)
            return
        self._launch_plan(resolved, overwrite)

    def _cancel_operation(self) -> None:
        if self.queue_controller.active:
            self.queue_controller.cancel_current()
            return
        if self._preflight_plan is not None:
            # The short worker probe may finish in the background. Dropping
            # the pending plan ensures its result cannot launch an encode.
            self._preflight_plan = None
            self._on_cancelled()
        else:
            self.runner.cancel()

    def _launch_plan(self, resolved: ConversionPlan, overwrite: bool) -> None:
        assert self.media is not None
        try:
            self.runner.start(self.media, resolved, overwrite=overwrite, preview=self._active_preview)
        except (OSError, ValueError, RuntimeError) as exc:
            preview_failed = self._active_preview is not None
            self.preview_store.discard()
            self._active_preview = None
            self._end_controls()
            QMessageBox.warning(self, "Preview could not be created" if preview_failed else "Cannot start conversion", str(exc))
            return
        if self._active_preview is None:
            self.current_plan = resolved
        self._started_at = time.monotonic()
        self._set_config_enabled(False)
        self.start_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.pause_button.setEnabled(self.runner.phase in {"analyzing", "converting"})
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.percent.setText("0%")
        LOG.info("Selected configuration: %r", self.settings)

    def _video_summary(self, resolved: ConversionPlan) -> str:
        if resolved.video_copy:
            return "Copy without re-encoding"
        if resolved.encoding_engine.backend == EncoderBackend.SOFTWARE_X264:
            return f"H.264 — Software x264, CRF {resolved.crf}, {resolved.preset}"
        display = next((cap.display_name for cap in self.hardware_capabilities
                        if cap.selection == resolved.encoding_engine),
                       resolved.encoding_engine.backend.display_name)
        return f"H.264 — {display}, {resolved.hardware_quality.label}"

    def _update_quality_controls(self) -> None:
        selection = self.engine_combo.currentData()
        software = not isinstance(selection, EncoderSelection) or selection.backend == EncoderBackend.SOFTWARE_X264
        self.video_form.setRowVisible(self.crf, software)
        self.video_form.setRowVisible(self.encode_preset, software)
        self.video_form.setRowVisible(self.hardware_quality, not software)

    def _detect_hardware(self, *, refresh: bool = False) -> None:
        # Startup detection is scheduled for the next event-loop turn. A window
        # closed before that turn must not start a worker during Qt teardown.
        if not self.isVisible():
            return
        if self._operation_busy():
            self.hardware_status.setText("Hardware detection is available after this conversion.")
            return
        if self._hardware_thread and self._hardware_thread.isRunning():
            return
        if refresh:
            self.storage.remove("hardware_assistant/dismissed_identity")
        self.hardware_status.setText("Detecting hardware encoders...")
        self._run_hardware_worker(refresh=refresh)

    def _run_hardware_worker(self, *, selection: EncoderSelection | None = None,
                             refresh: bool = False, request_plan: ConversionPlan | None = None) -> None:
        if request_plan is not None and self._preflight_plan is not request_plan:
            return
        if self._hardware_thread and self._hardware_thread.isRunning():
            QTimer.singleShot(100, lambda: self._run_hardware_worker(selection=selection,
                refresh=refresh, request_plan=request_plan))
            return
        thread = QThread(self)
        worker = HardwareDetectionWorker(self.hardware_detector, selection, refresh=refresh, request=request_plan,
            diagnosis_service=self.hardware_diagnosis_service if selection is None else None, runtime=self.runtime)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.detected.connect(self._hardware_detected)
        worker.diagnosed.connect(self._hardware_explained)
        worker.checked.connect(self._hardware_preflight_done)
        worker.failed.connect(self._hardware_worker_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._hardware_thread_done)
        self._hardware_thread, self._hardware_worker = thread, worker
        thread.start()
        self._update_queue_controls()

    def _hardware_thread_done(self) -> None:
        self._hardware_thread = None
        self._hardware_worker = None
        self._update_queue_controls()
        if self._close_after_probe:
            self._close_after_probe = False
            QTimer.singleShot(0, self.close)

    def _hardware_detected(self, capabilities: tuple[HardwareEncoderCapability, ...]) -> None:
        if self._operation_busy():
            self._queued_capabilities = capabilities
            return
        self.hardware_capabilities = capabilities
        self.queue_controller.capabilities = capabilities
        available = [cap for cap in capabilities if cap.available]
        previous = self.engine_combo.currentData()
        preferred = str(self.storage.value("preferred_encoder_backend", "software_x264"))
        self._loading = True
        self.engine_combo.clear()
        self.engine_combo.addItem("Software — x264", EncoderSelection())
        for cap in available:
            self.engine_combo.addItem(cap.display_name, cap.selection)
        desired = self.settings.encoding_engine if self.settings is not None else (
            previous if isinstance(previous, EncoderSelection) and previous.backend != EncoderBackend.SOFTWARE_X264 else None)
        if desired is None:
            desired = next((cap.selection for cap in available
                            if cap.selection.backend.value == preferred), EncoderSelection())
        index = next((i for i in range(self.engine_combo.count())
                      if self.engine_combo.itemData(i) == desired), -1)
        if index < 0:
            LOG.warning("Selected hardware is unavailable: %s", desired)
            self.engine_combo.addItem(desired.backend.display_name + " (unavailable)", desired)
            index = self.engine_combo.count() - 1
        self.engine_combo.setCurrentIndex(index)
        self._loading = False
        self._update_quality_controls()
        status = (f"{len(available)} hardware encoder(s) available" if available else
                  "No working GPU encoder detected; software x264 is available.")
        if preferred != EncoderBackend.SOFTWARE_X264.value and index == 0:
            status = "Preferred hardware encoder unavailable; using Software — x264."
        self.hardware_status.setText(status)
        if self.media is not None and self.settings is not None:
            self._refresh_plan()
        for job in self.queue.jobs:
            if job.editable:
                self.queue_controller.validate_job(job)
        self._queue_changed()

    def _hardware_preflight_done(self, capability: HardwareEncoderCapability,
                                 request_plan: ConversionPlan | None = None) -> None:
        if request_plan is not None and self._preflight_plan is not request_plan:
            return
        resolved = self._preflight_plan
        self._preflight_plan = None
        if resolved is None:
            return
        if capability.available:
            self._launch_plan(resolved, self._preflight_overwrite)
            return
        LOG.warning("Selected encoder failed preflight: %s", capability.reason_unavailable)
        self.preview_store.discard()
        self._active_preview = None
        self._end_controls()
        self.state.setText("Hardware encoder unavailable")
        self._hardware_capability_changed(capability)
        box = QMessageBox(QMessageBox.Icon.Warning, "Hardware encoder unavailable",
                          f"{capability.display_name} is currently unavailable.", parent=self)
        box.setDetailedText(capability.reason_unavailable or "")
        software = box.addButton("Use Software Encoding", QMessageBox.ButtonRole.AcceptRole)
        fix = box.addButton("Fix Hardware Acceleration", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is software:
            self.engine_combo.setCurrentIndex(0)
        elif box.clickedButton() is fix:
            self._show_hardware_assistant()

    def _hardware_worker_failed(self, error: str, request_plan: ConversionPlan | None = None) -> None:
        if request_plan is not None and self._preflight_plan is not request_plan:
            return
        LOG.error("Hardware detection failed: %s", error)
        if self._preflight_plan is not None:
            self._hardware_preflight_done(HardwareEncoderCapability(
                self._preflight_plan.encoding_engine, "", "Hardware encoder", "", None,
                False, error), request_plan)
        else:
            self.hardware_status.setText("Hardware detection failed; software x264 is available.")

    def _on_state(self, state: str) -> None:
        self.state.setText(state)
        self.pause_button.setText("Resume" if state == "Paused" else "Pause")
        self.pause_button.setEnabled(state == "Paused" or (
            self.runner.phase in {"analyzing", "converting"} and state != "Cancelling..."))

    def _on_stage(self, _label: str) -> None:
        self._started_at = time.monotonic()
        self.progress_bar.setValue(0)
        self.percent.setText("0%")
        self.elapsed.setText("Elapsed: 00:00:00")
        self.remaining.setText("Remaining: —")
        self.speed.setText("Speed: —")

    def _on_progress(self, progress: Progress) -> None:
        if progress.fraction is not None:
            percentage = round(progress.fraction * 100)
            self.progress_bar.setValue(percentage)
            self.percent.setText(f"{percentage}%")
        self.elapsed.setText(f"Elapsed: {_time(time.monotonic() - self._started_at) if self._started_at else '—'}")
        self.remaining.setText(f"Remaining: {_time(progress.eta_seconds)}")
        self.speed.setText(f"Speed: {progress.speed:.2f}x" if progress.speed else "Speed: —")

    def _end_controls(self) -> None:
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self._set_config_enabled(True)
        if self._queued_capabilities is not None:
            queued = self._queued_capabilities
            self._queued_capabilities = None
            self._hardware_detected(queued)
        self._refresh_plan()

    def _set_config_enabled(self, enabled: bool) -> None:
        self.preset_card.setEnabled(enabled)
        for index in range(self.setting_grid.count()):
            widget = self.setting_grid.itemAt(index).widget()
            if widget:
                widget.setEnabled(enabled)

    def _on_complete(self, destination: str) -> None:
        self.progress_bar.setValue(100)
        self.percent.setText("100%")
        if self._active_preview is None:
            self._queue_changed()
            return
        self._capture_preview_diagnostics("Preview ready")
        preview = self._active_preview
        self._active_preview = None
        if preview is not None:
            try:
                self.preview_store.commit(preview)
            except OSError as exc:
                self.preview_store.discard()
                self._end_controls()
                QMessageBox.warning(self, "Preview could not be created", str(exc))
                return
            self.state.setText("Preview ready")
            self._end_controls()
            if preview.settings.auto_open:
                self._open_preview()
            return

    def _on_failure(self, message: str, details: str) -> None:
        if self._active_preview is None:
            self._queue_changed()
            return
        self._capture_preview_diagnostics(message)
        preview = self._active_preview
        self._active_preview = None
        self.preview_store.discard()
        title = "Preview could not be created" if preview else "Conversion failed"
        self.state.setText(title)
        failed_plan = self.runner.plan
        self._end_controls()
        box = QMessageBox(QMessageBox.Icon.Critical, title, message, parent=self)
        box.setDetailedText(details)
        retry = None
        if (failed_plan and self.runner.failure_phase == "converting" and not failed_plan.video_copy
                and failed_plan.encoding_engine.backend != EncoderBackend.SOFTWARE_X264):
            box.setText(f"{failed_plan.encoding_engine.backend.display_name} could not complete this conversion.")
            retry = box.addButton("Retry with Software Encoding", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if retry is not None and box.clickedButton() is retry:
            # A full-file software retry occurs only after this explicit click.
            self.engine_combo.setCurrentIndex(0)
            self._create_preview_with_settings(preview.settings)

    def _on_cancelled(self) -> None:
        if self._active_preview is None:
            self._queue_changed()
            return
        self._capture_preview_diagnostics("Preview cancelled")
        preview = self._active_preview is not None
        self._active_preview = None
        self.preview_store.discard()
        self.state.setText("Preview cancelled" if preview else "Conversion cancelled")
        self._end_controls()

    def _show_command(self) -> None:
        if not self.current_plan:
            QMessageBox.information(self, "Command Preview", "Select a valid source and settings first.")
            return
        subtitle_file = None
        introduction = "Arguments are executed directly, without a shell:\n\n"
        if self.current_plan.subtitle_mode == SubtitleMode.BURN:
            source = self.current_plan.subtitle_source
            assert source is not None
            if isinstance(source, ExternalSubtitleSource):
                subtitle_file = Path(f"subtitle.{source.format.value}")
                introduction = f"External subtitle {source.path} is copied to a safe temporary filename.\n\n" + introduction
            else:
                subtitle_file = Path("subtitle.srt" if source.codec == "subrip" else "subtitle.ass")
                introduction = "The selected subtitle stream is extracted to a safe temporary filename.\n\n" + introduction
        processing = self.current_plan.audio_processing
        if processing.normalization_target:
            try:
                measurements = self.runner.loudness_cache.get(cache_key(self.current_plan, self.runtime))
            except (OSError, ValueError):
                measurements = None
            first_pass = "\n".join(analysis_command(self.current_plan, self.runtime.ffmpeg))
            if measurements is None:
                QMessageBox.information(self, "Command Preview", introduction + "Pass 1 (full selected audio):\n" +
                    first_pass + "\n\nPass 2 is built after analysis using validated measurements. "
                    "It will encode AAC with loudnorm and the targets shown in Output Summary.")
                return
            processing = processing.with_measurements(measurements)
            introduction += "Pass 1 (cached full-track measurements):\n" + first_pass + "\n\nPass 2:\n"
        args = build_command(self.current_plan, self.runtime.ffmpeg, Path("<temporary-output>.mp4"),
                             subtitle_file=subtitle_file, audio_processing=processing)
        message = introduction + "\n".join(args)
        QMessageBox.information(self, "Command Preview", message)

    def _show_loudness_details(self) -> None:
        target = self._loudness_target()
        text = (f"Current target: {target.preset.label}\nIntegrated: {target.integrated_lufs:g} LUFS\n"
                f"True peak: {target.true_peak_dbtp:g} dBTP\nRange: {target.loudness_range_lu:g} LU\n"
                f"Runtime loudnorm: {'available' if self.runtime.loudnorm_available else 'unavailable'}")
        job = self.queue.get(self.selected_job_id)
        reports = [record for record in (job.diagnostics, job.preview_diagnostics) if record.loudness] if job else []
        report = max(reports, key=lambda record: record.recorded_at).loudness if reports else None
        if report:
            measured = report.measurements
            text += (f"\n\nLast analysis: {report.source}\nAudio stream: {report.audio_index}\n"
                     f"Analysis target: {report.target.preset.label}, {report.target.integrated_lufs:g} LUFS, "
                     f"{report.target.true_peak_dbtp:g} dBTP, {report.target.loudness_range_lu:g} LU\n"
                     f"Cache reused: {report.cache_hit}\nMeasured I: {measured.input_i:g} LUFS\n"
                     f"Measured TP: {measured.input_tp:g} dBTP\nMeasured LRA: {measured.input_lra:g} LU\n"
                     f"Threshold: {measured.input_thresh:g} LUFS\nTarget offset: {measured.target_offset:g} LU")
            if report.result:
                text += (f"\nLast pass 2 mode: {report.result.normalization_type}\n"
                         f"Filter output I: {report.result.output_i:g} LUFS\n"
                         f"Filter output TP: {report.result.output_tp:g} dBTP")
        else:
            text += "\n\nNo completed loudness analysis in this session."
        box = QMessageBox(QMessageBox.Icon.Information, "Loudness Details", text,
                          QMessageBox.StandardButton.Ok, self)
        box.exec()

    def _show_settings(self) -> None:
        box = settings_dialog(self.runtime, self)
        box.exec()
        if box.selected_action == "logs":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_directory())))
        elif box.selected_action == "diagnostics":
            self._show_hardware_diagnostics()
        elif box.selected_action == "hardware":
            self._show_hardware_assistant()
        elif box.selected_action == "diagnostics_general":
            from video_converter.ui.diagnostics_dialog import DiagnosticsDialog
            self._diagnostics_dialog = DiagnosticsDialog(self.runtime, self.hardware_diagnosis, self)
            self._diagnostics_dialog.show()
        elif box.selected_action == "issue":
            from video_converter.product import ISSUES_URL
            QDesktopServices.openUrl(QUrl(ISSUES_URL))
        elif box.selected_action == "redetect":
            self._detect_hardware(refresh=True)
        elif box.selected_action == "notices":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(notices_path())))
        elif box.selected_action == "about":
            about = about_dialog(self.runtime, self)
            about.addButton(QMessageBox.StandardButton.Close)
            about.exec()
        elif box.selected_action == "reset":
            reset_preferences(self.storage)
            QMessageBox.information(self, "Settings reset", "Saved preferences were reset.")

    def _show_help(self) -> None:
        QMessageBox.information(self, "Help", "Add or drop videos into the queue. Select a job to configure it; Ctrl/Shift selects several. Choose the source in Copy from before copying settings. Drag pending rows to reorder them, then Start Queue.\n\nPause suspends the current process. Pause Queue finishes the current file before waiting. Cancel Current continues with the next file; Stop Queue cancels the current file and retains pending jobs.\n\nFor ASS, SSA or SRT files, choose Burn into video → External file → Browse. External subtitle files must be assigned separately for each job.")

    def _show_hardware_diagnostics(self) -> None:
        self._show_hardware_assistant()
        self._hardware_assistant.details_button.setChecked(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.add_files(paths)
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._operation_busy():
            QMessageBox.warning(self, "Conversion running", "Cancel the conversion before closing.")
            event.ignore()
            return
        if self._hardware_thread and self._hardware_thread.isRunning():
            self._close_after_probe = True
            event.ignore()
            return
        self.storage.setValue("geometry", self.saveGeometry())
        self.storage.setValue("queue_splitter", self.splitter.sizes())
        self.queue_controller.probes.close()
        for store in set(self._preview_stores.values()) | {self.preview_store}:
            store.cleanup()
        super().closeEvent(event)
