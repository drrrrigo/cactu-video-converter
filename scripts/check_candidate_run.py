"""A beta tag promotes only successful candidate artifacts from the same commit."""

import json
import os
import subprocess

if __name__ == "__main__":
    run_id = os.environ.get("BETA_CANDIDATE_RUN_ID", "")
    if not run_id.isdigit():
        raise RuntimeError("BETA_CANDIDATE_RUN_ID must identify the tested candidate workflow")
    result = subprocess.run(
        ["gh", "api", f"repos/drrrrigo/cactu-video-converter/actions/runs/{run_id}"],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    if (
        data["head_sha"] != os.environ["GITHUB_SHA"]
        or data["conclusion"] != "success"
        or data["event"] != "workflow_dispatch"
        or data["path"] != ".github/workflows/release.yml"
    ):
        raise RuntimeError("Candidate source/run does not match the final tag")
