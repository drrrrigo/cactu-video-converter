"""Integrate supplier notices for exact MSYS DLL bytes actually in the payload."""

import json
import shutil
import sys
from pathlib import Path

from release_common import ROOT, read_json, sha256


def integrate(payload, evidence_file, root=ROOT, python_root=None):
    evidence = read_json(evidence_file)
    policy = read_json(root / "release/msys-runtime-obligations.json")
    by_hash = {e["sha256"]: e for e in evidence["files"]}
    known_names = {e["filename"].lower() for e in evidence["files"]}
    packages = {(p["name"], p["version"]): p for p in evidence["packages"]}
    records, retained, other_suppliers = [], {}, []
    python_root = python_root or Path(sys.base_prefix)
    for file in sorted(payload.rglob("*.dll")):
        match = by_hash.get(sha256(file))
        if not match:
            if file.name.lower() in known_names:
                supplier_files = [python_root / "DLLs" / file.name, python_root / file.name]
                if not any(p.is_file() and sha256(p) == sha256(file) for p in supplier_files):
                    raise RuntimeError(
                        "MSYS DLL name matches but bytes differ and no alternate supplier is proven: "
                        + file.name
                    )
                other_suppliers.append(
                    {
                        "path": file.relative_to(payload).as_posix(),
                        "sha256": sha256(file),
                        "supplier": "CPython " + sys.version.split()[0],
                    }
                )
            continue
        package = packages[(match["package"], match["version"])]
        short = package["name"].removeprefix("mingw-w64-ucrt-x86_64-")
        if short not in policy:
            raise RuntimeError("No reviewed runtime-license classification for " + short)
        notices = []
        for notice in package["notices"]:
            relative = Path(notice["file"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe supplier notice path")
            source = (evidence_file.parent / relative).resolve()
            if (
                not source.is_relative_to(evidence_file.parent.resolve())
                or sha256(source) != notice["sha256"]
            ):
                raise RuntimeError("Supplier notice missing or changed")
            name = relative.as_posix().split("share/licenses/", 1)[1]
            target = payload / "_internal/licenses/native-msys2" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            notices.append(
                {"path": target.relative_to(payload).as_posix(), "sha256": sha256(target)}
            )
        if not notices:
            raise RuntimeError("Required MSYS notices absent for " + short)
        record = {
            "path": file.relative_to(payload).as_posix(),
            "sha256": sha256(file),
            "package": package["name"],
            "version": package["version"],
            "source_package": package["base"],
            **policy[short],
            "notices": notices,
        }
        records.append(record)
        retained[record["sha256"]] = record
    report = {
        "scope": "Only hash-matched DLLs in this actual payload; build-only packages excluded",
        "files": records,
        "other_supplier_files": other_suppliers,
        "license_audit_approved": False,
        "publication_approved": False,
    }
    destination = root / "build/msys-payload-notices.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    # Ship the mapping beside the exact notices; re-inventory after integration.
    (payload / "_internal/licenses/native-msys2").mkdir(parents=True, exist_ok=True)
    (payload / "_internal/licenses/native-msys2/FILE-MAP.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return retained
