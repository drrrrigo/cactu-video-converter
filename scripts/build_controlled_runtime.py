"""Build the selected AppImage stub from locked inputs in an offline namespace."""

import concurrent.futures
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from release_common import ROOT, download, read_json, sha256


def build(root=ROOT):
    lock = read_json(root / "release/appimage-controlled-lock.json")
    recipe = root / "scripts/build_controlled_appimage_runtime.sh"
    if sha256(recipe) != lock["build_recipe_sha256"]:
        raise RuntimeError("Controlled runtime build recipe changed; review and relock it")
    work = Path(
        os.environ.get("CACTU_RUNTIME_BUILD_ROOT", root / "build/controlled-runtime")
    ).resolve()
    work.mkdir(parents=True, exist_ok=True)
    base = lock["base"]
    archive = download(base["url"], base["sha256"], work / "alpine-minirootfs.tar.gz")
    sources = root / "release/evidence/local/sources"
    for entry in lock["build_source_archives"]:
        download(entry["url"], entry["sha256"], sources / entry["filename"])

    def acquire(package):
        target = work / "apks" / package["filename"]
        if target.is_file() and sha256(target) == package["sha256"]:
            return
        for repository in ("main", "community"):
            url = (
                "https://dl-cdn.alpinelinux.org/alpine/v3.21/"
                + repository
                + "/x86_64/"
                + package["filename"]
            )
            try:
                download(url, package["sha256"], target)
                return
            except OSError:
                continue
        raise RuntimeError("Pinned build APK unavailable: " + package["filename"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(acquire, lock["packages"]))
    sysroot = work / "rootfs"
    sysroot.mkdir(exist_ok=True)
    if not (sysroot / "bin/busybox").exists():
        # Deliberate OS-image handling: this exact hash-verified rootfs contains
        # absolute in-root symlinks. It is never an arbitrary caller archive.
        with tarfile.open(archive) as bundle:
            bundle.extractall(sysroot, filter="fully_trusted")
    if shutil.which("bwrap") is None:
        raise RuntimeError("bubblewrap is required for the isolated offline runtime build")
    command = [
        "bwrap",
        "--unshare-user",
        "--unshare-net",
        "--uid",
        "0",
        "--gid",
        "0",
        "--bind",
        str(sysroot),
        "/",
        "--bind",
        str(work),
        "/build",
        "--ro-bind",
        str(sources.resolve()),
        "/sources",
        "--ro-bind",
        str(recipe.parent),
        "/recipe",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--",
        "/bin/sh",
        "-ec",
        "/sbin/apk add --no-network /build/apks/*.apk; /bin/sh /recipe/build_controlled_appimage_runtime.sh",
    ]
    with (work / "build.log").open("w") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    runtime = work / "runtime-x86_64"
    if sha256(runtime) != lock["runtime_sha256"]:
        raise RuntimeError("Controlled runtime differs from the reviewed reproducible input hash")
    destination = root / "build/tools/runtime-x86_64"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime, destination)
    destination.chmod(0o755)
    receipt = {
        "runtime_sha256": sha256(runtime),
        "recipe_sha256": sha256(recipe),
        "rootfs_sha256": base["sha256"],
        "locked_apks": len(lock["packages"]),
        "compile_network": "disabled",
        "relink_object_sha256": sha256(work / "relink/runtime.o"),
        "link_map_sha256": sha256(work / "relink/runtime.map"),
        "publication_approval": False,
    }
    (root / "build/tools/controlled-runtime-build.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print("Controlled runtime verified:", receipt["runtime_sha256"])
    return destination


if __name__ == "__main__":
    build()
