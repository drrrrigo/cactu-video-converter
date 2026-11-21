import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ffmpeg_tool_profile import verify_tool_profile


class ToolProfileTests(unittest.TestCase):
    def test_same_version_with_changed_compiler_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "profile.json"
            expected = {"gcc": {"version": "gcc 16.2", "sha256": "a" * 64}}
            file.write_text(json.dumps({"profiles": {"native": {"tools": expected}}}))
            self.assertEqual(verify_tool_profile(file, "native", expected), "native")
            changed = {"gcc": {"version": "gcc 16.2", "sha256": "b" * 64}}
            with self.assertRaisesRegex(RuntimeError, "fingerprint changed"):
                verify_tool_profile(file, "native", changed)

    def test_missing_pinned_build_tool_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "profile.json"
            file.write_text(
                json.dumps({"profiles": {"native": {"tools": {"gcc": {"sha256": "a" * 64}}}}})
            )
            with self.assertRaisesRegex(RuntimeError, "tool set differs"):
                verify_tool_profile(file, "native", {})
