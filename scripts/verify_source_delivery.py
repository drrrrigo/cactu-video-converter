"""Verify retained source bytes and report gaps; no network or publication."""

import argparse
import json
from pathlib import Path
from release_common import ROOT, read_json, sha256


def verify(root=ROOT):
    cache = root / "release/evidence/local/sources"
    qt = read_json(root / "release/qt-source-lock.json")
    ffmpeg = read_json(root / "release/ffmpeg-source-lock.json")
    entries = list(qt["archives"]) + [e for e in ffmpeg["inputs"] if e["status"] == "RETAINED"]
    verified = []
    for entry in entries:
        name = entry["filename"]
        if Path(name).name != name or sha256(cache / name) != entry["sha256"]:
            raise RuntimeError("Retained source missing or changed: " + name)
        verified.append({"filename": name, "sha256": entry["sha256"], "url": entry["url"]})
    return {
        "retained_verified": verified,
        "blocked_inputs": [e for e in ffmpeg["inputs"] if e["status"] != "RETAINED"],
        "complete_corresponding_source": False,
        "remaining": ffmpeg["remaining_build_requirements"]
        + [
            "Qt wheel build/third-party correspondence",
            "native OS source packages/patches",
            "complete static runtime source/relinking review",
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
