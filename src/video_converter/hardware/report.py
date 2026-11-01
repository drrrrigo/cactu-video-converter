"""Bounded, local diagnostic export that excludes media/user path context."""

from __future__ import annotations

import re
from pathlib import Path

from video_converter.product import PRODUCT_NAME


def sanitize(text: str) -> str:
    text = str(text).replace(str(Path.home()), "<home>")
    text = re.sub(r"""["'](?:[A-Za-z]:[\\/]|/(?!dev/))[^\r\n]*?["']""", '"<path>"', text)
    text = re.sub(r"https?://\S+", "<url omitted>", text, flags=re.I)
    # FFmpeg test commands contain no media inputs; redact arbitrary absolute
    # paths in stderr nevertheless, keeping only graphics device nodes.
    text = re.sub(r"(?<![\w])[A-Za-z]:[\\/][^\s\r\n\"']+", "<path>", text)
    text = re.sub(r"(?<![\w/.])/(?!dev/(?:dri/|nvidia))[^\s\r\n\"']+", "<path>", text)
    text = re.sub(
        r"\b[^\s/\\\"']+\.(?:mkv|mp4|mov|avi|webm|ass|ssa|srt)\b", "<media file>", text, flags=re.I
    )
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def diagnostic_report(diagnosis) -> str:
    info = diagnosis.inventory
    lines = [
        f"{PRODUCT_NAME} {diagnosis.application_version}",
        f"OS: {info.os_name}",
        f"Distribution: {info.distribution.name} {info.distribution.version}",
        f"Distribution family: {info.distribution.family.value}",
        f"FFmpeg: {diagnosis.ffmpeg_version}",
        f"Runtime: {'bundled' if diagnosis.features.bundled else 'development'}",
        f"Hardware overall: {'Available' if diagnosis.available else 'Unavailable'}",
        "Software: x264 available",
    ]
    lines.extend(info.errors)
    if diagnosis.features.error:
        lines.append(diagnosis.features.error)
    for number, finding in enumerate(diagnosis.findings, 1):
        device, probe = finding.device, finding.probe
        lines += [
            f"\nFinding {number}: {finding.category.value}",
            f"Responsibility: {finding.responsibility.value}",
            f"Message: {finding.message}",
            f"Guide: {finding.guide_id}",
        ]
        if device:
            lines += [
                f"GPU: {device.model}",
                f"Vendor / PCI: {device.vendor.value} {device.vendor_id}:{device.device_id}",
                f"Driver: {device.driver or 'Not observed'}",
                f"Driver version: {device.driver_version or 'Not available'}",
                f"Adapter state: {device.adapter_status}",
            ]
            for node in device.render_nodes:
                lines.append(
                    f"Render device: {node.path}; exists={node.exists}; read={node.readable}; write={node.writable}; mode={node.mode}"
                )
        if finding.backend:
            lines.append(f"Expected backend: {finding.backend.display_name}")
        lines.append(f"Encoder present: {finding.encoder_present}")
        if probe:
            lines += [
                f"FFmpeg encoder: {probe.encoder_name}",
                f"Probed device: {probe.selection.device or 'default (adapter attribution not guaranteed)'}",
                f"Initialization: {'Passed' if probe.available else 'Not available'}; exit={probe.probe_exit_code}",
                "Probe command: " + " ".join(probe.probe_command),
                "Probe details: "
                + (probe.reason_unavailable or probe.initialization_details or "No error recorded")[
                    -3000:
                ],
            ]
    return sanitize("\n".join(lines))[:60000]
