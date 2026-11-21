"""Inspect cached supplier DLLs and extracted official DLLs. Never install them.

Normalized comparison excludes only the PE checksum, certificate directory entry
and certificate table. This is byte-comparison evidence, not WinVerifyTrust,
Authenticode validation, an assertion that re-signing is permitted, or a license.
"""

import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from release_common import ROOT, read_json, sha256
from windows_runtime import microsoft_runtime


def inspect(file):
    data = file.read_bytes()
    if data[:2] != b"MZ":
        raise RuntimeError("Expected a PE file")
    pe = struct.unpack_from("<I", data, 60)[0]
    if data[pe : pe + 4] != b"PE\0\0":
        raise RuntimeError("Invalid PE header")
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x20B:
        raise RuntimeError("Expected x64 PE32+")
    directory = optional + 112 + 32
    certificate, size = struct.unpack_from("<II", data, directory)
    if not size or certificate < directory + 8 or certificate + size != len(data):
        raise RuntimeError("Unexpected certificate layout; manual review required")
    normalized = (
        data[: optional + 64] + data[optional + 68 : directory] + data[directory + 8 : certificate]
    )
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "certificate.der"
        path.write_bytes(data[certificate + 8 : certificate + size])
        result = subprocess.run(
            ["openssl", "pkcs7", "-inform", "DER", "-in", str(path), "-print_certs", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
    return {
        "sha256": sha256(file),
        "size": len(data),
        "normalized_file_sha256": hashlib.sha256(normalized).hexdigest(),
        "certificate_size": size,
        "certificate_subjects": [s for s in result.stdout.splitlines() if s.startswith("subject=")],
        "signature_trust_verified": False,
    }


def review(cache, output):
    report = read_json(
        ROOT
        / "release/evidence/rc1-qualification-3b19839/windows/packaging/windows-x86_64-portable-payload.json"
    )
    official = [
        {
            "file": p.relative_to(cache).as_posix(),
            "name": p.name.removesuffix("_amd64"),
            **inspect(p),
        }
        for p in sorted(cache.glob("*-cabs/1/*-files/*_amd64"))
        if microsoft_runtime(p.name.removesuffix("_amd64"))
    ]
    rows = []
    for old in report["files"]:
        if not microsoft_runtime(old["path"]):
            continue
        relative = Path(old["path"]).relative_to("_internal")
        if len(relative.parts) == 1:
            relative = Path("CPython") / relative.name.lower()
        else:
            relative = relative.parent / relative.name.lower()
        source = cache / "wheel-dlls" / relative
        actual = inspect(source)
        if actual["sha256"] != old["sha256"]:
            raise RuntimeError(
                "Supplier bytes differ from exact historical payload: " + old["path"]
            )
        same_name = [o for o in official if o["name"].lower() == source.name.lower()]
        rows.append(
            {
                "historical_payload": old["path"],
                "supplier": old["copy_source_evidence"]["distribution"],
                "version": old["native"]["version_resource"]["FileVersion"],
                **actual,
                "official_whole_file_matches": [
                    o["file"] for o in same_name if o["sha256"] == actual["sha256"]
                ],
                "official_normalized_matches": [
                    o["file"]
                    for o in same_name
                    if o["normalized_file_sha256"] == actual["normalized_file_sha256"]
                ],
            }
        )
    result = {
        "scope": "Exact ten DLLs in historical clean 3b19839 audit packages; new system-prerequisite packages omit them",
        "method": __doc__,
        "files": rows,
        "official_extracted_files": official,
        "owner_license_acceptance_established": False,
        "redistribution_approved": False,
        "official_archives": read_json(cache / "download-receipt.json"),
        "cpython_source": read_json(cache / "cpython-embed-receipt.json"),
        "terms": read_json(cache / "official-terms-receipt.json"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Verified actual supplier bytes:",
        len(rows),
        "Qt normalized matches:",
        sum(bool(r["official_normalized_matches"]) for r in rows),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cache", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    review(args.cache, args.output)
