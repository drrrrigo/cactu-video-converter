"""Acquire only locked candidate sources, without executing upstream code."""

import argparse
from release_common import ROOT, read_json, download


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("target", choices=["linux-x86_64", "windows-x86_64"])
    args = p.parse_args()
    for entry in read_json(ROOT / "release/ffmpeg-controlled-lock.json")["sources"]:
        if entry["project"] == "AMF" and args.target.startswith("linux"):
            continue
        print("Verify locked source:", entry["project"], entry["filename"], flush=True)
        download(
            entry["url"],
            entry["sha256"],
            ROOT / "release/evidence/local/sources" / entry["filename"],
        )
