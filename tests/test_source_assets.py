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
