"""Log uncaught Qt/Python errors and offer recovery without raw traceback UI."""

import logging
import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMessageBox
from video_converter.services.diagnostics import record_error


class ErrorReporter(QObject):
    raised = Signal(str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.visible = False
        self.raised.connect(self.show_error)

    def hook(self, kind, value, traceback):
        logging.getLogger(__name__).critical(
            "Unexpected application exception", exc_info=(kind, value, traceback)
        )
        record_error(kind.__name__)
        if issubclass(kind, (KeyboardInterrupt, SystemExit)):
            sys.__excepthook__(kind, value, traceback)
            QApplication.instance().quit()
            return
        self.raised.emit(kind.__name__)

    def show_error(self, category):
        if self.visible:
            return
        self.visible = True
        try:
            box = QMessageBox(
                QMessageBox.Icon.Critical,
                "Unexpected Cactu error",
                "Cactu encountered an unexpected error. Review the current job before continuing. Original media files are not deleted by Cactu.",
                parent=self.window,
            )
            diagnostics = box.addButton("Copy Diagnostics", QMessageBox.ButtonRole.ActionRole)
            logs = box.addButton("Open Log Folder", QMessageBox.ButtonRole.ActionRole)
            issue = box.addButton("Report Issue", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.exec()
            if box.clickedButton() is diagnostics:
                from video_converter.services.diagnostics import report

                QApplication.clipboard().setText(
                    report(self.window.runtime, self.window.hardware_diagnosis)
                )
            elif box.clickedButton() in (logs, issue):
                from PySide6.QtCore import QUrl
                from PySide6.QtGui import QDesktopServices
                from video_converter.product import ISSUES_URL
                from video_converter.services.logging import log_directory

                target = (
                    QUrl(ISSUES_URL)
                    if box.clickedButton() is issue
                    else QUrl.fromLocalFile(str(log_directory()))
                )
                QDesktopServices.openUrl(target)
        finally:
            self.visible = False
