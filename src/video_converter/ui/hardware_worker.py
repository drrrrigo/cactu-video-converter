"""Run blocking FFmpeg GPU initialization probes away from the GUI thread."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.models.encoder import EncoderSelection


class HardwareDetectionWorker(QObject):
    detected = Signal(object)
    checked = Signal(object, object)
    failed = Signal(str, object)
    finished = Signal()
    diagnosed = Signal(object)

    def __init__(self, detector: HardwareEncoderDetector,
                 selection: EncoderSelection | None = None, *, refresh: bool = False,
                 request: object = None, diagnosis_service=None, runtime=None) -> None:
        super().__init__()
        self.detector = detector
        self.selection = selection
        self.refresh = refresh
        self.request = request
        self.diagnosis_service = diagnosis_service
        self.runtime = runtime

    @Slot()
    def run(self) -> None:
        try:
            if self.selection is None:
                capabilities = self.detector.detect(refresh=self.refresh)
                self.detected.emit(capabilities)
                if self.diagnosis_service is not None:
                    from video_converter.hardware.diagnosis import inspect_features
                    try:
                        features = inspect_features(self.detector, self.runtime)
                        self.diagnosed.emit(self.diagnosis_service.diagnose(capabilities, features, refresh=self.refresh))
                    except Exception:
                        # Explaining a failure must never revoke a successful probe.
                        logging.getLogger(__name__).exception("Hardware explanation unavailable; encoder results retained")
            else:
                self.checked.emit(self.detector.probe_selection(self.selection), self.request)
        except Exception as exc:
            self.failed.emit(str(exc), self.request)
            if self.selection is None and self.diagnosis_service is not None:
                from video_converter.models.hardware_diagnosis import RuntimeFeatures
                try:
                    self.diagnosed.emit(self.diagnosis_service.diagnose((), RuntimeFeatures(
                        error=f"Encoder inspection unavailable: {type(exc).__name__}"), refresh=True))
                except Exception:
                    logging.getLogger(__name__).exception("Hardware explanation unavailable; software remains usable")
        finally:
            self.finished.emit()
