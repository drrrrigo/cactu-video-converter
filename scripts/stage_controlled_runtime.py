"""Stage the selected source-built candidate without changing tracked source files."""

import hashlib
import json
import shutil
import subprocess

from release_common import ROOT, read_json, sha256


def checked_build(work, target, root=ROOT):
    baseline = read_json(root / "release/controlled-baseline.json")
    build = read_json(work / "manifest.json")
    lock = read_json(root / baseline["source_lock"])
    canonical = hashlib.sha256(
        json.dumps(lock, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    recipe = (root / baseline["recipe"]).read_bytes().replace(b"\r\n", b"\n")
    accepted_recipe = {
        hashlib.sha256(data).hexdigest() for data in [recipe, recipe.replace(b"\n", b"\r\n")]
    }
    expected = [e for e in lock["sources"] if e["project"] != "AMF" or target.startswith("windows")]
    if (
        canonical != baseline["source_lock_canonical_sha256"]
        or hashlib.sha256(recipe).hexdigest() != baseline["recipe_lf_sha256"]
    ):
        raise RuntimeError("Selected controlled baseline recipe/source lock changed")
    if (
        build["target"] != target
        or build["source_inputs"] != expected
        or build["recipe_sha256"] not in accepted_recipe
    ):
        raise RuntimeError("Controlled candidate does not match the selected source recipe")
    if build.get("verified_tool_fingerprint_profile") != baseline["profiles"][target]:
        raise RuntimeError("Controlled candidate lacks its required native tool profile")
    if "--enable-nonfree" in build["configure"]:
        raise RuntimeError("Nonfree candidate rejected")
    if {e["package"] for e in build.get("static_pkg_config_overrides", [])} != {
        "x264",
        "libass",
        "vpl",
        "dav1d",
    }:
        raise RuntimeError("Controlled static source selection evidence missing")
    if target.startswith("windows"):
        for name in ["ffmpeg", "ffprobe"]:
            imports = build.get("pe_imports", {}).get(name)
            if not imports or any(
                n.lower().startswith(("libass-", "libvpl-", "libx264", "libdav1d")) for n in imports
            ):
                raise RuntimeError("Unexpected controlled-library DLL fallback")
    suffix = ".exe" if target.startswith("windows") else ""
    for name in ["ffmpeg", "ffprobe"]:
        if sha256(work / "prefix/bin" / (name + suffix)) != build["outputs"][name]["sha256"]:
            raise RuntimeError("Controlled executable bytes changed")
    return build


def stage(work, target, root=ROOT):
    build = checked_build(work, target, root)
    selected = read_json(root / "vendor/ffmpeg/manifest.json")
    entry = selected[target]
    suffix = ".exe" if target.startswith("windows") else ""
    vendor = root / "vendor/ffmpeg/9.0.2" / target
    vendor.mkdir(parents=True, exist_ok=True)
    for name in ["ffmpeg", "ffprobe"]:
        shutil.copy2(work / "prefix/bin" / (name + suffix), vendor / (name + suffix))
    core = next((work / "sources/FFmpeg").iterdir())
    shutil.copy2(core / "COPYING.GPLv3", vendor / "FFmpeg-LICENSE.txt")
    entry.update(
        provider="Cactu selected controlled audit candidate",
        source_url=None,
        build_id=build["outputs"]["ffmpeg"]["-version"].splitlines()[0].split()[2],
        build_configuration=next(
            s.removeprefix("configuration: ")
            for s in build["outputs"]["ffmpeg"]["-version"].splitlines()
            if s.startswith("configuration: ")
        ),
        source_recipe="release/controlled-baseline.json + scripts/build_controlled_ffmpeg.py",
        license_sha256=sha256(vendor / "FFmpeg-LICENSE.txt"),
        hardware_encoders=["h264_nvenc", "h264_qsv", "h264_amf" if suffix else "h264_vaapi"],
        corresponding_source_complete=False,
        redistribution_approved=False,
    )
    # This is a directly built pair, not a fabricated downloadable provider archive.
    entry["input_kind"] = "direct-controlled-build"
    entry["pair_sha256"] = hashlib.sha256(
        "".join(build["outputs"][n]["sha256"] for n in ["ffmpeg", "ffprobe"]).encode()
    ).hexdigest()
    entry["archive_sha256"] = None
    entry["archive_filename"] = None
    for name in ["ffmpeg", "ffprobe"]:
        entry[name + "_sha256"] = build["outputs"][name]["sha256"]
    destination = root / "build/controlled-runtime-manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(selected, indent=2) + "\n")
    provenance = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "baseline_sha256": sha256(root / "release/controlled-baseline.json"),
        "controlled_build_manifest_sha256": sha256(work / "manifest.json"),
        "generated_runtime_manifest_sha256": sha256(destination),
        "binary_hashes": {n: build["outputs"][n]["sha256"] for n in ["ffmpeg", "ffprobe"]},
        "redistribution_approved": False,
    }
    return vendor, destination, provenance
