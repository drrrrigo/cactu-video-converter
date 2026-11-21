"""Verify retained native source/supplier evidence against immutable archive locks."""

import tarfile
from pathlib import Path
from release_common import ROOT, read_json, download, sha256


def acquire():
    entries = read_json(ROOT / "release/python-native-source-lock.json")["records"]
    entries.append(read_json(ROOT / "release/qt-icu-source-lock.json"))
    for entry in entries:
        archive = download(
            entry["url"],
            entry["sha256"],
            ROOT / "release/evidence/local/sources" / entry["filename"],
        )
        with tarfile.open(archive) as bundle:
            for match in entry.get("matching_payload_files", []):
                import hashlib

                actual = hashlib.sha256(
                    bundle.extractfile(match["archive_member"]).read()
                ).hexdigest()
                if actual != match["sha256"]:
                    raise RuntimeError("Official supplier DLL differs from payload evidence")
            for notice in entry.get("license_files", []):
                relative = notice["member"].split("/", 1)[-1]
                if ".." in Path(relative).parts or Path(relative).is_absolute():
                    raise RuntimeError("Unsafe notice member")
                destination = ROOT / "licenses/python-native" / entry["declared_tag"] / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(bundle.extractfile(notice["member"]).read())
                if sha256(destination) != notice["sha256"]:
                    raise RuntimeError("Notice bytes changed")
        print("Verified", entry["filename"])


if __name__ == "__main__":
    acquire()
