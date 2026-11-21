"""Exercise an isolated candidate; HEVC fixture generation uses the old provider.

Cactu decodes HEVC but does not encode it. This separates test-fixture creation
from tested candidate decoding/conversion without adding libx265 to the build.
"""

import argparse
import json
import subprocess
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from release_common import ROOT, sha256

sys.path.insert(0, str(ROOT / "src"))
from video_converter.ffmpeg.capabilities import capability_tables, require_capabilities
from video_converter.ffmpeg.runtime import FFmpegRuntime


def validate(candidate, output):
    suffix = ".exe" if sys.platform == "win32" else ""
    original = FFmpegRuntime.bundled_directory() / ("ffmpeg" + suffix)
    binary = candidate / ("ffmpeg" + suffix)
    tables = capability_tables(binary)
    require_capabilities(tables)
    if not {"mpeg4", "av1", "vp8", "vp9", "png", "flac", "ac3", "opus"} <= tables["-decoders"]:
        raise RuntimeError("Common input decoder regression")
    required_hw = {"h264_nvenc", "h264_qsv", "h264_amf" if suffix else "h264_vaapi"}
    if not required_hw <= tables["-encoders"]:
        raise RuntimeError("Missing required native hardware interfaces")
    if "mpeg4" not in tables["-decoders"] or "libxvid" in tables["-encoders"]:
        raise RuntimeError("Native Xvid input decoding / external encoder boundary incorrect")
    if "libdav1d" not in tables["-decoders"]:
        raise RuntimeError("Software AV1 decoder is required; native av1 is hardware-only")
    with tempfile.TemporaryDirectory(prefix="cactu-av1-fixture-") as folder:
        av1 = Path(folder) / "input.mkv"
        subprocess.run(
            [
                str(original),
                "-hide_banner",
                "-nostdin",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=s=128x72:d=0.2",
                "-frames:v",
                "1",
                "-c:v",
                "libaom-av1",
                "-cpu-used",
                "8",
                "-threads",
                "2",
                str(av1),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        decoded = subprocess.run(
            [
                str(binary),
                "-hide_banner",
                "-nostdin",
                "-i",
                str(av1),
                "-frames:v",
                "1",
                "-f",
                "framehash",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        if not any(
            line.strip() and not line.startswith("#") for line in decoded.stdout.splitlines()
        ):
            raise RuntimeError("AV1 fixture produced no decoded frame")
        reference = subprocess.run(
            [
                str(original),
                "-hide_banner",
                "-nostdin",
                "-i",
                str(av1),
                "-frames:v",
                "1",
                "-f",
                "framehash",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        def hashes(text):
            return [
                line.rsplit(",", 1)[-1].strip()
                for line in text.splitlines()
                if line.strip() and not line.startswith("#")
            ]

        if hashes(decoded.stdout) != hashes(reference.stdout):
            raise RuntimeError("Software AV1 decoded pixels differ from the provider reference")
        av1_fixture_sha256 = sha256(av1)
    real_run = subprocess.run
    real_bundled = FFmpegRuntime.bundled_directory
    fixtures = []

    def run(args, *positional, **kwargs):
        if isinstance(args, list) and "libx265" in args:
            args = [str(original), *args[1:]]
            fixtures.append("HEVC input fixture generated with unchanged provider")
        return real_run(args, *positional, **kwargs)

    def bundled():
        return real_bundled() if getattr(sys, "frozen", False) else candidate

    with (
        patch.object(FFmpegRuntime, "bundled_directory", side_effect=bundled),
        patch("subprocess.run", side_effect=run),
    ):
        tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=1).run(tests)
    previous = capability_tables(original)
    report = {
        "candidate_sha256": sha256(binary),
        "av1_software_decode": True,
        "av1_decoded_pixels_match_provider": True,
        "av1_fixture_sha256": av1_fixture_sha256,
        "tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "hevc_provider_fixture_count": len(fixtures),
        "capabilities": {k: sorted(v) for k, v in tables.items()},
        "capability_difference": {
            k: {"removed": sorted(previous[k] - v), "added": sorted(v - previous[k])}
            for k, v in tables.items()
        },
        "publication_approved": False,
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    if not result.wasSuccessful():
        raise RuntimeError("Controlled candidate failed compatibility tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    validate(args.candidate.resolve(), args.output)
