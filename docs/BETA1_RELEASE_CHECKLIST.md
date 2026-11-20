# Beta.1 authoritative release checklist

Reviewed: **2026-11-20**. Target: **v0.1.0-beta.1**. Preparation only: no public tag,
release or binary upload is authorized. States: **PASS**, **FAIL**, **BLOCKED**,
**PENDING MANUAL**, **NOT APPLICABLE**. PASS requires linked or retained evidence.

## Current decision

**BLOCKED — not RC READY and not ready for owner publication approval.**
Audited application/build-tooling source is
`eabc0920b4d091cba3b6670b263182babca7e539`, an audit commit, not RC1.
The following documentation/evidence receipt commit triggers the same full source
CI; its identity is its containing Git commit. No circular self-hash is invented.
Per the request, stop before RC1 while exact source/license closure is incomplete.
No public beta tag, release or binary upload was made.

**Canonical release Python: 3.14.7.** Keep the existing CI/toolchain pin. The old
local 3.14.8 candidate is preserved under ignored
`dist/superseded-python3.14.8-2026-11-01/` and superseded. Both native packages and
the rebuilt local audit image report 3.14.7 inside the frozen application. Packaging
rejects other patches before building.
The developer's installed 3.14.10 is not a release runtime.

## Repository and source

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Correct public repository | PASS | GitHub API: drrrrigo/cactu-video-converter, public, main |
| Clean inspected baseline | PASS | Clean committed eabc092 in all build receipts; workspace source synchronized with publishing clone |
| Cactu GPL-3.0-or-later | PASS | Owner decision; LICENSE and pyproject.toml |
| Current source/history secrets scan | PASS | audit_source.py --history: zero findings locally and in both native CI jobs; signature scanning does not prove universal absence |
| No private files/document labels | PASS | Retained reports contain package-relative paths, public source URLs, versions and hashes; no executable payload/media/credentials |
| Release freeze | PASS | Release tooling/dependencies/audit/docs only; application change exposes actual Python version in automated smoke evidence |
| Public beta tag absent | PASS | Remote exact-tag lookup returned no ref on 2026-11-20 |
| Public beta release absent | PASS | Repository releases API returned [] on 2026-11-20 |

## CI and dependency definition

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Windows and Linux historical source CI | PASS | [41351535190](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41351535190), baseline SHA, 148 tests/platform |
| Current preparation HEAD CI | PASS | [44810167677](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44810167677), eabc092: 157 discovered, 154 pass + 3 optional hardware skips per platform; receipt follow-up also triggers full CI |
| Historical packaged smoke | PASS | [41350221053](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221053); build/smoke passed, distribution gate correctly failed |
| Exact Python/build/runtime versions | PASS | release/requirements.txt and release/toolchain.json |
| Wheel/archive hash lock | PASS | 21 exact releases in requirements.lock; --require-hashes --only-binary install passed on Windows/Linux |
| Dependency source/role provenance | PASS | dependency-provenance.json, component-sources.json, source-evidence.json and actual payload inventories; provenance recording is distinct from complete source delivery |
| Exact current Python runtime | PASS | All native onedir/portable/AppImage and rebuilt local smoke reports show standard CPython 3.14.7 |
| Wrong-Python build rejection | PASS | Regression tests reject 3.14.8 and dirty/uncommitted trees before packaging |

## FFmpeg

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Exact Windows/Linux archive/member hashes | PASS | vendor/ffmpeg/manifest.json; current audit build n9.0.2-61-gd59078794d-20261120 verified in both native jobs |
| Pinned daily release availability | BLOCKED | Nov 20 inputs fetched successfully; old Nov 1 daily expired. No durable approved Cactu input/source mirror exists |
| Exact configuration / GPL / no nonfree | PASS | Separate current native runtime-evidence JSON retains actual -version/-buildconf/-L, GPL v3, libx264/libass, no --enable-nonfree |
| Software/subtitle/audio/hardware capability tables | PASS | Current mandatory tables validated natively; table exposure does not establish physical NVENC/AMF/QSV coverage |
| Immutable recipe revision | PASS | Manifest records recipe commit; recipe alone is not source closure |
| FFmpeg revision and patches retained | PASS | Exact FFmpeg core and recipe archives/hashes retained; per-linked-library patch/source closure remains blocked below |
| All linked dependency corresponding sources | BLOCKED | Per-component source/license inventory and retained source set incomplete |
| Recipient source retrieval instructions | BLOCKED | Require maintained exact source locations/hashes before approval |
| Nonfree provider exclusion | PASS | Nonfree configuration rejected; excluded provider remains excluded |

## Qt, Python, native libraries and packaging runtimes

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| PySide/Essentials/Addons/Shiboken versions | PASS | 6.11.2 pins; inventory actual payload subset |
| PySide license text provenance | PASS | licenses/qt-pyside-6.11.2/provenance.json, immutable source commit and hashes |
| Qt module license option / notices / sources | BLOCKED | Actual inventories include Core/Gui/Network/Widgets plus collected Pdf/Qml/Quick/VirtualKeyboard/plugins; exact module/source/third-party review incomplete |
| LGPL replacement/relinking/install information | BLOCKED | Review dynamic Qt/native libraries and statically linked AppImage runtime dependencies separately |
| Python exact PSF license text | PASS | licenses/Python-3.14.7.txt; only valid for a 3.14.7 runtime |
| Python runtime third-party/native closure | BLOCKED | Inspect final packaged runtime and dependent DLL/ELF files |
| Runtime Python packages / build-only distinction | PASS | Actual PYZ/CArchive/bootstrap/base-library tables used; environment notice inventory explicitly labeled build-context evidence |
| PyInstaller bootloader/exception | PASS | Exact 6.16.0 COPYING/exception packaged; actual bootstrap/runtime hooks inventoried; compiler is build-only |
| AppImage tool vs embedded runtime | BLOCKED | appimagetool 1.9.1 vs runtime fedfad51 identified separately, outer ELF prefix hashed; complete static dependency terms/source/relinking material incomplete |
| Inno compiler vs installed stub/uninstaller | BLOCKED | 7.1.1 source/root license retained; generated Setup prefix and installed uninstaller inventoried; additional component terms incomplete |
| Actual Windows DLL / Linux ELF origins | BLOCKED | 47 unresolved-origin files in each Windows payload, 101 in native Ubuntu AppImage; additional known origins still require terms/source/notices review |
| Host drivers not bundled/installed | PASS | All actual inventories report no known driver-file pattern matches; this does not approve unreviewed native libraries |

## Final candidate and release metadata

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Version metadata | PASS | 0.1.0-beta.1 / package 0.1.0b1 / numeric Windows 0.1.0.1 |
| Final clean RC1 source commit | BLOCKED | No RC1 declared until technical audit gates are satisfied |
| Final RC1 Windows installer | BLOCKED | Current native audit build/install/convert/uninstall passed; binary upload blocked, no retained approved RC1 |
| Final RC1 Windows portable ZIP | BLOCKED | Current native audit build/extract/convert passed; binary upload blocked, no retained approved RC1 |
| Final RC1 Linux AppImage | BLOCKED | Current native/local Python 3.14.7 audit images pass smoke; no final technically approved RC1 |
| Inventories: installed / portable / AppImage | PASS | Actual separate reports retained in release/evidence/beta1-audit-eabc092; audit-only, not final RC |
| Generated RC SHA256SUMS | BLOCKED | All three exact final artifacts are required; no invented hashes |
| Notices and license payload verified | BLOCKED | Must match the actual final inventories |
| Release notes / known issues / security policy | PASS | Existing drafts/policies; reconcile final state before approval |
| README download state | PASS | No approved binary download is advertised as available |
| Windows signing | NOT APPLICABLE | Optional for beta.1; current infrastructure/candidates are unsigned |
| Additional AppImage signing | NOT APPLICABLE | Optional; SHA-256 remains mandatory |
| Fail-closed publication workflow | PASS | Current native jobs stopped at distribution eligibility; protected owner environment and exact source/hash external attestation required |

## Manual verification

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Clean Windows 11 installer/portable desktop | PENDING MANUAL | docs/MANUAL_TEST_WINDOWS_BETA1.md; exact RC hashes required |
| CachyOS / RX 7700 XT packaged desktop | PENDING MANUAL | docs/MANUAL_TEST_LINUX_BETA1.md; source/GPU tests are insufficient |
| Second Linux environment | PENDING MANUAL | Prefer Ubuntu LTS; explicitly record unavailable environment if necessary |
| Wayland / X11 attribution | PENDING MANUAL | Record the actual tested display stack; do not claim both by inference |
| Final manual result/hash attestation | PENDING MANUAL | Tester, date, OS/build, SHA-256 and scenario results required |

## Current audit outputs — not RC1

Current native packaging run:
[44810167815](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44810167815).
Both build and smoke steps passed; the overall run failed at the intended technical
redistribution gate. Do not describe that workflow as a green release. All native
rows below use clean source `eabc0920b4d091cba3b6670b263182babca7e539`.
Only JSON/checksum text was uploaded. Windows runner binaries were not retained as
an owner-test RC set. The local image has a different native library set and is a
separate audit. Exact build-generated hashes are retained in the reports.

| Audit output | SHA-256 |
| --- | --- |
| Native Windows Setup | `6d34b7b6ea5351659f6e7487875fe034dc8de7a834958316d40bc3a591875c85` |
| Native Windows Portable | `ef3d970a2fd9fb72931650aa743476ba9146be0c5fc0900029eb0350e2327f82` |
| Native Ubuntu AppImage | `1b29aa4f44b8012e44cd787e176ca88ba5855785f8c807f530eb792babe54e86` |
| Local CachyOS AppImage, ignored dist/candidate | `a4ab0be5670ea2df3ae8bd482eeaeef4965bc50f49a5639677d6f0c6f91d53dd` |

| Actual native payload | Files | Native files | Embedded Python modules | Component groups requiring review |
| --- | ---: | ---: | ---: | ---: |
| Installed Windows + outer Setup prefix | 272 | 123 | 380 | 7 |
| Extracted Windows portable | 270 | 122 | 380 | 6 |
| Extracted Ubuntu AppImage + outer ELF prefix | 392 | 244 | 382 | 20 |

Group counts are not counts of unresolved files. Outer container prefixes are
inventoried separately from extracted-file counts. Full per-file hashes/origins,
actual Qt file lists, runtime evidence and report checksums are retained in
[the metadata-only audit receipt](../release/evidence/beta1-audit-eabc092/receipt.json).

Local eabc092 tests with pinned Python/FFmpeg and physical RX 7700 XT:
**157/157 PASS, zero skips, 61.796 seconds**. CI discovers 157 and skips three
optional physical hardware tests. These checks do not establish manual desktop
acceptance. Exact source/hash inputs and SOURCE_DATE_EPOCH improve repeatability;
bit-identical reproduction across changing hosted images/native libraries remains
**BLOCKED / unproven**.

The Ubuntu payload includes `usr/bin/_internal/libmvec.so.1` from glibc
2.35-0ubuntu3.18 even though libc/loader are host dependencies. Its necessity,
notices and corresponding source need explicit review. Existing packaged license
texts pass presence checks; complete third-party notice coverage remains BLOCKED.

## Final release approval

- [ ] Third-party redistribution approved by human review.
- [ ] Windows manual installer and portable tests passed.
- [ ] Linux manual tests passed; portability limits recorded.
- [ ] Exact RC artifacts, source commit, inventories and checksums approved.
- [ ] Owner explicitly authorized publication in a separate instruction.

**PUBLICATION IS BLOCKED WHILE ANY BOX ABOVE IS UNCHECKED.** Preparation must never
check owner approval, create v0.1.0-beta.1, or create/upload a public binary release.
Complete the exact dependency/source evidence first, then build RC1 and run both
manual guides against its exact hashes before requesting publication approval.

## Evidence locations and promotion

Technical audit: [RELEASE_LICENSE_AUDIT.md](RELEASE_LICENSE_AUDIT.md).
Implementation/results: [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md).
Promotion procedure: [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
Machine gates: release/config.json and vendor/ffmpeg/manifest.json. The checklist
does not override them. Manual evidence belongs outside the tested source commit
so recording results cannot silently change the source identity of an approved RC.
