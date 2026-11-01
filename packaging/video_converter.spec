"""PyInstaller ONEDIR specification; run on each target OS independently."""

import sys
from pathlib import Path

root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(root))
from scripts.branding_metadata import ASSETS, EXECUTABLE_NAME, write_windows_metadata

version_file, _ = write_windows_metadata(root / "build" / "branding")
platform = "windows-x86_64" if sys.platform == "win32" else "linux-x86_64"
source = root / "vendor" / "ffmpeg" / "9.0.2" / platform
suffix = ".exe" if sys.platform == "win32" else ""
for name in ("ffmpeg", "ffprobe"):
    if not (source / f"{name}{suffix}").is_file():
        raise RuntimeError("Verified bundled FFmpeg/FFprobe are required.")

a = Analysis([str(root / "src" / "video_converter" / "app.py")],
             pathex=[str(root / "src")], binaries=[(str(source / f"ffmpeg{suffix}"), "ffmpeg"),
                                                    (str(source / f"ffprobe{suffix}"), "ffmpeg")],
             datas=[(str(root / "THIRD_PARTY_NOTICES.md"), "."),
                    (str(ASSETS), "assets/branding"),
                    (str(root / "LICENSE"), "."),
                    (str(root / "build/licenses"), "licenses")],
             # License payload comes from the exact pinned build environment.
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=EXECUTABLE_NAME, console=False,
          icon=str(ASSETS / "cactu-video-converter.ico"),
          version=str(version_file) if sys.platform == "win32" else None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=EXECUTABLE_NAME)
