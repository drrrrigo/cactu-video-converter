# Final dependency review and common native audit candidate

This report supersedes FFMPEG_CONTROLLED_CLOSURE.md and earlier provider-only
blocker lists. Historical receipts keep their original identities. **AUDIT
CANDIDATE — NOT RC1.** No human license, technical approval or publication gate
is automatically cleared. No beta tag, Release, public executable or source
bundle is authorized by these tests.

## Engineering complete

The selected packaging baseline is now `release/controlled-baseline.json`, not
the generic provider. `stage_controlled_runtime.py` checks the locked recipe,
native tool profile, source inputs, four exact hash-named static libraries and
both executable hashes, then generates a build-local manifest consumed by
`build_release.py`. The legacy provider remains only a reference-fixture input
for HEVC/AV1 generation. Native packaging runs in the original clean checkout;
there is no synthetic source snapshot. No media-processing pipeline was rewritten.

FFmpeg uses x264/libass/dav1d/oneVPL plus required codec SDK interfaces; it excludes
nonfree and rejects unexpected libass/VPL/x264/dav1d DLL fallback. Actual AV1
reference pixels remain tested. Native command-entry hashes are checked, but the
bootstrap sysroot is not a hermetic toolchain. Byte-identical reproduction is not
a universal legal condition. Assembly remains disabled; performance qualification
and physical NVIDIA/Intel/Windows AMD devices are not inferred from interface tests.

Windows notices are selected by **actual DLL SHA-256**, not basename or the whole
MSYS installation. `msys_payload_notices.py` integrates the exact supplier texts
and ships `licenses/native-msys2/FILE-MAP.json`. CPython's same-named libffi DLL is
recognized by its own supplier bytes, avoiding false MSYS attribution. Only the
actual remaining native packages are included in the review and source offer.

The Qt review adds the previously missing **qtimageformats 6.11.2** module, retains
208 exact source notice files across the five selected Qt/PySide archives and
maps TIFF/WebP/TGA/WBMP/ICNS plugins to their own module. Actual 6.11.2 source
license alternatives support the selected GPL v3 route for eligible module code;
independent third-party terms remain applicable. ICU 73.2 identity/notices remain
mapped. The optional 20.6 MB Windows Mesa software renderer is omitted because
Cactu uses raster QtWidgets, with no QtQuick/OpenGL widget dependency; actual
frozen tests verify the resulting bundle. This does not remove FFmpeg hardware
encoding. Removed Qt/Mesa components are not remaining distribution blockers.

CPython 3.14.7's complete incorporated-notices document is packaged. Exact source
records identify bzip2, XZ/liblzma, zlib-ng, OpenSSL, mpdecimal 4.0.0, libffi 3.4.4
and zstd 1.5.7. Existing OpenSSL DLL bytes still match the official CPython supplier.
Permissive/public-domain terms require their actual notices; they do not create a
blanket demand to rebuild Python extensions byte-for-byte or publish all build tools.

Inno Setup 7.1.1 generated Setup/SetupLdr/uninstaller scope is reviewed separately
from the compiler: Pascal Script acknowledgement is retained, the small LZMA
loader uses its explicit exception/public-domain terms, and IS7zDec is the
public-domain C SDK decoder. The optional full 7z DLL and compiler-only
ISCC/ISIDE/Scintilla are not inferred as incorporated merely from a supplier SBOM.
See `release/inno-runtime-review.json` for exact source members and hashes.

The AppImage prefix retains its already tested runtime identity
`dcf5f5b07d5679e37c5a2decff55a65fc2962c565fdaacbf88eaf2bd4ad61ac4`.
Existing offline rebuild/relink evidence is reused. The recipient TAR retains all
15 static/CRT inputs, runtime.o, link map and applicable library sources/notices.
Ordinary kernel-header source archives are omitted from the proposed delivery;
they remain locked internal provenance/prerequisites. GCC sources remain where
standalone library/archive delivery requires them. No new runtime build or new
runtime hash is claimed from changing the source-offer layout.

## License-specific source and notice decisions

| Actual scope | Applicable action | Prepared evidence |
| --- | --- | --- |
| GPL Cactu/FFmpeg and selected Qt modules | Exact corresponding sources, used build inputs/recipes, applicable notices | Locked sources, exact source-commit TAR, candidate-bound index |
| LGPL dynamic libraries | Corresponding library sources/patches, notices and replacement information | Actual Ubuntu/MSYS source packages; `licenses/NATIVE_LIBRARY_REPLACEMENT.md` |
| AppImage LGPL static components | Sources, modifications, link/replacement material | Reduced verified source/relink TAR; original receipt retained |
| Separately delivered GCC runtime DLLs/shared libraries | Library GPL source method; exception governs eligible independent programs | Actual MSYS/Ubuntu GCC source package, GPL and exception texts |
| MIT/BSD/Apache/FTL/Unicode/bzip2/Zlib/public domain | Applicable copyright, license, attribution and change requirements | Actual payload notices; no standalone universal source duty |
| Permissive non-system inputs in the GPL FFmpeg combined work | Combined-work source scope may additionally require the used source | Only actual linked inputs, distinguished from independent permissive duties |
| Microsoft runtime DLLs | Applicable proprietary grant and owner qualifying rights | Exact paths, suppliers, versions and hashes; human decision remains pending |
| Ordinary OS interfaces and build-only tools | Do not label all downloaded packages shipped | Separate internal provenance and delivered-membership manifests |

The [GNU exception FAQ](https://www.gnu.org/licenses/gcc-exception-3.1-faq.html)
specifically distinguishes the independent program from delivery of libstdc++
itself. The library source duty is not waived by the exception. Likewise MSYS
liblzma 5.8.4 is 0BSD, CPython XZ 5.2.5 liblzma is public domain, gettext libintl
is LGPL rather than GPL tools, and actual FreeType uses the FTL choice.

`prepare_rc1_review.py` produces the finite per-file JSON/CSV table and local
proposed source set. Every source byte is checked against retained hashes. AMF
contains only unchanged include headers and root notices; unused bundled supplier
binaries are excluded. The recipient AMF lock overlay and per-header hashes
explain the layout change without altering the candidate baseline. Reopened TAR
members are verified. Existing cached sources are reused, not reacquired.

The proposed index binds **one exact source commit and all three binary hashes**.
Every asset remains `redistribution_approved:false`, and
`complete_corresponding_source:false` means **not human-approved**, not a silently
published offer. Future GitHub URLs are explicitly `PROPOSED_NOT_PUBLISHED`.
The actual source archives exist locally under `build/proposed-source-assets`;
only metadata is retained in Git. Publication rejects this unapproved set.

Post-build source approval uses the protected owner's mandatory exact index hash,
source commit and binary hashes. An optional configured pin is an additional
constraint. This avoids a self-referencing Git commit/index hash cycle while
preserving all existing approval, manual-test and per-asset hash checks.

## Common source candidate and verification

Final common native source: **3b19839d6a626dd0a339dc7997e79c7fe23f9935**.
Native qualification: [44931018788](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44931018788).
Linux retry: [44931526666](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44931526666), same exact commit. The original Linux job exited 139 (Python segmentation fault) during compatibility tests before packaging; its cause is not established. The isolated retry passed all 186 discovered tests (183 passes, three physical-GPU skips), AV1 reference pixels and frozen ONEDIR/AppImage smoke. No result from the failed attempt is counted as a pass. The native Ubuntu AppImage SHA-256 is `338622d40a3eff55d31df0c3f1e1d407da01656d439920fe38c3018efaddeee9`. Metadata is retained separately from any application binary.
No intermediate af99c29/aa196a4 or older packaged hash is substituted for this source.
Post-build review/reporting commits do not retroactively change the tested source.

Source CI [44931018572](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44931018572) passed on Ubuntu 22.04 and Windows 2025: 186 discovered, 183 passed plus three physical-GPU skips on each, Ruff, branding and complete history pattern scan. Final local controlled compatibility is **186/186**, zero skips/errors/failures, 74.612 seconds, including physical AMD RX 7700 XT VAAPI and AV1 reference pixels. Local source/history, branding and Ruff checks passed. Local GPU results do not imply physical NVENC/AMF/QSV cloud validation.

## Final native results and retained identities

Both successful native payloads were generated from the exact clean source
**3b19839d6a626dd0a339dc7997e79c7fe23f9935**, also recorded by their controlled
runtime manifests. Windows succeeded in run 44931018788; that workflow's overall
conclusion remains failure because of its separate failed first Linux job. Linux
succeeded in the isolated same-source retry 44931526666. Do not call the first
combined run wholly successful or substitute older audit bytes.

| Audit artifact (not uploaded / not RC1) | SHA-256 |
| --- | --- |
| CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage | `338622d40a3eff55d31df0c3f1e1d407da01656d439920fe38c3018efaddeee9` |
| CactuVideoConverter-Portable-0.1.0-beta.1.zip | `f73659308dfcfe272adecdedbfd3ff9076460703014a437e90fec2d22dc51eff` |
| CactuVideoConverter-Setup-0.1.0-beta.1.exe | `b2f46b79400c5a65fb93f6e6b290f67a0a003e8ff8604c05c93c5d1e02315e30` |

Each native controlled compatibility suite discovered **186 tests: 183 passed,
three physical-GPU skips, zero errors/failures**. AV1 software/reference pixels
passed. Linux frozen ONEDIR/AppImage smoke and Windows frozen ONEDIR/portable,
installer install-convert-uninstall smoke passed. These are automated tests,
not manual Windows 11/Linux acceptance.

The final actual inventories contain **398 native/prefix review rows**, with
378 engineering-evidence-prepared rows and 20 Microsoft-rights pending rows
(the ten Windows paths occur in portable and installed payloads). All actual
MSYS supplier notice hashes and applicable Qt/Python notice bytes verify against
the payloads. Forbidden optional Mesa/full-7z/compiler DLLs and libass/VPL fallback
are absent. The proposed offer has **95 indexed assets**, all source hashes
verified, zero missing engineering materials, no asset/overall approval. GCC
library sources are included for both actual Windows and Ubuntu library versions.

Metadata, CSV/JSON review, proposed source index, normalization/original-hash
receipts and post-build review-tool hash are in
`release/evidence/rc1-qualification-3b19839/`. Only metadata is committed. Source
archives remain local under `build/proposed-source-assets`; no binary is available
from these metadata-only jobs. Raw hosted logs remain local. The first Linux
exit-139 incident is preserved in the receipt, with cause unestablished and no
claim it was fixed; the complete same-source retry passed. If it recurs, collect
a Python native fault trace and isolate the active Qt test before promotion.

**No remaining missing-source/notice or failing-final-package engineering item
was found in this defined review.** Toolchain hermeticity, signing, production
performance, physical non-AMD hardware and manual desktop acceptance are not
claimed. Human review and distribution remain blocked as listed below.

## Pending owner/legal review and remaining work

| Affected artifacts | Condition / concrete missing evidence | Responsible | Resolution and verifiable completion |
| --- | --- | --- | --- |
| Ten actual VC runtime paths in both Windows payloads (14.44.35211.0 and 14.51.36247.0) | Applicable Microsoft Visual Studio/REDIST qualifying grant is unconfirmed | Owner / qualified legal reviewer | Written grant/strategy decision covering the exact mapped files. Owner answered “Não sei; manter como pendência jurídica”; recorded in `release/owner-runtime-decision.json`. |
| Exact three audit binaries plus proposed source/notice index | Final human review and approval of selected terms, source/replacement scope and exact hashes | Owner / license reviewer | Explicit approved records for these identities. No scan/test substitutes for this decision. |
| Future qualified RC1 artifact set | Windows 11 and Linux desktop acceptance, bound to exact available bytes | Owner / desktop testers | Record the manual checks below and hashes only after an eligible candidate is available. |

The Microsoft system-only VC14 x64 prerequisite alternative is documented in
`WINDOWS_RUNTIME_REDISTRIBUTION.md`, **not implemented or selected**. It would
change portable/offline/first-launch behavior and require clean-Windows tests;
hosted runners cannot prove the missing-prerequisite case. Do not silently fetch
runtimes or arbitrary DLLs. No repeated source scan can establish owner rights.

Final native tests and actual-notice/source verification passed as recorded above. Approval flags stay false even though the defined missing-materials engineering list is empty. Durable public recipient access is a later gated
publication action, not an assertion that proposed URLs already exist.

## Manual desktop acceptance required

**Not performed / not passed by this report.** Cloud offscreen smoke is automated
functional evidence. It does not qualify a human-tested RC1 or provide downloadable
binaries: these workflows retain metadata only. A later eligible, retained binary
set must be identified by exact SHA-256 before requesting desktop acceptance.

Windows 11 x86_64: install, launch, bundled FFmpeg lookup, software conversion,
Quick Preview, embedded/external subtitle burn, loudness, batch queue, pause/resume,
cancel, portable ZIP and uninstall. Linux x86_64: AppImage/FUSE desktop execution,
bundled FFmpeg, x264, AMD RX 7700 XT VAAPI, preview, subtitles/audio, queue,
cancellation and cleanup. Physical NVENC/AMF/QSV need the appropriate separate
hardware. A rebuilt artifact with different bytes requires its own acceptance.

## Next owner action

Resolve the **Microsoft redistribution strategy/rights** with qualified review;
the owner requested it remain pending. Review the finite component/source table
separately when ready. No publication confirmation is requested now, and RC1 is
not promoted while this human decision and final approval remain open.
