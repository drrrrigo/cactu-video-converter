"""Build isolated FFmpeg candidates; never modify the selected vendor runtime."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

from release_common import ROOT, read_json, sha256


def build(target, work, jobs):
    windows = os.name == "nt" or platform.system().startswith(("MINGW", "MSYS"))
    if (target.startswith("windows")) != windows:
        raise RuntimeError(
            "Native target required; Windows must run in its native MSYS2 environment"
        )
    lock = read_json(ROOT / "release/ffmpeg-controlled-lock.json")
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    prefix = work / "prefix"
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = str(work / "sources")
    env["PKG_CONFIG_PATH"] = str(prefix / "lib/pkgconfig")
    records = {}
    logs = work / "logs"
    logs.mkdir(exist_ok=True)

    def run(name, argv, cwd):
        with (logs / (name + ".log")).open("w") as log:
            subprocess.run(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

    sources = {}
    for entry in lock["sources"]:
        if entry["project"] == "AMF" and not windows:
            continue
        archive = ROOT / "release/evidence/local/sources" / entry["filename"]
        if sha256(archive) != entry["sha256"]:
            raise RuntimeError("Locked source changed: " + entry["project"])
        folder = work / "sources" / entry["project"]
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        with tarfile.open(archive) as bundle:
            members = None
            if entry["project"] == "AMF":
                members = [
                    m
                    for m in bundle.getmembers()
                    if "/amf/public/include/" in m.name
                    or Path(m.name).name.lower().startswith(("license", "copying"))
                ]
            bundle.extractall(folder, members=members, filter="data")
        sources[entry["project"]] = next(p for p in folder.iterdir() if p.is_dir())
    # Upstream's version.sh otherwise discovers the enclosing Cactu repository.
    version = "9.0.2-cactu-" + lock["sources"][0]["revision"][:12]
    (sources["FFmpeg"] / "VERSION").write_text(version + "\n")
    for command in ["gcc", "make", "pkg-config", "autoconf", "automake", "libtoolize"]:
        executable = shutil.which(command)
        if not executable:
            raise RuntimeError("Missing build tool: " + command)
        result = subprocess.run([executable, "--version"], capture_output=True, text=True)
        records[command] = {
            "sha256": sha256(Path(executable).resolve()),
            "version": result.stdout.splitlines()[0],
        }
    (work / "environment.json").write_text(
        json.dumps({"platform": platform.platform(), "tools": records}, indent=2) + "\n"
    )
    # No privileged SDK/driver installation. Headers are retained source inputs.
    run("nvheaders", ["make", "install", "PREFIX=" + str(prefix)], sources["nv-codec-headers"])
    run(
        "x264-configure",
        [
            "sh",
            "configure",
            "--prefix=" + str(prefix),
            "--enable-static",
            "--enable-pic",
            "--disable-cli",
            "--disable-asm",
        ],
        sources["x264"],
    )
    run("x264-build", ["make", "-j" + str(jobs)], sources["x264"])
    run("x264-install", ["make", "install"], sources["x264"])
    run("ass-autogen", ["sh", "autogen.sh"], sources["libass"])
    run(
        "ass-configure",
        [
            "sh",
            "configure",
            "--prefix=" + str(prefix),
            "--disable-shared",
            "--enable-static",
            "--disable-asm",
        ],
        sources["libass"],
    )
    run("ass-build", ["make", "-j" + str(jobs)], sources["libass"])
    run("ass-install", ["make", "install"], sources["libass"])
    flags = [
        "--prefix=" + str(prefix),
        "--disable-autodetect",
        "--disable-doc",
        "--disable-debug",
        "--disable-x86asm",
        "--disable-shared",
        "--enable-static",
        "--enable-gpl",
        "--enable-version3",
        "--enable-libx264",
        "--enable-libass",
        "--enable-libvpl",
        "--enable-ffnvcodec",
        "--enable-nvenc",
        "--enable-nvdec",
        "--enable-cuvid",
        "--pkg-config-flags=--static",
    ]
    if target.startswith("linux"):
        flags += ["--enable-vaapi"]
    else:
        include = prefix / "include/AMF"
        include.mkdir(parents=True, exist_ok=True)
        shutil.copytree(sources["AMF"] / "amf/public/include", include, dirs_exist_ok=True)
        flags += ["--enable-amf", "--extra-cflags=-I" + str(prefix / "include")]
    (work / "configure.json").write_text(json.dumps(flags, indent=2) + "\n")
    run("ffmpeg-configure", ["sh", "configure", *flags], sources["FFmpeg"])
    run("ffmpeg-build", ["make", "-j" + str(jobs)], sources["FFmpeg"])
    run("ffmpeg-install", ["make", "install"], sources["FFmpeg"])
    outputs = {}
    for name in ["ffmpeg", "ffprobe"]:
        binary = prefix / "bin" / (name + (".exe" if target.startswith("windows") else ""))
        outputs[name] = {"sha256": sha256(binary)}
        for flag in ["-version", "-buildconf", "-L"]:
            outputs[name][flag] = subprocess.check_output(
                [str(binary), flag], stderr=subprocess.STDOUT, text=True
            )
    manifest = {
        "target": target,
        "source_lock_sha256": sha256(ROOT / "release/ffmpeg-controlled-lock.json"),
        "recipe_sha256": sha256(Path(__file__)),
        "source_inputs": lock["sources"],
        "patches": [],
        "configure": flags,
        "tools": records,
        "outputs": outputs,
        "publication_approved": False,
        "complete_corresponding_source": False,
        "limitations": [
            "Host font/shaping/QSV/VAAPI dependency versions and source correspondence remain to be locked",
            "Assembly disabled for the initial candidate; performance is not representative",
            "No bit-identical reproduction claim",
        ],
    }
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return prefix


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("target", choices=["linux-x86_64", "windows-x86_64"])
    p.add_argument("--work", type=Path, default=ROOT / "build/ffmpeg-controlled")
    p.add_argument("--jobs", type=int, default=8)
    args = p.parse_args()
    build(args.target, args.work, args.jobs)
