"""Inventory actual extracted/installed payload bytes; unknown origins stay unknown."""

from __future__ import annotations

import ast
import importlib.metadata
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
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
            pe.close()
            return {"format": "PE", "needed": needed}
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
                        and str(entry[2]).startswith("PYMODULE")
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
        for entry in archive.toc:
            if entry.endswith(".pyz"):
                result.update(archive.open_embedded_archive(entry).toc)
    for archive in payload.rglob("base_library.zip"):
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if name.endswith(".pyc"):
                    module = name[:-4].replace("/", ".").removesuffix(".__init__")
                    result.add(module)
    return result


def host_package(source: Path) -> dict | None:
    if not sys.platform.startswith("linux"):
        return None
    # Only query a source selected by PyInstaller; never enumerate unrelated host files.
    try:
        result = subprocess.run(
            ["dpkg-query", "-S", str(source)], capture_output=True, text=True, check=False
        )
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
            }
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return None


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
        origin = sources.get(key) or sources.get(relative)
        component = None
        if origin:
            source, _kind = origin
            owner = owners.get(source.resolve())
            if owner:
                component = from_wheel(owner)
            elif source.is_relative_to(root / "src") or key.startswith("assets/"):
                component = dict(catalog["cactu"])
            elif source.is_relative_to(Path(sys.base_prefix)):
                component = dict(catalog["cpython"])
                component["version"] = sys.version.split()[0]
            elif source.is_relative_to(root / "vendor/ffmpeg"):
                entry = read_json(root / "vendor/ffmpeg/manifest.json")[target]
                component = dict(catalog["ffmpeg"])
                component.update(
                    version=entry["build_id"], corresponding_source=entry["source_recipe"]
                )
            elif native:
                component = host_package(source)
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
        records.append(
            {
                "path": relative,
                "sha256": sha256(file),
                "size": file.stat().st_size,
                "type": "native" if native else "data",
                "bundled": True,
                "component_id": component_id,
                "symlink": file.is_symlink(),
                "native": native_details(file, magic) if native else None,
            }
        )
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
        else:
            component = {
                "project": "UNRESOLVED",
                "version": "UNRESOLVED",
                "license": "UNRESOLVED",
                "review_status": "BLOCKED",
                "role": "embedded Python module",
            }
        modules.append({"name": name, "component_id": register(component)})
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
