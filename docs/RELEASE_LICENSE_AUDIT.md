# Release license audit — v0.1.0-beta.1

## Current blocker resolution — 2026-11-20

**BLOCKED before RC1.** No legal/publication approval is declared. The full current
facts, exact obstacles and remediation matrix are in
[BETA1_BLOCKER_RESOLUTION](BETA1_BLOCKER_RESOLUTION.md); authoritative gates are in
[BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md).

The current actual native payloads use clean source **7b7d23c**, audit run
[44845101385](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44845101385).
Both native builds and frozen smoke passed; distribution eligibility intentionally
failed and binary upload was skipped. JSON/checksum reports are retained in
release/evidence/beta1-resolution-7b7d23c, including original report hashes and
separate installed/portable/AppImage per-file source-obligation joins. Baseline
eabc092 reports remain unchanged and are historical comparisons.

| Item | Resolved technical evidence | Still open |
| --- | --- | --- |
| Cactu source | Owner chose GPL-3.0-or-later; LICENSE and SPDX metadata | No source-license choice pending |
| Dependency surface | 58 Windows native paths and 18 Ubuntu native paths removed; narrow unused Qt plugin exclusions, Windows Schannel and OS UCRT/API-set boundary verified by native smoke | No blanket exclusion of required libraries; libmvec remains an actual FFmpeg/FFprobe dependency |
| Native copying origins | 47 Windows / 101 Ubuntu unknown origins reduced to zero; actual supplier/OS/wheel version, SHA-256, PE versions/flags and component notices mapped | Known copying distribution does not establish upstream provenance, complete source or redistribution rights |
| Qt 6.11.2 | Exact qtbase/qtsvg/qtwayland/PySide source archives, module mapping and 196 legal/attribution files retained | Wheel build configuration and incorporated third-party correspondence, including ICU 73; eligible GPL/LGPL assessment and exact notice scope |
| Ubuntu libraries | All 64 exact source packages, original archives/Debian patches, notices and applicable common license texts retained; source parts match .dsc SHA-256 and size | PGP signatures not independently verified; file-specific conditions, replacement assessment and maintained recipient delivery |
| Windows CPython / native dependencies | Python 3.14.7 source, wheel/interpreter supplier and PE versions recorded; duplicate Qt OpenSSL pair removed, Python SSL retained | Native compression/SSL library source/build/notice mapping, beyond the PSF core text |
| MSVC runtime | Actual supplier versions 14.44.35211.0 and 14.51.36247.0 retained; compiler MSC v.1944; no actual PE prerelease resource flags | Exact supplier REDIST/terms and qualifying redistribution rights must be reviewed; do not invent owner Visual Studio licensing |
| FFmpeg n9.0.2-61 | Exact core/recipe/binary/configuration retained; GPL/version3/no-nonfree and required tables pass; 132/133 recipe input sources retained; observed immutable provider OCI digests recorded | Xvid SVN r2204 server authentication failure; complete linked/generated/vendor/toolchain source/patch/notices correspondence and durable binary/source delivery |
| AppImage runtime | Opaque stub replaced with controlled offline fedfad51-cactu1; rootfs/99 APK hashes, static source/patches/link map/objects retained; two builds and separate relink reproduce dcf5f5b0…; component TAR has 131 verified members | Final individual component conditions/source-delivery review and maintained recipient source assets. MIT runtime text does not cover every static library |
| Inno 7.1.1 | Exact source/SBOM, Pascal Script licence and required acknowledgement, LZMA SDK declaration and old decoder exception retained | Map actual Setup/uninstaller linked objects to component terms; optional SBOM/compiler components are not all shipped |
| Recipient delivery | Local source indexes/hash verification and a tested runtime component source/relink TAR exist; dynamic replacement instructions in licenses/NATIVE_LIBRARY_REPLACEMENT.md | Local cache is not a public offer; complete source set/maintained assets and publisher source-asset wiring remain incomplete |

The GPL option for eligible Qt modules is recorded as a proposed source-review
choice, not whole-Qt legal clearance. Independent third-party terms survive it.
Dynamic Qt/native libraries remain separate replaceable files without an added
Cactu signature check. Static libfuse/runtime obligations are assessed separately;
replacement of a Qt library does not satisfy those obligations.

Official references supporting the packaging boundary and remaining conditions:
[Qt SSL backends](https://doc.qt.io/qt-6.11/ssl.html),
[Windows UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170),
[Microsoft redistribution conditions](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files),
[Microsoft REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution),
[FFmpeg legal guidance](https://ffmpeg.org/legal.html).
These are evidence for review, not a legal opinion or certification.

The per-file reports distinguish missing provenance, notices, corresponding source,
build/patch information, replacement/relink material, removed unused components
and conditional grants. No known driver-file pattern or missing declared notice
path was found; that bounded check does not establish complete notice scope.

**Decision:** do not start RC1 promotion. Continue the exact remediation matrix,
then require separate owner license review, manual Windows/Linux exact-artifact
results and publication approval. All three global approvals remain false. No
public beta tag/release/binary/source-bundle upload occurred.

## Historical audit — 2026-11-01 (superseded inputs)

Initial audit 2026-11-01, before release implementation. **Publication blocked.**

## Cactu source

At initial inspection, no LICENSE file, SPDX selection or copyright-holder
declaration was present. The owner subsequently chose GPL-3.0-or-later; see the
owner-decision record below and root LICENSE. That resolves Cactu's original source
license. Exact third-party compatibility/redistribution review remains open. No
legal entity or copyright holder is invented.

## Exact shipped components

No beta release binary exists yet, so there is no final transitive binary inventory.
Current requested pins: Python 3.14.7, PySide6/Qt/Shiboken 6.11.2, psutil 7.2.2,
PyInstaller 6.16.0, FFmpeg/FFprobe 9.0.2. Installed development-system libraries are
not proof of a release payload. Record wheel/archive hashes, package license files,
FFmpeg -version/-buildconf/-L, dependency/source inventory and native packaging
license obligations as candidates are examined. All unresolved entries block release.

## Required evidence before redistribution

- Cactu owner-selected license and compatibility decision.
- Exact FFmpeg/FFprobe archives, provider, hashes and coherent versions/configuration.
- No --enable-nonfree; actual GPL/LGPL/version flags and external library effects.
- Corresponding source for the shipped FFmpeg and linked components, not only a
  generic upstream homepage or an unverifiable "source offer" string.
- Exact Qt/PySide/Shiboken/Python/psutil/packaged library notices and license texts;
  applicable source/relinking/installation information and redistribution conditions.
- Complete per-artifact dependency/license inventory, packaged license payload and
  maintained source locations. Native OS libraries excluded/included deliberately.
- Native packager/runtime license checks and final human redistribution approval.

This document will distinguish observed upstream facts, packaged evidence and
unresolved legal/redistribution obligations. It is not a blanket legal approval.

## Owner decisions and candidate findings — 2026-11-01

The owner selected **GPL-3.0-or-later** for Cactu's original source and identified
https://github.com/drrrrigo/cactu-video-converter. The official GNU GPL v3 text is now
LICENSE, with the “or later” declaration in source metadata/README. No copyright
holder/company was fabricated. The remote repository was initially empty, with no
prior commits; no older unpublished local history was present in this workspace.

### Excluded Linux provider

The version/configuration listing for the previously documented Martin Riedl 9.0.2
Linux build explicitly includes `--enable-nonfree`. It is excluded; it was not staged
or distributed. Evidence: [provider version record](https://ffmpeg.martin-riedl.de/download/linux/amd64/1789931100_9.0.2/versions.txt).
FFmpeg's [legal guidance](https://ffmpeg.org/legal.html) requires evaluating the actual
configuration and exact corresponding sources rather than treating all builds alike.

### Selected internal candidate inputs

Both BtbN dated archives come from `autobuild-2026-11-01-12-49`, with build identity
`n9.0.2-42-gd7643a0fe3-20261101`. This is the 9.0.2 branch plus 42 revisions, not an
assertion that these bytes are the pristine upstream 9.0.2 tarball. Exact archive,
FFmpeg, FFprobe and supplied license hashes/configuration are committed in the
manifest. Linux execution verified matching build IDs/configurations, required
software capabilities and NVENC/AMF/VAAPI/QSV table exposure. Windows native execution subsequently verified the same integrity/coherence and
mandatory software tables. The pinned build also exposes h264_vaapi on Windows,
in addition to NVENC/AMF/QSV; the manifest now records the observed table exactly.
This does not add a Cactu Windows VAAPI backend or claim physical GPU availability.

Linux archive SHA-256: `11570b7bb1436ff432c91202ae0e7ea4be65359fd06650e18935c1ee9d005bf6`.
Windows archive SHA-256: `ce92c2ee8a90fbe3da3e8a2bd510f4ebc0e838d4cf433371095ac2179f95e834`.
The downloaded bytes matched the GitHub-published digests before extraction/execution.
Linux `-L` reports GPL-3.0-or-later; configuration includes `--enable-gpl`,
`--enable-version3`, libx264 and libass, without `--enable-nonfree`.

The archives contain one FFmpeg GPL license file and many static linked components.
**That payload does not establish complete matching source and license closure.**
The full linked dependency list is in the recorded configure string. BtbN's build
recipe is recorded, but the actual source revisions/patches/notice texts for every
included component have not been archived/approved for Cactu redistribution.
Both `corresponding_source_complete` and `redistribution_approved` remain false.
A public Actions artifact upload is distribution too and is gated accordingly.

### Python/wheel/native payload

Candidate license collection records exact installed package versions, declared
license expressions and copied license-file hashes in `component-inventory.json`.
Qt/PySide licenses and bundled third-party texts, psutil BSD notices, PyInstaller
GPL/exception texts and associated build-tool notices are collected where supplied.
The local candidate uses CPython 3.14.8 (host patch), not the release pin 3.14.7; its
build evidence records this mismatch. It is not a final distributable.

Open review items: ship the exact Python 3.14.7 PSF/third-party texts; identify the
used Qt modules and GPL/LGPL option and all associated corresponding-source/install
information; inventory every collected ELF/DLL/platform plugin and its version,
license and source; assess native libraries collected from the build OS; record
appimagetool/type2-runtime and Inno Setup runtime/stub licensing for their exact
pins. AppImage tool/runtime hashes are fixed, but pinning is not a license approval.
See Qt's [license overview](https://doc.qt.io/qtforpython-6/licenses.html) and
PyInstaller's [license/exception](https://pyinstaller.org/en/v6.16.0/license.html).

**Current result: Cactu source decision resolved; public binary redistribution
remains BLOCKED.** No approval flags were set merely because a candidate runs.
Complete and review these exact-input/source obligations before enabling candidate
uploads, collecting final manual tests or pushing the public beta tag.

### Additional exact-package findings

The installed 6.11.2 PySide6, Essentials, Addons and Shiboken wheel file manifests
contained **zero license text files** matching the collection audit, despite their
SPDX declarations. A request for the exact upstream PySide GPL text returned HTTP
503. Do not describe those notices as shipped/complete merely because the package
metadata lists alternatives. Resolve the upstream module/third-party notices and
corresponding sources before approval. The exact Python 3.14.7 PSF/combined notice
was retrieved from its official version tag and is now licenses/Python-3.14.7.txt
(SHA-256 b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231).
This improves the payload but does not close the remaining Python/Qt/native audit.

The public repository gained initial README commit 55e3d27 before cloning. That
minimal history is preserved and will be included in the source/history scan;
the earlier observation of an uninitialized remote was a point-in-time observation.

BtbN documents a 14-day retention window for daily builds (month-end builds have
longer retention). This dated November 1 input is not a permanent source/archive
mirror. Before release approval, retain the approved binary inputs and exact
corresponding sources at maintained locations, with their recorded hashes. The
current downloader fails closed if an input disappears; a pinned URL alone does
not guarantee long-term rebuild availability.

### Recovered exact PySide source license payload

The official Qt mirror's `v6.11.2` annotated tag resolves to commit
`24627cd36e1593adf22eb1f2950e4248e7bcc1ec`. Its eight LICENSES text files were
retrieved successfully through the official GitHub mirror and retained under
`licenses/qt-pyside-6.11.2/`, with immutable URLs and SHA-256 values in
`provenance.json`. Candidate license collection now preserves this directory.
This supersedes the failed text-download attempt above, but does not establish
the complete Qt module/native third-party inventory or corresponding-source set.

The BtbN recipe tag resolves to commit
`5ece62897c650b863c1ddda7b6964845344aef2d`, recorded in the FFmpeg manifest.
An immutable recipe is useful provenance; it is not a substitute for the exact
sources and patches for every library in the produced binaries.

Native Windows/Linux package and frozen smoke tests now pass (candidate run
41350221053). This verifies runtime operation, not license/source completeness.
Both jobs correctly blocked public artifact upload at the license gate. Cactu's
source/history/privacy audit is recorded as complete with no findings; the separate
dependency license and final publication approvals remain false.


## Controlled FFmpeg implementation follow-up

See [FFMPEG_CONTROLLED_BUILD.md](FFMPEG_CONTROLLED_BUILD.md). A reduced Linux
candidate has actually compiled from locked FFmpeg/x264/libass/NV header sources.
libxvid is absent; native MPEG-4/HEVC decoding and required codec/filter tables pass.
An isolated frozen AppImage using the candidate passed preview/sequential queue/
loudness smoke. The selected vendor manifest was not changed. Host font/shaping/
VAAPI/VPL libraries and compiler source/replay closure remain incomplete; this is
a CachyOS experiment, not the official Ubuntu release baseline. No reproduction
or full source-compliance claim is made. Native Windows bootstrap is implemented
as a metadata-only manual workflow; its result must be assessed independently.

Publishing now supports approved corresponding-source assets, requires exact source
index hash approval and completeness/per-file hashes, and includes them in checksums.
No source archive or executable is uploaded by this experiment. All global approval
flags remain false. Qt/ICU/Python native, MSVC eligibility, installer scope and final
recipient source obligations remain open. RC1 is still blocked.
