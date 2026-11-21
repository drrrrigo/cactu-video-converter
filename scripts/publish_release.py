"""Explicit pre-release publication after all preceding gates succeed."""

import os
import subprocess
import sys
from pathlib import Path
from branding_metadata import PRODUCT_NAME, __version__
from checksums import expected_names
from release_common import ROOT, read_json
from release_policy import distribution_allowed
from release_gate import check_publication, source_commit
from source_assets import approved_source_assets

if __name__ == "__main__":
    directory = Path(sys.argv[1])
    distribution_allowed()
    check_publication(
        directory,
        evidence_path=ROOT / "build/manual-promotion.json",
        owner_approval_path=ROOT / "build/owner-publication-approval.json",
    )
    tag = "v" + __version__
    sources = approved_source_assets(
        directory,
        read_json(ROOT / "release/config.json"),
        read_json(ROOT / "build/owner-publication-approval.json"),
        source_commit(ROOT),
    )
    if os.environ.get("GITHUB_REF") != "refs/tags/" + tag:
        raise RuntimeError("Unexpected release ref")
    # No --clobber: an existing release/tag is not silently replaced.
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            *[str(directory / name) for name in (*expected_names(), "SHA256SUMS.txt")],
            *[str(path) for path in sources],
            "--repo",
            "drrrrigo/cactu-video-converter",
            "--verify-tag",
            "--prerelease",
            "--title",
            f"{PRODUCT_NAME} {tag}",
            "--notes-file",
            str(ROOT / f"docs/RELEASE_NOTES_{__version__}.md"),
        ],
        check=True,
    )
