"""Conservative current-tree secret/personal-artifact scan; no contents printed."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from release_common import ROOT

EXCLUDE = {
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "cache",
}
PATTERNS = {
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github-token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "cloud-key": r"\bAKIA[0-9A-Z]{16}\b",
    "credential-assignment": r"(?i)\b(?:api_key|access_token|password|secret_key)\s*[:=]\s*[\"\'][^\"\']{12,}[\"\']",
    "personal-home-path": r"/home/(?!alice(?:/|\b))[^/\s\"\']+/",
}


def paths(root):
    for file in root.rglob("*"):
        if file.is_file() and not any(
            part in EXCLUDE or part.startswith(".venv") or part.endswith(".egg-info")
            for part in file.relative_to(root).parts
        ):
            if file.suffix.lower() in {
                ".py",
                ".md",
                ".json",
                ".toml",
                ".yml",
                ".yaml",
                ".sh",
                ".iss",
                ".spec",
                ".txt",
                ".desktop",
            }:
                yield file


def audit(root=ROOT):
    findings = []
    for file in paths(root):
        if file.name == "audit_source.py":
            continue  # scanner contains its own signatures
        content = file.read_text(encoding="utf-8", errors="replace")
        for category, pattern in PATTERNS.items():
            for match in re.finditer(pattern, content):
                # Synthetic privacy fixtures are deliberately not real user credentials.
                if category == "personal-home-path" and "tests" in file.relative_to(root).parts:
                    continue
                findings.append(
                    {
                        "file": file.relative_to(root).as_posix(),
                        "line": content.count("\n", 0, match.start()) + 1,
                        "category": category,
                    }
                )
    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = audit()
    if args.history:
        result = subprocess.run(
            ["git", "rev-list", "--all"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise RuntimeError("Git history unavailable; history audit is not complete")
        for revision in result.stdout.splitlines():
            names = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", revision],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
            for name in names:
                if Path(name).suffix not in {
                    ".py",
                    ".md",
                    ".json",
                    ".toml",
                    ".yml",
                    ".yaml",
                    ".txt",
                    ".sh",
                }:
                    continue
                text = subprocess.run(
                    ["git", "show", revision + ":" + name],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                for category, pattern in PATTERNS.items():
                    if (
                        name == "scripts/audit_source.py"
                        or category == "personal-home-path"
                        and name.startswith("tests/")
                    ):
                        continue
                    if re.search(pattern, text):
                        findings.append({"file": name, "revision": revision, "category": category})
    print(json.dumps({"findings": findings, "history_checked": args.history}, indent=2))
    raise SystemExit(bool(findings))
