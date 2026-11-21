"""Packaging provenance must resolve aliases without inventing redistribution rights."""

import sys
import tempfile
import json
import io
import tarfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qt_payload_policy import (
    filter_gui_plugins,
    windows_network_plugins,
    windows_application_binaries,
)
from payload_inventory import resolve_copy_origin
from payload_diff import compare_payloads
from qt_file_mapping import qt_file_mapping
from retain_ffmpeg_sources import acquire, archive_url, recipe_inputs
from build_controlled_runtime import build as build_runtime


class PayloadResolutionTests(unittest.TestCase):
    def test_retained_version_tag_keeps_immutable_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            entry = {
                "filename": "tag.tar.gz",
                "repo": "https://github.com/example/project.git",
                "revision": "v1.2.3",
                "recipe_file": "example.sh",
                "status": "NOT_RETAINED",
            }
            (cache / entry["filename"]).write_bytes(b"retained")
            import hashlib

            retained = dict(
                entry,
                revision="a" * 40,
                declared_revision="v1.2.3",
                status="RETAINED",
                sha256=hashlib.sha256(b"retained").hexdigest(),
            )
            self.assertEqual(acquire(entry, cache, retained), retained)

    def test_changed_cached_source_is_not_silently_relocked(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            entry = {
                "filename": "source.tar.gz",
                "repo": "https://github.com/example/project.git",
                "revision": "a" * 40,
                "recipe_file": "example.sh",
                "status": "NOT_RETAINED",
            }
            (cache / entry["filename"]).write_bytes(b"changed")
            retained = dict(entry, status="RETAINED", sha256="b" * 64)
            result = acquire(entry, cache, retained)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("refusing to relock", result["reason"])

    def test_recipe_recognizes_svn_pin_instead_of_treating_it_as_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "recipe.tar"
            body = (
                b'SCRIPT_REPO="https://svn.code.sf.net/p/lame/svn/trunk/lame"\nSCRIPT_REV="7153"\n'
            )
            with tarfile.open(file, "w") as archive:
                info = tarfile.TarInfo("recipe/scripts.d/lame.sh")
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
            entry = recipe_inputs(file)[0]
            self.assertEqual(entry["revision"], "7153")
            self.assertEqual(entry["source_method"], "svn-export")

    def test_windows_os_contracts_are_removed_but_vc_runtime_stays(self):
        entries = [
            (name, "supplier/" + name, "BINARY")
            for name in [
                "api-ms-win-crt-runtime-l1-1-0.dll",
                "api-ms-win-core-console-l1-1-0.dll",
                "ucrtbase.dll",
                "VCRUNTIME140.dll",
                "MSVCP140.dll",
                "Qt6Core.dll",
            ]
        ]
        self.assertEqual(windows_application_binaries(entries), entries[3:])

    def test_controlled_runtime_refuses_changed_recipe_before_acquiring_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "release").mkdir()
            (root / "scripts").mkdir()
            (root / "scripts/build_controlled_appimage_runtime.sh").write_text("changed")
            (root / "release/appimage-controlled-lock.json").write_text(
                json.dumps({"build_recipe_sha256": "a" * 64})
            )
            with self.assertRaisesRegex(RuntimeError, "recipe changed"):
                build_runtime(root)

    def test_windows_tls_requires_native_backend_before_excluding_openssl(self):
        plugins = [("qschannelbackend.dll", "tls"), ("qopensslbackend.dll", "tls")]
        self.assertEqual(windows_network_plugins(plugins), plugins[:1])
        with self.assertRaisesRegex(RuntimeError, "Schannel"):
            windows_network_plugins(plugins[1:])

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
