"""Fail closed on changed compiler/build tool fingerprints for a named environment."""

import json
from pathlib import Path


def verify_tool_profile(profile_file: Path, name: str, actual: dict):
    profiles = json.loads(profile_file.read_text())["profiles"]
    if name not in profiles:
        raise RuntimeError("Unknown native build environment profile: " + name)
    expected = profiles[name]["tools"]
    if set(expected) != set(actual):
        raise RuntimeError("Native build tool set differs from the pinned profile")
    for tool, evidence in expected.items():
        if actual[tool] != evidence:
            raise RuntimeError("Native build tool fingerprint changed: " + tool)
    return name
