"""Fail-closed native integrity, build-identity and release capability validation."""

from __future__ import annotations

import subprocess
import json
import sys
from pathlib import Path

from release_common import ROOT, digest_valid, read_json, sha256

sys.path.insert(0, str(ROOT / "src"))
from video_converter.ffmpeg.capabilities import capability_tables, require_capabilities  # noqa: E402

MANIFEST = ROOT / "vendor/ffmpeg/manifest.json"


def validate(
    platform: str,
    *,
    directory: Path | None = None,
    evidence_path: Path | None = None,
    manifest_path: Path | None = None,
) -> Path:
    selected_manifest = manifest_path or MANIFEST
    if not selected_manifest.is_file():
        raise RuntimeError("FFmpeg provenance manifest is missing")
    entry = read_json(selected_manifest)[platform]
    fields = ["ffmpeg_sha256", "ffprobe_sha256", "license_sha256"]
    fields.append(
        "pair_sha256" if entry.get("input_kind") == "direct-controlled-build" else "archive_sha256"
    )
    for field in fields:
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
        result = subprocess.run(
            [str(binary), flag], capture_output=True, text=True, check=True, timeout=20
        )
        return result.stdout + result.stderr

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
    binary = directory / ("ffmpeg" + suffix)
    license_output = output(binary, "-L")
    normalized_license = " ".join(license_output.split())
    if (
        "GNU General Public License" not in normalized_license
        or "version 3" not in normalized_license
    ):
        raise RuntimeError("Exact FFmpeg -L output does not confirm expected GPL version 3 terms")
    if evidence_path:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(
                {
                    "target": platform,
                    "build_id": entry["build_id"],
                    "archive_filename": entry.get("archive_filename"),
                    "archive_sha256": entry.get("archive_sha256"),
                    "input_kind": entry.get("input_kind", "provider-archive"),
                    "pair_sha256": entry.get("pair_sha256"),
                    "ffmpeg_sha256": sha256(binary),
                    "ffprobe_sha256": sha256(directory / ("ffprobe" + suffix)),
                    "ffmpeg_version": output(binary, "-version"),
                    "ffprobe_version": output(directory / ("ffprobe" + suffix), "-version"),
                    "ffmpeg_buildconf": output(binary, "-buildconf"),
                    "ffmpeg_license": license_output,
                    "mandatory_capabilities_passed": True,
                    "nonfree": False,
                    "capability_tables": {flag: sorted(values) for flag, values in tables.items()},
                    "redistribution_approved": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"Verified exact {platform} FFmpeg/FFprobe build {identities[0]}")
    return directory


if __name__ == "__main__":
    validate(sys.argv[1])
