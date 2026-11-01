# Cactu Video Converter v0.1.0-beta.1

## First Public Beta

This is beta software. Expect bugs, platform-specific issues and hardware encoder
variation. Keep your original media files. Only assets attached to an approved
GitHub pre-release are public downloads; unfinished candidates are not releases.

## Highlights

- Smart MP4/H.264/AAC compatibility presets and per-file control.
- Sequential batch queue, multi-file import, independent settings and safe track matching.
- Software x264 plus optional GPU encoding and Hardware Acceleration Assistant guidance.
- Audio volume/clipping protection, measured loudness normalization and Quick Preview.
- Embedded/external text subtitles and local sanitized diagnostic reports.

## Downloads and platforms

Windows 11 x86_64: versioned Setup executable (recommended) or complete Portable ZIP.
Linux x86_64: versioned AppImage. Python, Qt, FFmpeg and FFprobe are included in
approved packages. macOS and ARM are unsupported. The Linux baseline is documented
in INSTALLATION.md; one development-distro test does not establish universal support.

SHA256SUMS.txt is generated from the final files. Compare hashes and obtain downloads
only from https://github.com/drrrrigo/cactu-video-converter/releases. Beta.1 is
unsigned unless explicitly identified otherwise; do not disable platform protection
globally to run it. Source review/checksums do not replace publisher identity checks.

## Hardware and known limitations

Software x264 remains available without a functioning GPU encoder. Host drivers and
render-device access are still required for GPU use; Cactu does not install drivers.
Physical validation currently covers AMD RX 7700 XT / Linux VAAPI. Other physical
backends and broad hybrid configurations remain unverified. See KNOWN_ISSUES.md.
ASS fonts must be available to the renderer; embedded font extraction and bitmap
subtitle burn-in are not implemented. Queue state is session-only.

## Reporting bugs

Use https://github.com/drrrrigo/cactu-video-converter/issues with version, OS,
installation type, selected encoder, reproduction steps and reviewed sanitized
Settings → Diagnostics output. Prefer synthetic examples; do not post private or
copyrighted media without permission. Report vulnerabilities privately via SECURITY.md.
No telemetry or automatic log/media uploads are present.

## Licensing

Cactu source: GPL-3.0-or-later. Third-party components retain their own licenses.
Exact redistribution/source/notices evidence must be complete before binaries are
published; see RELEASE_LICENSE_AUDIT.md and the packaged notices/license directory.
