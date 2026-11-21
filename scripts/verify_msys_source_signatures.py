"""Verify retained source signatures with an explicitly hash-locked official keyring."""

import argparse
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from release_common import ROOT, download, read_json, sha256


def verify():
    key_lock = read_json(ROOT / "release/msys-keyring-lock.json")
    cache = ROOT / "release/evidence/local/msys-sources"
    package = cache / key_lock["filename"]
    if sha256(package) != key_lock["sha256"]:
        raise RuntimeError("Official keyring package hash mismatch")
    results = []
    with tempfile.TemporaryDirectory(prefix="cactu-source-signatures-") as folder:
        work = Path(folder)
        keyring = work / "msys2.gpg"
        with tarfile.open(package) as archive:
            keyring.write_bytes(archive.extractfile("usr/share/pacman/keyrings/msys2.gpg").read())
            revoked = archive.extractfile("usr/share/pacman/keyrings/msys2-revoked").read().decode()
        published_keyring_sha256 = sha256(keyring)
        if keyring.read_bytes().startswith(b"-----BEGIN PGP PUBLIC KEY BLOCK-----"):
            binary = work / "msys2-binary.gpg"
            subprocess.run(
                [
                    "gpg",
                    "--homedir",
                    str(work),
                    "--batch",
                    "--dearmor",
                    "--output",
                    str(binary),
                    str(keyring),
                ],
                check=True,
                capture_output=True,
            )
            keyring = binary
        for source in read_json(ROOT / "release/controlled-msys-source-lock.json")[
            "source_packages"
        ]:
            files = [cache / source[k]["filename"] for k in ["signature", "archive"]]
            for kind, file in zip(["signature", "archive"], files):
                if sha256(file) != source[kind]["sha256"]:
                    raise RuntimeError("Source/signature bytes changed")
            result = subprocess.run(
                [
                    "gpgv",
                    "--homedir",
                    str(work),
                    "--keyring",
                    str(keyring),
                    "--status-fd",
                    "1",
                    *map(str, files),
                ],
                capture_output=True,
                text=True,
            )
            valid = [
                line.split()[2]
                for line in result.stdout.splitlines()
                if line.startswith("[GNUPG:] VALIDSIG ")
            ]
            if (
                result.returncode
                or len(valid) != 1
                or valid[0] in revoked
                or valid[0] not in key_lock["accepted_package_signers"]
            ):
                raise RuntimeError(
                    "Invalid/revoked MSYS2 source signature: "
                    + source["base"]
                    + " "
                    + result.stderr
                )
            results.append(
                {
                    "base": source["base"],
                    "version": source["version"],
                    "archive_sha256": source["archive"]["sha256"],
                    "signature_sha256": source["signature"]["sha256"],
                    "signer_fingerprint": valid[0],
                    "gpg_status": result.stdout.splitlines(),
                }
            )
        return {
            "keyring_package": key_lock,
            "keyring_member_sha256": published_keyring_sha256,
            "verification_keyring_sha256": sha256(keyring),
            "results": results,
            "verification_tools": {
                name: {
                    "sha256": sha256(Path(shutil.which(name)).resolve()),
                    "version": subprocess.check_output([name, "--version"], text=True).splitlines()[
                        0
                    ],
                }
                for name in ["gpg", "gpgv"]
            },
            "scope": "Cryptographic signature verification against the hash-locked publisher keyring obtained over official HTTPS. No independent offline root-of-trust or legal/source-completeness approval is claimed.",
            "complete_corresponding_source": False,
            "publication_approved": False,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquire-keyring", action="store_true")
    args = parser.parse_args()
    if args.acquire_keyring:
        lock = read_json(ROOT / "release/msys-keyring-lock.json")
        download(
            lock["url"],
            lock["sha256"],
            ROOT / "release/evidence/local/msys-sources" / lock["filename"],
        )
    output = ROOT / "release/evidence/msys-source-signature-verification.json"
    output.write_text(json.dumps(verify(), indent=2) + "\n")
    print("Retained MSYS2 source signatures verified")
