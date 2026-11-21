"""Join installed MSYS2 evidence to actual shipped bytes without rewriting inventories."""

import argparse
import json
import shutil
from pathlib import Path

from release_common import sha256


def join(payload_file, evidence_file, output, source_lock=None):
    payload = json.loads(payload_file.read_text())
    evidence = json.loads(evidence_file.read_text())
    packages = {(p["name"], p["version"]): p for p in evidence["packages"]}
    sources = {}
    if source_lock:
        sources = {
            (p["base"], p["version"]): p
            for p in json.loads(source_lock.read_text())["source_packages"]
        }
    by_hash = {}
    for file in evidence["files"]:
        by_hash.setdefault(file["sha256"], []).append(file)
    matches, used, unresolved = [], set(), []
    for file in payload["files"]:
        if file["type"] != "native":
            continue
        candidates = by_hash.get(file["sha256"], [])
        identities = {(f["package"], f["version"]) for f in candidates}
        if len(identities) == 1:
            package, version = next(iter(identities))
            used.add((package, version))
            matches.append(
                {
                    "path": file["path"],
                    "sha256": file["sha256"],
                    "package": package,
                    "version": version,
                    "matching_installed_paths": [c["installed_path"] for c in candidates],
                }
            )
        elif candidates:
            raise RuntimeError("Ambiguous byte ownership for " + file["path"])
        elif not (file.get("copy_source_evidence") or {}).get("distribution"):
            unresolved.append({"path": file["path"], "sha256": file["sha256"]})
    output.mkdir(parents=True, exist_ok=True)
    retained = []
    for key in sorted(used):
        package = dict(packages[key])
        source = sources.get((package.get("base", package["name"]), package["version"]))
        package["retained_source_archive"] = source["archive"] if source else None
        package["source_identity_matches_SRCINFO"] = bool(
            source and source.get("srcinfo_identity_matches")
        )
        for notice in package["notices"]:
            relative = Path(notice["file"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe notice path")
            source = (evidence_file.parent / notice["file"]).resolve()
            if (
                not source.is_relative_to(evidence_file.parent.resolve())
                or sha256(source) != notice["sha256"]
            ):
                raise RuntimeError("Invalid installed notice evidence: " + notice["file"])
            target = output / notice["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        retained.append(package)
    report = {
        "scope": "SHA-256 byte-ownership joins only. Package notices are retained evidence, not a completed license/source review.",
        "payload_artifact": payload["artifact"],
        "payload_inventory_sha256": sha256(payload_file),
        "installed_evidence_sha256": sha256(evidence_file),
        "matches": matches,
        "packages": retained,
        "unattributed_native_files": unresolved,
        "complete_corresponding_source": False,
        "publication_approved": False,
    }
    (output / "payload-msys-join.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("installed_evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-lock", type=Path)
    args = parser.parse_args()
    result = join(args.payload, args.installed_evidence, args.output, args.source_lock)
    print(
        "Exact byte joins:",
        len(result["matches"]),
        "remaining without distribution:",
        len(result["unattributed_native_files"]),
    )
