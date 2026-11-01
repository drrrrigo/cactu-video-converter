# Third-party notices — beta candidate

Cactu's original source is GPL-3.0-or-later; see LICENSE. This does not replace
upstream licenses. Candidate bundles include a `licenses/` directory collected from
the exact pinned Python/wheel build environment, FFmpeg's supplied GPL text and a
component inventory. That collection is evidence, not a declaration that every
native-library/source obligation has been satisfied.

## FFmpeg / FFprobe

Candidate: BtbN build n9.0.2-42-gd7643a0fe3-20261101, from the dated build archives
pinned in vendor/ffmpeg/manifest.json. Its actual configuration enables GPL/version3
and libx264, and does not enable nonfree. `ffmpeg -L` reports GPL v3 or later.
FFmpeg source: https://github.com/FFmpeg/FFmpeg . Build recipe:
https://github.com/BtbN/FFmpeg-Builds . These links alone do not provide an approved
complete corresponding-source set for every statically linked library.
The previously mentioned Martin Riedl Linux candidate enables `--enable-nonfree`
and is excluded from beta redistribution.

## Python, Qt and Python dependencies

Release pins: CPython 3.14.7; PySide6/Shiboken/Qt 6.11.2; psutil 7.2.2.
Python retains its PSF and included third-party notices. Qt/PySide components have
commercial/open-source alternatives and their own third-party notices; the exact
used modules/options and complete matching sources must be reviewed. psutil's
BSD license and copied notices remain in the candidate license payload. PyInstaller
has its own license/bootloader exception; its inclusion does not change Cactu's
owner-selected source license.

## Release blocker

See docs/RELEASE_LICENSE_AUDIT.md. Exact linked-component notices, matching sources,
Qt/native dependency closure and redistribution approval remain incomplete. Neither
an internally working candidate nor a general GPL label authorizes public binary
publication. The source/release workflow blocks binary artifact upload/publication
until these gates are explicitly cleared with evidence. No legal entity or copyright
holder for third-party components is invented here.
