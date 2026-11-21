"""Exercise Windows packaging with the pinned reference runtime TEST FIXTURE.

This does not select the legacy provider for release or qualify a controlled
candidate. It isolates prerequisite packaging tests when source hosting is down.
No executable is uploaded. Production stage/build/release gates are unchanged.
"""

import json
import shutil
import sys
from unittest.mock import patch

from release_common import ROOT, read_json, sha256
from windows_runtime import assert_no_runtime


def main():
    if sys.platform != "win32":
        raise RuntimeError("Native Windows required")
    import build_release
    from video_converter.ffmpeg.runtime import FFmpegRuntime

    manifest = ROOT / "vendor/ffmpeg/manifest.json"
    binary = FFmpegRuntime.bundled_directory()
    expected = read_json(manifest)["windows-x86_64"]
    if sha256(binary / "ffmpeg.exe") != expected["ffmpeg_sha256"]:
        raise RuntimeError("Reference fixture is not the exact pinned provider")
    fixture = (
        binary,
        manifest,
        {
            "fixture_only": True,
            "kind": "pinned-reference-provider",
            "not_selected_release_implementation": True,
        },
    )
    with (
        patch("stage_controlled_runtime.stage", return_value=fixture),
        patch.object(sys, "argv", ["build_release.py", "--candidate"]),
    ):
        build_release.main()
    output = ROOT / "dist/candidate"
    report = read_json(output / "windows-x86_64-build.json")
    report["candidate_stage"] = "PREREQUISITE_TEST_FIXTURE_NOT_RELEASE"
    report["fixture_runtime"] = report.pop("controlled_runtime")
    assert_no_runtime(ROOT / "dist/CactuVideoConverter")
    destination = ROOT / "build/prerequisite-package"
    destination.mkdir(exist_ok=True)
    for p in output.glob("*.json"):
        if not p.name.endswith("-build.json"):
            shutil.copy2(p, destination / p.name)
    (destination / "fixture-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "TEST FIXTURE passed: no bundled Microsoft runtime; portable and installed conversion/uninstall smoke. Not a controlled release candidate."
    )


if __name__ == "__main__":
    main()
