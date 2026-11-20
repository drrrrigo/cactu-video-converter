"""Packaging provenance must resolve aliases without inventing redistribution rights."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qt_payload_policy import filter_gui_plugins
from payload_inventory import resolve_copy_origin
from payload_diff import compare_payloads
from qt_file_mapping import qt_file_mapping
from retain_ffmpeg_sources import archive_url


class PayloadResolutionTests(unittest.TestCase):
    def test_source_acquisition_rejects_mutable_refs_and_unreviewed_hosts(self):
        for repo, revision in [
            ("https://github.com/FFmpeg/FFmpeg.git", "master"),
            ("https://unreviewed.invalid/source.git", "a" * 40),
        ]:
            with self.assertRaises(ValueError):
                archive_url(repo, revision)
        self.assertEqual(
            archive_url("https://github.com/FFmpeg/FFmpeg.git", "a" * 40),
            "https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/" + "a" * 40,
        )

    def test_only_pdf_and_virtual_keyboard_plugins_are_filtered(self):
        names = [
            "libqpdf.so",
            "qtvirtualkeyboardplugin.dll",
            "libqxcb.so",
            "libqwayland.so",
            "qwindows.dll",
            "libqoffscreen.so",
            "libqsvg.so",
            "libibusplatforminputcontextplugin.so",
            "libqgtk3.so",
        ]
        actual = filter_gui_plugins([(str(Path("plugins") / n), "plugins") for n in names])
        self.assertEqual([Path(s).name for s, _ in actual], names[2:])

    def test_collect_alias_chain_resolves_to_actual_copy_source(self):
        source = Path("/synthetic/Qt/lib/libQt6Core.so.6")
        origins = {
            "libQt6Core.so.6": (Path("PySide6/Qt/lib/libQt6Core.so.6"), "SYMLINK"),
            "PySide6/Qt/lib/libQt6Core.so.6": (source, "BINARY"),
        }
        self.assertEqual(resolve_copy_origin(origins, "libQt6Core.so.6"), (source, "BINARY"))

    def test_alias_cycle_is_unresolved(self):
        self.assertIsNone(
            resolve_copy_origin({"a": (Path("b"), "SYMLINK"), "b": (Path("a"), "SYMLINK")}, "a")
        )

    def test_payload_diff_separates_removal_from_provenance_resolution(self):
        before = {
            "artifact": {},
            "source_commit": "a",
            "components": [{"id": "u", "project": "UNRESOLVED"}],
            "files": [
                {"path": "keep.dll", "sha256": "same", "component_id": "u"},
                {"path": "remove.dll", "sha256": "old", "component_id": "u"},
            ],
        }
        after = {
            "artifact": {},
            "source_commit": "b",
            "components": [{"id": "known", "project": "Supplier"}],
            "files": [{"path": "keep.dll", "sha256": "same", "component_id": "known"}],
            "components_requiring_review": 1,
        }
        result = compare_payloads(before, after)
        self.assertEqual(result["removed"], ["remove.dll"])
        self.assertEqual(result["provenance_resolved"][0]["path"], "keep.dll")
        self.assertTrue(result["provenance_resolved"][0]["same_bytes"])
        self.assertFalse(result["license_approval"])

    def test_unexpected_qml_library_does_not_inherit_qtbase_license_mapping(self):
        mapping = qt_file_mapping("_internal/libQt6Quick.so.6", {"archives": []})
        self.assertEqual(mapping["source_project"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
