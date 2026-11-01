"""Backend-specific H.264 options and software-to-hardware frame transitions.

Options were checked against FFmpeg 9.0.2's local `-h encoder=...` output.
Runtime initialization probes remain authoritative for each actual build/device.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from video_converter.models.encoder import EncoderBackend, EncoderSelection, HardwareQuality


class VideoEncoderBackend(ABC):
    """Define the complete encoder setup used by both probes and conversions."""

    backend: EncoderBackend
    encoder_name: str

    @property
    def display_name(self) -> str:
        return self.backend.display_name

    def setup_args(self, selection: EncoderSelection) -> list[str]:
        """Global FFmpeg options placed before the input."""
        return []

    def filter_chain(self, subtitle_filter: str | None, selection: EncoderSelection) -> str | None:
        """Return ordered software filter and upload steps, if required."""
        return subtitle_filter

    @abstractmethod
    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        """Return output codec and quality options."""


class SoftwareX264Backend(VideoEncoderBackend):
    backend = EncoderBackend.SOFTWARE_X264
    encoder_name = "libx264"

    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        args = ["-c:v", "libx264", "-crf", str(crf), "-preset", preset]
        if pixel_format != "auto":
            args += ["-pix_fmt", pixel_format]
        return args


class NvencH264Backend(VideoEncoderBackend):
    backend = EncoderBackend.NVIDIA_NVENC
    encoder_name = "h264_nvenc"

    def filter_chain(self, subtitle_filter: str | None, selection: EncoderSelection) -> str:
        return ",".join(filter(None, [subtitle_filter, "format=yuv420p"]))

    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        nvenc_preset, cq = {
            HardwareQuality.HIGH: ("p6", "19"),
            HardwareQuality.BALANCED: ("p4", "23"),
            HardwareQuality.FAST: ("p2", "27"),
        }[quality]
        # NVENC CQ is a VBR target, not an x264 CRF equivalent.
        return ["-c:v", self.encoder_name, "-preset", nvenc_preset, "-tune", "hq",
                "-rc", "vbr", "-cq", cq, "-b:v", "0", "-profile:v", "high"]


class AmfH264Backend(VideoEncoderBackend):
    backend = EncoderBackend.AMD_AMF
    encoder_name = "h264_amf"

    def filter_chain(self, subtitle_filter: str | None, selection: EncoderSelection) -> str:
        return ",".join(filter(None, [subtitle_filter, "format=yuv420p"]))

    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        speed, qp_i, qp_p, qp_b = {
            HardwareQuality.HIGH: ("high_quality", "19", "21", "23"),
            HardwareQuality.BALANCED: ("balanced", "23", "25", "27"),
            HardwareQuality.FAST: ("speed", "28", "30", "32"),
        }[quality]
        return ["-c:v", self.encoder_name, "-quality", speed, "-rc", "cqp",
                "-qp_i", qp_i, "-qp_p", qp_p, "-qp_b", qp_b, "-profile:v", "high"]


class VaapiH264Backend(VideoEncoderBackend):
    backend = EncoderBackend.VAAPI
    encoder_name = "h264_vaapi"

    def setup_args(self, selection: EncoderSelection) -> list[str]:
        if not selection.device:
            raise ValueError("VAAPI requires a probed render device.")
        return ["-init_hw_device", f"vaapi=encode:{selection.device}",
                "-filter_hw_device", "encode"]

    def filter_chain(self, subtitle_filter: str | None, selection: EncoderSelection) -> str:
        # libass renders software frames. Convert to 8-bit NV12 *after* rendering,
        # then upload to the exact VAAPI device initialized above.
        return ",".join(filter(None, [subtitle_filter, "format=nv12", "hwupload"]))

    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        qp = {HardwareQuality.HIGH: "20", HardwareQuality.BALANCED: "24",
              HardwareQuality.FAST: "28"}[quality]
        return ["-c:v", self.encoder_name, "-rc_mode", "CQP", "-qp", qp,
                "-profile:v", "high"]


class QsvH264Backend(VideoEncoderBackend):
    backend = EncoderBackend.INTEL_QSV
    encoder_name = "h264_qsv"

    def setup_args(self, selection: EncoderSelection) -> list[str]:
        if sys.platform.startswith("linux"):
            if not selection.device:
                raise ValueError("Linux QSV requires a probed render device.")
            return ["-init_hw_device", f"qsv=encode,child_device={selection.device}",
                    "-filter_hw_device", "encode"]
        return []

    def filter_chain(self, subtitle_filter: str | None, selection: EncoderSelection) -> str:
        filters = [subtitle_filter, "format=nv12"]
        if sys.platform.startswith("linux"):
            # Explicit upload keeps a multi-GPU Linux selection on the probed
            # QSV device. Windows can submit software NV12 frames directly.
            filters.append("hwupload=extra_hw_frames=64")
        return ",".join(filter(None, filters))

    def encoding_args(self, quality: HardwareQuality, *, crf: int, preset: str,
                      pixel_format: str) -> list[str]:
        qsv_preset, global_quality = {
            HardwareQuality.HIGH: ("slow", "20"),
            HardwareQuality.BALANCED: ("medium", "24"),
            HardwareQuality.FAST: ("fast", "28"),
        }[quality]
        return ["-c:v", self.encoder_name, "-preset", qsv_preset,
                "-global_quality", global_quality, "-profile:v", "high"]


REGISTRY: dict[EncoderBackend, VideoEncoderBackend] = {
    backend.backend: backend for backend in (
        SoftwareX264Backend(), NvencH264Backend(), AmfH264Backend(),
        VaapiH264Backend(), QsvH264Backend(),
    )
}


def get_backend(backend: EncoderBackend) -> VideoEncoderBackend:
    return REGISTRY[backend]


def probe_command(ffmpeg: Path, selection: EncoderSelection,
                  quality: HardwareQuality = HardwareQuality.HIGH,
                  *, subtitle_name: str | None = None,
                  ten_bit_source: bool = False) -> list[str]:
    """Encode three tiny frames through the same backend/filter path as a movie."""
    adapter = get_backend(selection.backend)
    # Some VAAPI drivers require at least 128 pixels in *both* dimensions.
    # A 128x72 probe falsely marked an RX 7700 XT unavailable; 256x144 stays
    # tiny while satisfying that encoder's minimum frame size.
    source = "color=c=black:s=256x144:r=10:d=0.3"
    if ten_bit_source:
        source += ",format=yuv420p10le"
    args = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error",
            *adapter.setup_args(selection), "-f", "lavfi", "-i",
            source, "-frames:v", "3"]
    if subtitle_name not in {None, "subtitle.srt"}:
        raise ValueError("Only the fixed probe subtitle filename is allowed.")
    filters = adapter.filter_chain(f"subtitles={subtitle_name}" if subtitle_name else None,
                                   selection)
    if filters:
        args += ["-vf", filters]
    args += adapter.encoding_args(quality, crf=18, preset="medium",
                                  pixel_format="yuv420p")
    return [*args, "-f", "null", "-"]
