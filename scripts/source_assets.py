"""Validate approved corresponding-source assets before recipient distribution."""

from pathlib import Path
from release_common import read_json, sha256


def source_assets(directory: Path):
    manifest = read_json(directory / "SOURCE-ASSETS.json")
    if manifest.get("complete_corresponding_source") is not True:
        raise RuntimeError("Complete corresponding-source delivery is not approved")
    if not manifest.get("assets"):
        raise RuntimeError("Source assets are missing")
    result = [directory / "SOURCE-ASSETS.json"]
    for entry in manifest["assets"]:
        name = entry["filename"]
        if not name or Path(name).name != name or "\\" in name or ":" in name:
            raise RuntimeError("Unsafe source asset name")
        if entry.get("redistribution_approved") is not True:
            raise RuntimeError("Source asset redistribution not approved: " + name)
        path = directory / name
        if path.is_symlink() or sha256(path) != entry["sha256"]:
            raise RuntimeError("Source asset hash mismatch: " + name)
        result.append(path)
    return result
