"""One-time, allowlisted migration from the previous QSettings identity."""

from __future__ import annotations

import logging
from PySide6.QtCore import QByteArray, QSettings
from video_converter.product import LEGACY_PRODUCT_NAME, PRODUCT_NAME, SETTINGS_ORGANIZATION, SETTINGS_SCHEMA_VERSION

LOG = logging.getLogger(__name__)
MARKER = "legacy_settings_migrated"
DIRECTORY_KEYS = {"last_input_dir", "last_subtitle_dir", "bulk_output_dir"}
ENCODER_IDS = {"software_x264", "nvidia_nvenc", "amd_amf", "vaapi", "intel_qsv"}


def compatible_value(key: str, value):
    if key in DIRECTORY_KEYS and isinstance(value, str) and value and "\0" not in value and len(value) <= 4096:
        return value
    if key == "geometry" and isinstance(value, (QByteArray, bytes)) and 0 < len(value) <= 262144:
        return QByteArray(value)
    if key == "preferred_encoder_backend" and isinstance(value, str) and value in ENCODER_IDS:
        return value
    if key == "queue_splitter" and isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            sizes = [int(item) for item in value]
            if all(not isinstance(item, bool) for item in value) and all(0 <= item <= 10000 for item in sizes):
                return sizes
        except (ValueError, TypeError, OverflowError):
            pass
    return None


def migrate_settings(new: QSettings | None = None, legacy: QSettings | None = None) -> tuple[str, ...]:
    new = new if new is not None else QSettings(SETTINGS_ORGANIZATION, PRODUCT_NAME)
    legacy = legacy if legacy is not None else QSettings(LEGACY_PRODUCT_NAME, LEGACY_PRODUCT_NAME)
    new.setFallbacksEnabled(False)
    legacy.setFallbacksEnabled(False)
    if new.contains(MARKER):
        return ()
    copied = []
    # Even partial new settings belong to the user: never overlay old values.
    if not new.allKeys():
        for key in ("geometry", "queue_splitter", "preferred_encoder_backend", *sorted(DIRECTORY_KEYS)):
            value = compatible_value(key, legacy.value(key))
            if value is not None:
                new.setValue(key, value)
                copied.append(key)
    new.setValue("settings_schema_version", SETTINGS_SCHEMA_VERSION)
    new.setValue(MARKER, True)
    new.sync()
    if new.status() != QSettings.Status.NoError:
        LOG.warning("Could not persist %s settings migration; legacy preferences were left intact", PRODUCT_NAME)
    LOG.info("Settings migration checked; compatible keys copied: %s", copied)
    return tuple(copied)


def reset_preferences(settings: QSettings) -> None:
    """Reset user choices without importing discarded legacy values next launch."""
    settings.clear()
    settings.setValue("settings_schema_version", SETTINGS_SCHEMA_VERSION)
    settings.setValue(MARKER, True)
    settings.sync()
