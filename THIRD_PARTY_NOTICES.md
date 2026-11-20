# Third-party notices — beta candidate

Cactu's original source is GPL-3.0-or-later; see LICENSE. This does not replace
upstream licenses. Candidate bundles include a `licenses/` directory collected from
the exact pinned Python/wheel build environment, FFmpeg's supplied GPL text and a
component inventory. That collection is evidence, not a declaration that every
native-library/source obligation has been satisfied.

## FFmpeg / FFprobe

Audit input: FFmpeg-Builds build n9.0.2-61-gd59078794d-20261120, from the dated archives
pinned in vendor/ffmpeg/manifest.json. Its actual configuration enables GPL/version3
and libx264, and does not enable nonfree. `ffmpeg -L` reports GPL v3 or later.
FFmpeg source: https://github.com/FFmpeg/FFmpeg . Build recipe:
https://github.com/FFmpeg-Builds/FFmpeg-Builds . These links alone do not provide an approved
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

## Final preparation evidence

The active manifest now identifies the current **n9.0.2-61-gd59078794d-20261120**
audit input. The old dated release expired; an older retained input was evaluated
and rejected because it omitted later fixes. Neither is an approved final RC.
Runtime/tool license texts and immutable provenance are retained under
licenses/packaging-runtimes. Appimagetool is build-only; its separate embedded
runtime includes static third-party code with its own terms. Inno Setup contributes
installer/uninstaller code. PyInstaller contributes a bootloader/runtime hooks,
not the full build compiler as an application dependency.

Actual per-artifact payload reports determine which Python/Qt/native files are
shipped. The build-environment notice collection is not a shipped-runtime inventory.
Required third-party notice/source/relinking closure remains incomplete; these
added texts do not authorize redistribution or replace individual upstream terms.
