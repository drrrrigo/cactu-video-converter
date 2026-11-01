# FFmpeg / FFprobe beta provenance

The candidate manifest pins BtbN dated archives from autobuild-2026-11-01-12-49,
identity **n9.0.2-42-gd7643a0fe3-20261101**, for native Windows/Linux x86_64.
This is the 9.0.2 branch plus revisions; it is not described as the pristine 9.0.2
tarball. FFmpeg and FFprobe must match that exact identity/configuration and their
individual binary hashes. Never replace them with a system PATH binary in a frozen
build. Runtime downloads are not implemented.

`stage_ffmpeg.py` supports fixed ZIP/tar.xz archives, requires HTTPS and SHA-256,
verifies the full archive before opening it, reads only three exact members and
rejects links/oversized/traversal members. It validates an isolated staged pair
before replacing the prior staged payload. Staging/cache paths are gitignored.
`verify_ffmpeg.py` checks binary/license hashes, exact version/configuration, no
--enable-nonfree, essential software tables and pinned hardware encoder exposure.
The shared capability parser checks x264/AAC/text subtitle encoding, H.264/HEVC/
ASS/SSA/SubRip decoding, subtitles/loudnorm/alimiter/resampling/format filters and
MP4/Matroska/text demux/mux support. A physical GPU is not required for packaging.

The previously documented Martin Riedl Linux build enables **--enable-nonfree**;
it is excluded from beta redistribution. The chosen internal BtbN build reports
GPL-3.0-or-later and enables GPL/version3/libx264/libass without nonfree. This is
an observed configuration/license fact, not complete redistribution approval.

Public binary distribution remains blocked: the full matching source and notices
for statically linked components, exact Qt/native dependency closure and other
release obligations still need evidence. A generic source homepage/build recipe
and one GPL text are insufficient. See [RELEASE_LICENSE_AUDIT](RELEASE_LICENSE_AUDIT.md).
Do not set the manifest's source/redistribution approvals until those items are
actually resolved. Hash pins establish byte integrity, not license compliance.
