"""Local report copy, log-folder access and explicit public issue navigation."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)
from video_converter.product import ISSUES_URL
from video_converter.services.diagnostics import report
from video_converter.services.logging import log_directory


class DiagnosticsDialog(QDialog):
    def __init__(self, runtime, hardware=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cactu Diagnostics")
        self.resize(700, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Review this sanitized report before sharing. No media, logs or diagnostics are uploaded."
            )
        )
        self.text = QPlainTextEdit(report(runtime, hardware))
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        actions = QHBoxLayout()
        self.copy = QPushButton("Copy Diagnostics")
        self.copy.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        logs = QPushButton("Open Log Folder")
        logs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_directory())))
        )
        issue = QPushButton("Report Issue")
        issue.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ISSUES_URL)))
        for button in (self.copy, logs, issue):
            actions.addWidget(button)
        layout.addLayout(actions)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)
        layout.addWidget(close)
