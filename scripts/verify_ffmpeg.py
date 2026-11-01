"""Fail-closed native integrity, build-identity and release capability validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from release_common import ROOT, digest_valid, read_json, sha256

sys.path.insert(0, str(ROOT / "src"))
from video_converter.ffmpeg.capabilities import capability_tables, require_capabilities  # noqa: E402

MANIFEST = ROOT / "vendor/ffmpeg/manifest.json"


def validate(platform: str, *, directory: Path | None = None) -> Path:
    if not MANIFEST.is_file():
        raise RuntimeError("FFmpeg provenance manifest is missing")
    entry = read_json(MANIFEST)[platform]
    for field in ("archive_sha256", "ffmpeg_sha256", "ffprobe_sha256", "license_sha256"):
        if not digest_valid(entry.get(field, "")):
            raise RuntimeError("FFmpeg provenance digest missing: " + field)
    if (
        entry["version"] != "9.0.2"
        or not entry.get("build_configuration")
        or "--enable-nonfree" in entry["build_configuration"]
    ):
        raise RuntimeError("FFmpeg build is unsupported or unredistributable")
    directory = directory or ROOT / "vendor/ffmpeg" / entry["version"] / platform
    suffix = ".exe" if platform.startswith("windows") else ""

    def output(binary, flag):
        return subprocess.run(
            [str(binary), flag], capture_output=True, text=True, check=True, timeout=20
        ).stdout

    identities = []
    for name in ("ffmpeg", "ffprobe"):
        binary = directory / (name + suffix)
        if sha256(binary) != entry[name + "_sha256"]:
            raise RuntimeError(name + " SHA-256 mismatch")
        version = output(binary, "-version")
        token = version.splitlines()[0].split()[2]
        if token != entry["build_id"]:
            raise RuntimeError(name + " build identity mismatch: " + token)
        configuration = next(
            (
                line.partition("configuration: ")[2]
                for line in version.splitlines()
                if line.startswith("configuration: ")
            ),
            "",
        )
        if configuration != entry["build_configuration"] or "--enable-nonfree" in configuration:
            raise RuntimeError(name + " exact build configuration mismatch")
        identities.append(token)
    if identities[0] != identities[1]:
        raise RuntimeError("FFmpeg and FFprobe are not a coherent pair")
    if sha256(directory / "FFmpeg-LICENSE.txt") != entry["license_sha256"]:
        raise RuntimeError("FFmpeg license payload mismatch")
    tables = capability_tables(directory / ("ffmpeg" + suffix))
    require_capabilities(tables)
    hw = {"h264_nvenc", "h264_amf", "h264_qsv", "h264_vaapi"} & tables["-encoders"]
    if hw != set(entry["hardware_encoders"]):
        raise RuntimeError(
            "Hardware encoder exposure differs from the pinned build: "
            f"expected {sorted(entry['hardware_encoders'])}; detected {sorted(hw)}"
        )
    if not entry.get("source_recipe") or not entry.get("license"):
        raise RuntimeError("FFmpeg licensing provenance missing")
    print(f"Verified exact {platform} FFmpeg/FFprobe build {identities[0]}")
    return directory


if __name__ == "__main__":
    validate(sys.argv[1])
