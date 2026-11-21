import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from join_msys_payload_evidence import join


class MsysEvidenceJoinTests(unittest.TestCase):
    def test_filename_match_without_byte_match_does_not_attribute_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload, installed = root / "payload.json", root / "installed.json"
            payload.write_text(
                json.dumps(
                    {
                        "artifact": {},
                        "files": [{"path": "same.dll", "sha256": "a" * 64, "type": "native"}],
                    }
                )
            )
            installed.write_text(
                json.dumps(
                    {
                        "packages": [],
                        "files": [
                            {
                                "filename": "same.dll",
                                "sha256": "b" * 64,
                                "package": "wrong",
                                "version": "1",
                            }
                        ],
                    }
                )
            )
            result = join(payload, installed, root / "output")
            self.assertEqual(result["matches"], [])
            self.assertEqual(len(result["unattributed_native_files"]), 1)

    def test_changed_notice_bytes_block_retention(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload, installed = root / "payload.json", root / "installed.json"
            payload.write_text(
                json.dumps(
                    {
                        "artifact": {},
                        "files": [{"path": "actual.dll", "sha256": "a" * 64, "type": "native"}],
                    }
                )
            )
            (root / "COPYING").write_text("changed notice")
            installed.write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "name": "library",
                                "version": "1",
                                "notices": [{"file": "COPYING", "sha256": "b" * 64}],
                            }
                        ],
                        "files": [
                            {
                                "sha256": "a" * 64,
                                "package": "library",
                                "version": "1",
                                "installed_path": "ucrt64/bin/actual.dll",
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "Invalid installed notice"):
                join(payload, installed, root / "output")
