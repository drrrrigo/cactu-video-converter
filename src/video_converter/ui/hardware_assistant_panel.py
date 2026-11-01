"""MainWindow hardware-help bindings; no probing or command construction here."""

from __future__ import annotations

import logging
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton

from video_converter.hardware.report import sanitize
from video_converter.models.encoder import EncoderSelection
from video_converter.ui.hardware_assistant import HardwareAssistantDialog, plain_label

LOG = logging.getLogger(__name__)
DISMISSAL_KEY = "hardware_assistant/dismissed_identity"


class HardwareAssistantMixin:
    def _build_hardware_banner(self):
        frame = QFrame()
        frame.setObjectName("warning")
        layout = QHBoxLayout(frame)
        self.hardware_banner_text = plain_label("", "warningText")
        layout.addWidget(self.hardware_banner_text, 1)
        fix = QPushButton("Fix Hardware Acceleration")
        fix.clicked.connect(self._show_hardware_assistant)
        dismiss = QPushButton("Dismiss")
        dismiss.clicked.connect(self._dismiss_hardware_banner)
        layout.addWidget(fix)
        layout.addWidget(dismiss)
        frame.hide()
        return frame

    def _hardware_testing(self):
        return self._hardware_thread is not None and self._hardware_thread.isRunning()

    def _hardware_explained(self, diagnosis):
        if self._operation_busy():
            self._queued_diagnosis = diagnosis
            return
        self.hardware_diagnosis = diagnosis
        if self._hardware_assistant:
            self._hardware_assistant.show_diagnosis(diagnosis)
        self._refresh_hardware_banner()
        self._update_assistant_controls()

    def _refresh_hardware_banner(self):
        diagnosis = self.hardware_diagnosis
        if diagnosis is None:
            self.hardware_banner.hide()
            return
        if diagnosis.available:
            self.storage.remove(DISMISSAL_KEY)
        eligible = (
            diagnosis.banner_eligible and self.storage.value(DISMISSAL_KEY) != diagnosis.identity
        )
        if eligible:
            models = ", ".join(sanitize(d.model) for d in diagnosis.inventory.devices)[:180]
            self.hardware_banner_text.setText(
                f"⚠ Hardware acceleration is unavailable\n{models} detected. Software x264 remains available."
            )
        self.hardware_banner.setVisible(eligible)

    def _dismiss_hardware_banner(self):
        if self.hardware_diagnosis:
            self.storage.setValue(DISMISSAL_KEY, self.hardware_diagnosis.identity)
            self.storage.sync()
        self.hardware_banner.hide()

    def _show_hardware_assistant(self):
        if self._hardware_assistant is None:
            dialog = HardwareAssistantDialog(self)
            dialog.test_requested.connect(self._test_hardware_again)
            dialog.software_requested.connect(self._assistant_use_software)
            self._hardware_assistant = dialog
        if self.hardware_diagnosis:
            self._hardware_assistant.show_diagnosis(self.hardware_diagnosis)
        self._update_assistant_controls()
        self._hardware_assistant.show()
        self._hardware_assistant.raise_()
        self._hardware_assistant.activateWindow()
        # Startup detection owns the initial test; opening the assistant is read-only.

    def _test_hardware_again(self):
        if self._operation_busy() or self._hardware_testing():
            return
        LOG.info("Hardware Assistant: Test Again requested")
        self.storage.remove(DISMISSAL_KEY)
        self._detect_hardware(refresh=True)
        self._update_assistant_controls()

    def _assistant_use_software(self):
        job = self.queue.get(self.selected_job_id)
        if self._operation_busy() or self._hardware_testing() or not job or not job.editable:
            return
        index = next((i for i in range(self.engine_combo.count())
                      if self.engine_combo.itemData(i) == EncoderSelection()), -1)
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)

    def _update_assistant_controls(self):
        if self._queued_diagnosis is not None and not self._operation_busy():
            diagnosis, self._queued_diagnosis = self._queued_diagnosis, None
            self._hardware_explained(diagnosis)
        if self._hardware_assistant:
            job = self.queue.get(self.selected_job_id)
            self._hardware_assistant.set_busy(
                self._operation_busy(), self._hardware_testing(), bool(job and job.editable)
            )

    def _hardware_capability_changed(self, capability):
        capabilities = tuple(
            c for c in self.hardware_capabilities if c.selection != capability.selection
        ) + (capability,)
        self._hardware_detected(capabilities)
        if self.hardware_diagnosis:
            previous = self.hardware_diagnosis
            result = self.hardware_diagnosis_service.diagnose(
                capabilities, previous.features, inventory=previous.inventory, refresh=True
            )
            self._hardware_explained(result)
