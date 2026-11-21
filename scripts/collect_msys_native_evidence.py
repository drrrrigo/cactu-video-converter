"""Attribute installed MSYS2 DLL bytes; this is not a shipped-payload inventory."""

import argparse
import json
from pathlib import Path

from release_common import sha256


def fields(path):
    data, key = {}, None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("%") and line.endswith("%"):
            key = line.strip("%")
            data[key] = []
        elif line and key:
            data[key].append(line)
    return data


def collect(msys, output):
    msys = msys.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files, packages = [], []
    for database in sorted((msys / "var/lib/pacman/local").iterdir()):
        desc, listing = database / "desc", database / "files"
        if not desc.is_file() or not listing.is_file():
            continue
        metadata = fields(desc)
        owned = fields(listing).get("FILES", [])
        dlls = [n for n in owned if n.startswith("ucrt64/bin/") and n.lower().endswith(".dll")]
        if not dlls:
            continue
        name, version = metadata["NAME"][0], metadata["VERSION"][0]
        record = {
            "name": name,
            "version": version,
            "base": metadata.get("BASE", [name])[0],
            "license_labels": metadata.get("LICENSE", []),
            "package_description_sha256": sha256(desc),
            "package_file_list_sha256": sha256(listing),
            "notices": [],
        }
        for relative in owned:
            source = (msys / relative).resolve()
            if not source.is_relative_to(msys):
                raise RuntimeError("Package evidence path escapes the installation")
            if relative in dlls and source.is_file():
                files.append(
                    {
                        "filename": source.name,
                        "sha256": sha256(source),
                        "package": name,
                        "version": version,
                        "package_base": record["base"],
                        "installed_path": relative,
                    }
                )
            if relative.startswith("ucrt64/share/licenses/") and source.is_file():
                dest = output / "notices" / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source.read_bytes())
                record["notices"].append(
                    {"file": dest.relative_to(output).as_posix(), "sha256": sha256(dest)}
                )
        packages.append(record)
    if not files:
        raise RuntimeError("No MSYS2 DLL ownership evidence found")
    report = {
        "scope": "Installed build-input DLL evidence only; join to actual payload by SHA-256 before declaring a component shipped",
        "files": files,
        "packages": packages,
        "source_correspondence_complete": False,
        "publication_approved": False,
    }
    (output / "msys-native-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Attributed installed DLLs:", len(files), "packages:", len(packages))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("msys", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    collect(args.msys, args.output)
