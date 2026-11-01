"""Explicit pre-release publication after all preceding gates succeed."""

import os
import subprocess
import sys
from pathlib import Path
from branding_metadata import PRODUCT_NAME, __version__
from checksums import expected_names
from release_common import ROOT
from release_policy import distribution_allowed
from release_gate import check_publication

if __name__ == "__main__":
    directory = Path(sys.argv[1])
    distribution_allowed()
    check_publication(directory, evidence_path=ROOT / "build/manual-promotion.json")
    tag = "v" + __version__
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
