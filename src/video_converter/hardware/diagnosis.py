"""Interpret local evidence; encoder initialization remains the source of truth."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import replace

from video_converter import __version__
from video_converter.ffmpeg.encoders import get_backend
from video_converter.ffmpeg.hardware_detector import encoder_names
from video_converter.hardware.inventory import collect_inventory
from video_converter.hardware.resources import DriverGuideRegistry
from video_converter.models.encoder import EncoderBackend, HardwareEncoderCapability
from video_converter.models.hardware_diagnosis import (
    FailureCategory as Category,
    GpuVendor,
    HardwareAccelerationDiagnosis,
    HardwareFinding,
    HardwareInventory,
    Responsibility,
    RuntimeFeatures,
    Severity,
)

LOG = logging.getLogger(__name__)


def expected_backends(vendor: GpuVendor, platform: str) -> tuple[EncoderBackend, ...]:
    if platform.startswith("win"):
        backend = {
            GpuVendor.NVIDIA: EncoderBackend.NVIDIA_NVENC,
            GpuVendor.AMD: EncoderBackend.AMD_AMF,
            GpuVendor.INTEL: EncoderBackend.INTEL_QSV,
        }.get(vendor)
        return (backend,) if backend else ()
    if platform.startswith("linux"):
        return {
            GpuVendor.NVIDIA: (EncoderBackend.NVIDIA_NVENC,),
            GpuVendor.AMD: (EncoderBackend.VAAPI,),
            GpuVendor.INTEL: (EncoderBackend.INTEL_QSV, EncoderBackend.VAAPI),
        }.get(vendor, ())
    return ()


def inspect_features(detector, runtime) -> RuntimeFeatures:
    errors = []
    run = getattr(detector, "run", subprocess.run)

    def output(flag):
        try:
            result = run(
                [str(runtime.ffmpeg), "-hide_banner", flag],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout
            errors.append(f"FFmpeg {flag} inspection failed (exit {result.returncode}).")
        except (OSError, subprocess.TimeoutExpired):
            errors.append(f"FFmpeg {flag} inspection was unavailable.")
        return None

    encoders = getattr(detector, "exposed_encoders", None)
    if encoders is None:
        raw = output("-encoders")
        encoders = frozenset(encoder_names(raw)) if raw is not None else None
    filters = output("-filters")
    apis = output("-hwaccels")
    return RuntimeFeatures(
        encoders,
        frozenset(re.findall(r"^\s*[.A-Z|]{3}\s+(\S+)\s", filters, re.M))
        if filters is not None
        else None,
        frozenset(line.strip() for line in apis.splitlines()[1:] if line.strip())
        if apis is not None
        else None,
        bool(getattr(sys, "frozen", False) or runtime.ffmpeg.parent == runtime.bundled_directory()),
        "; ".join(errors),
    )


def classify(
    device,
    backend,
    probe: HardwareEncoderCapability | None,
    features: RuntimeFeatures,
    platform: str,
) -> HardwareFinding:
    encoder = get_backend(backend).encoder_name
    present = encoder in features.encoders if features.encoders is not None else None
    responsibility = Responsibility.UNDETERMINED
    category = Category.UNKNOWN
    message = "Cactu could not establish why this hardware encoder is unavailable. View Diagnostics for the evidence."
    if probe and probe.available:
        category, responsibility = Category.AVAILABLE, Responsibility.NONE
        message = "The actual FFmpeg encoder initialization passed. This backend is available for supported conversions."
    else:
        details = (
            ((probe.reason_unavailable or "") + "\n" + probe.initialization_details).lower()
            if probe
            else ""
        )
        required_filters = {"format", "subtitles"}
        if platform.startswith("linux") and backend in {
            EncoderBackend.VAAPI,
            EncoderBackend.INTEL_QSV,
        }:
            required_filters.add("hwupload")
        api = {
            EncoderBackend.VAAPI: "vaapi",
            EncoderBackend.INTEL_QSV: "qsv",
            EncoderBackend.NVIDIA_NVENC: "cuda",
        }.get(backend)
        missing_feature = (
            (features.filters is not None and not required_filters <= features.filters)
            or (api and features.hardware_apis is not None and api not in features.hardware_apis)
            or "no such filter" in details
            or "unknown encoder" in details
        )
        if present is False:
            category = Category.FFMPEG_ENCODER_MISSING
            responsibility = (
                Responsibility.APPLICATION if features.bundled else Responsibility.RUNTIME
            )
            message = (
                "Cactu's bundled FFmpeg" if features.bundled else "The development FFmpeg runtime"
            ) + f" does not contain {encoder}. Driver updates cannot add it to this build."
        elif missing_feature:
            category = Category.APPLICATION_PACKAGING_ERROR
            responsibility = (
                Responsibility.APPLICATION if features.bundled else Responsibility.RUNTIME
            )
            message = "The FFmpeg build lacks a filter or hardware API required by Cactu's encoding pipeline. Check the application/runtime build."
        elif (
            platform.startswith("linux")
            and backend in {EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV}
            and device
        ):
            node = next(
                (n for n in device.render_nodes if probe and n.path == probe.selection.device), None
            )
            if probe and probe.selection.device and not node:
                category = Category.BACKEND_DEVICE_MISMATCH
                message = "The probed render device could not be associated with this GPU. Check the selected backend and device."
            elif not device.render_nodes or (node and node.exists is False):
                category, responsibility = Category.DEVICE_NODE_MISSING, Responsibility.SYSTEM
                message = "Cactu detected the GPU, but no render device was available for it. Driver, session or container restrictions may be responsible."
            elif node and (not node.readable or not node.writable):
                category, responsibility = Category.DEVICE_PERMISSION_DENIED, Responsibility.SYSTEM
                message = "Cactu can see the GPU render device, but this account/session cannot access it for encoding."
        if category == Category.UNKNOWN and device and device.driver_detected is False:
            category, responsibility = Category.DRIVER_NOT_DETECTED, Responsibility.SYSTEM
            message = "No bound graphics driver was detected for this GPU. The driver may not be loaded or visible in this environment."
        if category == Category.UNKNOWN:
            if "permission denied" in details:
                category, responsibility = Category.DEVICE_PERMISSION_DENIED, Responsibility.SYSTEM
                message = "The initialization probe reported an access denial. Check graphics device/session permissions in Diagnostics."
            elif any(
                term in details
                for term in (
                    "minimum required nvidia driver",
                    "driver does not support the required nvenc api",
                    "driver version is insufficient",
                    "incompatible driver",
                )
            ):
                category, responsibility = (
                    Category.DRIVER_TOO_OLD_OR_INCOMPATIBLE,
                    Responsibility.SYSTEM,
                )
                message = "The probe explicitly reported a driver/API incompatibility. Review official support for this runtime and GPU."
            elif any(
                term in details
                for term in (
                    "no capable devices found",
                    "encoding not supported",
                    "codec not supported",
                    "no usable encoding entrypoint",
                )
            ):
                category = Category.GPU_DETECTED_ENCODER_UNSUPPORTED
                message = "The GPU was detected, but the probe reports no supported hardware encoding capability for this backend. Software x264 remains available."
            elif any(
                term in details
                for term in (
                    "cannot load lib",
                    "failed to load",
                    "cannot load amf",
                    "library not found",
                )
            ):
                category, responsibility = Category.MISSING_SYSTEM_COMPONENT, Responsibility.SYSTEM
                message = "A graphics/media runtime library required by the backend could not be loaded. Review the system graphics stack and packaging details."
            elif probe and probe.probe_command:
                category = Category.BACKEND_INITIALIZATION_FAILED
                message = "FFmpeg found the backend, but could not initialize its encoding pipeline. A driver or runtime issue is possible; the exact cause is not established."
            elif probe and probe.initialization_details:
                category = Category.BACKEND_INITIALIZATION_FAILED
                message = "The hardware encoder initialization failed. View Diagnostics; this does not prove the driver is missing or outdated."
    severity = (
        Severity.INFO
        if category == Category.AVAILABLE
        else (
            Severity.ERROR
            if category in {Category.FFMPEG_ENCODER_MISSING, Category.APPLICATION_PACKAGING_ERROR}
            else Severity.WARNING
        )
    )
    return HardwareFinding(
        device, backend, category, severity, responsibility, message, probe, present
    )


class HardwareDiagnosisService:
    def __init__(self, runtime, inventory_provider=collect_inventory):
        self.runtime = runtime
        self.inventory_provider = inventory_provider
        self._cache: HardwareAccelerationDiagnosis | None = None

    def diagnose(
        self,
        capabilities,
        features: RuntimeFeatures,
        *,
        inventory: HardwareInventory | None = None,
        refresh: bool = False,
    ) -> HardwareAccelerationDiagnosis:
        if (
            self._cache is not None
            and not refresh
            and tuple(capabilities) == self._cache.capabilities
            and features == self._cache.features
            and (inventory is None or inventory == self._cache.inventory)
        ):
            return self._cache
        LOG.info("Hardware diagnosis started; refresh=%s", refresh)
        if inventory is None:
            try:
                inventory = self.inventory_provider()
            except Exception as exc:
                inventory = HardwareInventory(
                    sys.platform,
                    sys.platform,
                    errors=(f"Local graphics inventory unavailable: {type(exc).__name__}",),
                )
        findings = []
        for device in inventory.devices:
            for backend in expected_backends(device.vendor, inventory.platform):
                candidates = [
                    c
                    for c in capabilities
                    if c.selection.backend == backend
                    and (
                        c.selection.device in {n.path for n in device.render_nodes}
                        or c.selection.device is None
                    )
                ]
                if not candidates:
                    candidates = [None]
                for probe in candidates:
                    finding = classify(device, backend, probe, features, inventory.platform)
                    if (
                        probe
                        and not probe.selection.device
                        and sum(d.vendor == device.vendor for d in inventory.devices) > 1
                        and finding.category
                        not in {
                            Category.FFMPEG_ENCODER_MISSING,
                            Category.APPLICATION_PACKAGING_ERROR,
                        }
                    ):
                        finding = HardwareFinding(
                            device,
                            backend,
                            Category.MULTIPLE_GPU_AMBIGUITY,
                            Severity.WARNING,
                            Responsibility.UNDETERMINED,
                            "Multiple adapters match this default-device probe; its result cannot be assigned to an individual GPU.",
                            probe,
                            get_backend(backend).encoder_name in features.encoders
                            if features.encoders is not None
                            else None,
                        )
                    findings.append(finding)
        for probe in capabilities:
            if probe.available and not any(f.probe == probe for f in findings):
                findings.append(
                    classify(None, probe.selection.backend, probe, features, inventory.platform)
                )
        if not findings:
            unknown = bool(inventory.errors)
            findings.append(
                HardwareFinding(
                    None,
                    None,
                    Category.UNKNOWN if unknown else Category.NO_SUPPORTED_GPU,
                    Severity.INFO,
                    Responsibility.UNDETERMINED,
                    "GPU inventory is incomplete; hardware availability could not be established."
                    if unknown
                    else "No supported hardware H.264 encoder was detected. Software x264 is a supported configuration.",
                )
            )
        registry = DriverGuideRegistry()
        findings = [
            replace(f, guide_id=registry.lookup(f, inventory.platform, inventory.distribution).id)
            for f in findings
        ]
        result = HardwareAccelerationDiagnosis(
            inventory,
            features,
            tuple(findings),
            tuple(capabilities),
            self.runtime.ffmpeg_version,
            __version__,
        )
        self._cache = result
        LOG.info(
            "Hardware diagnosis OS=%s distro=%s devices=%s available=%s findings=%s",
            inventory.os_name,
            inventory.distribution.id,
            [
                (
                    d.vendor.value,
                    d.device_id,
                    d.driver,
                    d.driver_version,
                    [n.path for n in d.render_nodes],
                )
                for d in inventory.devices
            ],
            result.available,
            [
                (f.backend.value if f.backend else None, f.category.value, f.guide_id)
                for f in findings
            ],
        )
        if any(f.severity == Severity.ERROR for f in findings):
            LOG.error(
                "Hardware runtime/build capability issue; review Hardware Acceleration diagnostics"
            )
        return result
