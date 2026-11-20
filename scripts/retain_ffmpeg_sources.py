"""Acquire immutable recipe source inputs; never certify binary/source correspondence."""

import argparse
import concurrent.futures
import hashlib
import json
import re
import tarfile
import urllib.request
from pathlib import Path
from release_common import ROOT, read_json, sha256

RECIPE = "7f2a6b1050d302144de8366afa37a75e46f326aa"


def archive_url(repo, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Mutable/non-commit source ref requires explicit resolution")
    match = re.fullmatch(r"https://github.com/([\w.-]+)/([\w.-]+?)(?:\.git)?", repo)
    if match:
        return f"https://codeload.github.com/{match[1]}/{match[2]}/tar.gz/{revision}"
    match = re.fullmatch(
        r"https://(gitlab\.freedesktop\.org|code\.videolan\.org)/([\w./-]+?)(?:\.git)?", repo
    )
    if match:
        name = match[2].rsplit("/", 1)[-1]
        return f"https://{match[1]}/{match[2]}/-/archive/{revision}/{name}-{revision}.tar.gz"
    raise ValueError("Source host requires a verified archive retrieval adapter")


def recipe_inputs(archive):
    result = []
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if (
                not member.isfile()
                or "/scripts.d/" not in member.name
                or not member.name.endswith(".sh")
            ):
                continue
            script = bundle.extractfile(member).read().decode()
            values = dict(re.findall(r'^\s*(SCRIPT_(?:REPO|COMMIT)\d*)="([^"\n]+)"', script, re.M))
            for variable, repo in values.items():
                if not variable.startswith("SCRIPT_REPO"):
                    continue
                revision = values.get(variable.replace("REPO", "COMMIT"), "")
                entry = {
                    "recipe_file": member.name.split("/", 1)[1],
                    "repo": repo,
                    "revision": revision,
                    "source_role": "recipe input superset; actual linked inclusion not established",
                }
                try:
                    entry["url"] = archive_url(repo, revision)
                    entry["status"] = "NOT_RETAINED"
                    entry["filename"] = (
                        Path(member.name).stem
                        + "-"
                        + variable.removeprefix("SCRIPT_REPO")
                        + "-"
                        + revision
                        + ".tar.gz"
                    )
                except ValueError as exc:
                    entry["status"] = "BLOCKED"
                    entry["reason"] = str(exc)
                result.append(entry)
    return result


def acquire(entry, cache):
    entry = dict(entry)
    if entry["status"] == "BLOCKED":
        return entry
    target = cache / entry["filename"]
    partial = target.with_suffix(".partial")
    try:
        if not target.exists():
            request = urllib.request.Request(
                entry["url"], headers={"User-Agent": "Cactu-source-audit"}
            )
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
                size = 0
                while data := response.read(1024 * 1024):
                    size += len(data)
                    if size > 256 * 1024 * 1024:
                        raise ValueError(
                            "Archive exceeds acquisition bound; retain separately with explicit hash"
                        )
                    out.write(data)
            partial.replace(target)
        with tarfile.open(target) as source:
            members = [m for m in source.getmembers() if m.isfile()]
            if not members:
                raise ValueError("Empty source archive")
            entry["license_files"] = [
                {
                    "file": m.name.split("/", 1)[-1],
                    "sha256": hashlib.sha256(source.extractfile(m).read()).hexdigest(),
                }
                for m in members
                if m.size < 256 * 1024
                and m.name.count("/") < 3
                and Path(m.name)
                .name.lower()
                .startswith(("license", "copying", "notice", "copyright"))
            ]
        entry.update(status="RETAINED", sha256=sha256(target), size=target.stat().st_size)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        entry.update(status="BLOCKED", reason=type(exc).__name__ + ": " + str(exc))
    print(Path(entry["recipe_file"]).name, entry["status"], flush=True)
    return entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    cache = ROOT / "release/evidence/local/sources"
    cache.mkdir(parents=True, exist_ok=True)
    evidence = read_json(ROOT / "release/source-evidence.json")
    recipe = next(e for e in evidence["sources"] if e.get("source_commit") == RECIPE)
    archive = cache / recipe["retained_local_file"]
    if sha256(archive) != recipe["sha256"]:
        raise RuntimeError("Exact recipe source hash mismatch")
    inputs = recipe_inputs(archive)
    if args.download:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
            inputs = list(workers.map(lambda e: acquire(e, cache), inputs))
    result = {
        "recipe_commit": RECIPE,
        "recipe_sha256": sha256(archive),
        "inputs": inputs,
        "binary_correspondence_complete": False,
        "controlled_build_complete": False,
        "remaining_build_requirements": [
            "pin toolchain/base images and all non-git/generated/vendored inputs",
            "resolve blocked source inputs",
            "build and validate natively on Windows and Linux",
            "retain actual build logs/configuration/patches/notices and relinking material",
        ],
    }
    (ROOT / "release/ffmpeg-source-lock.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
