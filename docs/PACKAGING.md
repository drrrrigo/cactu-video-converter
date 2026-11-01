# Cactu beta packaging

`packaging/video_converter.spec` creates a PyInstaller ONEDIR bundle with Python,
PySide6/Qt, dependencies, bundled FFmpeg/FFprobe, branding, Cactu license and collected
third-party notices/licenses. The executable/collection is CactuVideoConverter.
Internal package/spec names remain stable. The official display version and PEP
440/numeric Windows forms derive from the single source version.

Windows Inno Setup 7.1.1 is a checksum-pinned build tool. It wraps ONEDIR as the
per-user `CactuVideoConverter-Setup-0.1.0-beta.1.exe`, with Start Menu/optional Desktop
shortcut, uninstall entry/icon and stable legacy upgrade identity. Its target is
Windows 11 x86_64 (not ARM). The build also produces the complete versioned Portable
ZIP. Native automated smoke tests run ONEDIR, extracted ZIP and an installed build,
then uninstall; manual Windows 11 testing remains a separate required gate.
Optional Authenticode hooks use an externally supplied certificate selector and
Windows SDK tool; no key/certificate is stored in source. Current candidates are unsigned.

Linux appimagetool 1.9.1 and its separate type-2 runtime asset are hash-pinned. The
runtime is passed explicitly: no unpinned continuous runtime download is allowed.
The AppDir includes AppRun, desktop/icon resources and ONEDIR payload. AppRun uses
shell builtins, so a deliberately empty PATH cannot break dirname/readlink lookup.
The AppImage includes Python/FFmpeg/Qt; kernel/GPU drivers and host graphics-stack
integration are not installed by Cactu. The supported build baseline is recorded
per artifact; a local CachyOS candidate does not prove Ubuntu/other compatibility.

`scripts/package_smoke.py` launches the exact frozen payload offscreen with PATH
empty and isolated user directories. It starts a MainWindow, uses bundled FFprobe,
generates synthetic video/audio/subtitles, converts through the existing planner/
runner, independently checks H.264/yuv420p/AAC, duration/Faststart, burned-track
absence and unchanged original bytes, and requires normal exit. AppImage smoke
uses extraction mode so FUSE is not assumed on CI hosts.

Candidate output is `dist/candidate`; it is not a public release. Binary artifact
upload is gated by exact licensing/corresponding-source approval. Public beta tags
promote artifacts from a successful same-commit candidate run, re-test them natively,
compare manual hashes, generate SHA256SUMS and create a GitHub **pre-release**.
No ordinary PR publishes binaries, no existing release is silently overwritten and
no different rebuilt candidate is substituted for the manually tested bytes.
See [release checklist](RELEASE_CHECKLIST.md), [license audit](RELEASE_LICENSE_AUDIT.md)
and [installation](INSTALLATION.md).
