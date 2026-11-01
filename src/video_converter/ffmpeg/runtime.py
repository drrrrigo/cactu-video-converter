"""The only service allowed to resolve FFmpeg executable locations."""

from __future__ import annotations

import shutil
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from video_converter.product import PRODUCT_NAME


EXPECTED_VERSION = "9.0.2"
ERROR = f"Bundled FFmpeg installation is incomplete or incompatible. Please reinstall {PRODUCT_NAME}."


@dataclass(frozen=True)
class FFmpegRuntime:
    ffmpeg: Path
    ffprobe: Path
    ffmpeg_version: str
    ffprobe_version: str
    loudnorm_available: bool = False

    @staticmethod
    def bundled_directory() -> Path:
        """PyInstaller ONEDIR adds data under _MEIPASS; source runs use repo vendor."""
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / "ffmpeg"  # type: ignore[attr-defined]
        platform = "windows-x86_64" if sys.platform == "win32" else "linux-x86_64"
        return Path(__file__).resolve().parents[3] / "vendor" / "ffmpeg" / EXPECTED_VERSION / platform

    @classmethod
    def locate(cls, *, allow_system_development: bool = False) -> FFmpegRuntime:
        ext = ".exe" if sys.platform == "win32" else ""
        directory = cls.bundled_directory()
        ffmpeg = directory / f"ffmpeg{ext}"
        ffprobe = directory / f"ffprobe{ext}"
        if not (ffmpeg.is_file() and ffprobe.is_file()):
            if getattr(sys, "frozen", False) or not allow_system_development:
                raise RuntimeError(ERROR)
            ffmpeg_path = shutil.which("ffmpeg")
            ffprobe_path = shutil.which("ffprobe")
            if not ffmpeg_path or not ffprobe_path:
                raise RuntimeError(ERROR)
            ffmpeg, ffprobe = Path(ffmpeg_path).resolve(), Path(ffprobe_path).resolve()
        def output(binary: Path, *args: str) -> str:
            result = subprocess.run([str(binary), *args], capture_output=True, text=True,
                                    timeout=15, check=False)
            if result.returncode != 0:
                raise RuntimeError(ERROR)
            return result.stdout + result.stderr
        ffmpeg_version = output(ffmpeg, "-version").splitlines()[0]
        ffprobe_version = output(ffprobe, "-version").splitlines()[0]
        if EXPECTED_VERSION not in ffmpeg_version or EXPECTED_VERSION not in ffprobe_version:
            raise RuntimeError(ERROR)
        if ffmpeg_version.split()[2] != ffprobe_version.split()[2]:
            raise RuntimeError("Bundled FFmpeg and FFprobe build identities do not match. Reinstall Cactu.")
        encoders = output(ffmpeg, "-hide_banner", "-encoders")
        filters = output(ffmpeg, "-hide_banner", "-filters")
        if "libx264" not in encoders or " aac " not in encoders or "subtitles" not in filters:
            raise RuntimeError(ERROR)
        loudnorm = bool(re.search(r"^\s*\S+\s+loudnorm\s+A->A\s", filters, re.MULTILINE))
        if not loudnorm:
            logging.getLogger(__name__).error("FFmpeg loudness normalization is unavailable: loudnorm filter missing")
        if getattr(sys, "frozen", False):
            from video_converter.ffmpeg.capabilities import capability_tables, require_capabilities
            try:
                require_capabilities(capability_tables(ffmpeg))
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError("Cactu's bundled media runtime is incomplete. Reinstall from the official release.") from exc
        return cls(ffmpeg, ffprobe, ffmpeg_version, ffprobe_version, loudnorm)
