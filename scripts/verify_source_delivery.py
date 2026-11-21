"""Verify retained source bytes and report gaps; no network or publication."""

import argparse
import json
from pathlib import Path
from release_common import ROOT, read_json, sha256


def verify(root=ROOT):
    cache = root / "release/evidence/local/sources"
    qt = read_json(root / "release/qt-source-lock.json")
    ffmpeg = read_json(root / "release/ffmpeg-source-lock.json")
    ubuntu = read_json(root / "release/ubuntu-source-lock.json")
    runtime = read_json(root / "release/appimage-controlled-lock.json")
    entries = (
        list(qt["archives"])
        + [e for e in ffmpeg["inputs"] if e["status"] == "RETAINED"]
        + runtime["build_source_archives"]
        + runtime["static_upstream_sources"]
    )
    python_native_path = root / "release/python-native-source-lock.json"
    if python_native_path.is_file():
        entries += [
            e
            for e in read_json(python_native_path)["records"]
            if e["repository"].endswith("source-deps")
        ]
    icu_path = root / "release/qt-icu-source-lock.json"
    if icu_path.is_file():
        entries.append(read_json(icu_path))
    verified = []
    for entry in entries:
        name = entry["filename"]
        if Path(name).name != name or sha256(cache / name) != entry["sha256"]:
            raise RuntimeError("Retained source missing or changed: " + name)
        verified.append({"filename": name, "sha256": entry["sha256"], "url": entry["url"]})
    ubuntu_verified = []
    for package in ubuntu["source_packages"]:
        if package["status"] != "RETAINED":
            raise RuntimeError("Ubuntu source package not retained: " + package["source_package"])
        folder = root / "release/evidence/local/ubuntu-sources" / package["cache_subdirectory"]
        for entry in [package["dsc"], *package["parts"]]:
            name = entry["filename"]
            if Path(name).name != name or sha256(folder / name) != entry["sha256"]:
                raise RuntimeError("Ubuntu source part missing or changed: " + name)
        ubuntu_verified.append(
            {
                "source_package": package["source_package"],
                "source_version": package["source_version"],
            }
        )
    return {
        "retained_verified": verified,
        "ubuntu_source_packages_verified": ubuntu_verified,
        "blocked_inputs": [e for e in ffmpeg["inputs"] if e["status"] != "RETAINED"],
        "complete_corresponding_source": False,
        "remaining": ffmpeg["remaining_build_requirements"]
        + [
            "Qt wheel build/third-party correspondence",
            "per-file native library terms and replacement assessment",
            "final static runtime source/relinking license review (material retained and relink tested)",
            "recipient-accessible maintained source delivery",
        ],
        "delivery_strategy": "approved release source asset plus immutable source-index/hash manifest; no daily URLs as sole retention",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/source-delivery-index.json")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "Verified source archives:",
        len(result["retained_verified"]),
        "blocked inputs:",
        len(result["blocked_inputs"]),
    )
    if args.require_complete and not result["complete_corresponding_source"]:
        raise SystemExit("Source delivery blocked: corresponding-source closure is incomplete")
