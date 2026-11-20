"""Compare exact extracted payloads; provenance resolution is not license approval."""

from pathlib import Path


def compare_payloads(before, after):
    old = {f["path"]: f for f in before["files"]}
    new = {f["path"]: f for f in after["files"]}
    old_components = {c["id"]: c for c in before["components"]}
    new_components = {c["id"]: c for c in after["components"]}

    def unresolved(files, components):
        return sorted(
            p
            for p, f in files.items()
            if components[f["component_id"]].get("project") == "UNRESOLVED"
        )

    previous = unresolved(old, old_components)
    current = unresolved(new, new_components)
    return {
        "before_artifact": before["artifact"],
        "after_artifact": after["artifact"],
        "before_source_commit": before["source_commit"],
        "after_source_commit": after["source_commit"],
        "before_file_count": len(old),
        "after_file_count": len(new),
        "removed": sorted(old.keys() - new.keys()),
        "added": sorted(new.keys() - old.keys()),
        "changed_bytes": sorted(
            p for p in old.keys() & new.keys() if old[p]["sha256"] != new[p]["sha256"]
        ),
        "previously_unresolved": previous,
        "still_unresolved": current,
        "provenance_resolved": [
            {
                "path": p,
                "same_bytes": old[p]["sha256"] == new[p]["sha256"],
                "origin": new_components[new[p]["component_id"]],
            }
            for p in previous
            if p in new and p not in current
        ],
        "components_still_requiring_review": after["components_requiring_review"],
        "license_approval": False,
    }


def write_comparisons(output: Path, root: Path, target: str):
    import json

    baseline = (
        root
        / "release/evidence/beta1-audit-eabc092"
        / ("windows" if target.startswith("windows") else "linux")
    )
    for report in output.glob(target + "-*-payload.json"):
        previous = baseline / report.name
        if previous.is_file():
            result = compare_payloads(
                json.loads(previous.read_text()), json.loads(report.read_text())
            )
            report.with_name(report.name.replace("-payload.json", "-comparison.json")).write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
