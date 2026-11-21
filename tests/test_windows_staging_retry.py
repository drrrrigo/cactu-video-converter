import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_ffmpeg import replace_validated


class WindowsStagingRetryTests(unittest.TestCase):
    def error(self, code):
        error = PermissionError("synthetic Windows file-access error")
        error.winerror = code
        return error

    def test_transient_sharing_error_retries_atomic_rename(self):
        with (
            patch("stage_ffmpeg.sys.platform", "win32"),
            patch("stage_ffmpeg.time.sleep") as sleep,
            patch(
                "stage_ffmpeg.os.replace", side_effect=[self.error(5), self.error(32), None]
            ) as replace,
        ):
            replace_validated(Path("verified"), Path("selected"))
        self.assertEqual(replace.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_permanent_access_error_remains_a_failure_after_bound(self):
        with (
            patch("stage_ffmpeg.sys.platform", "win32"),
            patch("stage_ffmpeg.time.sleep"),
            patch("stage_ffmpeg.os.replace", side_effect=self.error(5)) as replace,
        ):
            with self.assertRaises(PermissionError):
                replace_validated(Path("verified"), Path("selected"))
        self.assertEqual(replace.call_count, 8)

    def test_unexpected_access_error_is_not_retried(self):
        with (
            patch("stage_ffmpeg.sys.platform", "win32"),
            patch("stage_ffmpeg.time.sleep") as sleep,
            patch("stage_ffmpeg.os.replace", side_effect=self.error(1314)) as replace,
        ):
            with self.assertRaises(PermissionError):
                replace_validated(Path("verified"), Path("selected"))
        self.assertEqual(replace.call_count, 1)
        sleep.assert_not_called()
