"""Resolve published wheel hashes for exact versions; does not install or run them."""

import json
import re
from urllib.request import urlopen
from release_common import ROOT


def main():
    rows = [
        "# Generated from exact PyPI release metadata. Install with --require-hashes --only-binary=:all:.\n"
    ]
    provenance = []
    for line in (ROOT / "release/requirements.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_-]+)==([A-Za-z0-9.]+)", line)
        if not match:
            raise RuntimeError("Unpinned requirement: " + line)
        name, version = match.groups()
        metadata_url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urlopen(metadata_url, timeout=30) as response:
            data = json.load(response)
        wheels = [
            f for f in data["urls"] if f["packagetype"] == "bdist_wheel" and not f.get("yanked")
        ]
        if not wheels:
            raise RuntimeError("No usable wheels for " + name)
        hashes = sorted({f["digests"]["sha256"] for f in wheels})
        rows.append(
            line + " \\\n" + " \\\n".join("    --hash=sha256:" + value for value in hashes) + "\n"
        )
        provenance.append(
            {
                "name": name,
                "version": version,
                "metadata_url": metadata_url,
                "license_expression": data["info"].get("license_expression")
                or data["info"].get("license"),
                "project_urls": data["info"].get("project_urls"),
                "wheels": [
                    {"filename": f["filename"], "url": f["url"], "sha256": f["digests"]["sha256"]}
                    for f in wheels
                ],
                "source_archives": [
                    {"filename": f["filename"], "url": f["url"], "sha256": f["digests"]["sha256"]}
                    for f in data["urls"]
                    if f["packagetype"] == "sdist"
                ],
            }
        )
    (ROOT / "release/requirements.lock").write_text("\n".join(rows), encoding="utf-8")
    (ROOT / "release/dependency-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Locked {len(provenance)} exact releases with wheel SHA-256 values")


if __name__ == "__main__":
    main()
