"""Publication gates require real evidence; candidate builds do not imply approval."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from release_common import ROOT, read_json, sha256


def source_commit(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise RuntimeError("No auditable Git commit is available")
    return value


def check_publication(
    artifacts: Path, *, root: Path = ROOT, evidence_path: Path | None = None
) -> None:
    config = read_json(root / "release/config.json")
    if (
        config.get("repository") != "https://github.com/drrrrigo/cactu-video-converter"
        or config.get("source_license") != "GPL-3.0-or-later"
    ):
        raise RuntimeError("Release identity/license decision is missing")
    for gate in ("publication_approved", "license_audit_approved", "security_audit_approved"):
        if config.get(gate) is not True:
            raise RuntimeError("Publication blocked: " + gate)
    manifest = read_json(root / "vendor/ffmpeg/manifest.json")
    if any(
        e.get("redistribution_approved") is not True
        or e.get("corresponding_source_complete") is not True
        for e in manifest.values()
    ):
        raise RuntimeError("FFmpeg corresponding-source / redistribution review is incomplete")
    evidence_path = evidence_path or config.get("manual_candidate_evidence")
    if not evidence_path:
        raise RuntimeError("Exact candidate artifact manual-test evidence is missing")
    evidence = read_json(root / evidence_path)
    from checksums import expected_names

    if set(evidence.get("artifacts", {})) != set(expected_names()):
        raise RuntimeError("Manual evidence must name the three exact beta artifacts")
    if evidence.get("source_commit") != source_commit(root):
        raise RuntimeError("Candidate was tested from a different source commit")
    for platform in ("windows11_installer", "windows11_portable", "linux_desktop"):
        if evidence.get(platform, {}).get("passed") is not True:
            raise RuntimeError("Required manual platform test missing: " + platform)
    for name, digest in evidence.get("artifacts", {}).items():
        path = artifacts / name
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError("Final artifact differs from manually tested candidate: " + name)
    if len(evidence.get("artifacts", {})) != 3:
        raise RuntimeError("All three exact release artifacts must be manually verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "dist/release")
    args = parser.parse_args()
    check_publication(args.artifacts)
