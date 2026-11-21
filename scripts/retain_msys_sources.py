"""Retain exact MSYS2 source-only archives for SHA-attributed native packages."""

import argparse
import concurrent.futures
import hashlib
import json
import re
import tarfile
import urllib.request
from pathlib import Path

from release_common import ROOT, sha256

BASE = "https://repo.msys2.org/mingw/sources/"


def inspect_source(record, cache):
    with tarfile.open(cache / record["archive"]["filename"], "r:*") as archive:
        members = archive.getmembers()
        metadata = next(m for m in members if m.name.endswith("/.SRCINFO"))
        fields = {}
        for line in archive.extractfile(metadata).read().decode().splitlines():
            if " = " in line:
                key, value = line.split("=", 1)
                fields.setdefault(key.strip(), []).append(value.strip())
        version = fields["pkgver"][0] + "-" + fields["pkgrel"][0]
        if fields.get("epoch", ["0"])[0] != "0":
            version = fields["epoch"][0] + ":" + version
        if version != record["version"] or fields["pkgbase"][0] != record["base"]:
            raise RuntimeError("Source archive identity differs from installed package")
        files = []
        for member in members:
            if not member.isfile():
                continue
            digest = hashlib.sha256()
            with archive.extractfile(member) as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            files.append({"file": member.name, "size": member.size, "sha256": digest.hexdigest()})
        record["archive_members_verified"] = files
        record["srcinfo_identity_matches"] = True
    return record


def retain(join_file, output):
    join = json.loads(join_file.read_text())
    cache = ROOT / "release/evidence/local/msys-sources"
    cache.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BASE, timeout=60) as response:
        names = set(re.findall(r'href="([^"/]+)"', response.read().decode()))
    previous = json.loads(output.read_text()) if output.is_file() else {"source_packages": []}
    locked = {(p["base"], p["version"]): p for p in previous["source_packages"]}

    def acquire(identity):
        base, version = identity
        if not re.fullmatch(r"[a-z0-9+.-]+", base + version):
            raise RuntimeError("Unsafe MSYS2 package identity")
        record = locked.get(identity)
        if record:
            for item in [record["archive"], record["signature"]]:
                if sha256(cache / item["filename"]) != item["sha256"]:
                    raise RuntimeError("Retained MSYS2 source bytes changed")
            return inspect_source(record, cache)
        matches = [
            n
            for n in names
            if n.startswith(base + "-" + version + ".src.tar.") and not n.endswith(".sig")
        ]
        if len(matches) != 1:
            raise RuntimeError("Exact MSYS2 source archive unavailable/ambiguous: " + str(identity))
        files = []
        for name in [matches[0], matches[0] + ".sig"]:
            destination = cache / name
            temporary = destination.with_suffix(destination.suffix + ".partial")
            with (
                urllib.request.urlopen(BASE + name, timeout=120) as response,
                temporary.open("wb") as target,
            ):
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
            temporary.replace(destination)
            files.append(
                {
                    "filename": name,
                    "url": BASE + name,
                    "sha256": sha256(destination),
                    "size": destination.stat().st_size,
                }
            )
        print(base, version, "retained", flush=True)
        return inspect_source(
            {
                "base": base,
                "version": version,
                "archive": files[0],
                "signature": files[1],
                "verification": "Exact version-named source-only archive from official HTTPS repository; SHA-256 locked locally. Detached signature retained, not independently verified. Contents/build correspondence and license review remain required.",
            },
            cache,
        )

    identities = sorted({(p["base"], p["version"]) for p in join["packages"]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        packages = list(pool.map(acquire, identities))
    output.write_text(
        json.dumps(
            {
                "scope": "Source retention for exact byte-attributed MSYS2 package identities in the referenced audit payload; not every build-input package is shipped.",
                "payload_artifact": join["payload_artifact"],
                "source_packages": packages,
                "complete_corresponding_source": False,
                "publication_approved": False,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("join", type=Path)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "release/controlled-msys-source-lock.json"
    )
    args = parser.parse_args()
    retain(args.join, args.output)
