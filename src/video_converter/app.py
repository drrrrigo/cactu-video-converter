"""Desktop application entry point."""

from __future__ import annotations

import sys
import logging

from PySide6.QtWidgets import QApplication, QMessageBox

from video_converter.ffmpeg.runtime import FFmpegRuntime
from video_converter.services.logging import configure_logging
from video_converter.ui.main_window import MainWindow
from video_converter.ui.theme import apply_theme
from video_converter.ui.branding import application_icon
from video_converter.product import PRODUCT_NAME, PRODUCT_SLUG, SETTINGS_ORGANIZATION
from video_converter.services.settings_migration import migrate_settings
from video_converter.services.startup import check_writable_environment
from video_converter.ui.error_reporter import ErrorReporter
from video_converter import __version__


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(PRODUCT_NAME)
    app.setApplicationDisplayName(PRODUCT_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(SETTINGS_ORGANIZATION)
    app.setDesktopFileName(PRODUCT_SLUG)
    app.setWindowIcon(application_icon())
    apply_theme(app)
    try:
        check_writable_environment()
        migrate_settings()
        configure_logging()
        # Explicit source-only fallback is never available to a frozen release.
        runtime = FFmpegRuntime.locate(allow_system_development="--dev-system-ffmpeg" in sys.argv)
    except (RuntimeError, OSError) as exc:
        QMessageBox.critical(None, "Cactu configuration error", str(exc))
        return 1
    if "--release-smoke" in sys.argv:
        from video_converter.services.release_smoke import run_smoke
        from pathlib import Path

        index = sys.argv.index("--release-smoke")
        return run_smoke(runtime, Path(sys.argv[index + 1]))
    logging.info("Runtime: %s | %s", runtime.ffmpeg_version, runtime.ffprobe_version)
    try:
        window = MainWindow(runtime)
    except Exception:
        logging.getLogger(__name__).exception("Cactu could not initialize its main window")
        QMessageBox.critical(
            None,
            "Cactu startup error",
            "Cactu encountered an unexpected startup error. Review the local log folder before trying again.",
        )
        return 1
    reporter = ErrorReporter(window)
    sys.excepthook = reporter.hook
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
