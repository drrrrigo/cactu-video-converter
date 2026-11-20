# Beta.1 authoritative release checklist

Reviewed: **2026-11-20**. Target: **v0.1.0-beta.1**. Preparation only: no public tag,
release or binary upload is authorized. States: **PASS**, **FAIL**, **BLOCKED**,
**PENDING MANUAL**, **NOT APPLICABLE**. PASS requires linked or retained evidence.

## Current decision

**BLOCKED — not RC READY and not ready for publication.** Source baseline is
`da4d64db0567c94d0b11acfdb4e1de83022154b6`. This is not a final RC commit.
The public repository and supplied workspace matched at inspection. No beta tag
or GitHub release existed. Previous CI is historical evidence, not a replacement
for checks on the preparation commit.

**Canonical release Python: 3.14.7.** Keep the existing CI/toolchain pin. The old
local 3.14.8 candidate is superseded for release purposes. Packaging must reject
any other Python patch before building, rather than merely record a mismatch.
The developer's installed 3.14.10 is not a release runtime.

## Repository and source

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Correct public repository | PASS | GitHub API: drrrrigo/cactu-video-converter, public, main |
| Clean inspected baseline | PASS | Separate clone at baseline SHA; workspace bytes matched |
| Cactu GPL-3.0-or-later | PASS | Owner decision; LICENSE and pyproject.toml |
| Current source/history secrets scan | BLOCKED | Re-run after preparation changes |
| No private files/document labels | BLOCKED | Re-scan final tracked files and generated evidence |
| Release freeze | PASS | Only dependency, packaging, audit, workflow and documentation changes allowed |
| Public beta tag absent | PASS | Remote exact-tag lookup returned no ref on 2026-11-20 |
| Public beta release absent | PASS | Repository releases API returned [] on 2026-11-20 |

## CI and dependency definition

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Windows and Linux historical source CI | PASS | [41351535190](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41351535190), baseline SHA, 148 tests/platform |
| Current preparation HEAD CI | BLOCKED | Must run after changes; baseline evidence alone is insufficient |
| Historical packaged smoke | PASS | [41350221053](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221053); build/smoke passed, distribution gate correctly failed |
| Exact Python/build/runtime versions | PASS | release/requirements.txt and release/toolchain.json |
| Wheel/archive hash lock | FAIL | Python dependencies previously had version pins without wheel hash enforcement |
| Dependency source/role provenance | BLOCKED | Distinguish shipped modules, bootloader, build-only packages and OS libraries |
| Exact current Python runtime | FAIL | Existing local candidate reports 3.14.8, pin is 3.14.7 |
| Wrong-Python build rejection | FAIL | Existing build script only records python_pin_matches=false |

## FFmpeg

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Exact Windows/Linux archive/member hashes | PASS | vendor/ffmpeg/manifest.json; old archives retained in local ignored cache |
| Pinned daily release availability | FAIL | Exact Nov 1 release API now returns HTTP 404; daily retention expired |
| Exact configuration / GPL / no nonfree | PASS | Retained binary hashes and earlier native evidence; repeat for selected audit input |
| Software/subtitle/audio/hardware capability tables | PASS | Earlier native checks; repeat after any dependency pin change |
| Immutable recipe revision | PASS | Manifest records recipe commit; recipe alone is not source closure |
| FFmpeg revision and patches retained | BLOCKED | Obtain exact source and applicable patches, not merely an upstream homepage |
| All linked dependency corresponding sources | BLOCKED | Per-component source/license inventory and retained source set incomplete |
| Recipient source retrieval instructions | BLOCKED | Require maintained exact source locations/hashes before approval |
| Nonfree provider exclusion | PASS | Nonfree configuration rejected; excluded provider remains excluded |

## Qt, Python, native libraries and packaging runtimes

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| PySide/Essentials/Addons/Shiboken versions | PASS | 6.11.2 pins; inventory actual payload subset |
| PySide license text provenance | PASS | licenses/qt-pyside-6.11.2/provenance.json, immutable source commit and hashes |
| Qt module license option / notices / sources | BLOCKED | Record actual bundled modules and their individual third-party notices |
| LGPL replacement/relinking/install information | BLOCKED | Review dynamic Qt/native libraries and statically linked AppImage runtime dependencies separately |
| Python exact PSF license text | PASS | licenses/Python-3.14.7.txt; only valid for a 3.14.7 runtime |
| Python runtime third-party/native closure | BLOCKED | Inspect final packaged runtime and dependent DLL/ELF files |
| Runtime Python packages / build-only distinction | BLOCKED | Existing environment inventory incorrectly mixes tooling with runtime payload |
| PyInstaller bootloader/exception | BLOCKED | Retain exact terms and identify embedded bootloader/runtime hooks |
| AppImage tool vs embedded runtime | BLOCKED | Exact runtime MIT license also identifies statically linked third-party code; audit that code too |
| Inno compiler vs installed stub/uninstaller | BLOCKED | Retain exact license and additional component terms; inspect produced payload |
| Actual Windows DLL / Linux ELF origins | BLOCKED | Per-file inventories must come from produced artifacts, with unresolved origins explicit |
| Host drivers not bundled/installed | BLOCKED | Verify actual payload, not only packaging intent |

## Final candidate and release metadata

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Version metadata | PASS | 0.1.0-beta.1 / package 0.1.0b1 / numeric Windows 0.1.0.1 |
| Final clean RC1 source commit | BLOCKED | No RC1 declared until technical audit gates are satisfied |
| Final RC1 Windows installer | BLOCKED | Historical build exists; no retained, approved final candidate |
| Final RC1 Windows portable ZIP | BLOCKED | Historical build exists; no retained, approved final candidate |
| Final RC1 Linux AppImage | BLOCKED | Old local 3.14.8 image is not the release candidate |
| Inventories: installed / portable / AppImage | BLOCKED | Generate from each actual extracted/installed artifact |
| Generated RC SHA256SUMS | BLOCKED | All three exact final artifacts are required; no invented hashes |
| Notices and license payload verified | BLOCKED | Must match the actual final inventories |
| Release notes / known issues / security policy | PASS | Existing drafts/policies; reconcile final state before approval |
| README download state | PASS | No approved binary download is advertised as available |
| Windows signing | NOT APPLICABLE | Optional for beta.1; current infrastructure/candidates are unsigned |
| Additional AppImage signing | NOT APPLICABLE | Optional; SHA-256 remains mandatory |
| Fail-closed publication workflow | PASS | Existing license/source/manual gates and protected environment; revalidate after edits |

## Manual verification

| Check | State | Evidence / remaining action |
| --- | --- | --- |
| Clean Windows 11 installer/portable desktop | PENDING MANUAL | docs/MANUAL_TEST_WINDOWS_BETA1.md; exact RC hashes required |
| CachyOS / RX 7700 XT packaged desktop | PENDING MANUAL | docs/MANUAL_TEST_LINUX_BETA1.md; source/GPU tests are insufficient |
| Second Linux environment | PENDING MANUAL | Prefer Ubuntu LTS; explicitly record unavailable environment if necessary |
| Wayland / X11 attribution | PENDING MANUAL | Record the actual tested display stack; do not claim both by inference |
| Final manual result/hash attestation | PENDING MANUAL | Tester, date, OS/build, SHA-256 and scenario results required |

## Final release approval

- [ ] Third-party redistribution approved by human review.
- [ ] Windows manual installer and portable tests passed.
- [ ] Linux manual tests passed; portability limits recorded.
- [ ] Exact RC artifacts, source commit, inventories and checksums approved.
- [ ] Owner explicitly authorized publication in a separate instruction.

**PUBLICATION IS BLOCKED WHILE ANY BOX ABOVE IS UNCHECKED.** Preparation must never
check owner approval, create v0.1.0-beta.1, or create/upload a public binary release.

## Evidence locations and promotion

Technical audit: [RELEASE_LICENSE_AUDIT.md](RELEASE_LICENSE_AUDIT.md).
Implementation/results: [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md).
Promotion procedure: [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
Machine gates: release/config.json and vendor/ffmpeg/manifest.json. The checklist
does not override them. Manual evidence belongs outside the tested source commit
so recording results cannot silently change the source identity of an approved RC.
