"""Inventory actual extracted/installed payload bytes; unknown origins stay unknown."""

from __future__ import annotations

import ast
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter
from functools import lru_cache
from pathlib import Path

from release_common import ROOT, read_json, sha256


def native_details(file: Path, magic: bytes) -> dict:
    if magic.startswith(b"\x7fELF"):
        try:
            text = subprocess.run(
                ["readelf", "-d", str(file)], capture_output=True, text=True, check=True
            ).stdout
            return {
                "format": "ELF",
                "needed": re.findall(r"\(NEEDED\).*?\[([^]]+)\]", text),
                "soname": re.findall(r"\(SONAME\).*?\[([^]]+)\]", text),
            }
        except (OSError, subprocess.SubprocessError):
            return {"format": "ELF", "dependency_scan": "UNAVAILABLE"}
    if magic.startswith(b"MZ"):
        try:
            import pefile

            pe = pefile.PE(str(file), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
            )
            needed = [
                entry.dll.decode(errors="replace")
                for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", ())
            ]
            # Resource versions distinguish supplier DLLs from the package copying them.
            pe.parse_data_directories()
            version = {}
            for group in getattr(pe, "FileInfo", ()):
                for item in group:
                    for table in getattr(item, "StringTable", ()):
                        for key, value in table.entries.items():
                            key = key.decode(errors="replace")
                            if key in {
                                "CompanyName",
                                "ProductName",
                                "ProductVersion",
                                "FileVersion",
                                "OriginalFilename",
                                "LegalCopyright",
                            }:
                                version[key] = value.decode(errors="replace")
            fixed = getattr(pe, "VS_FIXEDFILEINFO", ())
            flags = int(fixed[0].FileFlags & fixed[0].FileFlagsMask) if fixed else None
            pe.close()
            return {
                "format": "PE",
                "needed": needed,
                "version_resource": version,
                "version_flags": flags,
                "prerelease_flag": bool(flags & 2) if flags is not None else None,
            }
        except (ImportError, OSError, ValueError):
            return {"format": "PE", "dependency_scan": "UNAVAILABLE"}
    return {}


def collect_origins(root: Path = ROOT) -> dict:
    """Use the native packager's copy records as provenance, never as a file inventory."""
    sources = {}
    for toc in (root / "build").glob("*/COLLECT-00.toc"):
        data = ast.literal_eval(toc.read_text(encoding="utf-8"))
        for name, source, kind in data[0]:
            sources[name.replace("\\", "/")] = (Path(source), kind)
    return sources


def resolve_copy_origin(sources: dict, key: str):
    """COLLECT symlink entries refer to another destination, not a host file."""
    visited = set()
    while key not in visited:
        visited.add(key)
        entry = sources.get(key)
        if not entry:
            return None
        source, kind = entry
        if kind != "SYMLINK":
            return entry
        key = source.as_posix()
    return None


def wheel_owners() -> dict:
    owners = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "")
        for file in dist.files or ():
            owners[Path(dist.locate_file(file)).resolve()] = (name, dist.version)
    return owners


def module_sources(root: Path) -> dict:
    sources = {}
    for toc in (root / "build").glob("*/Analysis-00.toc"):
        data = ast.literal_eval(toc.read_text(encoding="utf-8"))
        for field in data:
            if isinstance(field, list):
                for entry in field:
                    if (
                        isinstance(entry, tuple)
                        and len(entry) == 3
                        and str(entry[2]).startswith(("PYMODULE", "PYSOURCE"))
                    ):
                        sources[entry[0]] = Path(entry[1])
    return sources


def embedded_modules(payload: Path) -> set[str]:
    from PyInstaller.archive.readers import CArchiveReader

    result = set()
    for name in ("CactuVideoConverter", "CactuVideoConverter.exe"):
        executable = next(payload.rglob(name), None)
        if executable is None:
            continue
        archive = CArchiveReader(str(executable))
        for entry, info in archive.toc.items():
            if info[-1] == "s":
                result.add(entry)
            if entry.endswith(".pyz"):
                result.update(archive.open_embedded_archive(entry).toc)
    for archive in payload.rglob("base_library.zip"):
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if name.endswith(".pyc"):
                    module = name[:-4].replace("/", ".").removesuffix(".__init__")
                    result.add(module)
    return result


@lru_cache(maxsize=None)
def host_package(source: Path) -> dict | None:
    if not sys.platform.startswith("linux"):
        return None
    # Only query a source selected by PyInstaller; never enumerate unrelated host files.
    try:
        candidates = [source, source.resolve()]
        for file in list(candidates):
            if str(file).startswith("/usr/lib/"):
                candidates.append(Path(str(file).removeprefix("/usr")))
            elif str(file).startswith("/lib/"):
                candidates.append(Path("/usr" + str(file)))
        for candidate in dict.fromkeys(candidates):
            result = subprocess.run(
                ["dpkg-query", "-S", str(candidate)], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                break
        if result.returncode == 0:
            package = result.stdout.split(": ", 1)[0]
            value = subprocess.run(
                [
                    "dpkg-query",
                    "-W",
                    "-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}",
                    package,
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split("\t")
            copyright_file = Path("/usr/share/doc") / package.split(":")[0] / "copyright"
            return {
                "project": value[2] or package,
                "version": value[3] or value[1],
                "binary_package": value[0],
                "binary_version": value[1],
                "origin": "build-host-debian-package",
                "license": "REVIEW_REQUIRED",
                "corresponding_source": "REVIEW_REQUIRED: retain exact distro source package and patches",
                "host_copyright_sha256": sha256(copyright_file)
                if copyright_file.is_file()
                else None,
                "notice": "_internal/licenses/native-system/"
                + package.split(":")[0]
                + "/copyright",
                "review_status": "REVIEW_REQUIRED",
            }
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return None


def container_wrapper(artifact: Path, kind: str, root: Path) -> dict | None:
    if kind == "extracted-linux-appimage":
        offset = int(
            subprocess.run(
                [str(artifact.resolve()), "--appimage-offset"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        component = read_json(root / "release/component-sources.json")["appimage-runtime"]
        tool = read_json(root / "release/toolchain.json")["appimage_runtime"]
        description = (
            "actual embedded ELF prefix before SquashFS; packaging may modify metadata bytes"
        )
    elif kind == "installed-windows":
        import pefile

        pe = pefile.PE(str(artifact), fast_load=True)
        offset = pe.get_overlay_data_start_offset() or artifact.stat().st_size
        pe.close()
        component = read_json(root / "release/component-sources.json")["inno-setup"]
        tool = read_json(root / "release/toolchain.json")["inno_setup"]
        description = (
            "actual generated PE prefix; installer payload and component terms reviewed separately"
        )
    else:
        return None
    if not 0 < offset <= artifact.stat().st_size:
        raise RuntimeError("Invalid executable container boundary")
    import hashlib

    with artifact.open("rb") as stream:
        digest = hashlib.sha256(stream.read(offset)).hexdigest()
    return {
        "component": component,
        "prefix_bytes": offset,
        "prefix_sha256": digest,
        "pinned_input_sha256": tool["sha256"],
        "method": description,
    }


def inventory(
    payload: Path,
    artifact: Path,
    *,
    payload_kind: str,
    target: str,
    destination: Path,
    root: Path = ROOT,
    final_rc: bool = False,
) -> dict:
    sources, owners = collect_origins(root), wheel_owners()
    catalog = read_json(root / "release/component-sources.json")
    qt_lock_file = root / "release/qt-source-lock.json"
    qt_lock = read_json(qt_lock_file) if qt_lock_file.is_file() else None
    msys_file = root / "build/msys-payload-notices.json"
    msys_records = (
        {e["sha256"]: e for e in read_json(msys_file)["files"]} if msys_file.is_file() else {}
    )
    records, components = [], {}

    def register(component):
        component = dict(component)
        if component.get("notice") and component["notice"] != "UNRESOLVED":
            app_root = payload / "usr/bin" if (payload / "usr/bin").is_dir() else payload
            if not (app_root / component["notice"]).exists():
                component["review_status"] = "BLOCKED"
                component["missing_packaged_notice"] = component["notice"]
        identity = json.dumps(component, sort_keys=True)
        component_id = (
            components[identity]["id"]
            if identity in components
            else "component-" + str(len(components) + 1)
        )
        components.setdefault(identity, {"id": component_id, **component})
        return component_id

    def from_wheel(owner):
        component = {
            "license": "UNRESOLVED",
            "corresponding_source": "UNRESOLVED",
            "notice": "UNRESOLVED",
            "review_status": "BLOCKED",
        }
        component.update(catalog.get(owner[0].lower().replace("_", "-"), {}))
        component.update(project=owner[0], version=owner[1], origin="python-wheel")
        return component

    for file in sorted(payload.rglob("*")):
        if not file.is_file() and not file.is_symlink():
            continue
        relative = file.relative_to(payload).as_posix()
        if file.is_symlink():
            if not file.resolve().is_relative_to(payload.resolve()):
                raise RuntimeError("Packaged symlink escapes its payload: " + relative)
        with file.open("rb") as stream:
            magic = stream.read(4)
        native = magic.startswith(b"\x7fELF") or magic.startswith(b"MZ")
        key = relative.removeprefix("usr/bin/").removeprefix("_internal/")
        origin = resolve_copy_origin(sources, key) or resolve_copy_origin(sources, relative)
        details = native_details(file, magic) if native else None
        source_evidence = None
        component = None
        if origin:
            source, _kind = origin
            if source.is_file():
                source_evidence = {
                    "copy_kind": _kind,
                    "source_filename": source.name,
                    "source_sha256": sha256(source),
                    "copy_bytes_match": sha256(source) == sha256(file),
                }
                if source.is_relative_to(Path(sys.base_prefix)):
                    source_evidence["distribution"] = "CPython " + sys.version.split()[0]
                    source_evidence["relative_path"] = source.relative_to(
                        Path(sys.base_prefix)
                    ).as_posix()
                system_root = os.environ.get("SystemRoot")
                if system_root and source.is_relative_to(Path(system_root)):
                    source_evidence["distribution"] = "Windows runner image " + os.environ.get(
                        "ImageVersion", "UNRECORDED"
                    )
                    source_evidence["relative_path"] = source.relative_to(
                        Path(system_root)
                    ).as_posix()
            owner = owners.get(source.resolve())
            if owner:
                component = from_wheel(owner)
                if source_evidence:
                    source_evidence["distribution"] = owner[0] + " " + owner[1]
            elif source.is_relative_to(root / "src") or key.startswith("assets/"):
                component = dict(catalog["cactu"])
            elif source.is_relative_to(Path(sys.base_prefix)):
                component = dict(catalog["cpython"])
                component["version"] = sys.version.split()[0]
            elif source.is_relative_to(root / "vendor/ffmpeg"):
                runtime_manifest = root / "build/controlled-runtime-manifest.json"
                entry = read_json(
                    runtime_manifest
                    if runtime_manifest.is_file()
                    else root / "vendor/ffmpeg/manifest.json"
                )[target]
                expected_hash = entry[
                    "ffprobe_sha256" if file.name.startswith("ffprobe") else "ffmpeg_sha256"
                ]
                if sha256(file) != expected_hash:
                    raise RuntimeError("Runtime inventory does not match selected FFmpeg manifest")
                component = dict(catalog["ffmpeg"])
                component.update(
                    version=entry["build_id"], corresponding_source=entry["source_recipe"]
                )
            elif native:
                component = host_package(source)
            if source_evidence and source_evidence["copy_bytes_match"] is not True:
                component = None
        msys = msys_records.get(sha256(file)) if native else None
        if msys:
            component = {
                "project": msys["source_package"],
                "version": msys["version"],
                "origin": "exact-msys2-package-by-sha256",
                "license": msys["license"],
                "notice": msys["notices"][0]["path"],
                "required_action": msys["required_action"],
                "source_delivery_required": msys["source_delivery_required"],
                "review_status": "ENGINEERING_NOTICE_INTEGRATED_PENDING_HUMAN_REVIEW",
            }
            source_evidence = {
                "distribution": msys["package"] + " " + msys["version"],
                "source_sha256": msys["sha256"],
                "copy_bytes_match": True,
            }
        if native and details and details.get("format") == "PE":
            version = details.get("version_resource", {})
            if "Microsoft" in version.get("CompanyName", ""):
                component = {
                    "project": "Microsoft Windows / Visual C++ runtime",
                    "version": version.get("FileVersion", "UNRESOLVED"),
                    "role": "supplier runtime DLL; bundled, not Cactu/Qt code",
                    "license": "Microsoft redistribution terms: exact grant review required",
                    "corresponding_source": "https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files",
                    "review_status": "REVIEW_REQUIRED",
                    "included_by": component.get("project", "native dependency analysis")
                    if component
                    else "native dependency analysis",
                }
                if details.get("prerelease_flag") is True:
                    component["review_status"] = "BLOCKED"
                    component["redistribution_obstacle"] = (
                        "PE resource marks prerelease; Microsoft preview-code redistribution permission must not be assumed"
                    )
        if relative.startswith("unins"):
            component = dict(catalog["inno-setup"])
        elif (
            file.name == "AppRun"
            or file.name.endswith((".desktop", ".png"))
            and "/" not in relative
        ):
            component = dict(catalog["cactu"])
        elif file.name == ".DirIcon":
            component = dict(catalog["cactu"])
        elif file.name == "base_library.zip":
            component = dict(catalog["cpython"])
        elif file.name == "CactuVideoConverter" or file.name == "CactuVideoConverter.exe":
            component = dict(catalog["pyinstaller"])
            component["role"] = "bootloader plus embedded Cactu/Python module archive"
        elif "licenses/" in relative or file.name in {"LICENSE", "THIRD_PARTY_NOTICES.md"}:
            component = {
                "project": "license-and-notice-material",
                "version": "payload",
                "license": "per-file terms",
                "role": "notice",
                "review_status": "NOTICE_MATERIAL",
            }
        if component is None:
            component = {
                "project": "UNRESOLVED",
                "version": "UNRESOLVED",
                "license": "UNRESOLVED",
                "role": "native-library" if native else "payload-data-or-archive",
                "review_status": "BLOCKED",
                "corresponding_source": "UNRESOLVED",
            }
        component_id = register(component)
        record = {
            "path": relative,
            "sha256": sha256(file),
            "size": file.stat().st_size,
            "type": "native" if native else "data",
            "bundled": True,
            "component_id": component_id,
            "symlink": file.is_symlink(),
            "native": details,
            "copy_source_evidence": source_evidence,
        }
        if qt_lock:
            from qt_file_mapping import qt_file_mapping

            record["qt_source_mapping"] = qt_file_mapping(relative, qt_lock)
        records.append(record)
    modules = []
    provenance = module_sources(root)
    for name in sorted(embedded_modules(payload)):
        source = provenance.get(name)
        owner = owners.get(source.resolve()) if source else None
        if owner:
            component = from_wheel(owner)
        elif source and source.is_relative_to(root / "src"):
            component = dict(catalog["cactu"])
        elif source and source.is_relative_to(Path(sys.base_prefix)):
            component = dict(catalog["cpython"])
        elif name == "pyiboot01_bootstrap":
            component = dict(catalog["pyinstaller"])
        else:
            component = {
                "project": "UNRESOLVED",
                "version": "UNRESOLVED",
                "license": "UNRESOLVED",
                "review_status": "BLOCKED",
                "role": "embedded Python module",
            }
        modules.append({"name": name, "component_id": register(component)})
    wrapper = container_wrapper(artifact, payload_kind, root)
    if wrapper:
        wrapper["component_id"] = register(wrapper.pop("component"))
    unresolved = [
        c
        for c in components.values()
        if c.get("review_status") not in {"TECHNICAL_EVIDENCE", "NOTICE_MATERIAL"}
    ]
    result = {
        "schema_version": 1,
        "payload_kind": payload_kind,
        "target": target,
        "artifact": {"filename": artifact.name, "sha256": sha256(artifact)},
        "inventory_method": "walked actual extracted/installed payload; TOC/RECORD used only for origin attribution",
        "technical_license_complete": not unresolved,
        "final_rc": final_rc,
        "file_count": len(records),
        "file_types": dict(Counter(r["type"] for r in records)),
        "components": list(components.values()),
        "files": records,
        "embedded_python_modules": modules,
        "executable_container_wrapper": wrapper,
        "components_requiring_review": len(unresolved),
        "system_runtime_boundary": "Host graphics/kernel drivers are not licensed by this inventory; native dependency review remains mandatory",
    }
    native_names = {Path(r["path"]).name.lower() for r in records if r["type"] == "native"}
    needed = {name for r in records for name in (r.get("native") or {}).get("needed", ())}
    result["not_bundled_dependency_names"] = sorted(
        name for name in needed if name.lower() not in native_names
    )
    result["unexpected_driver_files"] = [
        r["path"]
        for r in records
        if re.search(
            r"(?:^|/)(?:dri/|icd\.d/)|(?:libnvidia|libcuda|nvidia_drv|amdgpu_drv)|\.ko(?:\.|$)",
            r["path"],
            re.I,
        )
    ]
    if result["unexpected_driver_files"]:
        result["technical_license_complete"] = False
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    result["source_commit"] = commit.stdout.strip() if commit.returncode == 0 else None
    if not records:
        raise RuntimeError("Cannot approve an empty payload inventory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
