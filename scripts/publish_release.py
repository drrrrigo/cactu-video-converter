"""Explicit pre-release publication after all preceding gates succeed."""

import os
import subprocess
import sys
from pathlib import Path
from branding_metadata import PRODUCT_NAME, __version__
from checksums import expected_names
from release_common import ROOT, read_json, sha256, digest_valid
from release_policy import distribution_allowed
from release_gate import check_publication
from source_assets import source_assets

if __name__ == "__main__":
    directory = Path(sys.argv[1])
    distribution_allowed()
    check_publication(
        directory,
        evidence_path=ROOT / "build/manual-promotion.json",
        owner_approval_path=ROOT / "build/owner-publication-approval.json",
    )
    tag = "v" + __version__
    expected_sources = read_json(ROOT / "release/config.json").get("source_assets_manifest_sha256")
    if (
        not digest_valid(expected_sources or "")
        or sha256(directory / "SOURCE-ASSETS.json") != expected_sources
    ):
        raise RuntimeError(
            "Exact source asset index has not been approved in the release configuration"
        )
    sources = source_assets(directory)
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
