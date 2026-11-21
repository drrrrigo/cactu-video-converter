"""Prepare finite component review and proposed recipient assets; never approve/upload."""

import argparse
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

from dependency_license_policy import UBUNTU
from release_common import ROOT, read_json, sha256


def copyleft(license):
    return ("GPL" in license or "MPL" in license) and "exception" not in license


def prepare(reports, destination):
    builds = [read_json(p) for p in reports.rglob("*-build.json")]
    if len(builds) != 2 or {b["target"] for b in builds} != {"windows-x86_64", "linux-x86_64"}:
        raise RuntimeError("Exactly one final build from each platform is required")
    commits = {b["source_commit"] for b in builds}
    if len(commits) != 1 or any(
        not b["source_tree_clean"]
        or b.get("controlled_runtime", {}).get("source_commit") != b["source_commit"]
        for b in builds
    ):
        raise RuntimeError("Candidate builds do not share one clean controlled source commit")
    commit = next(iter(commits))
    artifacts = {name: digest for b in builds for name, digest in b["artifacts"].items()}
    destination.mkdir(parents=True, exist_ok=True)
    output = ROOT / "build/proposed-source-assets"
    output.mkdir(parents=True, exist_ok=True)
    assets, rows, missing = {}, [], []

    def asset(file, component, obligation, url=None, expected=None):
        if not file.is_file():
            missing.append(
                {
                    "component": component,
                    "missing_file": file.name,
                    "completion": "Retain the exact required source asset before approval",
                }
            )
            return
        digest = sha256(file)
        if expected is not None and digest != expected:
            raise RuntimeError("Proposed source bytes differ from retained lock: " + file.name)
        if file.name in assets and assets[file.name]["sha256"] != digest:
            raise RuntimeError("Source asset filename collision")
        target = output / file.name
        if not target.exists():
            os.link(file, target)
        elif sha256(target) != digest:
            raise RuntimeError("Previously prepared source asset changed")
        record = assets.setdefault(
            file.name,
            {
                "filename": file.name,
                "sha256": digest,
                "components": [],
                "license_obligations": [],
                "redistribution_approved": False,
                "retrieval_url": "https://github.com/drrrrigo/cactu-video-converter/releases/download/v0.1.0-beta.1/"
                + file.name,
                "retrieval_status": "PROPOSED_NOT_PUBLISHED",
                "upstream_source": url,
            },
        )
        if component not in record["components"]:
            record["components"].append(component)
        if obligation not in record["license_obligations"]:
            record["license_obligations"].append(obligation)

    app = output / ("Cactu-source-" + commit + ".tar")
    if not app.exists():
        subprocess.run(
            ["git", "archive", "--format=tar", "--output", str(app), commit], cwd=ROOT, check=True
        )
    asset(
        app,
        "Cactu / packaging recipe",
        "GPL-3.0-or-later application source; exact native candidate commit",
    )
    for e in read_json(ROOT / "release/ffmpeg-controlled-lock.json")["sources"]:
        asset(
            ROOT / "release/evidence/local/sources" / e["filename"],
            "FFmpeg combined executable / " + e["project"],
            "GPL corresponding-source build input (not an independent permissive-library source duty)",
            e["url"],
            expected=e["sha256"],
        )
    qt = read_json(ROOT / "release/qt-source-lock.json")
    for e in qt["archives"]:
        asset(
            ROOT / "release/evidence/local/sources" / e["filename"],
            "Qt / " + e["project"],
            "Selected GPL v3 module source and supplied upstream build scripts",
            e["url"],
            expected=e["sha256"],
        )
    ubuntu = {
        (p["source_package"], p["source_version"]): p
        for p in read_json(ROOT / "release/controlled-ubuntu-source-lock.json")["source_packages"]
    }
    msys = {
        (p["base"], p["version"]): p
        for p in read_json(ROOT / "release/controlled-msys-source-lock.json")["source_packages"]
    }
    icu = {e["sha256"]: e for e in read_json(ROOT / "release/qt-icu-source-lock.json")["files"]}
    python_extra = {
        name: e
        for e in read_json(ROOT / "release/python-incorporated-review.json")["dependencies"]
        for name in e["files"]
    }
    native = {
        e["sha256"]: e for e in read_json(ROOT / "release/native-file-source-mapping.json")["files"]
    }
    for report in sorted(reports.rglob("*-payload.json")):
        p = read_json(report)
        components = {c["id"]: c for c in p["components"]}
        actual_files = {f["path"]: f for f in p["files"]}
        prefix = "usr/bin/" if p["target"].startswith("linux") else ""

        def check_notice(relative, source):
            raw = source.read_bytes().replace(b"\r\n", b"\n")
            acceptable = {
                hashlib.sha256(data).hexdigest() for data in [raw, raw.replace(b"\n", b"\r\n")]
            }
            record = actual_files.get(prefix + "_internal/" + relative)
            if record is None or record["sha256"] not in acceptable:
                missing.append(
                    {
                        "component": p["artifact"]["filename"],
                        "missing_file": relative,
                        "completion": "Integrate the actual required notice and re-inventory; LF/CRLF is allowed, substantive differences are not",
                    }
                )

        projects = {
            f["qt_source_mapping"]["source_project"]
            for f in p["files"]
            if f.get("qt_source_mapping")
        }
        for notice in read_json(ROOT / "licenses/qt-6.11.2/provenance.json")["files"]:
            if notice["project"] in projects:
                check_notice(notice["packaged_file"], ROOT / notice["packaged_file"])
        check_notice(
            "licenses/python-native/CPython-3.14.7-INCORPORATED-NOTICES.rst",
            ROOT / "licenses/python-native/CPython-3.14.7-INCORPORATED-NOTICES.rst",
        )
        if p["target"].startswith("windows"):
            mappings = list(reports.rglob("msys-payload-notices.json"))
            if len(mappings) != 1:
                raise RuntimeError("Exact Windows MSYS notice map required")
            for dll in read_json(mappings[0])["files"]:
                for notice in dll["notices"]:
                    if actual_files.get(notice["path"], {}).get("sha256") != notice["sha256"]:
                        missing.append(
                            {
                                "component": dll["path"],
                                "missing_file": notice["path"],
                                "completion": "Restore exact hash-matched supplier notice and re-inventory",
                            }
                        )
        wrapper = p.get("executable_container_wrapper")
        if wrapper:
            rows.append(
                {
                    "platform": p["target"],
                    "payload": p["payload_kind"],
                    "component": "AppImage static runtime"
                    if p["target"].startswith("linux")
                    else "Inno Setup prefix",
                    "file": p["artifact"]["filename"]
                    + ":prefix[0:"
                    + str(wrapper["prefix_bytes"])
                    + "]",
                    "sha256": wrapper["prefix_sha256"],
                    "license": "MIT + LGPL-2.1-or-later + linked permissive/runtime-exception terms"
                    if p["target"].startswith("linux")
                    else "Inno permissive + applicable incorporated runtime terms",
                    "required_action": "retain specific notices and supplied LGPL source/relink material"
                    if p["target"].startswith("linux")
                    else "retain Inno copyright/website notices and Pascal Script acknowledgement; use actual runtime scope",
                    "evidence": [
                        "release/runtime-source-delivery.json"
                        if p["target"].startswith("linux")
                        else "release/inno-runtime-review.json",
                        wrapper["pinned_input_sha256"],
                    ],
                    "status": "ENGINEERING_EVIDENCE_PREPARED",
                }
            )
        for f in p["files"]:
            if f["type"] != "native":
                continue
            c = components[f["component_id"]]
            project = c["project"]
            license = c.get("license", "UNRESOLVED")
            requirement = "retain applicable notice and attribution"
            evidence = []
            status = "ENGINEERING_EVIDENCE_PREPARED"
            source = None
            if c.get("origin") == "build-host-debian-package":
                license = UBUNTU.get(project, "UNRESOLVED")
                source = ubuntu.get((project, c["version"]))
                evidence.append(c.get("notice"))
                if copyleft(license):
                    requirement = "supply corresponding library source/patches; retain license; dynamic replacement information"
                    if source:
                        cache = (
                            ROOT
                            / "release/evidence/local/ubuntu-sources"
                            / source["cache_subdirectory"]
                        )
                        for e in [source["dsc"], *source["parts"]]:
                            asset(
                                cache / e["filename"],
                                project,
                                license + " dynamic library source/patches",
                                e["url"],
                            )
                    else:
                        missing.append(
                            {
                                "component": project,
                                "version": c["version"],
                                "missing_file": "exact Ubuntu source package",
                                "completion": "Retain exact source package and patches",
                            }
                        )
            elif c.get("origin") == "exact-msys2-package-by-sha256":
                license = c["license"]
                requirement = c["required_action"]
                evidence.append(c["notice"])
                source = msys.get((project, c["version"]))
                # Non-system libraries linked into the GPL FFmpeg aggregate are
                # supplied for that combined-work source scope, not because MIT
                # or BSD independently requires source publication. Compiler
                # runtimes retain their explicit exception/System Library scope.
                if c.get("source_delivery_required") or "GCC-exception" not in license:
                    if source:
                        asset(
                            ROOT
                            / "release/evidence/local/msys-sources"
                            / source["archive"]["filename"],
                            project,
                            license
                            + " library source/recipe for selected GPL FFmpeg aggregate (independent permissive terms remain notice-only)",
                            source["archive"]["url"],
                        )
                    else:
                        missing.append(
                            {
                                "component": project,
                                "version": c["version"],
                                "missing_file": "exact MSYS source archive",
                                "completion": "Retain matching source-only package",
                            }
                        )
            elif f.get("qt_source_mapping"):
                q = f["qt_source_mapping"]
                license = "GPL-3.0-only (eligible module code) + incorporated independent terms"
                requirement = "provide selected module source, upstream build information and actual module/third-party notices"
                evidence = [q["source_archive"], q["packaged_notice_directory"]]
                if q["source_project"] == "UNRESOLVED":
                    status = "ENGINEERING_BLOCKED"
                    missing.append(
                        {
                            "component": f["path"],
                            "missing_file": "Qt module mapping",
                            "completion": "Map actual module and acquire exact source/notices",
                        }
                    )
            elif f["sha256"] in icu:
                icu_lock = read_json(ROOT / "release/qt-icu-source-lock.json")
                asset(
                    ROOT / "release/evidence/local/sources" / icu_lock["filename"],
                    "Qt linked ICU",
                    "Proposed selected GPL Qt aggregate source support; Unicode permissive terms alone impose notices, not standalone source publication",
                    icu_lock["url"],
                    expected=icu_lock["sha256"],
                )
                license = "Unicode-DFS-2016 AND incorporated ICU third-party terms"
                evidence = ["licenses/icu-73.2/icu4c/LICENSE"]
                requirement = "retain ICU copyright/license/third-party notices; no standalone source-publication requirement under these permissive terms"
            elif f["sha256"] in native:
                entry = native[f["sha256"]]
                tag = entry.get("dependency_tag", "")
                license = (
                    "bzip2-1.0.6"
                    if "bzip2" in tag
                    else "LicenseRef-Public-Domain"
                    if "xz-" in tag
                    else "Apache-2.0"
                    if "openssl" in tag
                    else "Zlib"
                )
                evidence = ["release/native-file-source-mapping.json"]
                requirement = "retain PSF and actual incorporated permissive/public-domain dependency notices; no universal source/reproducibility obligation"
            elif project.startswith("Microsoft Windows"):
                license = "Microsoft conditional redistribution grant"
                requirement = "Owner establish applicable license/REDIST rights or approve official-prerequisite strategy"
                status = "HUMAN LEGAL / OWNER DECISION"
                evidence = ["docs/WINDOWS_RUNTIME_REDISTRIBUTION.md"]
            elif project.startswith("FFmpeg/"):
                license = "GPL-3.0-or-later combined executable"
                requirement = "corresponding controlled source inputs, build recipe and applicable dependency notices"
                evidence = [
                    "release/controlled-baseline.json",
                    "release/ffmpeg-controlled-lock.json",
                ]
            elif project == "CPython" and Path(f["path"]).name in python_extra:
                dependency = python_extra[Path(f["path"]).name]
                license = (
                    dependency["license"]
                    if f["path"].endswith(".dll")
                    else "Python-2.0 AND " + dependency["license"]
                )
                requirement = "retain exact CPython incorporated copyright/license notices; no independent source-publication duty under these permissive terms"
                evidence = [
                    "release/python-incorporated-review.json",
                    "licenses/python-native/CPython-3.14.7-INCORPORATED-NOTICES.rst",
                ]
            elif project == "CPython":
                license = "Python-2.0 + incorporated per-file terms"
                evidence = ["licenses/Python-3.14.7.txt", "release/python-native-source-lock.json"]
                requirement = "retain PSF/native notices; source availability retained as attribution evidence, not universal permissive-license source duty"
            elif "Inno" in project:
                license = "Inno permissive + Pascal Script acknowledgement + LZMA public-domain/linking-exception terms"
                requirement = "retain original copyright/website notices, required Pascal Script acknowledgement and runtime notices"
                evidence = ["release/inno-runtime-review.json", "THIRD_PARTY_NOTICES.md"]
            elif "PyInstaller" in project:
                license = "GPL-2.0-or-later WITH Bootloader-exception"
                requirement = "retain bootloader exception and embedded run-time hook Apache notices; no automatic GPL source duty for the combined application from the exception"
                evidence = ["licenses/packaging-runtimes/PyInstaller-6.16.0-COPYING.txt"]
            elif project == "UNRESOLVED" or license == "UNRESOLVED":
                status = "ENGINEERING_BLOCKED"
                missing.append(
                    {
                        "component": f["path"],
                        "missing_file": "actual license/origin attribution",
                        "completion": "Resolve actual file origin and license",
                    }
                )
            if license == "UNRESOLVED":
                status = "ENGINEERING_BLOCKED"
                missing.append(
                    {
                        "component": f["path"],
                        "missing_file": "per-file license classification",
                        "completion": "Classify the actual library from its supplier notice, not the whole build package",
                    }
                )
            if c.get("missing_packaged_notice"):
                status = "ENGINEERING_BLOCKED"
                missing.append(
                    {
                        "component": f["path"],
                        "missing_file": c["missing_packaged_notice"],
                        "completion": "Integrate required actual notice and re-inventory",
                    }
                )
            rows.append(
                {
                    "platform": p["target"],
                    "payload": p["payload_kind"],
                    "component": project,
                    "file": f["path"],
                    "sha256": f["sha256"],
                    "license": license,
                    "required_action": requirement,
                    "evidence": evidence,
                    "status": status,
                }
            )
    runtime = read_json(ROOT / "release/runtime-source-delivery.json")
    runtime_file = ROOT.parent / "blocker-clone-build/source-delivery" / runtime["filename"]
    if not runtime_file.exists():
        runtime_file = (
            ROOT.parent.parent / "blocker-clone-build/source-delivery" / runtime["filename"]
        )
    if runtime_file.is_file() and sha256(runtime_file) != runtime["sha256"]:
        raise RuntimeError("Runtime source/relink archive changed")
    asset(
        runtime_file,
        "AppImage LGPL-linked prefix",
        "LGPL source/relink objects/instructions for actual static components",
    )
    instructions = output / "RECIPIENT-SOURCE-INSTRUCTIONS.txt"
    instructions.write_text(
        "PROPOSED ONLY — NO PUBLICATION OR HUMAN APPROVAL\nCandidate source commit: "
        + commit
        + "\nVerify SHA256 for every indexed file. Unpack Cactu-source TAR for exact source, locks, workflows and build scripts. FFmpeg: acquire/cache indexed source inputs under release/evidence/local/sources and use scripts/build_controlled_ffmpeg.py with the recorded native tool profile. Qt: supplied module archives include CMake and PySide build scripts; see upstream README and licenses/NATIVE_LIBRARY_REPLACEMENT.md. Ubuntu sources: dpkg-source -x the indexed .dsc with its original/debian archives. MSYS source-only archives contain PKGBUILD, patches and upstream source; use native MSYS makepkg tooling. Runtime source/relink TAR includes its own instructions and replacement objects. General available build tools are prerequisites, not automatically shipped code. Future release-asset URLs in this index are proposals and do not exist as a published offer.\n"
    )
    asset(
        instructions,
        "all recipients",
        "source retrieval, hash verification and build/replacement information",
    )
    result = {
        "candidate_source_commit": commit,
        "candidate_binary_artifacts": artifacts,
        "classification": "PROPOSED_PENDING_HUMAN_REVIEW",
        "complete_corresponding_source": False,
        "assets": list(assets.values()),
        "remaining_engineering": missing,
        "proposed_materials_prepared": not missing,
        "recipient_notice_location": "Each exact binary package contains _internal/licenses (Linux usr/bin/_internal/licenses), including actual native-system/MSYS, Qt and Python notices. The exact Cactu source archive also contains supplier notice material. Refer to component-review.json for the finite per-file mapping.",
        "human_decisions": [
            {
                "id": "MSVC-RIGHTS",
                "affected": "actual Microsoft runtime DLLs in Windows payloads",
                "condition": "applicable Visual Studio redistribution terms and REDIST grant",
                "owner_answer": "Owner does not know qualifying rights; keep as legal pending (2026-11-21)",
                "responsible": "owner / qualified legal reviewer",
                "resolution": "Confirm qualifying grant, or choose official prerequisite and implement/test changed installer/portable/offline behavior",
                "completion": "Written decision tied to actual files/versions and strategy",
            },
            {
                "id": "FINAL-LICENSE-SOURCE-APPROVAL",
                "affected": "exact candidate binaries and proposed source/notice set",
                "responsible": "human license reviewer / owner",
                "resolution": "Review finite component table and proposed assets; approve exact identities separately",
                "completion": "Explicit approved records; no automatic flag change",
            },
        ],
        "publication_approved": False,
    }
    (output / "SOURCE-ASSETS.json").write_text(json.dumps(result, indent=2) + "\n")
    (destination / "proposed-source-assets.json").write_text(json.dumps(result, indent=2) + "\n")
    (destination / "component-review.json").write_text(
        json.dumps(
            {"candidate_source_commit": commit, "files": rows, "human_approval": False}, indent=2
        )
        + "\n"
    )
    with (destination / "component-review.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "platform",
                "payload",
                "component",
                "file",
                "sha256",
                "license",
                "required_action",
                "evidence",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(
        "Candidate",
        commit,
        "native rows",
        len(rows),
        "proposed assets",
        len(assets),
        "engineering gaps",
        len(missing),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("reports", type=Path)
    p.add_argument("destination", type=Path)
    args = p.parse_args()
    prepare(args.reports, args.destination)
