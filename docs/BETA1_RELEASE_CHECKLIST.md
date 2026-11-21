# Beta.1 authoritative release checklist

> Current status (2026-11-21): see [Controlled build closure](FFMPEG_CONTROLLED_CLOSURE.md). That report supersedes historical test counts, provider-only blockers and pending implementation claims below. All technical/license/publication approvals remain false. Earlier milestone records are retained for traceability.

## Current controlled-build checklist — 2026-11-21

| Check | Current state |
| --- | --- |
| Native source recipes / source locks / executable manifests | IMPLEMENTED; six Linux / seven Windows source inputs, transitive review separate |
| Required software/audio/subtitle/preview/queue behavior | Local complete suite with physical AMD VAAPI passes; native evidence scoped to exact candidates |
| Ubuntu controlled frozen ONEDIR/AppImage | PASS at 4e47bab, run 44902731258 |
| Windows controlled source/static-input PE proof | PASS at c56ebf6, run 44904194890: 177 discovered, 3 GPU skips, ONEDIR/portable/installer install-convert-uninstall; original 4e47 staging failure retained separately |
| Complete source CI after Windows staging correction | PASS at 78a4bc1, run 44904835443, Windows/Linux: 177 discovered, 3 GPU skips, Ruff/branding/history scans |
| Official MSYS source archive acquisition/signatures | 20 source-only archives retained; internal identities/member hashes checked, gpgv verifies against pinned official keys; not license approval |
| Ubuntu exact sources | 64 actual current packages; 65 unique retained historical/current package versions |
| AppImage controlled runtime / independent relink | Exact dcf5f5b0… hash reproduced; TMPDIR namespace regression fixed and actual rebuild checked |
| Source asset publishing support | IMPLEMENTED, disabled; exact approved index SHA required and currently null |
| Complete source/build/notice/rights/manual/delivery closure | BLOCKED; see current closure report for exact inputs/actions |
| RC1 / provider promotion / beta publication | BLOCKED; three global approvals false; no public beta tag, binaries or source bundles |

## Historical provider checklist

Historical checklist reviewed **2026-11-20**. Target v0.1.0-beta.1. Preparation/audit only.
**BLOCKED before RC1; not ready for owner publication approval.**

## Source and validation

| Check | State | Exact evidence / remaining action |
| --- | --- | --- |
| Repository and original-source license | PASS | drrrrigo/cactu-video-converter; owner chose GPL-3.0-or-later |
| Native audit source | PASS | Clean 7b7d23c9c77afac0933cc1607ab0160cbbc7ec3c; no claim that a later evidence/docs commit produced these artifacts |
| Source CI on packaged source | PASS | Run 44844968490, Windows/Linux: 166 discovered, 163 pass + 3 optional physical-GPU skips each |
| Final local source suite | PASS | 169 tests, 69.376 s, CPython 3.14.7, physical RX 7700 XT VAAPI enabled |
| Follow-up a99c208 source CI | PASS | Run 44851028673: 169 discovered, 166 pass + 3 optional hardware skips on each platform; all source checks pass |
| Hash-locked environment | PASS | release/requirements.lock, toolchain.json; Python 3.14.7 enforced before packaging |
| Frozen native software/preview/queue smoke | PASS | Audit 44845101385 builds Windows/Linux, installer install/convert/uninstall, portable/AppImage extraction, subtitles, Faststart, preview and two-job loudness queue |
| Distribution gate | PASS (gate behavior) | Same audit overall FAIL only at Verify distribution eligibility; binary upload skipped |
| Physical cloud GPU coverage | NOT AVAILABLE | Native CI has no physical NVENC/AMF/QSV hardware; tables/probes are not hardware validation |
| Final desktop/manual evidence | PENDING MANUAL | Windows 11 installer/portable, Linux RX 7700 XT, second Linux environment/display stack and exact hashes |

## Dependency resolution

| Check | State | Exact evidence / remaining action |
| --- | --- | --- |
| Actual installed/portable/AppImage inventories | PASS | release/evidence/beta1-resolution-7b7d23c; receipt hashes original report bytes |
| Unknown native copying origins | PASS | Windows 47→0 each, Ubuntu 101→0; upstream source/license closure is separate |
| Unused Qt/Windows runtime surface | PASS | 58 Windows native paths removed, 18 Ubuntu native paths removed; narrow hooks, Schannel and OS contracts validated |
| Required libmvec | PASS (necessity/source retention) | FFmpeg and FFprobe ELF dependencies; glibc 2.35 source/patches/notices retained |
| Qt module sources and notice acquisition | PASS | Four immutable 6.11.2 archives, 196 legal/attribution files, actual file/module mapping |
| Qt wheel third-party/build correspondence | BLOCKED | ICU 73 and other exact incorporated dependencies/configuration/terms still need review |
| Ubuntu exact source packages | PASS (acquisition) | All 64 source packages retained; parts match .dsc SHA-256/size, PGP signatures not separately verified |
| Ubuntu individual conditions/replacement/delivery | BLOCKED | Per-file obligation reports and licenses/NATIVE_LIBRARY_REPLACEMENT.md; final assessment/delivery remains |
| Windows Python/native dependency closure | BLOCKED | Supplier/version known; exact SSL/compression sources/build/notices remain |
| Microsoft runtime redistribution conditions | BLOCKED | Exact 14.44/14.51 files/suppliers known, no prerelease PE flags; exact grant/REDIST and owner rights review required |
| FFmpeg core/recipe/capabilities | PASS | n9.0.2-61-gd59078794d-20261120; actual GPL/version3, no nonfree, mandatory tables retained per platform |
| FFmpeg matching complete source graph | BLOCKED | 132/133 top-level inputs retained; Xvid r2204 auth failure plus generated/vendor/toolchain/build/notice correspondence incomplete |
| FFmpeg toolchain image identities | PASS (observation) | ffmpeg-provider-build-evidence.json records digests actually used; no controlled FFmpeg replacement completed |
| AppImage controlled runtime/relink engineering | PASS | Offline repeated build and relink reproduce dcf5f5b0…; runtime-source-delivery.json verifies local 131-file component TAR |
| AppImage final terms/source delivery | BLOCKED | Static components need final review and maintained recipient assets; local TAR is not a complete source offer |
| Inno additional term acquisition | PASS | Exact SBOM/Pascal Script/LZMA notices and acknowledgement retained |
| Inno actual generated component scope | BLOCKED | Map Setup/uninstaller incorporated objects to required terms |
| PyInstaller/psutil source roles and notices | PASS (technical evidence) | Actual embedded modules/native files distinguish runtime from build-only dependencies |
| Complete notice payload | BLOCKED | Declared notices exist; full individual incorporated-component scope remains under review |
| Maintained recipient source/binary retention | BLOCKED | No approved immutable public source assets; publisher source-asset integration required |

## Current exact audit outputs — not RC1

Run [44845101385](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44845101385)
uses 7b7d23c. Build/smoke passed, overall distribution check intentionally failed.
Only JSON/checksum metadata was uploaded. Hosted application binaries were not
retained as an owner-test RC set. These hashes identify audit outputs only.

| Output | SHA-256 |
| --- | --- |
| Ubuntu AppImage | 1d92f9a3759fd652738f88d260cb41b7ad5addeddbc2acfebde058109dfe88a1 |
| Windows Portable | bebd60df9ed69517287a380a5d81e12c2c2438f113895e3c7c2b4f364c8eee17 |
| Windows Setup | 715d8b6e2c8c423d2474a67b6572b39aff1bde1b7b9bf565dfbe7f177c93fb36 |

Installed/portable/AppImage: 449/447/705 total files, 65/64/226 native files.
Legal material increases total files while native code decreases. Eight/seven/88
component groups require review; these are not unidentified-file counts.
Historical eabc092 outputs remain unchanged under release/evidence/beta1-audit-eabc092.
Earlier local audit images are separate from hosted 7b7d23c bytes. The 3.14.8
local image remains explicitly superseded; canonical release Python is 3.14.7.

## Final gates

| Gate | State |
| --- | --- |
| technical_license_audit_complete | false — exact remaining matrix in BETA1_BLOCKER_RESOLUTION.md |
| license_audit_approved | false — no human redistribution approval |
| publication_approved | false — no publication authorization |
| Final clean RC1 and final three-artifact manual hash attestation | BLOCKED / PENDING MANUAL |
| Beta tag/release/public binary or source-bundle upload | NOT PERFORMED |
| Source/history bounded signature scan | Run locally and in source CI; findings must be empty, not a security certification |
| Windows/AppImage signing | Optional, current audit artifacts unsigned |

Do not ask the owner to approve missing technical evidence. Resolve the remaining
source/build/notice/delivery/grant records, build an exact RC set, then obtain manual
results and separate human license/publication approvals. No blanket source offer
or legal clearance is asserted. See BETA1_BLOCKER_RESOLUTION.md for remediation.


Local testing output: clean a99c208 CachyOS AppImage, Python 3.14.7, SHA-256
188166a15179b3a7295c2427a1cabce7f09b99eb8a5ff89027375a7f5257984f.
Frozen ONEDIR/AppImage preview and two-job/loudness tests pass. This audit-only local
image is separate from hosted 7b7d23c and has 91 unmapped host Arch library copying
origins. It is not the release baseline or RC1; manual desktop acceptance remains
pending. Receipt: release/evidence/beta1-local-a99c208/receipt.json. Subsequent
metadata/docs-only commits run the source workflow independently.


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
