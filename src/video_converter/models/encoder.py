"""Typed hardware encoder identity and probe results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EncoderBackend(str, Enum):
    SOFTWARE_X264 = "software_x264"
    NVIDIA_NVENC = "nvidia_nvenc"
    AMD_AMF = "amd_amf"
    VAAPI = "vaapi"
    INTEL_QSV = "intel_qsv"

    @property
    def display_name(self) -> str:
        return {
            self.SOFTWARE_X264: "Software — x264",
            self.NVIDIA_NVENC: "NVIDIA NVENC",
            self.AMD_AMF: "AMD AMF",
            self.VAAPI: "VAAPI Hardware Encoder",
            self.INTEL_QSV: "Intel Quick Sync",
        }[self]


class HardwareQuality(str, Enum):
    HIGH = "high"
    BALANCED = "balanced"
    FAST = "fast"

    @property
    def label(self) -> str:
        return {self.HIGH: "High Quality", self.BALANCED: "Balanced", self.FAST: "Fast"}[self]


@dataclass(frozen=True)
class EncoderSelection:
    """Device identity is separate from the user-facing display name."""

    backend: EncoderBackend = EncoderBackend.SOFTWARE_X264
    device: str | None = None


@dataclass(frozen=True)
class HardwareEncoderCapability:
    selection: EncoderSelection
    encoder_name: str
    display_name: str
    platform: str
    vendor: str | None
    available: bool
    reason_unavailable: str | None = None
    initialization_details: str = ""
    supports_h264: bool = True
    supports_10bit_input_conversion: bool = False
    supports_subtitle_pipeline: bool = False
    probe_command: tuple[str, ...] = ()
    probe_exit_code: int | None = None
