import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qt_payload_policy import windows_application_binaries
from windows_runtime import assert_no_runtime, microsoft_runtime, validate_clean_evidence


class WindowsRuntimePolicyTests(unittest.TestCase):
    def test_all_ten_actual_supplier_paths_are_removed_without_removing_gcc_or_qt(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads(
            (
                root
                / "release/evidence/rc1-qualification-3b19839/windows/packaging/windows-x86_64-portable-payload.json"
            ).read_text()
        )
        names = [f["path"] for f in report["files"] if microsoft_runtime(f["path"])]
        self.assertEqual(len(names), 10)
        entries = [
            (name, "supplier", "BINARY")
            for name in names + ["Qt6Core.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll"]
        ]
        self.assertEqual(
            [x[0] for x in windows_application_binaries(entries)],
            ["Qt6Core.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll"],
        )

    def test_postcollection_guard_rejects_nested_or_new_runtime_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / "_internal/other/MSVCP140_atomic_wait.dll"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"unexpected supplier runtime")
            with self.assertRaisesRegex(RuntimeError, "system-installed"):
                assert_no_runtime(root)

    def test_setup_removes_only_exact_legacy_app_paths_after_prerequisite_check(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads(
            (
                root
                / "release/evidence/rc1-qualification-3b19839/windows/packaging/windows-x86_64-portable-payload.json"
            ).read_text()
        )
        installer = (root / "packaging/windows/CactuVideoConverter.iss").read_text()
        for record in report["files"]:
            if microsoft_runtime(record["path"]):
                self.assertIn("{app}\\" + record["path"].replace("/", "\\"), installer)
        self.assertNotIn("{sys}\\MSVCP", installer)
        self.assertNotIn("{sys}\\VCRUNTIME", installer)

    def test_windows_backslashes_and_case_are_handled(self):
        self.assertTrue(microsoft_runtime(r"PySide6\VCRUNTIME140_1.DLL"))
        self.assertFalse(microsoft_runtime("libwinpthread-1.dll"))
        self.assertFalse(microsoft_runtime("msvcp140.dll.txt"))

    def clean_fixture(self):
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / "release/windows-runtime-policy.json").read_text())
        artifacts = {
            "CactuVideoConverter-Portable-0.1.0-beta.1.zip": "a" * 64,
            "CactuVideoConverter-Setup-0.1.0-beta.1.exe": "b" * 64,
        }
        base = dict(
            result="PASS",
            clean_windows_test=True,
            automatic_runtime_install=False,
            bundled_microsoft_runtime_files=0,
            guest_identity_sha256="c" * 64,
            os_build="26100",
            artifacts={"portable": "a" * 64, "setup": "b" * 64},
        )
        missing = dict(
            base,
            phase="Missing",
            probe_exit=10,
            installer_exit=7,
            system_dll_versions={name: None for name in policy["required_dlls"]},
        )
        smoke = {
            key: True
            for key in (
                "ok",
                "frozen",
                "runtime_bundled",
                "faststart",
                "original_unchanged",
                "quick_preview",
                "embedded_subtitle_queue",
                "loudness_queue",
            )
        }
        installed = dict(
            base,
            phase="Installed",
            probe_exit=0,
            installer_exit=0,
            uninstall="PASS",
            system_dll_versions={name: "14.52.37029.0" for name in policy["required_dlls"]},
            portable_smoke=smoke,
            installed_smoke=smoke,
        )
        return {"missing": missing, "installed": installed}, artifacts

    def test_complete_same_guest_exact_artifact_qualification_is_accepted(self):
        record, artifacts = self.clean_fixture()
        validate_clean_evidence(record, artifacts)

    def test_other_binary_or_guest_evidence_is_rejected(self):
        record, artifacts = self.clean_fixture()
        record["installed"]["guest_identity_sha256"] = "d" * 64
        with self.assertRaises(RuntimeError):
            validate_clean_evidence(record, artifacts)
        record, artifacts = self.clean_fixture()
        artifacts[next(iter(artifacts))] = "e" * 64
        with self.assertRaises(RuntimeError):
            validate_clean_evidence(record, artifacts)

    def test_host_with_existing_runtime_cannot_count_as_missing_baseline(self):
        record, artifacts = self.clean_fixture()
        record["missing"]["system_dll_versions"]["msvcp140.dll"] = "14.52.37029.0"
        with self.assertRaises(RuntimeError):
            validate_clean_evidence(record, artifacts)

    def test_partial_or_older_system_runtime_is_rejected(self):
        record, artifacts = self.clean_fixture()
        record["installed"]["system_dll_versions"]["vcruntime140.dll"] = "14.44.35211.0"
        with self.assertRaises(RuntimeError):
            validate_clean_evidence(record, artifacts)
