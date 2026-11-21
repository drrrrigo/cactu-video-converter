"""Prepare a local, explicitly incomplete source bundle for candidate review."""

import json
import tarfile
import io
from release_common import ROOT, read_json, sha256


def prepare():
    lock = read_json(ROOT / "release/ffmpeg-controlled-lock.json")
    output = ROOT / "build/source-delivery"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "Cactu-FFmpeg-controlled-source-review.tar"
    with tarfile.open(archive, "w") as bundle:
        for entry in lock["sources"]:
            if entry["project"] == "AMF":
                continue  # This local component bundle targets the Linux candidate.
            source = ROOT / "release/evidence/local/sources" / entry["filename"]
            if sha256(source) != entry["sha256"]:
                raise RuntimeError("Source changed: " + entry["project"])
            bundle.add(source, arcname="release/evidence/local/sources/" + entry["filename"])
        for name in [
            "scripts/build_controlled_ffmpeg.py",
            "scripts/release_common.py",
            "scripts/ffmpeg_tool_profile.py",
            "release/ffmpeg-native-environments.json",
            "release/ffmpeg-controlled-lock.json",
            "release/ffmpeg-build-tool-lock.json",
            ".github/workflows/ffmpeg-controlled.yml",
            "docs/FFMPEG_CONTROLLED_BUILD.md",
            "LICENSE",
        ]:
            bundle.add(ROOT / name, arcname=name)
        version = ("9.0.2-cactu-" + lock["sources"][0]["revision"][:12] + "\n").encode()
        entry = tarfile.TarInfo("generated/FFmpeg/VERSION")
        entry.size = len(version)
        bundle.addfile(entry, io.BytesIO(version))
        readme = (
            "LOCAL INCOMPLETE COMPONENT SOURCE REVIEW BUNDLE — NOT APPROVED FOR PUBLICATION\n"
            "Scope: Linux FFmpeg source inputs and Cactu build recipe only.\n"
            "Run with Python 3.14: python scripts/build_controlled_ffmpeg.py linux-x86_64\n"
            "Native prerequisites are shown in .github/workflows/ffmpeg-controlled.yml.\n"
            "The optional --environment-profile requires the exact recorded build-tool hashes.\n"
            "This is not a hermetic toolchain: host font/shaping/compression/VA libraries,\n"
            "compiler/sysroot source and exact build correspondence are separate obligations.\n"
            "Assembly is disabled. No bit-identical FFmpeg reproduction is asserted.\n"
            "Windows AMF input is excluded. Cactu application/Qt/Python/native/runtime source\n"
            "and per-component notices, final terms review and maintained delivery are not\n"
            "satisfied by this component bundle. SOURCE-ASSETS.json remains unapproved.\n"
        ).encode()
        entry = tarfile.TarInfo("README-SOURCE-REVIEW.txt")
        entry.size = len(readme)
        bundle.addfile(entry, io.BytesIO(readme))
    manifest = {
        "complete_corresponding_source": False,
        "assets": [
            {"filename": archive.name, "sha256": sha256(archive), "redistribution_approved": False}
        ],
        "remaining": [
            "host native library and compiler source/build correspondence",
            "source selection and packaged validation for the exact final native candidates",
            "final component license review",
        ],
    }
    (output / "SOURCE-ASSETS.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Local review material only:", archive.name)


if __name__ == "__main__":
    prepare()
