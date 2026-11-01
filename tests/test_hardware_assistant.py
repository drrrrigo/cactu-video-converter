"""Hardware evidence, conservative classifications and official remediation."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector
from video_converter.hardware.inventory import (
    distribution,
    linux_inventory,
    windows_device,
    render_device,
)
from video_converter.hardware.diagnosis import (
    HardwareDiagnosisService,
    classify,
    expected_backends,
    inspect_features,
)
from video_converter.hardware.resources import DriverGuideRegistry, RESOURCES, trusted_url
from video_converter.hardware.report import diagnostic_report, sanitize
from video_converter.models.encoder import (
    EncoderBackend as Backend,
    EncoderSelection,
    HardwareEncoderCapability,
)
from video_converter.models.hardware_diagnosis import (
    DistributionFamily as Family,
    FailureCategory as Category,
    GpuDevice,
    GpuVendor as Vendor,
    HardwareInventory,
    LinuxDistribution,
    RenderDevice,
    Responsibility,
    RuntimeFeatures,
)

NODE = RenderDevice("/dev/dri/renderD129", True, True, True, "crw-rw----")
AMD = GpuDevice(
    "pci-amd", Vendor.AMD, "AMD Radeon RX 7700 XT", "1002", "747e", "amdgpu", "", True, (NODE,)
)
INTEL = GpuDevice(
    "pci-intel",
    Vendor.INTEL,
    "Intel Graphics",
    "8086",
    "1234",
    "i915",
    "",
    True,
    (replace(NODE, path="/dev/dri/renderD130"),),
)
NVIDIA = GpuDevice("pci-nvidia", Vendor.NVIDIA, "NVIDIA RTX", "10de", "1234", "nvidia", "1.2", True)
FEATURES = RuntimeFeatures(
    frozenset({"h264_vaapi", "h264_qsv", "h264_nvenc", "h264_amf"}),
    frozenset({"subtitles", "format", "hwupload"}),
    frozenset({"vaapi", "qsv", "cuda"}),
    True,
)
RUNTIME = FFmpegRuntime(
    Path("/usr/bin/ffmpeg"), Path("/usr/bin/ffprobe"), "FFmpeg 9.0.2", "FFprobe 9.0.2"
)
ARCH = LinuxDistribution("cachyos", ("arch",), "CachyOS", "", Family.ARCH)


def capability(
    backend=Backend.VAAPI, available=False, node=NODE.path, error="Initialization failed"
):
    encoder = {
        Backend.VAAPI: "h264_vaapi",
        Backend.INTEL_QSV: "h264_qsv",
        Backend.NVIDIA_NVENC: "h264_nvenc",
        Backend.AMD_AMF: "h264_amf",
    }[backend]
    return HardwareEncoderCapability(
        EncoderSelection(backend, node),
        encoder,
        backend.display_name,
        "linux",
        None,
        available,
        None if available else error,
        "" if available else error,
        probe_command=("ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=256x144", "-f", "null", "-"),
        probe_exit_code=0 if available else 1,
    )


def diagnosis(
    devices=(AMD,), caps=None, features=FEATURES, platform="linux", distro=ARCH, errors=()
):
    inventory = HardwareInventory(platform, platform, devices, distro, errors)
    return HardwareDiagnosisService(RUNTIME).diagnose(
        caps if caps is not None else (capability(),), features, inventory=inventory
    )


class InventoryTests(unittest.TestCase):
    def test_distribution_ids_and_families_without_evaluating_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "os-release"
            for identity, like, expected in [
                ("cachyos", "arch", Family.ARCH),
                ("ubuntu", "debian", Family.DEBIAN),
                ("fedora", "rhel", Family.FEDORA),
                ("opensuse-tumbleweed", "suse", Family.SUSE),
                ("strange", "", Family.UNKNOWN),
            ]:
                file.write_text(
                    f'ID={identity}\nID_LIKE="{like}"\nNAME="Test OS"\nVERSION_ID="42"\nX=$(touch malicious)\n'
                )
                result = distribution(file)
                self.assertEqual(result.family, expected)
                self.assertEqual(result.version, "42")
            self.assertFalse((Path(directory) / "malicious").exists())

    def test_windows_uses_structured_vendor_ids_and_preserves_driver_versions(self):
        for pci, vendor in [
            ("1002", Vendor.AMD),
            ("10de", Vendor.NVIDIA),
            ("8086", Vendor.INTEL),
            ("9999", Vendor.UNKNOWN),
        ]:
            result = windows_device(
                f"PCI\\VEN_{pci}&DEV_1234",
                "Misleading Intel NVIDIA AMD name",
                "display.dll",
                "12.34",
            )
            self.assertEqual(result.vendor, vendor)
            self.assertEqual(result.driver_version, "12.34")
            self.assertTrue(result.driver_detected)
        self.assertEqual(windows_device("unstructured", "NVIDIA").vendor, Vendor.UNKNOWN)

    def test_linux_multiple_gpus_nodes_bound_driver_and_no_external_utility(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pci, drm, dri = root / "pci", root / "drm", root / "dri"
            for path in (pci, drm, dri):
                path.mkdir()
            driver = root / "drivers/amdgpu"
            driver.mkdir(parents=True)
            for index, vendor in enumerate(("1002", "8086")):
                gpu = pci / f"0000:0{index}:00.0"
                gpu.mkdir()
                (gpu / "class").write_text("0x030000")
                (gpu / "vendor").write_text("0x" + vendor)
                (gpu / "device").write_text("0x1234")
                (gpu / "driver").symlink_to(driver, target_is_directory=True)
                (gpu / "product_name").write_text(f"GPU {index}")
                node = drm / f"renderD{129 + index}"
                node.mkdir()
                (node / "device").symlink_to(gpu, target_is_directory=True)
                (dri / node.name).write_bytes(b"node fixture")
            release = root / "os-release"
            release.write_text("ID=cachyos\nID_LIKE=arch")
            with patch("subprocess.run", side_effect=AssertionError("No CLI utility allowed")):
                result = linux_inventory(pci, drm, dri, release)
            self.assertEqual([d.vendor for d in result.devices], [Vendor.AMD, Vendor.INTEL])
            self.assertEqual(
                [d.render_nodes[0].path for d in result.devices],
                [str(dri / "renderD129"), str(dri / "renderD130")],
            )
            self.assertEqual(result.devices[0].driver, "amdgpu")
            self.assertEqual(result.distribution.family, Family.ARCH)
            (dri / "renderD129").unlink()
            result = linux_inventory(pci, drm, dri, release)
            self.assertFalse(result.devices[0].render_nodes[0].exists)

    def test_permission_and_missing_device_evidence(self):
        with (
            tempfile.NamedTemporaryFile() as file,
            patch("video_converter.hardware.inventory.os.access", return_value=False),
        ):
            node = render_device(Path(file.name))
            self.assertTrue(node.exists)
            self.assertFalse(node.readable or node.writable)
        self.assertFalse(render_device(Path("/nonexistent/renderD9000")).exists)

    def test_retest_rediscovery_and_encoder_cache(self):
        def run(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch(
            "video_converter.ffmpeg.hardware_detector.render_nodes",
            return_value=(Path("/dev/dri/renderD129"),),
        ) as nodes:
            detector = HardwareEncoderDetector(Path("ffmpeg"), run=run)
            first = detector.detect()
            count = nodes.call_count
            detector.detect()
            self.assertEqual(nodes.call_count, count)
            nodes.return_value = (Path("/dev/dri/renderD130"),)
            second = detector.detect(refresh=True)
            self.assertNotEqual(first, second)
            self.assertIn("/dev/dri/renderD130", [c.selection.device for c in second])


class DiagnosisTests(unittest.TestCase):
    def test_available_requires_real_probe_success(self):
        self.assertFalse(diagnosis().available)
        result = diagnosis(caps=(capability(available=True),))
        self.assertTrue(result.available)
        self.assertFalse(result.banner_eligible)
        self.assertEqual(result.findings[0].category, Category.AVAILABLE)
        # Actual success wins over an incomplete/stale supplemental table.
        self.assertTrue(
            diagnosis(
                caps=(capability(available=True),), features=replace(FEATURES, filters=frozenset())
            ).available
        )

    def test_missing_encoder_is_packaging_never_driver(self):
        result = diagnosis(features=replace(FEATURES, encoders=frozenset()))
        finding = result.findings[0]
        self.assertEqual(finding.category, Category.FFMPEG_ENCODER_MISSING)
        self.assertEqual(finding.responsibility, Responsibility.APPLICATION)
        self.assertEqual(DriverGuideRegistry().lookup(finding, "linux", ARCH).resources, ())
        self.assertEqual(
            diagnosis(features=replace(FEATURES, encoders=frozenset(), bundled=False))
            .findings[0]
            .responsibility,
            Responsibility.RUNTIME,
        )

    def test_required_filter_api_absence_is_runtime_build_error(self):
        for features in (
            replace(FEATURES, filters=frozenset({"format"})),
            replace(FEATURES, hardware_apis=frozenset()),
        ):
            self.assertEqual(
                diagnosis(features=features).findings[0].category,
                Category.APPLICATION_PACKAGING_ERROR,
            )

    def test_missing_render_node_permission_and_bound_driver(self):
        for gpu, expected in [
            (replace(AMD, render_nodes=()), Category.DEVICE_NODE_MISSING),
            (
                replace(AMD, render_nodes=(replace(NODE, readable=False),)),
                Category.DEVICE_PERMISSION_DENIED,
            ),
            (replace(AMD, driver="", driver_detected=False), Category.DRIVER_NOT_DETECTED),
        ]:
            probe = capability(node=None) if not gpu.render_nodes else capability()
            self.assertEqual(
                diagnosis(devices=(gpu,), caps=(probe,)).findings[0].category, expected
            )

    def test_unknown_failure_and_supported_signatures(self):
        for error, expected in [
            ("Failed for an unknown reason", Category.BACKEND_INITIALIZATION_FAILED),
            ("No capable devices found", Category.GPU_DETECTED_ENCODER_UNSUPPORTED),
            (
                "Driver does not support the required NVENC API",
                Category.DRIVER_TOO_OLD_OR_INCOMPATIBLE,
            ),
            ("Cannot load libnvidia-encode.so.1", Category.MISSING_SYSTEM_COMPONENT),
        ]:
            finding = diagnosis(caps=(capability(error=error),)).findings[0]
            self.assertEqual(finding.category, expected)
        self.assertEqual(diagnosis(caps=()).findings[0].category, Category.UNKNOWN)
        self.assertNotEqual(
            diagnosis(caps=(capability(error="Driver is installed but failed"),))
            .findings[0]
            .category,
            Category.DRIVER_TOO_OLD_OR_INCOMPATIBLE,
        )

    def test_no_gpu_is_informational_and_inventory_error_is_unknown(self):
        self.assertEqual(
            diagnosis(devices=(), caps=()).findings[0].category, Category.NO_SUPPORTED_GPU
        )
        self.assertFalse(diagnosis(devices=(), caps=()).banner_eligible)
        self.assertEqual(
            diagnosis(devices=(), caps=(), errors=("Inventory restricted",)).findings[0].category,
            Category.UNKNOWN,
        )
        self.assertEqual(
            diagnosis(devices=(replace(AMD, vendor=Vendor.UNKNOWN),), caps=()).findings[0].category,
            Category.NO_SUPPORTED_GPU,
        )

    def test_windows_vendor_success_failure_and_missing_encoder(self):
        for device, backend in [
            (AMD, Backend.AMD_AMF),
            (NVIDIA, Backend.NVIDIA_NVENC),
            (INTEL, Backend.INTEL_QSV),
        ]:
            for available in (True, False):
                result = diagnosis(
                    devices=(device,),
                    caps=(capability(backend, available, node=None),),
                    platform="win32",
                )
                self.assertEqual(result.available, available)
                self.assertEqual(result.findings[0].backend, backend)
                if not available:
                    self.assertNotEqual(result.findings[0].category, Category.DRIVER_NOT_DETECTED)
        result = diagnosis(
            devices=(NVIDIA,),
            caps=(capability(Backend.NVIDIA_NVENC, node=None),),
            platform="win32",
            features=replace(FEATURES, encoders=frozenset()),
        )
        self.assertEqual(result.findings[0].category, Category.FFMPEG_ENCODER_MISSING)

    def test_multiple_gpus_one_success_means_available_and_no_global_warning(self):
        caps = (
            capability(Backend.INTEL_QSV, True, INTEL.render_nodes[0].path),
            capability(Backend.NVIDIA_NVENC, node=None),
        )
        result = diagnosis(devices=(INTEL, NVIDIA), caps=caps)
        self.assertTrue(result.available)
        self.assertFalse(result.banner_eligible)
        self.assertTrue(any(f.category == Category.AVAILABLE for f in result.findings))
        self.assertTrue(any(f.category != Category.AVAILABLE for f in result.findings))

    def test_default_device_same_vendor_ambiguity_and_exact_node_association(self):
        other = replace(NVIDIA, id="second-nvidia")
        result = diagnosis(
            devices=(NVIDIA, other), caps=(capability(Backend.NVIDIA_NVENC, True, node=None),)
        )
        self.assertTrue(result.available)
        self.assertEqual({f.category for f in result.findings}, {Category.MULTIPLE_GPU_AMBIGUITY})
        missing = diagnosis(
            devices=(NVIDIA, other),
            caps=(capability(Backend.NVIDIA_NVENC, node=None),),
            features=replace(FEATURES, encoders=frozenset()),
        )
        self.assertEqual({f.category for f in missing.findings}, {Category.FFMPEG_ENCODER_MISSING})
        other = replace(
            AMD, id="other-amd", render_nodes=(replace(NODE, path="/dev/dri/renderD130"),)
        )
        result = diagnosis(
            devices=(AMD, other),
            caps=(capability(), capability(available=True, node="/dev/dri/renderD130")),
        )
        self.assertEqual(
            [f.category for f in result.findings],
            [Category.BACKEND_INITIALIZATION_FAILED, Category.AVAILABLE],
        )
        self.assertEqual(
            classify(
                AMD, Backend.VAAPI, capability(node="/dev/dri/renderD140"), FEATURES, "linux"
            ).category,
            Category.BACKEND_DEVICE_MISMATCH,
        )

    def test_semantic_backend_mapping_and_session_cache_identity(self):
        self.assertEqual(expected_backends(Vendor.AMD, "linux"), (Backend.VAAPI,))
        self.assertEqual(
            expected_backends(Vendor.INTEL, "linux"), (Backend.INTEL_QSV, Backend.VAAPI)
        )
        inventory = HardwareInventory("linux", "Linux", (AMD,), ARCH)
        with patch(
            "subprocess.run",
            side_effect=AssertionError("No processes while interpreting cached evidence"),
        ):
            service = HardwareDiagnosisService(RUNTIME, lambda: inventory)
            first = service.diagnose((capability(),), FEATURES)
            self.assertIs(first, service.diagnose((capability(),), FEATURES))
            changed = service.diagnose(
                (capability(),),
                FEATURES,
                inventory=replace(inventory, devices=(replace(AMD, driver_version="new"),)),
                refresh=True,
            )
            self.assertNotEqual(first.identity, changed.identity)

    def test_runtime_features_are_read_only_ffmpeg_queries(self):
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            text = (
                " V..... h264_vaapi GPU\n"
                if "-encoders" in command
                else " ... format V->V\n ... subtitles V->V\n ... hwupload V->V\n"
                if "-filters" in command
                else "Hardware acceleration methods:\nvaapi\nqsv\ncuda\n"
            )
            return subprocess.CompletedProcess(command, 0, text, "")

        detector = HardwareEncoderDetector(RUNTIME.ffmpeg, devices=(), run=run)
        result = inspect_features(detector, RUNTIME)
        self.assertIn("h264_vaapi", result.encoders)
        self.assertEqual(result.filters, frozenset({"format", "subtitles", "hwupload"}))
        self.assertEqual([c[-1] for c in commands], ["-encoders", "-filters", "-hwaccels"])


class GuideAndPrivacyTests(unittest.TestCase):
    def test_vendor_resources_and_no_driver_remedy_for_build_errors(self):
        registry = DriverGuideRegistry()
        for gpu, backend, key in [
            (AMD, Backend.AMD_AMF, "amd"),
            (NVIDIA, Backend.NVIDIA_NVENC, "nvidia"),
            (INTEL, Backend.INTEL_QSV, "intel"),
        ]:
            finding = diagnosis(
                devices=(gpu,), caps=(capability(backend, node=None),), platform="win32"
            ).findings[0]
            guide = registry.lookup(finding, "win32", LinuxDistribution())
            self.assertEqual(guide.resources[0].id, key)
            self.assertFalse(guide.optional_commands)
        finding = diagnosis(features=replace(FEATURES, encoders=frozenset())).findings[0]
        self.assertFalse(registry.lookup(finding, "win32", LinuxDistribution()).resources)

    def test_supported_families_and_unknown_distribution_do_not_guess_commands(self):
        for family, key in [
            (Family.ARCH, "arch"),
            (Family.DEBIAN, "debian"),
            (Family.FEDORA, "fedora"),
            (Family.SUSE, "suse"),
            (Family.UNKNOWN, "amd"),
        ]:
            distro = replace(ARCH, family=family, id="test")
            finding = diagnosis(devices=(replace(AMD, render_nodes=()),), distro=distro).findings[0]
            guide = DriverGuideRegistry().lookup(finding, "linux", distro)
            self.assertEqual([r.id for r in guide.resources], [key] if key else [])
            self.assertFalse(guide.optional_commands)

    def test_support_urls_are_static_https_and_cannot_be_injected(self):
        for item in RESOURCES:
            self.assertTrue(trusted_url(item))
            self.assertFalse(trusted_url(replace(item, url="https://evil.example/driver")))
            self.assertFalse(trusted_url(replace(item, url=item.url.replace("https:", "http:"))))
            self.assertTrue(item.last_reviewed)

    def test_sanitized_report_omits_home_media_paths_and_arbitrary_urls(self):
        error = f'Could not load {Path.home()}/Videos/PrivateMovie.mkv; "C:\\Users\\Secret Name\\Subtitles\\Private.ass" /tmp/private/subtitle.srt https://evil.example/secret\nPermission denied'
        result = diagnosis(caps=(capability(error=error),))
        report = diagnostic_report(result)
        for secret in (
            str(Path.home()),
            "PrivateMovie",
            "Secret Name",
            "Private.ass",
            "evil.example",
            "/tmp/private",
        ):
            self.assertNotIn(secret, report)
        self.assertIn(NODE.path, report)
        self.assertIn("FFmpeg 9.0.2", report)
        self.assertIn("DEVICE_PERMISSION_DENIED", report)
        self.assertEqual(
            sanitize("/dev/dri/renderD129 /dev/nvidia0"), "/dev/dri/renderD129 /dev/nvidia0"
        )


if __name__ == "__main__":
    unittest.main()


class NativeAdapterBoundaryTests(unittest.TestCase):
    def test_windows_adapter_api_and_registry_without_powershell_or_vendor_cli(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from video_converter.hardware.inventory import windows_adapters

        observed = []

        def enum(device, index, pointer, flags):
            observed.append((device, index, flags))
            if index > 0:
                return False
            item = pointer._obj
            self.assertGreater(item.cb, 0)
            item.DeviceName = "DISPLAY0"
            item.DeviceID = "PCI\\VEN_1002&DEV_747E"
            item.DeviceString = "AMD Radeon RX 7700 XT"
            item.DeviceKey = "\\Registry\\Machine\\System\\Graphics\\0000"
            item.StateFlags = 1
            return True

        winreg = MagicMock()
        values = {
            "InstalledDisplayDrivers": "amdgpu.dll",
            "DriverVersion": "32.1",
            "ProviderName": "AMD",
        }
        winreg.QueryValueEx.side_effect = lambda key, field: (values[field], 1)
        with (
            patch.dict("sys.modules", {"winreg": winreg}),
            patch(
                "ctypes.WinDLL", return_value=SimpleNamespace(EnumDisplayDevicesW=enum), create=True
            ),
            patch("subprocess.run", side_effect=AssertionError("No shell utilities")),
        ):
            adapters = windows_adapters()
        self.assertEqual(len(adapters), 1)
        self.assertEqual(adapters[0].vendor, Vendor.AMD)
        self.assertEqual(adapters[0].driver_version, "32.1")
        self.assertEqual(observed, [(None, 0, 0), (None, 1, 0)])
        self.assertEqual(winreg.OpenKey.call_args.args[1], "System\\Graphics\\0000")

    def test_sanitization_keeps_embedded_render_node_and_removes_actual_windows_paths(self):
        value = "vaapi=encode:/dev/dri/renderD128 C:\\Users\\Private\\movie.mkv"
        clean = sanitize(value)
        self.assertIn("vaapi=encode:/dev/dri/renderD128", clean)
        self.assertNotIn("Private", clean)
        self.assertNotIn("movie.mkv", clean)


class InventoryResilienceTests(unittest.TestCase):
    def test_optional_local_pci_names_and_missing_database(self):
        from video_converter.hardware.inventory import pci_device_name

        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "pci.ids"
            file.write_text(
                "1002  AMD\n\t747e  Navi 32 [RX 7700 XT / 7800 XT]\n8086  Intel\n\t747e  Different device\n"
            )
            self.assertEqual(
                pci_device_name("1002", "747e", (file,)), "Navi 32 [RX 7700 XT / 7800 XT]"
            )
            self.assertEqual(pci_device_name("1002", "0000", (file,)), "")
            self.assertEqual(pci_device_name("1002", "747e", (Path(folder) / "missing",)), "")

    def test_inventory_failure_cannot_remove_a_working_backend(self):
        def broken_inventory():
            raise PermissionError("restricted")

        service = HardwareDiagnosisService(RUNTIME, broken_inventory)
        result = service.diagnose((capability(available=True),), FEATURES)
        self.assertTrue(result.available)
        self.assertTrue(result.inventory.errors)
