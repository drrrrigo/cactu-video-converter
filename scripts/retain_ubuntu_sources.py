"""Retain exact source packages for libraries copied from the native Ubuntu runner."""

import argparse
import concurrent.futures
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from release_common import ROOT, read_json, sha256


def request_json(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)


def retrieve(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
        while data := response.read(1024 * 1024):
            output.write(data)
    partial.replace(target)


def acquire(item, cache):
    project, version = item
    result = {"source_package": project, "source_version": version, "status": "BLOCKED"}
    try:
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", project) or not re.fullmatch(
            r"[A-Za-z0-9.+:~_-]+", version
        ):
            raise ValueError("Unsafe source package name/version")
        query = {
            "ws.op": "getPublishedSources",
            "source_name": project,
            "version": version,
            "exact_match": "true",
        }
        entries = request_json(
            "https://api.launchpad.net/1.0/ubuntu/+archive/primary?" + urllib.parse.urlencode(query)
        )["entries"]
        matching = [
            e
            for e in entries
            if e.get("source_package_name") == project
            and e.get("source_package_version") == version
        ]
        if not matching:
            query["status"] = "Superseded"
            entries = request_json(
                "https://api.launchpad.net/1.0/ubuntu/+archive/primary?"
                + urllib.parse.urlencode(query)
            )["entries"]
            matching = [
                e
                for e in entries
                if e.get("source_package_name") == project
                and e.get("source_package_version") == version
            ]
        if not matching:
            raise RuntimeError(
                "Exact source publication not found; do not substitute another version"
            )
        publication = matching[0]
        urls = request_json(publication["self_link"] + "?ws.op=sourceFileUrls")
        by_name = {
            urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]): url
            for url in urls
        }
        name = next(n for n in by_name if n.endswith(".dsc"))
        if Path(name).name != name:
            raise ValueError("Unsafe source descriptor filename")
        folder = cache / project / version.replace(":", "_")
        dsc = folder / name
        if not dsc.exists():
            retrieve(by_name[name], dsc)
        text = dsc.read_text()
        section = text.split("Checksums-Sha256:\n", 1)[1]
        parts = []
        for line in section.splitlines():
            match = re.fullmatch(r" ([a-f0-9]{64})\s+(\d+)\s+(\S+)", line)
            if not match:
                break
            digest, size, filename = match.groups()
            if Path(filename).name != filename:
                raise RuntimeError("Unsafe source member name")
            target = folder / filename
            if not target.is_file() or sha256(target) != digest:
                retrieve(by_name[filename], target)
            if target.stat().st_size != int(size) or sha256(target) != digest:
                raise RuntimeError("Ubuntu source part differs from official dsc checksum")
            parts.append(
                {
                    "filename": filename,
                    "url": by_name[filename],
                    "sha256": digest,
                    "size": int(size),
                }
            )
        if not parts:
            raise RuntimeError("No SHA-256 source parts parsed from dsc")
        result.update(
            status="RETAINED",
            publication=publication["self_link"],
            cache_subdirectory=folder.relative_to(cache).as_posix(),
            dsc={"filename": name, "url": by_name[name], "sha256": sha256(dsc)},
            parts=parts,
            verification="exact Launchpad source version over HTTPS; parts match dsc SHA-256; PGP signature not independently verified",
        )
    except Exception as exc:
        result["reason"] = type(exc).__name__ + ": " + str(exc)
    print(project, version, result["status"], flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    inventory = read_json(args.payload)
    packages = sorted(
        {
            (c["project"], c["version"])
            for c in inventory["components"]
            if c.get("origin") == "build-host-debian-package"
        }
    )
    cache = ROOT / "release/evidence/local/ubuntu-sources"
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda p: acquire(p, cache), packages))
    report = {
        "inventory_source_commit": inventory["source_commit"],
        "artifact": inventory["artifact"],
        "source_packages": records,
        "publication_approved": False,
        "scope": "actual copied Ubuntu-library source packages, not FFmpeg/Qt wheel/static runtime closure",
    }
    (ROOT / "release/ubuntu-source-lock.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
