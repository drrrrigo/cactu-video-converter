# Beta.1 authoritative release checklist

Reviewed **2026-11-20**. Target v0.1.0-beta.1. Preparation/audit only.
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
