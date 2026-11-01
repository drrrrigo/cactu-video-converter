"""Product identity, safe settings migration, assets and readable theme contracts."""

import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QByteArray, QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from video_converter.product import PRODUCT_NAME, PRODUCT_SLUG
from video_converter.services.settings_migration import MARKER, compatible_value, migrate_settings, reset_preferences
from video_converter.ui import theme
from video_converter.ui.branding import about_dialog, application_icon, branding_directory, notices_path, settings_dialog
from video_converter.ffmpeg.runtime import FFmpegRuntime

ROOT = Path(__file__).resolve().parents[1]


def contrast(foreground, background):
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    values = sorted((luminance(foreground), luminance(background)))
    return (values[1] + 0.05) / (values[0] + 0.05)


class SettingsMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.new = QSettings(str(Path(self.temp.name) / "new.ini"), QSettings.Format.IniFormat)
        self.old = QSettings(str(Path(self.temp.name) / "old.ini"), QSettings.Format.IniFormat)

    def test_compatible_preferences_migrate_once_without_modifying_legacy(self):
        preferences = {"geometry": QByteArray(b"saved geometry"), "queue_splitter": [300, 900],
                       "preferred_encoder_backend": "vaapi", "last_input_dir": "/Films/日本語",
                       "last_subtitle_dir": "/Subtitles", "bulk_output_dir": "/Converted"}
        for key, value in preferences.items():
            self.old.setValue(key, value)
        self.old.setValue("external_subtitle_path", "/stale/movie.ass")
        self.old.setValue("queue_jobs", "transient")
        self.old.sync()
        before = Path(self.old.fileName()).read_bytes()
        self.assertEqual(set(migrate_settings(self.new, self.old)), set(preferences))
        for key, value in preferences.items():
            self.assertEqual(self.new.value(key), value)
        self.assertFalse(self.new.contains("external_subtitle_path"))
        self.assertFalse(self.new.contains("queue_jobs"))
        self.new.setValue("last_input_dir", "/New")
        self.assertEqual(migrate_settings(self.new, self.old), ())
        self.assertEqual(self.new.value("last_input_dir"), "/New")
        self.assertEqual(Path(self.old.fileName()).read_bytes(), before)

    def test_nonempty_new_settings_never_receive_legacy_overlay(self):
        self.new.setValue("last_input_dir", "/New")
        self.old.setValue("last_subtitle_dir", "/Old")
        self.assertEqual(migrate_settings(self.new, self.old), ())
        self.assertFalse(self.new.contains("last_subtitle_dir"))
        self.assertTrue(self.new.value(MARKER))

    def test_missing_legacy_store_is_safe(self):
        self.assertEqual(migrate_settings(self.new, self.old), ())
        self.assertEqual(self.new.value("settings_schema_version"), 1)

    def test_reset_does_not_import_discarded_preferences_again(self):
        self.old.setValue("last_input_dir", "/Legacy")
        migrate_settings(self.new, self.old)
        reset_preferences(self.new)
        self.assertEqual(migrate_settings(self.new, self.old), ())
        self.assertFalse(self.new.contains("last_input_dir"))

    def test_malformed_and_transient_values_are_rejected(self):
        for key, value in (("geometry", "not bytes"), ("queue_splitter", [True, 42]),
                           ("queue_splitter", [-1, 3]), ("queue_splitter", [1, 2, 3]),
                           ("queue_splitter", ["bad", 2]), ("last_input_dir", "bad\0path"),
                           ("preferred_encoder_backend", "unknown"), ("external_subtitle", "/movie.ass")):
            self.assertIsNone(compatible_value(key, value), (key, value))


class BrandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])
        theme.apply_theme(cls.app)

    def delete_widget(self, widget):
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_source_and_frozen_asset_resolution(self):
        self.assertEqual(branding_directory(), ROOT / "assets/branding")
        self.assertEqual(notices_path(), ROOT / "THIRD_PARTY_NOTICES.md")
        self.assertFalse(application_icon().isNull())
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", "/bundle", create=True):
            self.assertEqual(branding_directory(), Path("/bundle/assets/branding"))
            self.assertEqual(notices_path(), Path("/bundle/THIRD_PARTY_NOTICES.md"))
        with patch("video_converter.ui.branding.Path.is_dir", return_value=False), \
                patch("video_converter.ui.branding.sysconfig.get_path", return_value="/wheel"):
            self.assertEqual(branding_directory(), Path(f"/wheel/share/{PRODUCT_SLUG}/branding"))
        with patch("video_converter.ui.branding.Path.is_file", return_value=False), \
                patch("video_converter.ui.branding.sysconfig.get_path", return_value="/wheel"):
            self.assertEqual(notices_path(), Path(f"/wheel/share/{PRODUCT_SLUG}/THIRD_PARTY_NOTICES.md"))

    def test_about_retains_version_and_third_party_attribution(self):
        runtime = FFmpegRuntime(Path("ffmpeg"), Path("ffprobe"), "FFmpeg 9.0.2", "FFprobe 9.0.2")
        box = about_dialog(runtime)
        self.assertEqual(box.windowTitle(), f"About {PRODUCT_NAME}")
        self.assertIn("0.1.0", box.text())
        self.assertIn(runtime.ffmpeg_version, box.text())
        self.assertIn(runtime.ffprobe_version, box.text())
        self.assertIn("their own licenses", box.informativeText())
        self.delete_widget(box)

    def test_settings_actions_remain_readable_on_a_narrow_desktop(self):
        runtime = FFmpegRuntime(Path("ffmpeg"), Path("ffprobe"), "FFmpeg 9.0.2", "FFprobe 9.0.2")
        box = settings_dialog(runtime)
        # Native Windows fonts and the beta's extra diagnostics/issue actions need
        # more room than the old 400px fixture. A 640px dialog fits a 1366px laptop
        # at 150% scale; check actual label size hints instead of font-specific pixels.
        box.resize(640, box.sizeHint().height())
        box.show()
        self.app.processEvents()
        self.assertIn(PRODUCT_NAME, box.windowTitle())
        self.assertLessEqual(box.minimumSizeHint().width(), 640)
        self.assertLessEqual(box.width(), 640)
        for action in box.findChildren(QPushButton):
            self.assertGreaterEqual(action.width(), action.sizeHint().width(), action.text())
        button = next(b for b in box.findChildren(QPushButton) if b.text() == "About")
        button.click()
        self.assertEqual(box.selected_action, "about")
        self.delete_widget(box)

    def test_text_and_primary_button_states_have_readable_contrast(self):
        for foreground, background in (
            (theme.TEXT_PRIMARY, theme.BACKGROUND), (theme.TEXT_SECONDARY, theme.SURFACE),
            (theme.TEXT_MUTED, theme.SURFACE), (theme.TEXT_PRIMARY, theme.SELECTION_SURFACE),
            (theme.WARNING, theme.WARNING_SURFACE), (theme.ERROR, theme.ERROR_SURFACE),
            *((theme.TEXT_ON_ACCENT, color) for color in (theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED)),
        ):
            self.assertGreaterEqual(contrast(foreground, background), 4.5, (foreground, background))
        self.assertNotEqual(theme.SUCCESS, theme.ACCENT)

    def test_main_window_uses_product_identity_and_separate_percent_label(self):
        from video_converter.ui.main_window import MainWindow
        runtime = FFmpegRuntime(Path("ffmpeg"), Path("ffprobe"), "FFmpeg 9.0.2", "FFprobe 9.0.2")
        with tempfile.TemporaryDirectory() as temporary, patch.object(MainWindow, "_detect_hardware"):
            window = MainWindow(runtime)
            window.storage = QSettings(str(Path(temporary) / "settings.ini"), QSettings.Format.IniFormat)
            self.assertEqual(window.windowTitle(), PRODUCT_NAME)
            self.assertFalse(window.windowIcon().isNull())
            self.assertIn(PRODUCT_NAME, [label.text() for label in window.findChildren(QLabel)])
            self.assertFalse(window.progress_bar.isTextVisible())
            self.assertEqual(window.percent.text(), "0%")
            self.delete_widget(window)

    def test_platform_metadata_and_icon_payloads(self):
        with patch.dict(sys.modules):
            with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
                runpy.run_path(str(ROOT / "scripts/check_branding.py"), run_name="__main__")


if __name__ == "__main__":
    unittest.main()
