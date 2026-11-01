"""Local hardware evidence and explanations, independent of Qt presentation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from video_converter.models.encoder import EncoderBackend, HardwareEncoderCapability


class GpuVendor(str, Enum):
    AMD = "AMD"
    NVIDIA = "NVIDIA"
    INTEL = "Intel"
    UNKNOWN = "Unknown"


class DistributionFamily(str, Enum):
    ARCH = "Arch"
    DEBIAN = "Debian"
    FEDORA = "Fedora"
    SUSE = "SUSE"
    UNKNOWN = "Unknown"


class FailureCategory(str, Enum):
    AVAILABLE = "AVAILABLE"
    NO_SUPPORTED_GPU = "NO_SUPPORTED_GPU"
    GPU_DETECTED_ENCODER_UNSUPPORTED = "GPU_DETECTED_ENCODER_UNSUPPORTED"
    FFMPEG_ENCODER_MISSING = "FFMPEG_ENCODER_MISSING"
    DRIVER_NOT_DETECTED = "DRIVER_NOT_DETECTED"
    DRIVER_TOO_OLD_OR_INCOMPATIBLE = "DRIVER_TOO_OLD_OR_INCOMPATIBLE"
    DEVICE_NODE_MISSING = "DEVICE_NODE_MISSING"
    DEVICE_PERMISSION_DENIED = "DEVICE_PERMISSION_DENIED"
    BACKEND_INITIALIZATION_FAILED = "BACKEND_INITIALIZATION_FAILED"
    MULTIPLE_GPU_AMBIGUITY = "MULTIPLE_GPU_AMBIGUITY"
    BACKEND_DEVICE_MISMATCH = "BACKEND_DEVICE_MISMATCH"
    MISSING_SYSTEM_COMPONENT = "MISSING_SYSTEM_COMPONENT"
    APPLICATION_PACKAGING_ERROR = "APPLICATION_PACKAGING_ERROR"
    UNKNOWN = "UNKNOWN"

    @property
    def label(self) -> str:
        return {
            self.AVAILABLE: "Available",
            self.NO_SUPPORTED_GPU: "No supported GPU encoder detected",
            self.GPU_DETECTED_ENCODER_UNSUPPORTED: "Encoder unsupported by this probe",
            self.FFMPEG_ENCODER_MISSING: "FFmpeg encoder missing",
            self.DRIVER_NOT_DETECTED: "Graphics driver not detected",
            self.DRIVER_TOO_OLD_OR_INCOMPATIBLE: "Driver / API incompatible",
            self.DEVICE_NODE_MISSING: "Render device missing",
            self.DEVICE_PERMISSION_DENIED: "Device access denied",
            self.BACKEND_INITIALIZATION_FAILED: "Encoder initialization failed",
            self.MULTIPLE_GPU_AMBIGUITY: "Adapter attribution uncertain",
            self.BACKEND_DEVICE_MISMATCH: "Backend / device mismatch",
            self.MISSING_SYSTEM_COMPONENT: "Graphics runtime component unavailable",
            self.APPLICATION_PACKAGING_ERROR: "FFmpeg build capability missing",
            self.UNKNOWN: "Cause not established",
        }[self]


class Severity(str, Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"


class Responsibility(str, Enum):
    NONE = "No action needed"
    SYSTEM = "System / graphics stack"
    APPLICATION = "Cactu packaging"
    RUNTIME = "Development FFmpeg runtime"
    UNDETERMINED = "Cause not established"


@dataclass(frozen=True)
class LinuxDistribution:
    id: str = ""
    id_like: tuple[str, ...] = ()
    name: str = "Unknown Linux distribution"
    version: str = ""
    family: DistributionFamily = DistributionFamily.UNKNOWN


@dataclass(frozen=True)
class RenderDevice:
    path: str
    exists: bool | None
    readable: bool
    writable: bool
    mode: str = ""


@dataclass(frozen=True)
class GpuDevice:
    id: str
    vendor: GpuVendor
    model: str
    vendor_id: str = ""
    device_id: str = ""
    driver: str = ""
    driver_version: str = ""
    driver_detected: bool | None = None
    render_nodes: tuple[RenderDevice, ...] = ()
    adapter_status: str = ""


@dataclass(frozen=True)
class HardwareInventory:
    platform: str
    os_name: str
    devices: tuple[GpuDevice, ...] = ()
    distribution: LinuxDistribution = LinuxDistribution()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeFeatures:
    encoders: frozenset[str] | None = None
    filters: frozenset[str] | None = None
    hardware_apis: frozenset[str] | None = None
    bundled: bool = False
    error: str = ""


@dataclass(frozen=True)
class HardwareFinding:
    device: GpuDevice | None
    backend: EncoderBackend | None
    category: FailureCategory
    severity: Severity
    responsibility: Responsibility
    message: str
    probe: HardwareEncoderCapability | None = None
    encoder_present: bool | None = None
    guide_id: str = ""


@dataclass(frozen=True)
class HardwareAccelerationDiagnosis:
    inventory: HardwareInventory
    features: RuntimeFeatures
    findings: tuple[HardwareFinding, ...]
    capabilities: tuple[HardwareEncoderCapability, ...]
    ffmpeg_version: str
    application_version: str

    @property
    def available(self) -> bool:
        return any(cap.available for cap in self.capabilities)

    @property
    def banner_eligible(self) -> bool:
        return not self.available and any(
            d.vendor != GpuVendor.UNKNOWN for d in self.inventory.devices
        )

    @property
    def identity(self) -> str:
        # No paths, names or raw stderr are persisted in the dismissal record.
        state = (
            self.application_version.split(".")[0],
            self.inventory.platform,
            self.inventory.os_name,
            self.inventory.distribution.id,
            self.ffmpeg_version,
            self.available,
            [
                (
                    d.id,
                    d.vendor.value,
                    d.device_id,
                    d.driver,
                    d.driver_version,
                    [(n.path, n.exists, n.readable, n.writable) for n in d.render_nodes],
                )
                for d in self.inventory.devices
            ],
            [(f.backend.value if f.backend else None, f.category.value) for f in self.findings],
        )
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
