"""Join immutable payload evidence to retained sources without approving distribution."""

import argparse
import hashlib
import json
from pathlib import Path

from release_common import ROOT, read_json, sha256


def resolve(payload_path, root=ROOT, controlled_manifest=None):
    payload = read_json(payload_path)
    packages = {
        (p["source_package"], p["source_version"]): p
        for p in read_json(root / "release/ubuntu-source-lock.json")["source_packages"]
    }
    controlled = read_json(controlled_manifest) if controlled_manifest else None
    if controlled:
        lock_path = root / "release/ffmpeg-controlled-lock.json"
        locked = read_json(lock_path)
        lf_bytes = lock_path.read_bytes().replace(b"\r\n", b"\n")
        accepted_hashes = {
            hashlib.sha256(data).hexdigest()
            for data in [lf_bytes, lf_bytes.replace(b"\n", b"\r\n")]
        }
        expected_inputs = [
            entry
            for entry in locked["sources"]
            if entry["project"] != "AMF" or controlled["target"].startswith("windows")
        ]
        if (
            controlled["source_lock_sha256"] not in accepted_hashes
            or controlled["source_inputs"] != expected_inputs
        ):
            raise RuntimeError("Controlled source lock does not match this build")
        suffix = ".exe" if controlled["target"].startswith("windows") else ""
        for name, output in controlled["outputs"].items():
            if not any(
                Path(f["path"]).name == name + suffix and f["sha256"] == output["sha256"]
                for f in payload["files"]
            ):
                raise RuntimeError("Controlled manifest executable does not match payload: " + name)
        for package in read_json(root / "release/controlled-ubuntu-source-lock.json")[
            "source_packages"
        ]:
            packages[(package["source_package"], package["source_version"])] = package
    exact_native = {}
    for lock in ["native-file-source-mapping.json", "qt-icu-source-lock.json"]:
        path = root / "release" / lock
        if path.is_file():
            for entry in read_json(path)["files"]:
                exact_native.setdefault(entry["sha256"], []).append(
                    {"manifest": "release/" + lock, "record": entry}
                )
    components = {c["id"]: c for c in payload["components"]}
    rows = []
    for file in payload["files"]:
        component = components[file["component_id"]]
        project = component["project"]
        evidence = []
        obligations = []
        mapping = file.get("qt_source_mapping")
        if component.get("origin") == "build-host-debian-package":
            source = packages.get((project, component["version"]))
            if source and source["status"] == "RETAINED":
                evidence.append(
                    {
                        "manifest": "release/controlled-ubuntu-source-lock.json"
                        if controlled
                        else "release/ubuntu-source-lock.json",
                        "source_package": project,
                        "source_version": component["version"],
                        "descriptor_sha256": source["dsc"]["sha256"],
                    }
                )
                obligations += ["license_conditions_review", "recipient_source_delivery"]
            else:
                obligations += ["corresponding_source", "build_and_patches"]
        elif mapping:
            evidence.append(mapping)
            obligations += [
                "wheel_build_and_third_party_correspondence",
                "third_party_notice_scope",
                "recipient_source_delivery",
            ]
        elif project.startswith("FFmpeg/"):
            evidence += (
                [
                    {
                        "manifest": controlled_manifest.name,
                        "sha256": sha256(controlled_manifest),
                        "recipe_sha256": controlled["recipe_sha256"],
                        "source_lock_sha256": controlled["source_lock_sha256"],
                        "source_inputs": controlled["source_inputs"],
                    }
                ]
                if controlled
                else [
                    "release/ffmpeg-source-lock.json",
                    "release/ffmpeg-provider-build-evidence.json",
                ]
            )
            obligations += (
                [
                    "native_transitive_toolchain_build_correspondence",
                    "per_library_notice_scope_review",
                    "durable_binary_and_source_delivery",
                ]
                if controlled
                else [
                    "complete_linked_corresponding_source",
                    "generated_vendored_inputs_and_patches",
                    "per_library_notices",
                    "durable_binary_and_source_delivery",
                ]
            )
        elif project.startswith("Microsoft Windows"):
            evidence.append(component["corresponding_source"])
            obligations += ["supplier_redistribution_grant_and_terms"]
        elif project in {"PySide6_Essentials", "PySide6_Addons", "shiboken6"}:
            evidence.append("release/qt-source-lock.json")
            obligations += [
                "individual_upstream_source_and_build_correspondence",
                "individual_license_and_notices",
            ]
        elif project == "CPython":
            evidence.append("release/source-evidence.json: CPython 3.14.7 core source")
            if file["type"] == "native":
                obligations += ["python_native_third_party_source_build_and_notices"]
        elif "Inno" in project:
            evidence.append("licenses/packaging-runtimes/inno-components")
            obligations += ["exact_generated_stub_component_and_notice_scope"]
        elif "AppImage" in project:
            evidence.append("release/runtime-source-delivery.json")
            obligations += ["static_component_terms_review", "recipient_source_delivery"]
        evidence += exact_native.get(file["sha256"], [])
        rows.append(
            {
                "path": file["path"],
                "sha256": file["sha256"],
                "type": file["type"],
                "component_id": file["component_id"],
                "project": project,
                "version": component.get("version"),
                "license_record": component.get("license"),
                "packaged_notice_record": component.get("notice"),
                "copy_source_evidence": file.get("copy_source_evidence"),
                "source_resolution_evidence": evidence,
                "open_obligations": obligations,
            }
        )
    return {
        "source_commit": payload["source_commit"],
        "artifact": payload["artifact"],
        "payload_report": payload_path.name,
        "payload_report_sha256": sha256(payload_path),
        "technical_license_audit_complete": False,
        "license_audit_approved": False,
        "publication_approved": False,
        "scope": "Evidence join, not legal clearance. Empty open_obligations is not individual approval. Embedded modules and outer wrapper retain the original inventory records.",
        "dynamic_replacement_information": "licenses/NATIVE_LIBRARY_REPLACEMENT.md",
        "outer_wrapper": payload["executable_container_wrapper"],
        "outer_wrapper_review": (
            "AppImage: controlled source/relink receipt and final terms/delivery review; "
            "Setup/uninstaller: exact incorporated component scope remains under review"
        ),
        "files": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--controlled-build-manifest", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            resolve(args.payload, controlled_manifest=args.controlled_build_manifest), indent=2
        )
        + "\n",
        encoding="utf-8",
    )
