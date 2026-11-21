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

## Retained Qt and installer component notices

Qt source/module license and third-party attribution material for the pinned
6.11.2 source revisions is supplied in `licenses/qt-6.11.2/`. This is a conservative
notice superset for the selected source modules, not a declaration that every
listed third-party component is linked into Cactu. Per-file mapping and exact
source archive hashes accompany the payload/source manifests. Eligible Qt/PySide
components are evaluated under their GPL v3 option; independent third-party terms
remain applicable. Native libraries remain separate replaceable files in ONEDIR.

The Windows installer is made using Inno Setup and RemObjects Pascal Script.
RemObjects Pascal Script can be found at https://github.com/remobjects/pascalscript.
Its retained license requires this acknowledgement in documentation. The exact
Inno Setup 7.1.1 SBOM, Pascal Script notice, LZMA SDK public-domain declaration and
older size-optimized decoder's linking exception are under
`licenses/packaging-runtimes/inno-components/`. The SBOM identifies optional
components as well as the compiler; listing an optional component does not assert
it is present in the generated installer. No blanket installer approval is given.

## Controlled AppImage runtime audit input

The 9b36721 and 7b7d23c audits select Cactu-controlled fedfad51-cactu1 rather than the opaque
provider stub. Exact rootfs/APK/source/patch/relink input hashes and the repeated
runtime hash are in release/appimage-controlled-lock.json. Its source-derived
static library notices accompany licenses/packaging-runtimes/controlled-runtime.
The runtime uses libfuse/squashfuse, musl, zstd, zlib, mimalloc and GCC target
runtime inputs with their individual terms. The source notice collection is a
conservative superset; only link-map inputs are declared incorporated. Native CI passed; complete recipient
source delivery and human review remain required. This is not beta approval.


## Current controlled-runtime and native audit evidence

The 7b7d23c native audit actually uses the controlled fedfad51-cactu1 runtime;
it is no longer only a proposed next audit input. Sources, static link inputs,
notices and an independently tested relink are recorded. The local component
source TAR receipt is release/runtime-source-delivery.json; no public complete
source offer is asserted. GPL/LGPL and independent component terms still apply.

Current actual native payload mapping, exact Ubuntu sources/patches and proposed
eligible Qt module options are recorded in release/evidence/beta1-resolution-7b7d23c,
release/ubuntu-source-lock.json and release/qt-source-lock.json. Windows Qt uses OS
Schannel; Python OpenSSL remains separately subject to its actual supplier terms.
Visual C++ runtime DLLs retain Microsoft conditions and are not relicensed by Qt
or Cactu. Complete upstream/build/notice/delivery review remains blocked as specified
in docs/BETA1_BLOCKER_RESOLUTION.md. These records do not authorize publication.


## Controlled FFmpeg source-root notices (unapproved candidates)

Controlled candidate source notices for FFmpeg, x264, libass, NV codec headers,
oneVPL and Windows AMF headers are retained in licenses/ffmpeg-controlled. Its
provenance index identifies exact upstream bytes and platform scope. It is a
source-root notice superset, not a final declaration that optional/build-only code
is incorporated. The selected provider runtime is unchanged. The ICU 73.2 and
CPython OpenSSL/compression source/supplier notices are retained separately under
licenses/icu-73.2 and licenses/python-native. Source archives remain local; exact
mapping does not automatically approve complete corresponding-source delivery or
individual component terms. See docs/FFMPEG_CONTROLLED_BUILD.md.
