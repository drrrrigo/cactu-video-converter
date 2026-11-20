# Release license audit — v0.1.0-beta.1

## Current audit — 2026-11-20

**BLOCKED. No final RC1 or redistribution approval is declared.** The authoritative
status is [BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md). Historical evidence
below describes earlier candidates and must not be mistaken for the current inputs.

### Facts observed and technical evidence

| Component / exact file | Fact observed | Technical evidence / license obligation | Unresolved question / resolution |
| --- | --- | --- | --- |
| Cactu original source | Owner chose GPL-3.0-or-later | LICENSE, pyproject.toml, repository history | No missing owner license choice |
| CPython runtime | Canonical release remains 3.14.7; mismatches and dirty trees are now rejected before packaging | Official source SHA-256 `3b48dac8fb59f62eaa67ac83c1eb12bda1b7a08406dd286e252c11a66be27f81`; exact PSF text; pinned CI-family Linux interpreter hash in toolchain.json | Final payload must show 3.14.7 and account for its native dependencies; old 3.14.8 image is superseded |
| FFmpeg / FFprobe executables, both platforms | Previous Nov 1 release is now HTTP 404; its archives remain only in the local ignored cache | User must be able to rebuild from maintained inputs. Dated daily releases have short retention | Preserve approved inputs/source at a maintained location before RC1; do not rely on an expiring URL |
| Retained Oct 31 FFmpeg n9.0.2-39 | Investigated, then rejected for RC use | Compared with prior n9.0.2-42: excludes Ogg allocation-error handling and chained Vorbis parsing fixes; [upstream comparison](https://github.com/FFmpeg/FFmpeg/compare/7adfbe40dc...d7643a0fe3) | A retained older build must not silently regress fixes; it is audit evidence only |
| Current dated FFmpeg n9.0.2-61-gd59078794d-20261120 | Preparation/audit input remains in the 9.0.2 family, with exact Windows/Linux archives, hashes, configuration, recipe and FFmpeg revision in the manifest | GPL/version3, libx264/libass, no nonfree; repeat native -version/-buildconf/-L and capability validation for these exact bytes | Not a final selected/approved RC. Full linked-library source/notice closure and durable input retention remain incomplete |
| Statically linked libx264/libass and other enabled FFmpeg libraries | A recipe revision lists source declarations; it does not ship or prove the entire matching source set | release/source-evidence.json retains exact recipe/FFmpeg source archives and hashes; inspect all enabled libraries and patches | Need complete per-library sources/notices and correspondence to binaries, including toolchain/runtime code. Recipe base images use floating tags; source declarations alone do not close this |
| PySide6 / Essentials / Addons / Shiboken 6.11.2 | Existing wheel versions remain pinned; only actual packaged modules are inventoried | Eight exact source-license texts retained at commit `24627cd36e1593adf22eb1f2950e4248e7bcc1ec` | Proposed GPL-3.0 option for eligible binding/Qt modules requires review of each actual module and included third-party terms; no blanket whole-Qt approval |
| Qt native libraries and platform/image/input plugins | Native payload walker records actual files/ hashes, origin wheel, embedded Python modules and dynamic dependencies | Actual artifact reports replace the former development-environment-only list | Need module-specific notices, exact sources and LGPL/GPL assessment. Each unresolved file stays BLOCKED; a general GPL text is insufficient |
| Linux libraries copied from build OS | Per-file source package/version and copyright hash are queried where available | Need exact distribution source packages/patches, packaged notices and appropriate LGPL replacement/relinking information | Unidentified or uncopied notices/source packages prevent closure; do not infer approval from an OS package name |
| Windows DLLs | Actual installed and extracted portable files are enumerated separately, including PE import dependencies | Need origin/version/terms for Python, Qt, Microsoft runtime and other DLLs | Resolve native reports individually; no arbitrary developer DLL is approved by default |
| psutil 7.2.2 | BSD-3-Clause notice is collected from the exact installed wheel | Exact wheel/source hashes recorded in dependency-provenance.json; actual shipped native and Python modules are inventoried | Verify final packaged notice and module mapping |
| PyInstaller 6.16.0 | Compiler is build-only; bootloader/runtime hooks are embedded | Exact COPYING with bootloader exception retained under licenses/packaging-runtimes; actual executable/PYZ inspection identifies embedded modules | Do not describe the complete compiler, altgraph or test packages as shipped runtime dependencies merely because installed in the build environment |
| appimagetool 1.9.1 | Hash-pinned build-only tool; filesystem output embeds a separately pinned runtime | Tool input and runtime/stub roles recorded separately; license/source review of the tool remains required | Build-tool licensing does not establish embedded runtime compliance |
| AppImage runtime `runtime-x86_64`, SHA-256 `617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46` | Source commit `fedfad51acc2860b2916a1eef32ba4a500ff31ef`; root MIT text explicitly lists statically linked libraries | Source retained; Makefile links squashfuse, zstd, zlib, fuse3 and mimalloc. Script pins fuse 3.15.0 and squashfuse 0.5.2, including a libfuse patch | Need the complete static dependency notices/source/relinking material. Alpine package-derived inputs are not fully pinned by the root MIT text; libfuse LGPL obligations survive |
| Inno Setup 7.1.1 generated Setup/uninstaller | Exact source commit `2527da77ff7983514f535d19391a748c5d898336` and license retained | Root terms permit use/redistribution subject to retained copyrights/addresses and other component exceptions; inspect exact installed stub/runtime | Need included compression/other third-party terms and final stub inventory. Root license alone is not approval for every component |

The facts above are **technical evidence, not legal certainty**. Licenses are not
changed merely because Cactu uses GPL. Public binary uploads remain behind the
existing false redistribution flags and now also require complete exact-payload
evidence at publication. Owner approval cannot override missing technical evidence.

### Source delivery and LGPL assessment

Recipient source instructions are **not complete**, so no valid blanket source offer
is asserted. `release/source-evidence.json` lists retained immutable archives and
their hashes; local archives are under ignored release/evidence/local/sources.
Those archives cover only the projects explicitly named there, not every linked
library. Full corresponding sources/patches/build information must be retained at
maintained, recipient-accessible locations alongside an approved release.

Qt libraries in ONEDIR/AppImage are separate dynamic files. The packaging does not
deliberately prevent local replacement, and no application signature enforcement
is added. This observation alone does not establish LGPL compliance. If relying
on LGPL for a module, preserve its notices, corresponding modified/unmodified
sources, reverse-engineering/replacement rights and required installation/relinking
information. Other Qt modules may require the GPL option. Statically linked
libfuse in the AppImage runtime needs separate analysis; replacing a Qt DLL does
not satisfy that obligation. No runtime/kernel/GPU driver is licensed by analogy.

### Exact native payload findings and stop condition

Audited source is `eabc0920b4d091cba3b6670b263182babca7e539`; native run
[44810167815](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44810167815)
passed both build/smoke steps and failed only at the intended distribution gate.
Metadata-only evidence is retained in
`release/evidence/beta1-audit-eabc092/`, including separate installed/portable/
AppImage inventories, actual FFmpeg output and build-generated hashes. No CI
application binary was uploaded. These are audit outputs, not a final RC inventory.

The actual Ubuntu image contains 392 files (244 native), 382 embedded Python
modules and 20 component groups requiring review. Windows installed/portable
contain 272/270 files, 123/122 native files, 380 embedded modules each and 7/6 open
groups. There are 101 unresolved file origins in Ubuntu and 47 in each Windows
payload. Known origin is not the same as reviewed terms/source delivery. Exact
lists and hashes are in the retained reports; do not extrapolate from group counts.

| Exact file/component in audit output | License / evidence observed | Reason blocked | Possible resolution |
| --- | --- | --- | --- |
| `usr/bin/_internal/ffmpeg/ffmpeg`, `ffprobe`; Windows `_internal/ffmpeg/ffmpeg.exe`, `ffprobe.exe` | Actual GPL-3.0-or-later output/configuration with version3, x264/libass, no nonfree; individual static dependencies retain their terms | Core/recipe archives exist, complete matching linked-library sources/patches/notices and durable delivery do not | Retain/host the complete matching source/build set or use a controlled fully documented build; preserve mandatory capabilities |
| AppImage outer ELF prefix, pinned runtime input SHA `617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46` | MIT runtime plus libfuse LGPL-2.1 material, squashfuse and other static dependencies | musl/zstd/zlib/mimalloc exact Alpine-derived correspondence, complete notices and applicable static relinking material unresolved | Reconstruct exact static inputs/source/objects/patches and review delivery, or replace runtime only after compatibility/compliance validation |
| `usr/bin/_internal/PySide6/Qt/lib/libQt6VirtualKeyboard.so.6`, `libQt6Pdf.so.6`, other actual Qt modules/plugins; Windows `_internal/PySide6/Qt6VirtualKeyboard.dll`, `Qt6Pdf.dll` | Qt 6.11.2 source/license texts retained; module terms and third-party terms apply individually | Proposed GPL option not yet established for the complete actual module/third-party subset | Map each actual library/plugin to exact module sources/notices and chosen permitted license option; preserve dynamic replacement information where LGPL is relied on |
| `usr/bin/_internal/libmvec.so.1` | Build-host glibc source package 2.35-0ubuntu3.18; glibc LGPL terms require file-specific review | Bundled even though libc/loader remain host dependencies; exact notice/source and necessity not closed | Retain distribution source/patches/notices and document replacement, or deliberately exclude only after dependency/functional validation |
| `usr/bin/_internal/libssl.so.3`, `libcrypto.so.3`; Windows `_internal/libssl-3-x64.dll`, `libcrypto-3-x64.dll` and additional Python-provided OpenSSL pair | Actual files/imports/hashes recorded; exact OpenSSL build/version-specific terms not established by a Python project label | Per-file versions/provenance/notices incomplete; CPython PSF notice alone is not an OpenSSL review | Resolve exact Python/runner-provided origins, applicable OpenSSL source/license text and packaged notices |
| Windows `_internal/ucrtbase.dll`, `_internal/api-ms-win-crt-*.dll`, `_internal/PySide6/MSVCP140*.dll` | Actual Microsoft runtime files recorded; applicable Microsoft redistribution terms need exact input/version attribution | Wheel/OS origin and redistribution conditions not completely evidenced | Match files to approved runtime distribution/EULA/notice evidence; do not infer rights from an import name |
| Setup executable PE prefix and installed `unins000.exe` | Inno Setup 7.1.1 root license/source retained, additional component terms apply | Compression and other installer runtime/stub terms not completely audited | Retain exact additional terms/notices/source where required and map them to generated installer/uninstaller components |

No known graphics/kernel driver-file patterns were found in the actual outputs.
That scan is supporting evidence only, not blanket approval for native libraries.
Full packaged Cactu/PSF/PyInstaller/psutil/retained Qt text presence is verified,
but missing component-specific notices prevent calling the license payload complete.

**STOP before RC1 under the request's dependency rule.** These gaps are explicit
technical evidence deficiencies, not a claim that the named dependencies can never
be redistributed. Do not ask the owner to bless missing source/notices. Close them,
build an exact reviewed RC, then request manual results and final human approval.

### Final owner approval

- Technical dependency/source closure: **BLOCKED**.
- Human third-party redistribution approval: **NOT GIVEN**.
- Windows/Linux exact-artifact manual tests: **PENDING MANUAL OWNER TEST**.
- Final owner publication approval: **NOT GIVEN**.

If the source correspondence cannot be established for the selected provider,
stop RC1 and use the contingency in [FFMPEG_SOURCE_BUILD_STRATEGY](FFMPEG_SOURCE_BUILD_STRATEGY.md).
Do not flip any approval flag to compensate for missing evidence.

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
