"""Validate candidate distribution and exact tested-artifact promotion policies."""

import argparse
import json
import os
from pathlib import Path
from release_common import ROOT, read_json
from release_gate import check_publication
from branding_metadata import __version__


def distribution_allowed(root=ROOT):
    config = read_json(root / "release/config.json")
    if config.get("technical_license_audit_complete") is not True:
        raise RuntimeError(
            "Binary distribution blocked: technical dependency/source review is incomplete"
        )
    if config.get("license_audit_approved") is not True:
        raise RuntimeError(
            "Binary distribution blocked: exact dependency/license/source audit not approved"
        )
    baseline = root / "release/controlled-baseline.json"
    if baseline.is_file():
        entry = read_json(baseline)
        if (
            entry.get("redistribution_approved") is not True
            or entry.get("corresponding_source_complete") is not True
        ):
            raise RuntimeError(
                "Binary distribution blocked: selected controlled baseline source/license approval incomplete"
            )
        return
    manifest = read_json(root / "vendor/ffmpeg/manifest.json")
    if set(manifest) != {"linux-x86_64", "windows-x86_64"}:
        raise RuntimeError(
            "Binary distribution blocked: both exact platform manifests are required"
        )
    for entry in manifest.values():
        if (
            entry.get("redistribution_approved") is not True
            or entry.get("corresponding_source_complete") is not True
        ):
            raise RuntimeError(
                "Binary distribution blocked: corresponding FFmpeg/linked-component sources are incomplete"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "dist/release")
    args = parser.parse_args()
    distribution_allowed()
    if args.publish:
        if os.environ.get("GITHUB_REF") != "refs/tags/v" + __version__:
            raise RuntimeError("Tag does not match the central release version")
        raw = os.environ.get("BETA_MANUAL_EVIDENCE", "")
        if not raw:
            raise RuntimeError(
                "Manual evidence is missing from the protected public-beta environment"
            )
        evidence = json.loads(raw)
        target = ROOT / "build/manual-promotion.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(evidence))
        approval_raw = os.environ.get("BETA_OWNER_APPROVAL", "")
        if not approval_raw:
            raise RuntimeError(
                "Explicit owner publication approval is missing from the protected environment"
            )
        approval = ROOT / "build/owner-publication-approval.json"
        approval.write_text(json.dumps(json.loads(approval_raw)))
        check_publication(args.artifacts, evidence_path=target, owner_approval_path=approval)
