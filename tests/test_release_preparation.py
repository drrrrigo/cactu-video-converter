"""Release boundaries: matching runtime, clean commit and honest artifact inventories."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_environment import check_environment
from payload_inventory import inventory
from release_gate import check_payload_evidence, check_publication, check_manual_record
from release_policy import distribution_allowed


class ReleasePreparationTests(unittest.TestCase):
    def test_technical_review_cannot_be_bypassed_by_a_redistribution_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/config.json").write_text(
                json.dumps(
                    {"technical_license_audit_complete": False, "license_audit_approved": True}
                )
            )
            with self.assertRaisesRegex(RuntimeError, "technical dependency/source review"):
                distribution_allowed(root)

    def test_manual_pass_boolean_without_tester_date_and_scenarios_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "tester/date/environment"):
            check_manual_record("windows11_installer", {"passed": True})
        with self.assertRaisesRegex(RuntimeError, "scenario has not passed"):
            check_manual_record(
                "windows11_portable",
                {
                    "passed": True,
                    "tester": "synthetic fixture",
                    "test_date": "2026-11-20",
                    "os_build": "synthetic",
                    "scenario_results": {"W15": "FAIL"},
                },
            )

    def test_wrong_python_patch_cannot_create_a_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/toolchain.json").write_text('{"python":"3.14.7"}')
            with self.assertRaisesRegex(RuntimeError, "requires Python 3.14.7"):
                check_environment(root, python_version="3.14.8")

    def test_clean_commit_is_recorded_and_dirty_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/toolchain.json").write_text('{"python":"3.14.7"}')
            (root / "release/requirements.txt").write_text("")
            (root / "release/requirements.lock").write_text("# synthetic empty environment\n")

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init")
            git("add", ".")
            git(
                "-c",
                "user.name=Release tests",
                "-c",
                "user.email=tests@example.invalid",
                "commit",
                "-m",
                "fixture",
            )
            result = check_environment(root, python_version="3.14.7")
            self.assertEqual(result["source_commit"], git("rev-parse", "HEAD"))
            self.assertTrue(result["source_tree_clean"])
            (root / "release/requirements.txt").write_text("# changed after commit\n")
            with self.assertRaisesRegex(RuntimeError, "clean, committed"):
                check_environment(root, python_version="3.14.7")

    def test_unknown_native_file_is_inventoried_without_invented_license(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/component-sources.json").write_text("{}")
            payload = root / "payload"
            payload.mkdir()
            (payload / "unknown.so").write_bytes(b"\x7fELFsynthetic")
            artifact = root / "synthetic.AppImage"
            artifact.write_bytes(b"synthetic artifact")
            with patch("payload_inventory.wheel_owners", return_value={}):
                report = inventory(
                    payload,
                    artifact,
                    payload_kind="synthetic",
                    target="linux-x86_64",
                    destination=root / "report.json",
                    root=root,
                )
            self.assertEqual(report["file_count"], 1)
            self.assertEqual(report["files"][0]["path"], "unknown.so")
            self.assertEqual(report["components"][0]["license"], "UNRESOLVED")
            self.assertFalse(report["technical_license_complete"])

    def test_payload_symlink_cannot_disclose_a_host_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/component-sources.json").write_text("{}")
            payload = root / "payload"
            payload.mkdir()
            outside = root / "private-file"
            outside.write_bytes(b"never inventory this")
            (payload / "link").symlink_to(outside)
            with patch("payload_inventory.wheel_owners", return_value={}):
                with self.assertRaisesRegex(RuntimeError, "escapes"):
                    inventory(
                        payload,
                        outside,
                        payload_kind="synthetic",
                        target="linux-x86_64",
                        destination=root / "report.json",
                        root=root,
                    )

    def test_committed_boolean_does_not_substitute_for_explicit_owner_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release").mkdir()
            (root / "release/config.json").write_text(
                json.dumps(
                    {
                        "repository": "https://github.com/drrrrigo/cactu-video-converter",
                        "source_license": "GPL-3.0-or-later",
                        "publication_approved": True,
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "external owner attestation"):
                check_publication(root, root=root)

    def test_missing_inventory_blocks_publication_independently_of_boolean_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "inventory missing"):
                check_payload_evidence(Path(directory), "a" * 40)


if __name__ == "__main__":
    unittest.main()
