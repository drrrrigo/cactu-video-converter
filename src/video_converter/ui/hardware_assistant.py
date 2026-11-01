"""Structured local hardware help, with explicit re-test and sanitized copying."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)

from video_converter.hardware.report import diagnostic_report
from video_converter.hardware.resources import DriverGuideRegistry, trusted_url
from video_converter.models.hardware_diagnosis import FailureCategory, Severity
from video_converter.ui.branding import application_icon
from video_converter.product import PRODUCT_NAME


def plain_label(text, name=""):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setObjectName(name)
    return label


class HardwareAssistantDialog(QDialog):
    test_requested = Signal()
    software_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Hardware Acceleration — {PRODUCT_NAME}")
        self.setWindowIcon(application_icon())
        self.resize(740, 640)
        self.setMinimumSize(440, 420)
        self.diagnosis = None
        self.report_text = "Hardware detection has not completed. Software x264 is available."
        outer = QVBoxLayout(self)
        outer.addWidget(plain_label("Hardware Acceleration", "section"))
        self.overall = plain_label("Checking hardware… Software x264 remains available.")
        outer.addWidget(self.overall)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.rows = QVBoxLayout(self.content)
        self.rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setAccessibleName("Sanitized hardware diagnostics")
        self.details.hide()
        outer.addWidget(self.details, 1)
        controls = QHBoxLayout()
        self.test_button = QPushButton("Test Again")
        self.test_button.setObjectName("primary")
        self.test_button.clicked.connect(self.test_requested)
        self.software_button = QPushButton("Use Software x264")
        self.software_button.setEnabled(False)
        self.software_button.clicked.connect(self.software_requested)
        controls.addWidget(self.test_button)
        controls.addWidget(self.software_button)
        outer.addLayout(controls)
        second = QHBoxLayout()
        self.details_button = QPushButton("View Diagnostics")
        self.details_button.setCheckable(True)
        self.details_button.toggled.connect(self.details.setVisible)
        self.copy_button = QPushButton("Copy Diagnostics")
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.report_text))
        second.addWidget(self.details_button)
        second.addWidget(self.copy_button)
        outer.addLayout(second)
        self.note = plain_label(
            "Diagnosis stays local. Cactu does not install drivers, run package managers or change device permissions.",
            "muted",
        )
        outer.addWidget(self.note)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)
        outer.addWidget(close)

    def set_busy(self, busy: bool, detecting: bool = False, software_editable: bool = True):
        self.test_button.setEnabled(not busy and not detecting)
        self.test_button.setText("Testing…" if detecting else "Test Again")
        self.test_button.setToolTip(
            "Hardware detection is unavailable while a conversion is running."
            if busy
            else "A hardware test is in progress."
            if detecting
            else "Refresh devices and run initialization probes again."
        )
        self.software_button.setEnabled(software_editable and not busy and not detecting)

    def show_diagnosis(self, diagnosis):
        self.diagnosis = diagnosis
        self.report_text = diagnostic_report(diagnosis)
        self.details.setPlainText(self.report_text)
        self.overall.setText(
            ("✓ Hardware available" if diagnosis.available else "○ Hardware unavailable")
            + " · Software x264 ✓ Available"
        )
        self.overall.setObjectName("successText" if diagnosis.available else "muted")
        self.overall.style().unpolish(self.overall)
        self.overall.style().polish(self.overall)
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        info = diagnosis.inventory
        if info.platform.startswith("linux"):
            self.rows.addWidget(
                plain_label(
                    f"{info.distribution.name} · {info.distribution.family.value} family", "muted"
                )
            )
        registry = DriverGuideRegistry()
        for finding in diagnosis.findings:
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            title = finding.device.model if finding.device else "Hardware inventory"
            if finding.backend:
                title += " · " + finding.backend.display_name
            layout.addWidget(plain_label(title, "section"))
            symbol = (
                "✓"
                if finding.category == FailureCategory.AVAILABLE
                else "✕"
                if finding.severity == Severity.ERROR
                else "⚠"
                if finding.severity == Severity.WARNING
                else "○"
            )
            layout.addWidget(
                plain_label(
                    f"{symbol} {finding.category.label} · {finding.responsibility.value}",
                    "errorText"
                    if finding.severity == Severity.ERROR
                    else "warningText"
                    if finding.severity == Severity.WARNING
                    else "successText"
                    if finding.category == FailureCategory.AVAILABLE
                    else "muted",
                )
            )
            layout.addWidget(plain_label(finding.message))
            if finding.device:
                driver = finding.device.driver or (
                    "Detected" if finding.device.driver_detected else "Not observed"
                )
                layout.addWidget(
                    plain_label(f"Driver: {driver} {finding.device.driver_version}", "muted")
                )
            guide = registry.lookup(finding, info.platform, info.distribution)
            if finding.category != FailureCategory.AVAILABLE:
                layout.addWidget(plain_label(guide.explanation))
                for step in guide.steps:
                    layout.addWidget(plain_label("• " + step, "muted"))
                for support in guide.resources:
                    button = QPushButton(support.label)
                    button.clicked.connect(
                        lambda checked=False, item=support: self.open_resource(item)
                    )
                    layout.addWidget(button)
                if guide.resources:
                    layout.addWidget(
                        plain_label(
                            f"Resources reviewed {guide.last_reviewed}. Package names may change; check official documentation.",
                            "muted",
                        )
                    )
            self.rows.addWidget(card)

    def open_resource(self, support):
        if not trusted_url(support):
            QMessageBox.warning(
                self,
                "Support link unavailable",
                "This resource is not in Cactu's trusted support registry.",
            )
            return
        if not QDesktopServices.openUrl(QUrl(support.url)):
            QMessageBox.warning(
                self,
                "Browser unavailable",
                "The official support page could not be opened. Try your browser or the documentation later.",
            )
