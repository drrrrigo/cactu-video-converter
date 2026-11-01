"""Hardware architecture tests requiring no physical GPU."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_converter.conversion.planner import plan
from video_converter.conversion.validator import ValidationError
from video_converter.ffmpeg.command_builder import build_command
from video_converter.ffmpeg.encoders import REGISTRY, get_backend, probe_command
from video_converter.ffmpeg.hardware_detector import HardwareEncoderDetector, encoder_names
from video_converter.media.ffprobe_service import parse_probe
from video_converter.models.conversion import SubtitleMode
from video_converter.models.encoder import (
    EncoderBackend, EncoderSelection, HardwareEncoderCapability, HardwareQuality,
)
from video_converter.presets.web_kosmi import settings_for


class HardwareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "video.mkv"
        self.source.write_bytes(b"fixture")
        self.media = parse_probe({
            "format": {"format_name": "matroska", "duration": "10"},
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "hevc",
                 "pix_fmt": "yuv420p10le", "width": 1920, "height": 1080},
                {"index": 1, "codec_type": "audio", "codec_name": "flac", "channels": 6},
                {"index": 3, "codec_type": "subtitle", "codec_name": "ass",
                 "tags": {"language": "por"}},
            ]}, self.source)

    def _capability(self, selection: EncoderSelection) -> HardwareEncoderCapability:
        adapter = get_backend(selection.backend)
        return HardwareEncoderCapability(selection, adapter.encoder_name, adapter.display_name,
                                         "test", None, True)

    def test_registry_and_models(self) -> None:
        self.assertEqual(set(REGISTRY), set(EncoderBackend))
        self.assertEqual(HardwareQuality.HIGH.label, "High Quality")
        self.assertNotEqual(EncoderSelection(EncoderBackend.VAAPI, "/dev/dri/renderD128"),
                            EncoderSelection(EncoderBackend.VAAPI, "/dev/dri/renderD129"))

    def test_explicit_hardware_requires_successful_probe(self) -> None:
        selected = EncoderSelection(EncoderBackend.NVIDIA_NVENC)
        settings = settings_for(self.source).customized(encoding_engine=selected)
        with self.assertRaisesRegex(ValidationError, "currently unavailable"):
            plan(self.media, settings)
        resolved = plan(self.media, settings, capabilities=(self._capability(selected),))
        self.assertEqual(resolved.encoding_engine, selected)
        self.assertIn("NVIDIA NVENC", resolved.description)

    def test_stream_copy_wins_over_selected_hardware(self) -> None:
        compatible = parse_probe({
            "format": {"format_name": "matroska"},
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"index": 2, "codec_type": "audio", "codec_name": "aac"},
            ]}, self.source)
        selected = EncoderSelection(EncoderBackend.NVIDIA_NVENC)
        resolved = plan(compatible, settings_for(self.source).customized(encoding_engine=selected))
        self.assertTrue(resolved.video_copy)
        command = build_command(resolved, Path("ffmpeg"), Path("output.mp4"))
        self.assertEqual(command[command.index("-c:v") + 1], "copy")
        self.assertNotIn("h264_nvenc", command)

    def test_backend_commands_and_subtitle_filter_order(self) -> None:
        cases = (
            (EncoderSelection(EncoderBackend.NVIDIA_NVENC), "h264_nvenc",
             "subtitles=subtitle.ass,format=yuv420p"),
            (EncoderSelection(EncoderBackend.AMD_AMF), "h264_amf",
             "subtitles=subtitle.ass,format=yuv420p"),
            (EncoderSelection(EncoderBackend.VAAPI, "/dev/dri/renderD129"), "h264_vaapi",
             "subtitles=subtitle.ass,format=nv12,hwupload"),
            (EncoderSelection(EncoderBackend.INTEL_QSV, "/dev/dri/renderD129"), "h264_qsv",
             "subtitles=subtitle.ass,format=nv12,hwupload=extra_hw_frames=64"),
        )
        for selected, encoder, filters in cases:
            with self.subTest(encoder=encoder):
                settings = settings_for(self.source).customized(
                    encoding_engine=selected, hardware_quality=HardwareQuality.HIGH,
                    subtitle_mode=SubtitleMode.BURN, subtitle_index=3)
                resolved = plan(self.media, settings, capabilities=(self._capability(selected),))
                self.assertFalse(resolved.video_copy)
                command = build_command(resolved, Path("ffmpeg"), Path("output.mp4"),
                                        subtitle_file=Path("/tmp/subtitle.ass"))
                self.assertEqual(command[command.index("-c:v") + 1], encoder)
                self.assertEqual(command[command.index("-vf") + 1], filters)
                self.assertEqual(command[command.index("-map") + 1], "0:0")
                self.assertIn("+faststart", command)
                self.assertEqual(command[command.index("-c:a") + 1], "aac")
                self.assertNotIn("-crf", command)
                if selected.backend == EncoderBackend.VAAPI:
                    self.assertIn("vaapi=encode:/dev/dri/renderD129", command)
                if selected.backend == EncoderBackend.INTEL_QSV:
                    self.assertIn("qsv=encode,child_device=/dev/dri/renderD129", command)

    def test_quality_mapping_is_backend_specific(self) -> None:
        expected = {
            EncoderBackend.NVIDIA_NVENC: ("-cq", "19", "27"),
            EncoderBackend.AMD_AMF: ("-qp_p", "21", "30"),
            EncoderBackend.VAAPI: ("-qp", "20", "28"),
            EncoderBackend.INTEL_QSV: ("-global_quality", "20", "28"),
        }
        for backend_id, (flag, high, fast) in expected.items():
            backend = get_backend(backend_id)
            high_args = backend.encoding_args(HardwareQuality.HIGH, crf=18, preset="medium",
                                              pixel_format="yuv420p")
            fast_args = backend.encoding_args(HardwareQuality.FAST, crf=18, preset="medium",
                                              pixel_format="yuv420p")
            self.assertEqual(high_args[high_args.index(flag) + 1], high)
            self.assertEqual(fast_args[fast_args.index(flag) + 1], fast)

    def test_ten_bit_source_uses_eight_bit_hardware_input_without_subtitles(self) -> None:
        for backend_id, device, expected_filter in (
            (EncoderBackend.NVIDIA_NVENC, None, "format=yuv420p"),
            (EncoderBackend.AMD_AMF, None, "format=yuv420p"),
            (EncoderBackend.VAAPI, "/dev/dri/renderD129", "format=nv12,hwupload"),
            (EncoderBackend.INTEL_QSV, "/dev/dri/renderD129",
             "format=nv12,hwupload=extra_hw_frames=64"),
        ):
            with self.subTest(backend=backend_id.value):
                selected = EncoderSelection(backend_id, device)
                resolved = plan(self.media,
                                settings_for(self.source).customized(encoding_engine=selected),
                                capabilities=(self._capability(selected),))
                command = build_command(resolved, Path("ffmpeg"), Path("output.mp4"))
                self.assertEqual(command[command.index("-vf") + 1], expected_filter)
                self.assertEqual(command[command.index("-c:v") + 1], get_backend(backend_id).encoder_name)
                self.assertEqual(command[command.index("-c:a") + 1], "aac")
                self.assertIn("+faststart", command)

    def test_platform_backend_policy(self) -> None:
        def no_encoders(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, "", "")
        windows = HardwareEncoderDetector(Path("ffmpeg"), platform="win32", devices=[], run=no_encoders).detect()
        linux = HardwareEncoderDetector(Path("ffmpeg"), platform="linux", devices=[], run=no_encoders).detect()
        self.assertIn(EncoderBackend.AMD_AMF, {cap.selection.backend for cap in windows})
        self.assertNotIn(EncoderBackend.AMD_AMF, {cap.selection.backend for cap in linux})
        self.assertIn(EncoderBackend.VAAPI, {cap.selection.backend for cap in linux})

    def test_two_stage_detection_caches_and_checks_each_device(self) -> None:
        commands: list[list[str]] = []
        def fake_run(command, **_kwargs):
            commands.append(command)
            if "-encoders" in command:
                return subprocess.CompletedProcess(command, 0,
                    " V....D h264_nvenc NVIDIA\n V....D h264_vaapi VAAPI\n V..... h264_qsv QSV\n", "")
            success = "vaapi=encode:/dev/dri/renderD129" in command
            return subprocess.CompletedProcess(command, 0 if success else 1,
                                               "", "No usable GPU" if not success else "")
        detector = HardwareEncoderDetector(Path("ffmpeg"), platform="linux",
            devices=[Path("/dev/dri/renderD128"), Path("/dev/dri/renderD129")], run=fake_run)
        result = detector.detect()
        self.assertEqual(len(result), 5)
        self.assertEqual([c.selection.device for c in result if c.available], ["/dev/dri/renderD129"])
        self.assertTrue(result[2].supports_10bit_input_conversion)
        self.assertTrue(result[2].supports_subtitle_pipeline)
        self.assertTrue(all(c.reason_unavailable for c in result if not c.available))
        before = len(commands)
        self.assertEqual(detector.detect(), result)
        self.assertEqual(len(commands), before)

    def test_encoder_presence_alone_is_not_availability(self) -> None:
        self.assertEqual(encoder_names(" V....D h264_nvenc NVIDIA\n"), {"h264_nvenc"})
        def fake_run(command, **_kwargs):
            if "-encoders" in command:
                return subprocess.CompletedProcess(command, 0, " V....D h264_nvenc NVIDIA\n", "")
            return subprocess.CompletedProcess(command, 1, "", "Cannot load CUDA")
        result = HardwareEncoderDetector(Path("ffmpeg"), platform="linux", devices=[], run=fake_run).detect()
        self.assertFalse(any(cap.available for cap in result))
        self.assertIn("Cannot load CUDA", result[0].reason_unavailable)

    def test_windows_qsv_uses_software_nv12_frames(self) -> None:
        with patch("video_converter.ffmpeg.encoders.sys.platform", "win32"):
            command = probe_command(Path("ffmpeg"), EncoderSelection(EncoderBackend.INTEL_QSV))
        self.assertIn("format=nv12", command)
        self.assertFalse(any("child_device" in item for item in command))

    def test_vaapi_probe_frame_meets_hardware_minimum_height(self) -> None:
        command = probe_command(Path("ffmpeg"),
                                EncoderSelection(EncoderBackend.VAAPI, "/dev/dri/renderD128"))
        source = command[command.index("-i") + 1]
        self.assertIn("s=256x144", source)
