"""Acquire immutable recipe source inputs; never certify binary/source correspondence."""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from release_common import ROOT, read_json, sha256

RECIPE = "7f2a6b1050d302144de8366afa37a75e46f326aa"
GIT_HOSTS = {
    "github.com",
    "git.code.sf.net",
    "git.savannah.gnu.org",
    "gitlab.com",
    "gitlab.freedesktop.org",
    "code.videolan.org",
    "aomedia.googlesource.com",
    "chromium.googlesource.com",
}


def trusted_git(repo):
    parsed = urllib.parse.urlsplit(repo)
    return (
        parsed.scheme == "https"
        and parsed.hostname in GIT_HOSTS
        and not parsed.username
        and not parsed.password
    )


def resolve_version_tag(entry):
    tag = entry["revision"]
    if not re.fullmatch(r"(?:v?\d+\.\d+(?:\.\d+)?|openssl-\d+\.\d+\.\d+|R\d+)", tag):
        raise ValueError("Only explicit release-version tags may be resolved")
    match = re.fullmatch(r"https://github.com/([\w.-]+)/([\w.-]+?)(?:\.git)?", entry["repo"])
    if not match:
        raise ValueError("Version tag needs a supported upstream tag API")
    url = f"https://api.github.com/repos/{match[1]}/{match[2]}/git/ref/tags/" + urllib.parse.quote(
        tag, safe=""
    )
    with urllib.request.urlopen(url, timeout=45) as response:
        obj = json.load(response)["object"]
    tag_object = obj["sha"]
    for _ in range(4):
        if obj["type"] == "commit":
            entry.update(
                declared_revision=tag,
                revision=obj["sha"],
                tag_object_sha=tag_object,
                source_method="archive",
                url=archive_url(entry["repo"], obj["sha"]),
            )
            return
        if obj["type"] != "tag":
            break
        with urllib.request.urlopen(obj["url"], timeout=45) as response:
            obj = json.load(response)["object"]
    raise ValueError("Tag did not resolve to one immutable commit")


def export_git(entry, cache, partial):
    repo = entry.get("fetch_repo", entry["repo"])
    if not trusted_git(repo) or not re.fullmatch(r"[a-f0-9]{40}", entry["revision"]):
        raise ValueError("Exact commit and reviewed HTTPS Git host are required")
    objects = cache.parent / "git-source-objects" / entry["filename"].removesuffix(".tar.gz")
    objects.mkdir(parents=True, exist_ok=True)

    def git(*args):
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=objects,
            capture_output=True,
            check=True,
            timeout=120,
        )

    if not (objects / "HEAD").exists():
        git("init", "--bare")
    try:
        git("cat-file", "-e", entry["revision"] + "^{commit}")
    except subprocess.CalledProcessError:
        git("fetch", "--depth=1", repo, entry["revision"])
    commit = git("rev-parse", entry["revision"] + "^{commit}").stdout.decode().strip()
    if commit != entry["revision"]:
        raise ValueError("Fetched Git object differs from the recipe commit")
    entry["unretained_gitlink_inputs"] = [
        line
        for line in git("ls-tree", "-r", commit).stdout.decode().splitlines()
        if line.startswith("160000 ")
    ]
    tar = objects / "source.tar"
    with tar.open("wb") as output:
        subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "archive",
                "--format=tar",
                "--prefix=source/",
                commit,
            ],
            cwd=objects,
            stdout=output,
            check=True,
            timeout=120,
        )
    with tar.open("rb") as source, partial.open("wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as zipped:
            shutil.copyfileobj(source, zipped)
    tar.unlink()


def export_svn(entry, cache, partial):
    parsed = urllib.parse.urlsplit(entry["repo"])
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"svn.code.sf.net", "svn.xvid.org"}
        or not entry["revision"].isdigit()
    ):
        raise ValueError("Reviewed HTTPS SVN host and exact numeric revision are required")
    if shutil.which("svn") is None:
        raise RuntimeError(
            "Exact SVN revision identified; an isolated SVN export client is required"
        )
    with tempfile.TemporaryDirectory(dir=cache.resolve().parent) as folder:
        checkout = Path(folder) / "source"
        subprocess.run(
            [
                "svn",
                "export",
                "--non-interactive",
                "--ignore-externals",
                "-r",
                entry["revision"],
                entry["repo"] + "@" + entry["revision"],
                str(checkout),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )

        def normalize(info):
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            return info

        with (
            partial.open("wb") as output,
            gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped,
        ):
            with tarfile.open(fileobj=zipped, mode="w|") as archive:
                archive.add(checkout, arcname="source", filter=normalize)
    entry["svn_externals_ignored"] = True


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
            values = dict(
                re.findall(r'^\s*(SCRIPT_(?:REPO|COMMIT|REV|MIRROR)\d*)="([^"\n]+)"', script, re.M)
            )
            for variable, repo in values.items():
                if not variable.startswith("SCRIPT_REPO"):
                    continue
                revision = values.get(variable.replace("REPO", "COMMIT"), "") or values.get(
                    variable.replace("REPO", "REV"), ""
                )
                entry = {
                    "recipe_file": member.name.split("/", 1)[1],
                    "repo": repo,
                    "revision": revision,
                    "source_role": "recipe input superset; actual linked inclusion not established",
                }
                entry["filename"] = (
                    Path(member.name).stem
                    + "-"
                    + variable.removeprefix("SCRIPT_REPO")
                    + "-"
                    + revision
                    + ".tar.gz"
                )
                try:
                    entry["url"] = archive_url(repo, revision)
                    entry["status"] = "NOT_RETAINED"
                    entry["source_method"] = "archive"
                except ValueError as exc:
                    mirror = values.get(variable.replace("REPO", "MIRROR"), "")
                    if revision.isdigit() and repo.startswith("https://svn."):
                        entry.update(status="NOT_RETAINED", source_method="svn-export", url=repo)
                    elif re.fullmatch(r"[a-f0-9]{40}", revision) and trusted_git(repo):
                        entry.update(status="NOT_RETAINED", source_method="git-export", url=repo)
                        if trusted_git(mirror):
                            entry["fetch_repo"] = mirror
                    elif repo.startswith("https://github.com/") and re.fullmatch(
                        r"(?:v?\d+\.\d+(?:\.\d+)?|openssl-\d+\.\d+\.\d+|R\d+)", revision
                    ):
                        entry.update(status="NOT_RETAINED", source_method="version-tag", url=repo)
                    else:
                        entry.update(status="BLOCKED", reason=str(exc))
                result.append(entry)
    return result


def acquire(entry, cache, retained=None):
    entry = dict(entry)
    if entry["status"] == "BLOCKED":
        return entry
    target = cache / entry["filename"]
    partial = target.with_suffix(".partial")
    try:
        if retained and retained.get("status") == "RETAINED":
            # Preserve resolved tags/export metadata and verify bytes against the
            # existing lock. Re-running must never silently repin a moved tag or
            # bless a modified local archive with a new hash.
            declared = retained.get("declared_revision", retained["revision"])
            if retained["repo"] != entry["repo"] or declared != entry["revision"]:
                raise ValueError("Retained source identity differs from the recipe")
            if target.is_file():
                if sha256(target) != retained["sha256"]:
                    raise ValueError("Retained source archive changed; refusing to relock")
                return dict(retained)
            entry = dict(retained)
        if entry.get("source_method") == "version-tag":
            resolve_version_tag(entry)
        if not target.exists():
            if entry.get("source_method") == "git-export":
                export_git(entry, cache, partial)
                partial.replace(target)
            elif entry.get("source_method") == "svn-export":
                export_svn(entry, cache, partial)
                partial.replace(target)
            else:
                request = urllib.request.Request(
                    entry["url"], headers={"User-Agent": "Cactu-source-audit"}
                )
                limit = (
                    1024
                    if entry["repo"] == "https://github.com/GPUOpen-LibrariesAndSDKs/AMF.git"
                    else 256
                )
                try:
                    with (
                        urllib.request.urlopen(request, timeout=60) as response,
                        partial.open("wb") as out,
                    ):
                        size = 0
                        while data := response.read(1024 * 1024):
                            size += len(data)
                            if size > limit * 1024 * 1024:
                                raise ValueError("Archive exceeds bounded acquisition size")
                            out.write(data)
                except OSError:
                    if not trusted_git(entry["repo"]):
                        raise
                    partial.unlink(missing_ok=True)
                    export_git(entry, cache, partial)
                    entry["source_method"] = "git-export"
                    entry["archive_url_attempted"] = entry["url"]
                    entry["url"] = entry["repo"]
                partial.replace(target)
        if retained and retained.get("status") == "RETAINED":
            if sha256(target) != retained["sha256"]:
                target.unlink()
                raise ValueError("Reacquired source differs from the retained lock")
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
        previous_path = ROOT / "release/ffmpeg-source-lock.json"
        previous = read_json(previous_path) if previous_path.is_file() else {}
        retained = {
            e["filename"]: e
            for e in previous.get("inputs", [])
            if previous.get("recipe_commit") == RECIPE
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
            inputs = list(
                workers.map(lambda e: acquire(e, cache, retained.get(e["filename"])), inputs)
            )
    result = {
        "recipe_commit": RECIPE,
        "recipe_sha256": sha256(archive),
        "inputs": inputs,
        "binary_correspondence_complete": False,
        "controlled_build_complete": False,
        "remaining_build_requirements": [
            "use observed pinned toolchain images from ffmpeg-provider-build-evidence.json; retain all generated/vendored inputs",
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
