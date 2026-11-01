"""Beta integrity, runtime/startup, archive safety and publication blockers."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from branding_metadata import __version__, write_windows_metadata
from checksums import expected_names, generate
from release_common import safe_member, download
from release_gate import check_publication
from stage_ffmpeg import unpack
from video_converter import __package_version__
from video_converter.ffmpeg.capabilities import REQUIRED, require_capabilities, table_names
from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.services.startup import check_writable_environment
from video_converter.services.diagnostics import record_error, report


class ReleaseIntegrityTests(unittest.TestCase):
    def test_beta_single_source_and_windows_numeric_version(self):
        self.assertEqual(__version__, "0.1.0-beta.1")
        self.assertEqual(__package_version__, "0.1.0b1")
        with tempfile.TemporaryDirectory() as folder:
            version, include = write_windows_metadata(Path(folder))
            self.assertIn("filevers=(0, 1, 0, 1)", version.read_text())
            self.assertIn("0.1.0-beta.1", version.read_text())
            self.assertIn('NumericVersion "0.1.0.1"', include.read_text())

    def test_capability_tables_parse_exact_names_and_fail_missing_mandatory_features(self):
        self.assertEqual(
            table_names(" DE matroska,webm  Matroska\n V..... libx264 H264\n ... loudnorm A->A\n"),
            {"matroska", "webm", "libx264", "loudnorm"},
        )
        tables = {flag: set(names) for flag, names in REQUIRED.items()}
        require_capabilities(tables)
        tables["-filters"].remove("alimiter")
        with self.assertRaisesRegex(RuntimeError, "alimiter"):
            require_capabilities(tables)

    def test_download_mismatch_leaves_previous_file_and_rejects_insecure_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "archive"
            target.write_bytes(b"previous")
            with self.assertRaises(RuntimeError):
                download("http://invalid.example/a", "a" * 64, target)
            self.assertEqual(target.read_bytes(), b"previous")
            with self.assertRaises(RuntimeError):
                download("https://example.com/a", "not-a-hash", target)
            self.assertFalse(safe_member("../escape.exe"))
            self.assertFalse(safe_member("/absolute"))
            self.assertFalse(safe_member("C:\\evil"))
            self.assertTrue(safe_member("fixed/bin/ffmpeg"))

    def test_archive_exact_members_hashes_and_no_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "payload.zip"
            contents = {
                "fixed/ffmpeg": b"ffmpeg",
                "fixed/ffprobe": b"ffprobe",
                "fixed/LICENSE": b"license",
            }
            with zipfile.ZipFile(archive, "w") as z:
                for name, data in contents.items():
                    z.writestr(name, data)
                z.writestr("../escape", b"never extract")
            metadata = {
                "archive_format": "zip",
                "ffmpeg_member": "fixed/ffmpeg",
                "ffprobe_member": "fixed/ffprobe",
                "license_member": "fixed/LICENSE",
                "ffmpeg_sha256": hashlib.sha256(b"ffmpeg").hexdigest(),
                "ffprobe_sha256": hashlib.sha256(b"ffprobe").hexdigest(),
                "license_sha256": hashlib.sha256(b"license").hexdigest(),
            }
            target = root / "stage"
            target.mkdir()
            unpack(archive, metadata, target)
            self.assertEqual((target / "ffmpeg").read_bytes(), b"ffmpeg")
            self.assertFalse((root / "escape").exists())
            metadata["ffmpeg_member"] = "../escape"
            with self.assertRaises(RuntimeError):
                unpack(archive, metadata, target)

    def test_checksums_come_from_all_three_actual_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(RuntimeError):
                generate(root)
            for name in expected_names():
                (root / name).write_bytes(name.encode())
            result = generate(root).read_text()
            self.assertEqual(len(result.splitlines()), 3)
            for name in expected_names():
                self.assertIn(hashlib.sha256(name.encode()).hexdigest() + "  " + name, result)

    def test_publication_stops_at_unapproved_licensing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "release").mkdir()
            (root / "release/config.json").write_text(
                json.dumps(
                    {
                        "repository": "https://github.com/drrrrigo/cactu-video-converter",
                        "source_license": "GPL-3.0-or-later",
                        "publication_approved": False,
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "publication_approved"):
                check_publication(root, root=root)

    def test_publication_requires_exact_tested_commit_and_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "release").mkdir()
            (root / "vendor/ffmpeg").mkdir(parents=True)
            config = {
                "repository": "https://github.com/drrrrigo/cactu-video-converter",
                "source_license": "GPL-3.0-or-later",
                "publication_approved": True,
                "license_audit_approved": True,
                "security_audit_approved": True,
                "manual_candidate_evidence": "evidence.json",
            }
            (root / "release/config.json").write_text(json.dumps(config))
            (root / "vendor/ffmpeg/manifest.json").write_text(
                json.dumps(
                    {
                        "linux": {
                            "redistribution_approved": True,
                            "corresponding_source_complete": True,
                        }
                    }
                )
            )
            evidence = {
                "source_commit": "a" * 40,
                "windows11_installer": {"passed": True},
                "windows11_portable": {"passed": True},
                "linux_desktop": {"passed": True},
                "artifacts": {},
            }
            for name in expected_names():
                (root / name).write_bytes(b"tested")
                evidence["artifacts"][name] = hashlib.sha256(b"tested").hexdigest()
            (root / "evidence.json").write_text(json.dumps(evidence))
            with patch("release_gate.source_commit", return_value="a" * 40):
                check_publication(root, root=root)
            (root / expected_names()[0]).write_bytes(b"different binary")
            with (
                patch("release_gate.source_commit", return_value="a" * 40),
                self.assertRaisesRegex(RuntimeError, "differs"),
            ):
                check_publication(root, root=root)
            with (
                patch("release_gate.source_commit", return_value="b" * 40),
                self.assertRaisesRegex(RuntimeError, "different source"),
            ):
                check_publication(root, root=root)


class StartupAndDiagnosticsTests(unittest.TestCase):
    def test_config_and_temp_writability_failure_is_user_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            check_writable_environment(Path(folder))
            with patch(
                "video_converter.services.startup.tempfile.TemporaryFile",
                side_effect=PermissionError("private details"),
            ):
                with self.assertRaisesRegex(RuntimeError, "configuration directory"):
                    check_writable_environment(Path(folder))
            with patch(
                "video_converter.services.startup.tempfile.TemporaryDirectory",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaisesRegex(RuntimeError, "temporary workspace"):
                    check_writable_environment(Path(folder))

    def test_frozen_missing_binaries_cannot_fall_back_to_path(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", folder, create=True),
            patch("shutil.which", side_effect=AssertionError("No PATH fallback")),
        ):
            with self.assertRaises(RuntimeError):
                FFmpegRuntime.locate(allow_system_development=True)

    def test_general_diagnostics_include_versions_architecture_and_error_category_without_media(
        self,
    ):
        runtime = FFmpegRuntime(
            Path("ffmpeg"), Path("ffprobe"), "ffmpeg version 9.0.2", "ffprobe version 9.0.2"
        )
        record_error("RuntimeError")
        result = report(runtime)
        for value in (__version__, "Architecture:", "FFprobe:", "RuntimeError", "no telemetry"):
            self.assertIn(value, result)
        self.assertNotIn(str(Path.home()), result)

    def test_release_workflow_requires_pre_release_and_no_pr_publishing(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/release.yml").read_text()
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("environment: public-beta", workflow)
        self.assertIn("check_candidate_run.py", workflow)
        script = (root / "scripts/publish_release.py").read_text()
        self.assertIn('"--prerelease"', script)
        self.assertNotIn("--clobber", script.replace("# No --clobber:", ""))


class AtomicOutputSafetyTests(unittest.TestCase):
    def test_no_clobber_and_explicit_overwrite(self):
        from video_converter.services.output_commit import commit_output

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            partial = root / "partial"
            target = root / "output"
            partial.write_bytes(b"verified output")
            target.write_bytes(b"concurrent original")
            with self.assertRaises(FileExistsError):
                commit_output(partial, target)
            self.assertEqual(target.read_bytes(), b"concurrent original")
            self.assertEqual(partial.read_bytes(), b"verified output")
            target.unlink()
            commit_output(partial, target)
            self.assertEqual(target.read_bytes(), b"verified output")
            self.assertFalse(partial.exists())
            partial.write_bytes(b"explicit new output")
            commit_output(partial, target, overwrite=True)
            self.assertEqual(target.read_bytes(), b"explicit new output")


class UnexpectedErrorRecoveryTests(unittest.TestCase):
    def test_exception_is_logged_without_private_traceback_in_dialog(self):
        from PySide6.QtWidgets import QApplication, QWidget
        from video_converter.ui.error_reporter import ErrorReporter

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        _app = QApplication.instance() or QApplication([])
        window = QWidget()
        reporter = ErrorReporter(window)
        messages = []

        def display(box):
            messages.append(box.text())
            return 0

        with (
            patch("video_converter.ui.error_reporter.QMessageBox.exec", display),
            self.assertLogs("video_converter.ui.error_reporter", level="CRITICAL"),
        ):
            reporter.hook(RuntimeError, RuntimeError("/private/user/movie.mkv"), None)
        self.assertTrue(messages)
        self.assertNotIn("/private/user", messages[0])
        self.assertIn("unexpected error", messages[0])
        self.assertFalse(reporter.visible)
        window.close()


if __name__ == "__main__":
    unittest.main()
