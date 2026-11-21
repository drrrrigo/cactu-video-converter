import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from source_assets import source_assets


class SourceAssetsTests(unittest.TestCase):
    def test_unapproved_or_changed_source_never_reaches_publisher(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "sources.tar"
            file.write_bytes(b"review fixture")
            entry = {
                "filename": file.name,
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "redistribution_approved": False,
            }
            manifest = {"complete_corresponding_source": False, "assets": [entry]}
            index = root / "SOURCE-ASSETS.json"
            index.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, "Complete"):
                source_assets(root)
            manifest["complete_corresponding_source"] = True
            index.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, "not approved"):
                source_assets(root)
            entry["redistribution_approved"] = True
            index.write_text(json.dumps(manifest))
            self.assertEqual(source_assets(root), [index, file])
            file.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                source_assets(root)

    def test_source_approval_is_bound_to_protected_owner_and_actual_candidates(self):
        from source_assets import approved_source_assets

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "sources.tar"
            source.write_bytes(b"owned source review fixture")
            manifest = {
                "complete_corresponding_source": True,
                "candidate_source_commit": "a" * 40,
                "candidate_binary_artifacts": {"app.exe": "b" * 64},
                "assets": [
                    {
                        "filename": source.name,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "redistribution_approved": True,
                    }
                ],
            }
            index = root / "SOURCE-ASSETS.json"
            index.write_text(json.dumps(manifest))
            owner = {
                "approved": True,
                "approved_by": "drrrrigo",
                "source_commit": "a" * 40,
                "artifacts": manifest["candidate_binary_artifacts"],
                "source_assets_manifest_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
            }
            self.assertEqual(
                approved_source_assets(
                    root, {"source_assets_manifest_sha256": None}, owner, "a" * 40
                ),
                [index, source],
            )
            owner["artifacts"] = {"different.exe": "c" * 64}
            with self.assertRaisesRegex(RuntimeError, "different candidate"):
                approved_source_assets(root, {}, owner, "a" * 40)

    def test_source_approval_never_bypasses_configured_pin_or_missing_owner(self):
        from source_assets import approved_source_assets

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            index = root / "SOURCE-ASSETS.json"
            index.write_text("{}")
            owner = {
                "approved": True,
                "approved_by": "drrrrigo",
                "source_commit": "a" * 40,
                "source_assets_manifest_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
            }
            with self.assertRaisesRegex(RuntimeError, "Configured"):
                approved_source_assets(
                    root, {"source_assets_manifest_sha256": "b" * 64}, owner, "a" * 40
                )
            owner["approved"] = False
            with self.assertRaisesRegex(RuntimeError, "attestation"):
                approved_source_assets(root, {}, owner, "a" * 40)
