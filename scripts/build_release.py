"""Native candidate packaging. Publication requires separate reviewed gates."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from branding_metadata import (
    ASSETS,
    EXECUTABLE_NAME,
    PRODUCT_SLUG,
    __version__,
    appimage_filename,
    desktop_entry,
)
from collect_licenses import collect
from package_smoke import smoke
from release_common import ROOT, platform_id, read_json, sha256
from verify_ffmpeg import validate


def sign(file: Path) -> bool:
    thumbprint = os.environ.get("CACTU_SIGN_CERT_SHA1")
    if not thumbprint:
        return False
    if sys.platform != "win32":
        raise RuntimeError("Authenticode signing requires Windows")
    tool = shutil.which("signtool")
    if not tool:
        raise RuntimeError("Configured signing requires Windows SDK signtool")
    subprocess.run(
        [
            tool,
            "sign",
            "/sha1",
            thumbprint,
            "/fd",
            "SHA256",
            "/tr",
            "http://timestamp.digicert.com",
            "/td",
            "SHA256",
            str(file),
        ],
        check=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        action="store_true",
        help="Internal candidate only; does not approve redistribution",
    )
    args = parser.parse_args()
    if not args.candidate:
        raise RuntimeError(
            "Build an internal --candidate first; publish only the exact reviewed artifacts via the release workflow"
        )
    config = read_json(ROOT / "release/toolchain.json")
    target = platform_id()
    runtime = validate(target)
    licenses = ROOT / "build/licenses"
    if licenses.exists():
        shutil.rmtree(licenses)
    collect(licenses)
    shutil.copy2(runtime / "FFmpeg-LICENSE.txt", licenses / "FFmpeg-LICENSE.txt")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(ROOT / "packaging/video_converter.spec"),
        ],
        cwd=ROOT,
        check=True,
    )
    bundle = ROOT / "dist" / EXECUTABLE_NAME
    output = ROOT / "dist/candidate"
    output.mkdir(parents=True, exist_ok=True)
    executable = bundle / (EXECUTABLE_NAME + (".exe" if sys.platform == "win32" else ""))
    signed = sign(executable)
    smoke(executable, destination=output / (target + "-onedir-smoke.json"))
    evidence = {
        "version": __version__,
        "target": target,
        "python": platform.python_version(),
        "python_pin": config["python"],
        "python_pin_matches": platform.python_version() == config["python"],
        "signed": signed,
        "artifacts": {},
        "candidate_only": True,
    }
    if sys.platform == "win32":
        archive = output / f"{EXECUTABLE_NAME}-Portable-{__version__}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for file in sorted(bundle.rglob("*")):
                if file.is_file():
                    z.write(file, file.relative_to(bundle.parent).as_posix())
        with tempfile.TemporaryDirectory(prefix="cactu-portable-") as temporary:
            with zipfile.ZipFile(archive) as z:
                z.extractall(temporary)
            smoke(
                Path(temporary) / EXECUTABLE_NAME / (EXECUTABLE_NAME + ".exe"),
                destination=output / (target + "-portable-smoke.json"),
            )
        iscc = ROOT / "build/tools/inno/ISCC.exe"
        if not iscc.is_file():
            raise RuntimeError("Run scripts/install_packaging_tool.py for pinned Inno Setup first")
        subprocess.run(
            [str(iscc), str(ROOT / "packaging/windows/CactuVideoConverter.iss")],
            cwd=ROOT,
            check=True,
        )
        installer = ROOT / "dist" / f"{EXECUTABLE_NAME}-Setup-{__version__}.exe"
        sign(installer)
        shutil.copy2(installer, output / installer.name)
        from smoke_installer import test_installer

        test_installer(output / installer.name)
        evidence["artifacts"] = {p.name: sha256(p) for p in (archive, output / installer.name)}
    else:
        appdir = ROOT / "build" / f"{EXECUTABLE_NAME}.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        shutil.copytree(bundle, appdir / "usr/bin")
        shutil.copy2(ROOT / "packaging/linux/AppRun", appdir / "AppRun")
        (appdir / "AppRun").chmod(0o755)
        (appdir / f"{PRODUCT_SLUG}.desktop").write_text(desktop_entry(), encoding="utf-8")
        shutil.copy2(ASSETS / f"{PRODUCT_SLUG}.png", appdir / f"{PRODUCT_SLUG}.png")
        tool = ROOT / "build/tools/appimagetool.AppImage"
        if not tool.is_file():
            raise RuntimeError(
                "Run scripts/install_packaging_tool.py for pinned appimagetool first"
            )
        destination = output / appimage_filename()
        environment = os.environ.copy()
        environment.update(APPIMAGE_EXTRACT_AND_RUN="1", ARCH="x86_64", NO_APPSTREAM="1")
        # Fixed tool digest is rechecked even if a previous build left a tool behind.
        if sha256(tool) != config["appimagetool"]["sha256"]:
            raise RuntimeError("Packager tool hash mismatch")
        runtime_file = ROOT / "build/tools/runtime-x86_64"
        if sha256(runtime_file) != config["appimage_runtime"]["sha256"]:
            raise RuntimeError("AppImage runtime hash mismatch")
        subprocess.run(
            [str(tool), "--runtime-file", str(runtime_file), str(appdir), str(destination)],
            env=environment,
            check=True,
        )
        smoke(destination, destination=output / (target + "-appimage-smoke.json"))
        evidence["artifacts"] = {destination.name: sha256(destination)}
    (output / (target + "-build.json")).write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print("Internal candidate artifacts: " + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
