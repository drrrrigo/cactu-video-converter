"""System-only Microsoft prerequisite; never acquire/install Microsoft binaries."""

import json
import re
import shutil
import subprocess
from pathlib import Path

try:
    from .release_common import ROOT, read_json, sha256
except ImportError:
    from release_common import ROOT, read_json, sha256


def microsoft_runtime(name):
    return bool(
        re.fullmatch(
            r"(?:msvcp|vcruntime)\d+[^/]*\.dll", Path(name.replace("\\", "/")).name.lower()
        )
    )


def assert_no_runtime(bundle):
    unexpected = [
        p.relative_to(bundle).as_posix()
        for p in bundle.rglob("*")
        if p.is_file() and microsoft_runtime(p.name)
    ]
    if unexpected:
        raise RuntimeError("Microsoft runtime must be system-installed: " + ", ".join(unexpected))


def validate_clean_evidence(record, artifacts):
    """Additional publication condition; protected manual/owner gates still apply."""
    if not isinstance(record, dict):
        raise RuntimeError("Exact clean-Windows runtime evidence is missing")
    missing, installed = record.get("missing", {}), record.get("installed", {})
    identity = {
        "portable": next((v for k, v in artifacts.items() if "Portable-" in k), ""),
        "setup": next((v for k, v in artifacts.items() if "Setup-" in k), ""),
    }
    if not all(identity.values()):
        raise RuntimeError("Exact Windows artifact hashes are missing")
    for phase, result in (("Missing", missing), ("Installed", installed)):
        if (
            result.get("phase") != phase
            or result.get("result") != "PASS"
            or result.get("clean_windows_test") is not True
            or result.get("automatic_runtime_install") is not False
            or result.get("bundled_microsoft_runtime_files") != 0
            or {k: str(v).lower() for k, v in result.get("artifacts", {}).items()} != identity
            or not re.fullmatch(r"[a-fA-F0-9]{64}", result.get("guest_identity_sha256", ""))
        ):
            raise RuntimeError("Clean-Windows runtime evidence differs from the exact candidate")
    if (
        missing.get("guest_identity_sha256") != installed.get("guest_identity_sha256")
        or missing.get("probe_exit") != 10
        or missing.get("installer_exit") in (None, 0)
        or any(missing.get("system_dll_versions", {}).values())
        or installed.get("probe_exit") != 0
        or installed.get("installer_exit") != 0
        or installed.get("uninstall") != "PASS"
    ):
        raise RuntimeError("Missing/present prerequisite scenarios have not passed in one guest")
    policy = read_json(ROOT / "release/windows-runtime-policy.json")
    for result in (missing, installed):
        if set(result.get("system_dll_versions", {})) != set(policy["required_dlls"]):
            raise RuntimeError("Clean-Windows system DLL inventory is incomplete")
        if not str(result.get("os_build", "")).isdigit() or int(result["os_build"]) < 22000:
            raise RuntimeError("Clean-Windows evidence must identify Windows 11")
    for value in installed["system_dll_versions"].values():
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)(?:\s|$)", value or "")
        if not match or tuple(map(int, match.groups())) < tuple(policy["qualification_floor"]):
            raise RuntimeError("Clean-Windows runtime does not meet the qualification floor")
    for name in ("portable_smoke", "installed_smoke"):
        if not all(
            installed.get(name, {}).get(k) is True
            for k in (
                "ok",
                "frozen",
                "runtime_bundled",
                "faststart",
                "original_unchanged",
                "quick_preview",
                "embedded_subtitle_queue",
                "loudness_queue",
            )
        ):
            raise RuntimeError("Clean-Windows frozen smoke is incomplete")


def build_launcher(destination, *, test=False, root=ROOT):
    policy = read_json(root / "release/windows-runtime-policy.json")
    if policy["strategy"] != "system-prerequisite":
        raise RuntimeError("Unreviewed Windows runtime strategy")
    work = root / "build/windows-runtime"
    work.mkdir(parents=True, exist_ok=True)
    a, b, c, d = policy["qualification_floor"]
    strings = ", ".join('L"' + name + '"' for name in policy["required_dlls"])
    (work / "windows-runtime-config.h").write_text(
        f"#define CACTU_VERSION_MS {((a << 16) | b)}UL\n"
        f"#define CACTU_VERSION_LS {((c << 16) | d)}UL\n"
        f'#define CACTU_MINIMUM_TEXT L"{a}.{b}.{c}.{d}"\n'
        f'#define CACTU_GUIDANCE L"{policy["official_guidance"]}"\n'
        f"static const WCHAR *CACTU_DLLS[] = {{{strings}}};\n"
        f"#define CACTU_DLL_COUNT {len(policy['required_dlls'])}\n"
    )
    compiler = shutil.which("gcc")
    if not compiler:
        raise RuntimeError(
            "Native MinGW GCC is required for the CRT-independent prerequisite launcher"
        )
    command = [
        compiler,
        "-Os",
        "-fno-builtin",
        "-fno-stack-protector",
        "-nostdlib",
        "-mwindows",
        "-Wl,--entry,CactuMain",
        "-Wl,--no-insert-timestamp",
        "-I",
        str(work),
        str(root / "packaging/windows/runtime_launcher.c"),
        "-o",
        str(destination),
        "-lkernel32",
        "-luser32",
        "-lshell32",
        "-lversion",
    ]
    if test:
        command.insert(1, "-DCACTU_RUNTIME_TEST")
    if not test:
        from video_converter import __version__

        version = __version__.replace("-beta.", ".").replace(".", ",")
        resource = work / "launcher.rc"
        resource.write_text(
            '1 ICON "' + (root / "assets/branding/cactu-video-converter.ico").as_posix() + '"\n'
            f"1 VERSIONINFO FILEVERSION {version} PRODUCTVERSION {version}\n"
            "FILEFLAGSMASK 0x3f FILEFLAGS 0 FILEOS 0x40004 FILETYPE 1\n"
            'BEGIN BLOCK "StringFileInfo" BEGIN BLOCK "040904B0" BEGIN\n'
            'VALUE "CompanyName", "Cactu Video Converter contributors\\0"\n'
            'VALUE "ProductName", "Cactu Video Converter\\0"\n'
            'VALUE "FileDescription", "Cactu Video Converter\\0"\n'
            'END END BLOCK "VarFileInfo" BEGIN VALUE "Translation", 1033, 1200 END END\n'
        )
        resource_object = work / "launcher-resource.o"
        subprocess.run(["windres", str(resource), str(resource_object)], check=True)
        command.insert(-4, str(resource_object))
    subprocess.run(command, check=True)
    from payload_inventory import native_details

    imports = native_details(destination, b"MZ")["needed"]
    if set(name.lower() for name in imports) - {
        "kernel32.dll",
        "user32.dll",
        "shell32.dll",
        "version.dll",
    }:
        raise RuntimeError("Prerequisite launcher acquired a non-system/CRT dependency")
    return {
        "sha256": sha256(destination),
        "needed": imports,
        "test_binary": test,
        "source_sha256": sha256(root / "packaging/windows/runtime_launcher.c"),
        "compiler_sha256": sha256(Path(compiler)),
    }


def prepare_bundle(bundle, root=ROOT):
    assert_no_runtime(bundle)
    notice_record = read_json(root / "release/python-incorporated-review.json")[
        "windows_binary_notice"
    ]
    notice = root / notice_record["file"]
    if sha256(notice) != notice_record["sha256"]:
        raise RuntimeError("Exact CPython Windows binary license changed")
    scope = (
        "Cactu's own source remains GPL-3.0-or-later. The following CPython Windows "
        "binary license and its Additional Conditions apply to their respective "
        "third-party components, including embedded Microsoft Distributable Code. "
        "They do not restrict Cactu's own GPL source or programs running on Python. "
        "Before using or redistributing that Microsoft code, agree to its applicable "
        "restrictions below.\n\n"
    )
    portable_notice = bundle / "WINDOWS-THIRD-PARTY-LICENSES.txt"
    portable_notice.write_text(scope + notice.read_text(encoding="utf-8"), encoding="utf-8-sig")
    work = root / "build/windows-runtime"
    work.mkdir(parents=True, exist_ok=True)
    (work / "installer-license.txt").write_text(
        "Cactu source license and separate third-party Windows binary terms\n\n"
        + (root / "LICENSE").read_text(encoding="utf-8")
        + "\n\n"
        + scope
        + notice.read_text(encoding="utf-8"),
        encoding="utf-8-sig",
    )
    executable = bundle / "CactuVideoConverter.exe"
    core = bundle / "CactuVideoConverter-core.exe"
    executable.rename(core)
    evidence = build_launcher(executable, root=root)
    evidence.update(
        cpython_windows_notice_sha256=sha256(notice), portable_notice_sha256=sha256(portable_notice)
    )
    shutil.copy2(root / "packaging/windows/PREREQUISITES.txt", bundle / "PREREQUISITES.txt")
    evidence.update(
        strategy="system-prerequisite", core_sha256=sha256(core), automatic_download=False
    )
    (root / "build/windows-runtime/launcher-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    return evidence
