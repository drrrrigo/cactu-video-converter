"""Acquire only pinned FFmpeg inputs; verify before opening or executing them."""

from __future__ import annotations

import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from release_common import ROOT, download, read_json, safe_member, sha256
from verify_ffmpeg import MANIFEST, validate


def unpack(archive: Path, metadata: dict, destination: Path) -> None:
    required = {
        metadata["ffmpeg_member"]: "ffmpeg",
        metadata["ffprobe_member"]: "ffprobe",
        metadata["license_member"]: "FFmpeg-LICENSE.txt",
    }
    suffix = ".exe" if metadata["ffmpeg_member"].endswith(".exe") else ""
    opener = zipfile.ZipFile if metadata["archive_format"] == "zip" else tarfile.open
    with opener(archive) as bundle:
        for member, name in required.items():
            if not safe_member(member):
                raise RuntimeError("Unsafe manifest archive member")
            if isinstance(bundle, zipfile.ZipFile):
                info = bundle.getinfo(member)
                if (
                    info.file_size > 500_000_000
                    or (info.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise RuntimeError("Invalid ZIP member")
                source = bundle.open(member)
            else:
                info = bundle.getmember(member)
                if not info.isfile() or info.size > 500_000_000:
                    raise RuntimeError("Invalid tar member")
                source = bundle.extractfile(info)
            target = destination / (name + suffix if name in {"ffmpeg", "ffprobe"} else name)
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            expected = (
                metadata.get(f"{name}_sha256")
                if name in {"ffmpeg", "ffprobe"}
                else metadata["license_sha256"]
            )
            if sha256(target) != expected:
                raise RuntimeError(f"{name} extracted SHA-256 mismatch")
            if name in {"ffmpeg", "ffprobe"} and not suffix:
                target.chmod(0o755)


def stage(platform: str, *, cache: Path | None = None) -> Path:
    metadata = read_json(MANIFEST)[platform]
    cache = cache or ROOT / "vendor/ffmpeg/cache"
    archive = download(
        metadata["source_url"],
        metadata["archive_sha256"],
        cache / (metadata["archive_sha256"] + ".archive"),
    )
    destination = ROOT / "vendor/ffmpeg" / metadata["version"] / platform
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / "payload"
        staged.mkdir()
        unpack(archive, metadata, staged)
        validate(platform, directory=staged)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staged, destination)
    return destination


if __name__ == "__main__":
    stage(sys.argv[1])
