"""Prepare local runtime source/relink material; never publish or approve it."""

import io
import json
import tarfile
from pathlib import Path
from release_common import ROOT, read_json, sha256


def prepare(root=ROOT, experiment: Path | None = None):
    experiment = experiment or root / "build/controlled-runtime"
    lock = read_json(root / "release/appimage-controlled-lock.json")
    cache = root / "release/evidence/local/sources"
    files = {}

    def add(path, name, expected=None):
        if not path.is_file() or expected and sha256(path) != expected:
            raise RuntimeError("Source/relink input missing or changed: " + name)
        files[name] = path

    for entry in lock["build_source_archives"] + lock["static_upstream_sources"]:
        add(
            cache / entry["filename"],
            "release/evidence/local/sources/" + entry["filename"],
            entry["sha256"],
        )
    for entry in lock["aports_source_recipes"]:
        for file in entry["recipe_and_patch_files"]:
            relative = entry["origin"] + "/" + file["file"]
            add(
                experiment / "relink/aports" / relative, "relink/aports/" + relative, file["sha256"]
            )
    for entry in lock["relink_inputs"]:
        name = "relink/sysroot/" + entry["sysroot_path"].lstrip("/")
        add(experiment / name, name, entry["sha256"])
    add(experiment / "relink/runtime.o", "relink/runtime.o", lock["runtime_object_sha256"])
    add(experiment / "relink/runtime.map", "relink/runtime.map", lock["link_map_sha256"])
    add(experiment / "relink/data_sections.ld", "relink/data_sections.ld")
    for name in [
        "scripts/build_controlled_runtime.py",
        "scripts/build_controlled_appimage_runtime.sh",
        "scripts/release_common.py",
        "release/appimage-controlled-lock.json",
        "LICENSE",
    ]:
        add(root / name, name)
    for file in (root / "licenses/packaging-runtimes").rglob("*"):
        if file.is_file():
            relative = file.relative_to(root / "licenses/packaging-runtimes").as_posix()
            if relative.startswith(("controlled-runtime/", "libfuse-3.15.0/")) or relative in {
                "AppImage-runtime-LICENSE.txt",
                "squashfuse-0.5.2-LICENSE.txt",
                "LGPL-2.1.txt",
            }:
                add(file, file.relative_to(root).as_posix())
    output = root / "build/source-delivery"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "Cactu-AppImage-fedfad51-cactu1-source-and-relink.tar"
    readme = b"""Cactu controlled AppImage runtime: local review material, not a public source offer.

This component archive contains upstream sources, Alpine recipes/patches, runtime.o,
15 recorded static/CRT link inputs, link script/map, notices and rebuild scripts.
The Cactu build scripts are GPL-3.0-or-later; see LICENSE. Other components retain
their individual licenses and notices.
Compiler/rootfs/APK binary packages are not redistributed inside this archive.
Their exact retrieval hashes are in release/appimage-controlled-lock.json.

To reproduce the stock stub, install Python 3.14.7 and bubblewrap on Linux x86_64,
then run: python scripts/build_controlled_runtime.py
The production helper verifies locked inputs and the stock output hash.

To modify/relink, work on copies in the reconstructed Alpine root. Use the raw
scripts/build_controlled_appimage_runtime.sh as the compile/link recipe, without
the production output-hash guard. Modify the retained source or replace a static
library under relink/sysroot. The same clang link command can use runtime.o plus
-L/build/relink/sysroot/usr/local/lib -L/build/relink/sysroot/usr/lib before the
library flags to prefer these replacement libraries. Keep data_sections.ld,
-static-pie, the recorded CRT/toolchain and the final AI byte patch from the recipe.
Build an AppImage with appimagetool --runtime-file MODIFIED_RUNTIME APPDIR OUTPUT.
No Cactu signing key, proprietary approval token or signature bypass is required.

Preserve component licenses/notices and mark modifications. This runtime archive
does not close FFmpeg/Qt/other Cactu dependency obligations or approve publication.
Before delivery, review this material and retain it beside the approved binary,
with its SHA-256 and a maintained recipient-accessible source index.
"""
    manifest = {
        "scope": "controlled AppImage runtime source/relink component only",
        "publication_approved": False,
        "files": {name: sha256(path) for name, path in sorted(files.items())},
    }
    extra = {
        "README.txt": readme,
        "SOURCE-MANIFEST.json": (json.dumps(manifest, indent=2) + "\n").encode(),
    }
    with tarfile.open(destination, "w") as bundle:
        for name in sorted(set(files) | set(extra)):
            info = tarfile.TarInfo(name)
            info.mtime, info.mode = 1795205905, 0o644
            if name in extra:
                info.size = len(extra[name])
                bundle.addfile(info, io.BytesIO(extra[name]))
            else:
                info.size = files[name].stat().st_size
                with files[name].open("rb") as stream:
                    bundle.addfile(info, stream)
    receipt = {
        "filename": destination.name,
        "sha256": sha256(destination),
        "size": destination.stat().st_size,
        "source_and_relink_files": len(files),
        "scope": manifest["scope"],
        "publication_approved": False,
    }
    (output / "runtime-source-delivery.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt))
    return destination


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path)
    prepare(experiment=parser.parse_args().experiment)
