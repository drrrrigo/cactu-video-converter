"""Publication gates require real evidence; candidate builds do not imply approval."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from release_common import ROOT, read_json, sha256

MANUAL_SCENARIOS = {
    "windows11_installer": (
        "W01",
        "W02",
        "W03",
        "W04",
        "W05",
        "W06",
        "W08",
        "W09",
        "W10",
        "W11",
        "W12",
        "W13",
        "W16",
        "W17",
    ),
    "windows11_portable": ("W15",),
    "linux_desktop": (
        "L01",
        "L02",
        "L03",
        "L04",
        "L05",
        "L06",
        "L07",
        "L08",
        "L09",
        "L10",
        "L11",
        "L13",
        "L14",
        "L15",
    ),
}


def check_manual_record(platform: str, record: dict) -> None:
    fields = (
        ("tester", "test_date", "os_build")
        if platform.startswith("windows")
        else ("tester", "test_date", "distribution", "kernel", "display_stack")
    )
    if any(not isinstance(record.get(field), str) or not record[field].strip() for field in fields):
        raise RuntimeError("Manual tester/date/environment evidence is incomplete: " + platform)
    if any(
        record.get("scenario_results", {}).get(case) != "PASS"
        for case in MANUAL_SCENARIOS[platform]
    ):
        raise RuntimeError("Required manual scenario has not passed: " + platform)


def check_payload_evidence(artifacts: Path, commit: str) -> None:
    from checksums import expected_names

    reports = (
        "windows-x86_64-installed-payload.json",
        "windows-x86_64-portable-payload.json",
        "linux-x86_64-appimage-payload.json",
    )
    for report_name, filename in zip(reports, expected_names()):
        path = artifacts / report_name
        if not path.is_file():
            raise RuntimeError("Exact payload inventory missing: " + report_name)
        report = read_json(path)
        if (
            report.get("source_commit") != commit
            or report.get("final_rc") is not True
            or report.get("technical_license_complete") is not True
            or report.get("components_requiring_review") != 0
            or not report.get("files")
            or report.get("artifact", {}).get("filename") != filename
            or report.get("artifact", {}).get("sha256") != sha256(artifacts / filename)
            or not report.get("components")
            or any(
                c.get("review_status") not in {"TECHNICAL_EVIDENCE", "NOTICE_MATERIAL"}
                for c in report["components"]
            )
        ):
            raise RuntimeError(
                "Payload inventory is incomplete or differs from reviewed artifact: " + filename
            )


def source_commit(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise RuntimeError("No auditable Git commit is available")
    return value


def check_publication(
    artifacts: Path,
    *,
    root: Path = ROOT,
    evidence_path: Path | None = None,
    owner_approval_path: Path | None = None,
) -> None:
    config = read_json(root / "release/config.json")
    if (
        config.get("repository") != "https://github.com/drrrrigo/cactu-video-converter"
        or config.get("source_license") != "GPL-3.0-or-later"
    ):
        raise RuntimeError("Release identity/license decision is missing")
    if not owner_approval_path:
        raise RuntimeError(
            "Publication blocked: publication_approved requires an external owner attestation"
        )
    for gate in (
        "technical_license_audit_complete",
        "license_audit_approved",
        "security_audit_approved",
    ):
        if config.get(gate) is not True:
            raise RuntimeError("Publication blocked: " + gate)
    selected_baseline = root / "release/controlled-baseline.json"
    manifest = (
        {"selected-controlled-baseline": read_json(selected_baseline)}
        if selected_baseline.is_file()
        else read_json(root / "vendor/ffmpeg/manifest.json")
    )
    if not selected_baseline.is_file() and set(manifest) != {"linux-x86_64", "windows-x86_64"}:
        raise RuntimeError("Both exact platform FFmpeg manifests are required")
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
    owner = read_json(root / owner_approval_path)
    from checksums import expected_names
    from branding_metadata import __version__

    if evidence.get("source_commit") != source_commit(root):
        raise RuntimeError("Candidate was tested from a different source commit")
    if (
        owner.get("approved") is not True
        or owner.get("approved_by") != "drrrrigo"
        or not owner.get("approved_at")
        or owner.get("version") != __version__
        or owner.get("source_commit") != source_commit(root)
        or owner.get("artifacts") != evidence.get("artifacts")
    ):
        raise RuntimeError(
            "Explicit owner publication approval does not match the tested source/artifacts"
        )

    if set(evidence.get("artifacts", {})) != set(expected_names()):
        raise RuntimeError("Manual evidence must name the three exact beta artifacts")
    for platform in ("windows11_installer", "windows11_portable", "linux_desktop"):
        if evidence.get(platform, {}).get("passed") is not True:
            raise RuntimeError("Required manual platform test missing: " + platform)
        check_manual_record(platform, evidence[platform])
    for name, digest in evidence.get("artifacts", {}).items():
        path = artifacts / name
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError("Final artifact differs from manually tested candidate: " + name)
    if len(evidence.get("artifacts", {})) != 3:
        raise RuntimeError("All three exact release artifacts must be manually verified")
    check_payload_evidence(artifacts, source_commit(root))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ROOT / "dist/release")
    args = parser.parse_args()
    check_publication(args.artifacts)
