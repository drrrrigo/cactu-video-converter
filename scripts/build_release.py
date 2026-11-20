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
from build_environment import check_environment
from payload_inventory import inventory


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
    parser.add_argument(
        "--rc1",
        action="store_true",
        help="Private RC1; requires completed technical license/source review",
    )
    args = parser.parse_args()
    if args.candidate == args.rc1:
        raise RuntimeError(
            "Choose exactly one of --candidate (audit only) or --rc1 (technically reviewed private RC)"
        )
    if args.rc1:
        if (
            read_json(ROOT / "release/config.json").get("technical_license_audit_complete")
            is not True
        ):
            raise RuntimeError("RC1 blocked: technical license/source review is incomplete")
        if any(
            e.get("corresponding_source_complete") is not True
            for e in read_json(ROOT / "vendor/ffmpeg/manifest.json").values()
        ):
            raise RuntimeError("RC1 blocked: FFmpeg corresponding sources are incomplete")
    environment_evidence = check_environment()
    os.environ["SOURCE_DATE_EPOCH"] = str(environment_evidence["source_date_epoch"])
    config = read_json(ROOT / "release/toolchain.json")
    target = platform_id()
    output = ROOT / "dist/candidate"
    output.mkdir(parents=True, exist_ok=True)
    runtime = validate(target, evidence_path=output / (target + "-runtime-evidence.json"))
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
    executable = bundle / (EXECUTABLE_NAME + (".exe" if sys.platform == "win32" else ""))
    signed = sign(executable)
    smoke(executable, destination=output / (target + "-onedir-smoke.json"))
    evidence = {
        "version": __version__,
        "target": target,
        **environment_evidence,
        "candidate_stage": "RC1" if args.rc1 else "AUDIT_ONLY_NOT_RC1",
        "candidate_id": __version__ + ("-rc1" if args.rc1 else "-audit"),
        "platform": platform.platform(),
        "runner_image": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "packaging_toolchain": config,
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
            inventory(
                Path(temporary) / EXECUTABLE_NAME,
                archive,
                payload_kind="extracted-windows-portable",
                target=target,
                destination=output / (target + "-portable-payload.json"),
                final_rc=args.rc1,
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

        test_installer(
            output / installer.name,
            inventory_destination=output / (target + "-installed-payload.json"),
            final_rc=args.rc1,
        )
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
        with tempfile.TemporaryDirectory(prefix="cactu-inventory-") as temporary:
            subprocess.run(
                [str(destination.resolve()), "--appimage-extract"],
                cwd=temporary,
                check=True,
                capture_output=True,
            )
            inventory(
                Path(temporary) / "squashfs-root",
                destination,
                payload_kind="extracted-linux-appimage",
                target=target,
                destination=output / (target + "-appimage-payload.json"),
                final_rc=args.rc1,
            )
        evidence["artifacts"] = {destination.name: sha256(destination)}
    if args.rc1:
        reports = list(output.glob(target + "-*-payload.json"))
        if not reports or any(
            read_json(p).get("technical_license_complete") is not True for p in reports
        ):
            raise RuntimeError("RC1 blocked: actual packaged-payload license review is incomplete")
    (output / (target + "-SHA256SUMS.txt")).write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(evidence["artifacts"].items())),
        encoding="utf-8",
    )
    (output / (target + "-build.json")).write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print("Internal candidate artifacts: " + str(output))
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
