"""Export an isolated packaging snapshot; never promote the selected runtime."""

import json
import shutil
import subprocess
import sys
import tarfile

from release_common import ROOT, read_json, sha256


def prepare(work, destination):
    target = "windows-x86_64" if sys.platform == "win32" else "linux-x86_64"
    suffix = ".exe" if sys.platform == "win32" else ""
    manifest = read_json(work / "manifest.json")
    if manifest["target"] != target:
        raise RuntimeError("Native snapshot target mismatch")
    if destination.exists():
        raise RuntimeError("Use a fresh snapshot directory; existing evidence is preserved")
    destination.mkdir(parents=True)
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, names):
        source = ROOT / name
        if source.is_file():
            out = destination / name
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, out)
    vendor = destination / "vendor/ffmpeg/9.0.2" / target
    vendor.mkdir(parents=True, exist_ok=True)
    for name in ["ffmpeg", "ffprobe"]:
        source = work / "prefix/bin" / (name + suffix)
        if sha256(source) != manifest["outputs"][name]["sha256"]:
            raise RuntimeError("Candidate output changed")
        shutil.copy2(source, vendor / source.name)
    core = next((work / "sources/FFmpeg").iterdir())
    shutil.copy2(core / "COPYING.GPLv3", vendor / "FFmpeg-LICENSE.txt")
    archive = work / ("controlled-" + target + ".tar")
    with tarfile.open(archive, "w") as bundle:
        for name in ["ffmpeg" + suffix, "ffprobe" + suffix, "FFmpeg-LICENSE.txt"]:
            bundle.add(vendor / name, arcname=name)
    selected = read_json(destination / "vendor/ffmpeg/manifest.json")
    entry = selected[target]
    entry.update(
        provider="Cactu controlled candidate (unapproved)",
        source_url=None,
        archive_format="tar",
        ffmpeg_member="ffmpeg" + suffix,
        ffprobe_member="ffprobe" + suffix,
        license_member="FFmpeg-LICENSE.txt",
        build_id=manifest["outputs"]["ffmpeg"]["-version"].splitlines()[0].split()[2],
        build_configuration=next(
            s.removeprefix("configuration: ")
            for s in manifest["outputs"]["ffmpeg"]["-version"].splitlines()
            if s.startswith("configuration: ")
        ),
        archive_filename=archive.name,
        archive_sha256=sha256(archive),
        license_sha256=sha256(vendor / "FFmpeg-LICENSE.txt"),
        hardware_encoders=["h264_nvenc", "h264_qsv", "h264_amf" if suffix else "h264_vaapi"],
        source_recipe="scripts/build_controlled_ffmpeg.py + release/ffmpeg-controlled-lock.json; isolated unapproved candidate",
        corresponding_source_complete=False,
        redistribution_approved=False,
    )
    for name in ["ffmpeg", "ffprobe"]:
        entry[name + "_sha256"] = manifest["outputs"][name]["sha256"]
    (destination / "vendor/ffmpeg/manifest.json").write_text(json.dumps(selected, indent=2) + "\n")
    provenance = {
        "upstream_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
        .decode()
        .strip(),
        "upstream_source_tree_clean": not subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT
        ),
        "candidate_manifest_sha256": sha256(work / "manifest.json"),
        "candidate_source_lock_sha256": sha256(ROOT / "release/ffmpeg-controlled-lock.json"),
        "generated_vendor_manifest_sha256": sha256(destination / "vendor/ffmpeg/manifest.json"),
        "scope": "Isolated packaging export; no selected-runtime promotion or archive download URL",
        "publication_approved": False,
    }
    (destination / "release/controlled-snapshot.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Cactu build experiment",
            "-c",
            "user.email=build@example.invalid",
            "commit",
            "-qm",
            "Isolated controlled candidate snapshot",
        ],
        cwd=destination,
        check=True,
    )


if __name__ == "__main__":
    prepare(
        (ROOT / "build/ffmpeg-controlled").resolve(),
        (ROOT / "build/controlled-app-snapshot").resolve(),
    )
