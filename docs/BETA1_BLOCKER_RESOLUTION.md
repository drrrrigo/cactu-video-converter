# Beta.1 redistribution blocker resolution

Current controlled-build outcome and remaining RC1 blockers: [FFMPEG_CONTROLLED_CLOSURE](FFMPEG_CONTROLLED_CLOSURE.md), reviewed 2026-11-21. This is the authoritative current summary; the following sections preserve earlier audit results and intermediate build history. A blocker or test count from an earlier section must not be applied to a later candidate without its exact source/artifact identity.

Reviewed 2026-11-20 (America/Sao_Paulo). **Improved, still BLOCKED before RC1.**
Only packaging, source retention and audit tooling changed. Product/media behavior
is preserved. No beta tag, release, binary or source-bundle publication occurred.
All three technical/license/publication approval fields remain false.

## Resolved engineering issues

Baseline: actual eabc092 audit retained unchanged. New native payload source:
**7b7d23c9c77afac0933cc1607ab0160cbbc7ec3c**. The containing follow-up commit adds
source acquisition/evidence/docs; it must not be substituted for the packaged SHA.

| Payload | Before files (native) | After files (native) | Removed | Added notice/data paths | Unknown copying origins before → after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Windows installed | 272 (123) | 449 (65) | 58 | 235 | 47 → 0 |
| Windows portable | 270 (122) | 447 (64) | 58 | 235 | 47 → 0 |
| Ubuntu AppImage | 392 (244) | 705 (226) | 18 | 331 | 101 → 0 |

Total files increased because legal material was added; native code decreased.
All 47 former unknown Windows paths were removed. On Linux, 93 retained paths
received copying origins and eight formerly unknown paths were removed.
Known copying distribution is **not** complete upstream/source/license clearance.
Eight/seven/88 component groups still require review for installed/portable/Linux;
these finer groups are not unresolved-origin file counts.

* QtGui now excludes only the unused PDF image and virtual keyboard input plugins
  before native analysis. QtPdf/QML/Quick/VirtualKeyboard chains disappear.
  QtCore/Gui/Widgets/Network, SVG, platform plugins, native input methods and styles
  remain. Import/dependency analysis and frozen preview/queue tests support this.
* Windows Qt TLS uses Schannel. Its optional OpenSSL Qt plugin and two duplicate
  host OpenSSL DLLs are excluded; Python SSL dependencies remain. Frozen tests
  confirm supportsSsl() and active Schannel.
* Forty-five app-local UCRT/API-set contract files are excluded. Windows 10/11
  supplies these OS contracts; Visual C++ runtime DLLs remain. No arbitrary DLL
  replacement or new system installation is introduced.
* libmvec.so.1 remains: both FFmpeg and FFprobe declare it in ELF dependencies.
  Its exact glibc distribution source/patches/notices are now retained.
* Copy-source resolution follows PyInstaller aliases and merged /lib and /usr/lib
  ownership. Actual hashes, wheel/OS origins, PE versions/flags and Ubuntu sources
  are recorded. No final PE has its prerelease resource flag set. No known driver
  patterns or missing declared notices were found; undeclared obligations remain.

## Controlled AppImage runtime replacement

The opaque stub was replaced with **fedfad51-cactu1**, from the same upstream
runtime source in an isolated Alpine 3.21.10 root with 99 hash-locked APK inputs.
Network is disabled during installation/compilation. Sources, six exact aports
recipe/patch snapshots, compiler, link map, runtime.o and 15 static/CRT inputs are
recorded in release/appimage-controlled-lock.json.

Two local offline builds and native Ubuntu CI produced runtime SHA-256
`dcf5f5b07d5679e37c5a2decff55a65fc2962c565fdaacbf88eaf2bd4ad61ac4`.
An offline relink using retained object/static inputs reproduced that hash.
Incorporated code includes libfuse, squashfuse, musl, zstd, zlib, mimalloc and GCC
target runtime inputs. Individual notices/exceptions are retained; MIT is not
blanket clearance for the static libraries.

The local source/relink component TAR contains 131 verified files plus README and
manifest, SHA-256
`4760a8477193572c103daaa76a50258f0d0cf6fcde6d7f16e78615f39a7be459`.
Every member hash was checked after reopening it. It excludes compiler/rootfs/APK
binaries, whose retrieval hashes remain locked. Replacement instructions require
no Cactu signing key. Receipt: release/runtime-source-delivery.json. This is local
review material, **not a complete Cactu source offer or a published source asset**.

## Sources and notices acquired

* Four exact Qt/PySide 6.11.2 archives (qtbase, qtsvg, qtwayland, bindings), immutable
  commits and hashes: release/qt-source-lock.json. Actual Qt files map to source,
  module, proposed eligible GPL option and notice directory. The 196 retained
  legal/attribution files are a conservative notice superset for these modules,
  not a claim that every listed third party is shipped.
* All **64 exact Ubuntu source packages**, original archives and Debian patches,
  retained with each part matching official .dsc SHA-256/size. Exact Launchpad
  publications: release/ubuntu-source-lock.json. PGP signatures were not separately
  verified. Obligation reports join these records to actual library versions.
* **132 of 133** top-level FFmpeg recipe inputs retained (previously 115).
  Explicit version tags resolve to immutable commits; Git exports verify object
  IDs; LAME uses SVN r7153 through an isolated signed-package SVN client. Reruns
  preserve resolved tags/hashes and reject changed cached bytes.
* Exact provider build logs identify the OCI image digests actually used:
  release/ffmpeg-provider-build-evidence.json. The selected executable build stays
  n9.0.2-61-gd59078794d-20261120; no FFmpeg replacement was made.
* Inno Setup 7.1.1 source/SBOM, Pascal Script license/required acknowledgement,
  LZMA SDK public-domain terms and old decoder exception retained. Optional
  compiler/SBOM components are not automatically declared incorporated.

verify_source_delivery.py verified 146 Qt/FFmpeg/runtime source entries and all
64 Ubuntu source packages from local bytes. This is not proof of a complete
source graph or binary correspondence.

## Exact remaining obstacles and remediation

| Category | Affected files / evidence | Remaining action |
| --- | --- | --- |
| Missing corresponding source | Xvid scripts.d/50-xvid.sh, SVN r2204 | Official HTTPS SVN returns E170013/E215004 authentication failure. Obtain an authorized exact export or verified official equivalent mirror; do not substitute another revision. No credentials supplied. |
| Source/build/patch correspondence | Windows _internal/ffmpeg/ffmpeg.exe and ffprobe.exe; Linux usr/bin/_internal/ffmpeg/ffmpeg and ffprobe | Top-level archives are not the linked source graph. Retain generated/Cargo/vendor/submodule inputs, patches, toolchain/runtime sources, per-library notices and actual configurations; join to each executable. |
| Controlled FFmpeg contingency | Exact images now observed; provider recipe/input locks | Implement and validate controlled native Windows/Linux builds if provider correspondence cannot close. No replacement FFmpeg build completed here. Preserve required capabilities. |
| Upstream provenance / notices / build | Actual Qt wheel ICU and other third-party binaries without module mappings; Qt build_correspondence=REVIEW_REQUIRED | Obtain wheel build configuration and exact third-party source/notice mapping, including ICU 73; assess individual GPL/LGPL options. Wheel copying origin alone is insufficient. |
| Python incorporated libraries | Native CPython files, especially Windows SSL/compression extensions | Join exact upstream versions/build sources and terms; PSF core source/text alone is insufficient. |
| Conditional redistribution grant | MSVCP/VCRUNTIME 14.44.35211.0 and 14.51.36247.0, supplier recorded per file | Review exact supplier REDIST/terms and owner qualifying rights. No PE prerelease flags found; this is not a grant. Do not self-certify a Visual Studio license. |
| Native terms / replacement | Ubuntu libraries joined to 64 exact source packages | Review file-specific conditions and dynamic replacement method. Acquisition is done; assessment and recipient delivery remain. |
| Installer incorporation / notices | Generated Setup prefix and unins000.exe | Map actual Inno compression/runtime objects to retained SBOM/terms; distinguish optional compiler-only components. |
| Static relink / delivery review | Controlled AppImage prefix | Source/patch/object/static inputs and tested instructions now exist. Review component obligations and maintain recipient delivery. |
| Durable recipient delivery | Required binary/source/notice sets | Maintain approved immutable source assets/indexes beside binaries. Current publisher uploads three application artifacts and checksums only; source-asset integration remains. Local caches/TAR are not public delivery. |

No owner approval is requested to compensate for missing technical records.
After closure, require human license review, exact-artifact Windows 11/portable/
Linux desktop tests, then final publication approval.

## Tests and exact evidence

* Final local suite: **169 tests passed**, 69.376 s, canonical Python 3.14.7,
  opt-in RX 7700 XT VAAPI/loudness/embedded+external subtitle checks enabled.
* Native source CI [44844968490](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44844968490),
  7b7d23c: 166 discovered, 163 pass + three physical-GPU skips per platform.
* Native packaging audit [44845101385](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44845101385)
  passed builds/frozen smoke on Windows/Linux: x264/AAC/Faststart, subtitles,
  preview, sequential two-job/loudness queue and installer install/convert/uninstall.
  Overall run intentionally **failed at distribution eligibility**; binary upload
  skipped. No cloud physical-GPU validation or green release workflow is claimed.
* Metadata-only reports, exact comparisons and per-file source-obligation joins:
  release/evidence/beta1-resolution-7b7d23c/. Original bytes/hash receipts retained.
  Generated joins do not rewrite original inventories.
* The containing follow-up commit triggers full source CI again. Its result is
  separate from the native packaged source SHA.

A new internal audit build for local testing is technically feasible, labelled as
an audit. **RC1 preparation/promotion remains blocked.** Hosted runner binaries
were not retained as an owner-test RC set. Manual desktop records remain pending;
earlier local AppImages are distinct audit outputs, not the 7b7d23c hosted bytes.


## Final source validation and local audit package

Follow-up source **a99c208142d36e42449073f982de2e54bf04b9de** passed native
Windows/Linux source CI [44851028673](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44851028673):
169 discovered, 166 passed and three optional physical-GPU skips per platform;
Ruff/branding/bounded source-history scans passed. This is separate from the
7b7d23c hosted package audit and the local 169/169 physical AMD source test run.

A fresh local CachyOS AppImage was built from clean a99c208 with Python 3.14.7.
ONEDIR and AppImage frozen tests pass, including preview and a two-job loudness
queue. SHA-256:
`188166a15179b3a7295c2427a1cabce7f09b99eb8a5ff89027375a7f5257984f`.
The file is local under dist/candidate; earlier audit output was preserved under
dist/audit-eabc092-20261120. No executable was uploaded. Metadata-only receipt:
release/evidence/beta1-local-a99c208/receipt.json.

This local image has 611 files (228 native) and 91 unresolved copying origins for
host Arch/CachyOS libraries, outside the Ubuntu dpkg mapping. It is explicitly an
**AUDIT_ONLY_NOT_RC1** local test build, not the Ubuntu baseline inventory and not
a redistribution-approved RC. The zero unknown-origin claim above applies only
to the retained 7b7d23c native Ubuntu/Windows inventories. Full local inventory
remains beside the ignored local artifact; no extra portability/legal clearance
or manual desktop result is inferred. Release/tag lookup remained empty.

This evidence-only follow-up does not change the existing media or packaging
pipeline. Its containing commit triggers source CI again; CI success never alters
the false technical/license/publication approvals or the remaining blocker matrix.


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


## Current controlled-build engineering results

The reduced Linux FFmpeg candidate is implemented and tested: 170/170 source tests
pass with physical AMD VAAPI, and isolated ONEDIR/AppImage smoke passes. Sources,
output hashes, capability differences, actual XVID input decoding and 24 host-library
fingerprints are in release/evidence/controlled-ffmpeg-linux and
FFMPEG_CONTROLLED_BUILD.md. Compression/character conversion is explicitly enabled
to preserve PNG and screen-recording decoders. The selected provider is unchanged.

Two actual OpenSSL DLL hashes match official CPython 3.14.7 binary-deps exactly;
OpenSSL/bzip2/XZ/zlib-ng sources/notices and the Qt ICU 73.2 source/notices are now
retained and reverified. This resolves those specific source/supplier identification
items, without claiming full wheel/static-extension correspondence or legal approval.
The source publisher supports exact approved index/assets/checksums; it remains
fail-closed and no sources/binaries were uploaded. Windows native bootstrap and
Ubuntu-baseline/toolchain/source/notice closure remain separate pending gates.
All three global approvals remain false; RC1 is not ready. See the full current
report for hashes, limitations and genuine owner actions after technical closure.
