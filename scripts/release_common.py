"""Pinned release inputs, checksums and filesystem-safe archive access."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import platform
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest_valid(value: str) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[a-f0-9]{64}", value))


def download(url: str, digest: str, target: Path) -> Path:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or not digest_valid(digest)
    ):
        raise RuntimeError("A fixed HTTPS URL and SHA-256 are required")
    if target.is_file() and sha256(target) == digest:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = Path(temporary) / "download"
        headers = {"User-Agent": "Cactu-release-build"}
        if parsed.hostname == "api.github.com" and "/releases/assets/" in parsed.path:
            headers["Accept"] = "application/octet-stream"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response, staged.open("wb") as out:
            if urllib.parse.urlsplit(response.url).scheme != "https":
                raise RuntimeError("Insecure archive redirect")
            shutil.copyfileobj(response, out)
        if sha256(staged) != digest:
            raise RuntimeError("Download SHA-256 mismatch; input was not accepted")
        os.replace(staged, target)
    return target


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and ":" not in name
    )


def platform_id() -> str:
    if platform.machine().lower() not in {"amd64", "x86_64"} or sys.maxsize <= 2**32:
        raise RuntimeError("Beta packaging requires native x86_64 Python")
    if sys.platform == "win32":
        return "windows-x86_64"
    if sys.platform.startswith("linux"):
        return "linux-x86_64"
    raise RuntimeError("Beta builds support only Windows and Linux x86_64")
