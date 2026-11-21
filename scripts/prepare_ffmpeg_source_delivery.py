"""Prepare a local, explicitly incomplete source bundle for candidate review."""

import json
import tarfile
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
            bundle.add(source, arcname="sources/" + entry["filename"])
        for name in [
            "scripts/build_controlled_ffmpeg.py",
            "release/ffmpeg-controlled-lock.json",
            "LICENSE",
        ]:
            bundle.add(ROOT / name, arcname=name)
    manifest = {
        "complete_corresponding_source": False,
        "assets": [
            {"filename": archive.name, "sha256": sha256(archive), "redistribution_approved": False}
        ],
        "remaining": [
            "host native library and compiler source/build correspondence",
            "native Windows build validation",
            "final component license review",
        ],
    }
    (output / "SOURCE-ASSETS.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Local review material only:", archive.name)


if __name__ == "__main__":
    prepare()
