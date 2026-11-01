"""Two-stage FFmpeg hardware encoder detection with session caching."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Callable, Sequence

from video_converter.ffmpeg.encoders import get_backend, probe_command
from video_converter.models.encoder import (
    EncoderBackend, EncoderSelection, HardwareEncoderCapability,
    HardwareQuality,
)

LOG = logging.getLogger(__name__)
VENDORS = {"0x1002": "AMD", "0x8086": "Intel", "0x10de": "NVIDIA"}


def render_nodes(dri_root: Path = Path("/dev/dri")) -> tuple[Path, ...]:
    """Consider every visible Linux render node; names are not fixed to D128."""
    return tuple(sorted(path for path in dri_root.glob("renderD*") if path.exists()))


def render_vendor(device: Path, sysfs_root: Path = Path("/sys/class/drm")) -> str | None:
    try:
        vendor_id = (sysfs_root / device.name / "device" / "vendor").read_text().strip().lower()
    except OSError:
        return None
    return VENDORS.get(vendor_id)


def encoder_names(output: str) -> set[str]:
    """Read encoder identifiers from FFmpeg's table, not description text."""
    return set(re.findall(r"^\s*V\S*\s+(\S+)\s+", output, flags=re.MULTILINE))


class HardwareEncoderDetector:
    """Probe actual initialization, including device and frame upload where used."""

    def __init__(self, ffmpeg: Path, *, platform: str | None = None,
                 devices: Sequence[Path] | None = None,
                 run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        self.ffmpeg = ffmpeg
        self.platform = platform or sys.platform
        self.devices = tuple(devices) if devices is not None else render_nodes()
        self._explicit_devices = devices is not None
        self.exposed_encoders: frozenset[str] | None = None
        self.run = run
        self._cache: tuple[HardwareEncoderCapability, ...] | None = None

    def detect(self, *, refresh: bool = False) -> tuple[HardwareEncoderCapability, ...]:
        """List every applicable backend/device and retain errors for diagnostics."""
        if self._cache is not None and not refresh:
            return self._cache
        if not self._explicit_devices:
            self.devices = render_nodes()
        LOG.info("Hardware detection started")
        result = self.run([str(self.ffmpeg), "-hide_banner", "-encoders"], capture_output=True,
                          text=True, timeout=10, check=False)
        if result.returncode != 0:
            raise RuntimeError("Could not inspect FFmpeg encoders: " + result.stderr[-1000:])
        exposed = encoder_names(result.stdout)
        self.exposed_encoders = frozenset(exposed)
        capabilities: list[HardwareEncoderCapability] = []
        for backend in self._platform_backends():
            adapter = get_backend(backend)
            selections = self._selections(backend)
            if not selections:
                capabilities.append(HardwareEncoderCapability(
                    EncoderSelection(backend), adapter.encoder_name, adapter.display_name,
                    self.platform, None, False, "No DRM render device is available."))
                continue
            for selection in selections:
                if adapter.encoder_name not in exposed:
                    capability = self._capability(selection, False,
                                                  "Encoder is absent from this FFmpeg build.")
                else:
                    capability = self.probe_selection(selection)
                capabilities.append(capability)
        self._cache = tuple(capabilities)
        LOG.info("Hardware detection finished: %s", [
            (cap.display_name, cap.available, cap.reason_unavailable) for cap in capabilities])
        return self._cache

    def probe_selection(self, selection: EncoderSelection) -> HardwareEncoderCapability:
        """Recheck a chosen backend immediately before conversion launch."""
        LOG.info("Testing %s on %s", selection.backend.value, selection.device or "default device")
        # The same subtitle -> format -> upload path is exercised here so an
        # encoder that only works without libass is never shown as usable.
        with tempfile.TemporaryDirectory(prefix="video-converter-gpu-probe-") as workdir:
            Path(workdir, "subtitle.srt").write_text(
                "1\n00:00:00,000 --> 00:00:00,300\nProbe\n", encoding="utf-8")
            checks = [(quality, False) for quality in HardwareQuality]
            checks.append((HardwareQuality.HIGH, True))
            for quality, ten_bit in checks:
                command = probe_command(self.ffmpeg, selection, quality,
                                        subtitle_name="subtitle.srt",
                                        ten_bit_source=ten_bit)
                try:
                    result = self.run(command, capture_output=True, text=True,
                                      timeout=10, check=False, cwd=workdir)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    return replace(self._capability(selection, False,
                                            f"{quality.label}{' / 10-bit input' if ten_bit else ''}: {exc}"),
                                   probe_command=tuple(command))
                if result.returncode != 0:
                    error = result.stderr.strip()[-3000:]
                    capability = self._capability(selection, False,
                                                  f"{quality.label}{' / 10-bit input' if ten_bit else ''}: {error or 'FFmpeg could not initialize this encoder.'}", error)
                    LOG.info("Hardware probe %s failed: %s", capability.display_name, error[-500:])
                    return replace(capability, probe_command=tuple(command), probe_exit_code=result.returncode)
        capability = self._capability(selection, True, None)
        LOG.info("Hardware probe %s: available=%s details=%s", capability.display_name,
                 capability.available, "all quality and subtitle probes passed")
        return replace(capability, probe_command=tuple(command), probe_exit_code=0)

    def _platform_backends(self) -> tuple[EncoderBackend, ...]:
        if self.platform.startswith("win"):
            return (EncoderBackend.NVIDIA_NVENC, EncoderBackend.AMD_AMF, EncoderBackend.INTEL_QSV)
        if self.platform.startswith("linux"):
            return (EncoderBackend.NVIDIA_NVENC, EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV)
        return ()

    def _selections(self, backend: EncoderBackend) -> tuple[EncoderSelection, ...]:
        if self.platform.startswith("linux") and backend in {EncoderBackend.VAAPI, EncoderBackend.INTEL_QSV}:
            return tuple(EncoderSelection(backend, str(device)) for device in self.devices)
        return (EncoderSelection(backend),)

    def _capability(self, selection: EncoderSelection, available: bool,
                    reason: str | None, details: str = "") -> HardwareEncoderCapability:
        adapter = get_backend(selection.backend)
        vendor = render_vendor(Path(selection.device)) if selection.device and self.platform.startswith("linux") else None
        display = adapter.display_name
        if selection.backend == EncoderBackend.VAAPI and vendor:
            display = f"{vendor} GPU — VAAPI"
        if selection.device:
            display += f" ({Path(selection.device).name})"
        return HardwareEncoderCapability(selection, adapter.encoder_name, display,
                                         self.platform, vendor, available, reason, details,
                                         supports_h264=True,
                                         supports_10bit_input_conversion=available,
                                         supports_subtitle_pipeline=available)
