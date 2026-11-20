"""Retain notices from hash-verified immutable Qt archives, without claiming inclusion."""

import json
import posixpath
import tarfile
from pathlib import Path
from release_common import ROOT, read_json, sha256


def collect(root=ROOT):
    lock = read_json(root / "release/qt-source-lock.json")
    output = root / "licenses/qt-6.11.2"
    provenance, errors = [], []
    for entry in lock["archives"]:
        archive = root / "release/evidence/local/sources" / entry["filename"]
        if sha256(archive) != entry["sha256"]:
            raise RuntimeError("Qt source archive hash mismatch: " + entry["project"])
        with tarfile.open(archive) as bundle:
            files = {m.name: m for m in bundle.getmembers() if m.isfile()}
            base = next(iter(files)).split("/")[0]
            notices = {
                n
                for n in files
                if n.startswith(base + "/LICENSES/")
                or n.count("/") == 1
                and Path(n).name.lower().startswith(("license", "copying"))
            }
            records = []
            for name, member in files.items():
                if (
                    not name.endswith("qt_attribution.json")
                    or "/tests/" in name
                    or "/examples/" in name
                ):
                    continue
                notices.add(name)
                try:
                    data = json.loads(bundle.extractfile(member).read(), strict=False)
                except (ValueError, UnicodeError):
                    errors.append(
                        {"project": entry["project"], "file": name.removeprefix(base + "/")}
                    )
                    continue
                for record in data if isinstance(data, list) else [data]:
                    if not isinstance(record, dict):
                        continue
                    attrs = {
                        k: record[k]
                        for k in [
                            "Id",
                            "Name",
                            "Version",
                            "License",
                            "LicenseId",
                            "QtUsage",
                            "QtParts",
                            "Homepage",
                        ]
                        if k in record
                    }
                    attrs["source_file"] = name.removeprefix(base + "/")
                    records.append(attrs)
                    values = record.get("LicenseFile", [])
                    for value in [values] if isinstance(values, str) else values:
                        candidate = posixpath.normpath(
                            posixpath.join(posixpath.dirname(name), value)
                        )
                        if candidate.startswith(base + "/") and candidate in files:
                            notices.add(candidate)
            for name in sorted(notices):
                relative = name.removeprefix(base + "/")
                destination = output / entry["project"] / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(bundle.extractfile(files[name]).read())
                provenance.append(
                    {
                        "project": entry["project"],
                        "source_commit": entry["commit"],
                        "source_file": relative,
                        "packaged_file": destination.relative_to(root).as_posix(),
                        "sha256": sha256(destination),
                    }
                )
            (output / entry["project"] / "upstream-attributions.json").write_text(
                json.dumps(records, indent=2) + "\n", encoding="utf-8"
            )
    result = {
        "version": "6.11.2",
        "source_lock": "release/qt-source-lock.json",
        "scope": "notice superset for selected source modules, not proof all listed third parties ship",
        "binary_build_correspondence": False,
        "unparsed_attributions": errors,
        "files": provenance,
    }
    (output / "provenance.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "Retained Qt source notices:", len(provenance), "unparsed attribution records:", len(errors)
    )


if __name__ == "__main__":
    collect()
