"""Local rotating diagnostics logs."""

import logging
import platform
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from video_converter import __version__
from video_converter.product import PRODUCT_NAME


def log_directory() -> Path:
    directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def configure_logging() -> Path:
    path = log_directory() / "video-converter.log"
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=4, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    logging.info("%s %s on %s", PRODUCT_NAME, __version__, platform.platform())
    return path
