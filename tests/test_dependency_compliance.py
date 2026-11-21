import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from msys_payload_notices import integrate
from release_common import sha256
from stage_controlled_runtime import checked_build


class DependencyComplianceTests(unittest.TestCase):
    def fixture(self, root):
        (root / "release").mkdir()
        (root / "release/msys-runtime-obligations.json").write_text(
            json.dumps(
                {
                    "example": {
                        "license": "MIT",
                        "source_delivery_required": False,
                        "required_action": "retain notices",
                    }
                }
            )
        )
        evidence = root / "evidence"
        evidence.mkdir()
        notice = evidence / "notices/ucrt64/share/licenses/example/LICENSE"
        notice.parent.mkdir(parents=True)
        notice.write_text("Exact supplier notice\n")
        payload = root / "payload"
        (payload / "_internal").mkdir(parents=True)
        dll = payload / "_internal/example.dll"
        dll.write_bytes(b"actual DLL fixture")
        report = {
            "files": [
                {
                    "filename": dll.name,
                    "sha256": sha256(dll),
                    "package": "mingw-w64-ucrt-x86_64-example",
                    "version": "1",
                }
            ],
            "packages": [
                {
                    "name": "mingw-w64-ucrt-x86_64-example",
                    "base": "mingw-w64-example",
                    "version": "1",
                    "notices": [
                        {"file": notice.relative_to(evidence).as_posix(), "sha256": sha256(notice)}
                    ],
                }
            ],
        }
        file = evidence / "msys-native-evidence.json"
        file.write_text(json.dumps(report))
        return payload, file, dll

    def test_only_shipped_matching_dll_notice_is_integrated_and_mapped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload, evidence, dll = self.fixture(root)
            records = integrate(payload, evidence, root)
            self.assertIn(sha256(dll), records)
            self.assertEqual(
                (payload / "_internal/licenses/native-msys2/example/LICENSE").read_text(),
                "Exact supplier notice\n",
            )
            self.assertFalse(records[sha256(dll)]["source_delivery_required"])

    def test_same_filename_changed_bytes_rejects_attribution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload, evidence, dll = self.fixture(root)
            dll.write_bytes(b"different bytes")
            with self.assertRaisesRegex(RuntimeError, "bytes differ"):
                integrate(payload, evidence, root)

    def test_unshipped_package_is_not_added_to_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload, evidence, dll = self.fixture(root)
            dll.unlink()
            # No source DLLs means no supplier notices to claim as distributed.
            self.assertEqual(integrate(payload, evidence, root), {})

    def test_wrong_tool_profile_cannot_replace_selected_baseline(self):
        import shutil

        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in [
                "release/controlled-baseline.json",
                "release/ffmpeg-controlled-lock.json",
                "scripts/build_controlled_ffmpeg.py",
            ]:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repository / name, destination)
            work = root / "work"
            work.mkdir()
            build = json.loads(
                (
                    repository
                    / "release/evidence/controlled-ffmpeg-4e47/linux/ffmpeg-controlled/manifest.json"
                ).read_text()
            )
            build["verified_tool_fingerprint_profile"] = "wrong-profile"
            (work / "manifest.json").write_text(json.dumps(build))
            with self.assertRaisesRegex(RuntimeError, "tool profile"):
                checked_build(work, "linux-x86_64", root)

    def test_shipped_image_format_plugins_use_their_own_source_module(self):
        from qt_file_mapping import qt_file_mapping

        lock = {
            "version": "6.11.2",
            "archives": [
                {
                    "project": "qtimageformats",
                    "commit": "a" * 40,
                    "filename": "imageformats.tar.gz",
                    "url": "https://example.invalid/source",
                    "sha256": "b" * 64,
                }
            ],
        }
        for plugin in ["libqtiff.so", "qwebp.dll", "qicns.dll", "libqwbmp.so", "qtga.dll"]:
            result = qt_file_mapping("_internal/PySide6/Qt/plugins/imageformats/" + plugin, lock)
            self.assertEqual(result["source_project"], "qtimageformats")
