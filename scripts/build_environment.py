"""Reject unreviewable release builds before creating any package output."""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import sys
import sysconfig
from pathlib import Path

from packaging.requirements import Requirement

from release_common import ROOT, read_json, sha256


def check_environment(root: Path = ROOT, *, python_version: str | None = None) -> dict:
    toolchain = read_json(root / "release/toolchain.json")
    actual = python_version or platform.python_version()
    if actual != toolchain["python"]:
        raise RuntimeError(
            f"Release packaging requires Python {toolchain['python']}; found {actual}. "
            "Use the pinned interpreter; mismatched candidates are not permitted."
        )
    if platform.python_implementation() != "CPython" or sysconfig.get_config_var("Py_GIL_DISABLED"):
        raise RuntimeError("Release packaging requires the standard CPython build with the GIL")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("Release packaging requires a clean, committed source tree")
    epoch = subprocess.run(
        ["git", "show", "-s", "--format=%ct", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    installed = {}
    for line in (root / "release/requirements.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        value = importlib.metadata.version(requirement.name)
        if value not in requirement.specifier:
            raise RuntimeError(f"Release dependency mismatch: {requirement.name} {value}")
        installed[requirement.name] = value
    return {
        "source_commit": commit,
        "source_tree_clean": True,
        "source_date_epoch": int(epoch),
        "python": actual,
        "python_pin": toolchain["python"],
        "python_pin_matches": True,
        "python_abi": sys.implementation.cache_tag,
        "interpreter_executable_sha256": sha256(Path(sys._base_executable).resolve()),
        "dependency_versions": installed,
        "requirements_lock_sha256": sha256(root / "release/requirements.lock"),
    }
