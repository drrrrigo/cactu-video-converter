"""Validate approved corresponding-source assets before recipient distribution."""

from pathlib import Path
from release_common import read_json, sha256, digest_valid


def approved_source_assets(directory, config, owner, commit):
    """Bind source approval to the existing protected exact-artifact attestation.

    A post-build index hash cannot be committed into the commit it describes.
    The protected owner record supplies the mandatory exact hash; a configured
    static pin, when present, remains an additional constraint.
    """
    if (
        owner.get("approved") is not True
        or owner.get("approved_by") != "drrrrigo"
        or owner.get("source_commit") != commit
    ):
        raise RuntimeError("Source approval lacks the exact owner/source attestation")
    pin = owner.get("source_assets_manifest_sha256")
    if not digest_valid(pin or "") or sha256(directory / "SOURCE-ASSETS.json") != pin:
        raise RuntimeError("Exact source index is not approved by the owner attestation")
    configured = config.get("source_assets_manifest_sha256")
    if configured is not None and configured != pin:
        raise RuntimeError("Configured source index pin differs from owner approval")
    manifest = read_json(directory / "SOURCE-ASSETS.json")
    if manifest.get("candidate_source_commit") != commit or manifest.get(
        "candidate_binary_artifacts"
    ) != owner.get("artifacts"):
        raise RuntimeError("Source index belongs to different candidate source/binaries")
    return source_assets(directory)


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
