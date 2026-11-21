# Controlled FFmpeg and redistribution closure — 2026-11-21

**Material engineering progress; RC1 remains blocked.** This is the current
summary. Historical reports under release/evidence remain immutable. No beta tag,
GitHub release, public application binary artifact or source bundle was published.
The three global technical/license/publication approval fields remain false.
The selected vendor runtime remains unchanged; candidates are isolated.

## Resolved

* Native source build recipes now produce Windows and Linux FFmpeg/FFprobe.
  Six Linux source inputs and seven Windows inputs are revision/hash locked:
  FFmpeg, x264, libass, dav1d, NV codec headers, oneVPL, plus Windows AMF headers.
  Generated FFmpeg VERSION avoids accidentally inheriting Cactu's enclosing Git
  version. Source-built static oneVPL has explicit C++ runtime linkage.
* Real AV1 decoding is protected by a generated AV1 fixture and decoded pixel
  comparison. Native FFmpeg `av1` alone was hardware-only; source-built dav1d is
  now required. Earlier candidates without it are superseded.
* The Windows PE audit caught a second regression: MSYS2 libass/VPL DLLs were
  selected despite source-built archives existing. The corrected recipe links
  uniquely named static archives identified by hash, verifies local pkg-config
  selection and rejects replacement libass/VPL/x264/dav1d DLL imports. Absolute
  archive arguments were rejected after an actual FFmpeg configure link-order
  failure; exact `-l:` archive names preserve its linker ordering.
* Exact build-tool command-entry/version profiles now fail closed on drift. Profiles
  cover compiler/build tools, **not the entire sysroot or transitive toolchain**.
  Native package acquisition remains a bootstrap, not a replay-locked environment.
  Raw source-lock hashes differ with Windows CRLF checkout; evidence joins accept
  only LF/CRLF representations of the locked JSON and require exact source-input
  identities plus both executable hashes, preventing cross-candidate attribution.
* The AppImage offline build now sets TMPDIR inside its own namespace. A real
  rebuild after this fix reproduces runtime SHA-256
  `dcf5f5b07d5679e37c5a2decff55a65fc2962c565fdaacbf88eaf2bd4ad61ac4`.
  Earlier object/link-map/relink material remains retained and unchanged.
* Publication tooling accepts corresponding-source assets only through a complete,
  explicitly approved SHA-256-bound SOURCE-ASSETS index, in addition to existing
  owner/manual/license gates. The approval index is unset and publication disabled.

## Reduced

The controlled graph excludes external Xvid, x265, libvpx, libaom and other unused
provider encoders without removing required native MPEG4/HEVC/VP8/VP9 decoding.
AV1 uses dav1d. Xvid SVN r2204 is no longer an input to these candidates; it remains
a historical blocker for reconstructing the still-selected legacy provider.
The six/seven source counts do not include transitive native/toolchain inputs.

Local CachyOS development comparison, not an official release size promise:

| File | Selected provider / preceding audit | Controlled local candidate |
| --- | ---: | ---: |
| FFmpeg | 175,830,000 bytes | 33,648,544 bytes |
| FFprobe | 175,600,560 bytes | 33,427,200 bytes |
| AppImage | 220,223,888 bytes | 119,495,056 bytes |

The AppImages contain different source/legal metadata. No same-input two-build FFmpeg reproduction experiment has completed. Observed
candidates differ by platform, compiler/native dependencies, build prefix and,
for superseded attempts, recipe revision. Their differing hashes do not by
themselves prove or disprove deterministic reproduction. Only the AppImage
runtime has a tested identical-output claim. Production performance is not
qualified; assembly is disabled.

## Controlled FFmpeg validation and exact identity

Recipe: **4e47bab1db633b02cb8b5be95e077921ed6ba4a9**. Native audit run:
[44902731258](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44902731258).
Linux passed 172 tests (three physical-GPU skips), AV1 reference decoding and
frozen ONEDIR/AppImage smoke. Windows built successfully, passed the PE static-
input guard and converted software media, then failed at reference-provider
staging (WinError 5). This is not a Windows frozen-test pass. A bounded Windows
access/sharing-error retry was added without weakening hash/config validation;
permanent or unrelated errors still fail. The native Windows retry is
[44904194890](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44904194890)
at c56ebf68242cae0c312b4abd2529ed737cefd512 **completed successfully**:
177 tests, zero errors/failures, three physical-GPU skips; AV1 CPU decoding and
reference pixels pass. Frozen ONEDIR/portable tests and installer
install-convert-uninstall pass. The PE import guard confirms no MSYS libass/VPL
replacement DLLs. Both native tool profiles match their pinned command hashes.
Windows isolated snapshot: 6658937eb0a8ba19d691d8dee6917835ba92882b; upstream c56ebf6.

| Native Windows artifact (audit only; binary not uploaded) | SHA-256 |
| --- | --- |
| Portable ZIP | 36d9127696ae12ab34e46d2bb689eb7b761bed9b3337bd4e617e51b61a1adae4 |
| Setup EXE | f7d3994e9e5d343ad4f13f707b55b3e218b31a1e2c534489206a9d4ea891744a |
| FFmpeg EXE | ea099baa4d2f594bee1e36ee5b1975df55543b65ba9ac9f4b646e491a3c0a29c |
| FFprobe EXE | bca125f1fe873216cdea679b4e208da6edf72e64560f614e46acb632877db4c9 |

Evidence: release/evidence/controlled-ffmpeg-c56/. Portable has 500 files (85
native), installed 502 (86 native). All 21 retained MSYS DLLs join by SHA-256 to
19 installed packages / 18 source packages already present in the retained
20-source historical set. libass-9.dll and libvpl-2.dll are absent. The remaining
non-distribution paths in the join are generated Cactu/FFmpeg executables and the
Inno uninstaller, not unrecognized supplier DLLs; their build/installer review
is separate. This byte join does not rewrite the original inventories or close
native notice/source/license review.

Final code/tools source **78a4bc1677a7f5067847b393d85e2798c670a629** passed full
Windows/Linux source CI [44904835443](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44904835443):
177 discovered, 174 passed plus three physical-GPU skips per platform, Ruff,
branding and source/history pattern scans pass. Final local source/tools suite
is 177/177 with physical AMD VAAPI. Subsequent report/evidence-only commits must
not be substituted for the native packaged parent commits above.


Local corrected candidate: **177 tests passed, zero failures/errors/skips,
71.002 seconds**, Python 3.14.7, physical RX 7700 XT VAAPI tests enabled.
Coverage includes software x264/AAC/yuv420p/Faststart, subtitle burn, manual
volume/limiter, two-pass loudness, preview, queue controls/cancellation/cleanup,
runtime lookup, output verification and hardware discovery/commands. AV1 software
decode and reference pixel equality pass. Cloud GPU backends require separate
physical tests; interface presence does not validate NVENC/AMF/QSV devices.

Local frozen ONEDIR and AppImage smoke pass: software conversion, embedded
subtitles, Quick Preview, two sequential jobs with loudness, output verification
and unchanged input. Source export parent:
**e3bfa2c1404172278ee9eaefca19646a6d111f25**; isolated snapshot identity is recorded
in the retained build receipt, not substituted for the upstream parent.

Native Ubuntu AppImage SHA-256:
`4b88d70b6f2fe0f70ec68264046e9b9e78a4c859388b88b2920235363859e723`.
Its isolated snapshot commit is afa6e92d3b4385ed1921ebe458533875487cabb5;
upstream parent is 4e47bab. Metadata and exact file/source-obligation joins are
retained under release/evidence/controlled-ffmpeg-4e47/.

Local AppImage SHA-256:
`0dd4c2a26d03cdaf27e262e81860b0bfbf7e197ff0a86194fedeec1100475b8e`.
Receipt: release/evidence/controlled-ffmpeg-local-static/. Artifact is available
locally under dist/controlled-experiment, **CachyOS development/audit only**, not
the Ubuntu official baseline or a redistribution-approved RC. Older candidates
and the provider-based dist/candidate remain preserved separately.

Historical run 44899586355 at 7f9a9cc passed 170 tests (three cloud GPU skips) and
native frozen/installer smoke on both systems. Its Windows functional success
does **not** establish source selection for libass/VPL: PE audit discovered the
MSYS DLL fallback. Its metadata is retained with that qualification under
release/evidence/controlled-ffmpeg-7f9/. Original hashes and any generic hosted
workspace normalization are recorded; raw metadata remains local.

## Source, notices and executable correspondence

The build-generated manifest binds executable hashes to actual -version,
-buildconf, -L, enabled components, source/archive hashes, recipe hash, generated
VERSION, local static archive/pkg-config hashes, PE imports and tool fingerprints.
No nonfree build is permitted. Required hardware interfaces remain NVENC/AMF/QSV
on Windows and NVENC/VAAPI/QSV on Linux. Drivers are external.

* verify_source_delivery.py --controlled verifies 26 retained controlled/Qt/runtime/
  Python/ICU source records, 65 unique historical/current Ubuntu source packages,
  and the MSYS2 source archives/signatures. Source-closure remains false.
* The current 4e47 Ubuntu payload maps to 64 exact source packages. Shared caches reuse
  the historical 64 plus the older libva 2.14 input (65 unique versions in total).
  The controlled lock references the actual artifact; original Ubuntu lock stays
  unchanged. Its actual dependencies no longer require libmvec; the historical
  provider did. Neither condition is generalized to every FFmpeg build.
* SHA-only joins attribute all 23 previously unknown Windows native DLLs in the
  superseded 7f9 candidate to 21 installed MSYS packages. Only notices belonging
  to matched packages are retained; the installed inventory's 88 DLLs/57 packages
  are not all declared shipped. These identities reduce to 20 source packages
  because libgcc/libstdc++ share GCC source. Official exact-version source-only
  archives, recipes, patches, upstream source archives and detached signatures
  are cached. Internal .SRCINFO identity and member hashes were verified without
  executing supplier recipes. All 20 detached signatures were subsequently verified with gpgv against the
  official msys2-keyring 1~20260814-1 package, SHA-256 fixed to the publisher
  index; signers are restricted to fingerprints published by MSYS2 and checked
  against its revoked list. A corrupted-signature negative check failed as
  expected. Evidence: release/evidence/msys-source-signature-verification.json.
  Trust originates in official HTTPS-published keys/hashes, not an independently
  supplied offline root. Package identity/signature validity is not a completed
  legal or build-correspondence review. These joined MSYS notices are audit
  evidence; they are not automatically integrated into the current package
  payload. Review the actual required notices, integrate them and re-inventory
  before any candidate promotion.
* Exact Qt ICU 73.2 source/notice identity and the Windows CPython OpenSSL source
  identity are retained. Both audited Python OpenSSL DLL hashes match the official
  CPython binary-deps 3.5.7 archive. Six Python files have explicit source/supplier/
  notice mapping. Static compression-extension and exact wheel build evidence
  remain open. See qt-icu-source-lock, python-native-source-lock and
  native-file-source-mapping JSON records.
* The local FFmpeg component source-review TAR includes the Linux source inputs,
  recipe/helper/profile/build-tool locks, native workflow prerequisites, generated
  VERSION and explicit limitations. It excludes Windows AMF and is intentionally
  incomplete/unapproved. It does not duplicate native source caches or claim to
  be a complete application source offer. No source archive was uploaded.

MSYS2 documents [source-only archives](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-harfbuzz)
its [source repository](https://repo.msys2.org/mingw/sources/) and
[official signing fingerprints](https://www.msys2.org/dev/keyring/). Local lock hashes,
internal metadata and exact-payload byte joins are the retained evidence, rather
than an assumption that today's package index identifies a past executable.

## Remaining

| Scope / exact affected inputs | Concrete next step |
| --- | --- |
| Native font/shaping/compression libraries, compiler, CRT/sysroot and headers | Complete per-file source/build/patch/notice assessment; review Ubuntu source signatures and replay-lock inputs beyond the tool executable profiles. Retained MSYS and Ubuntu sources reduce acquisition work but do not prove a hermetic rebuild. Integrate reviewed required MSYS notices into the actual package and re-inventory before promotion. |
| Actual Qt wheels, ICU 73.2 and incorporated third parties | Obtain exact wheel build configuration and assess source/notice/module-license obligations. Source version identity alone does not establish wheel correspondence. |
| Python _bz2/_lzma and incorporated compression code | Retain exact static-extension build/patch/compiler correspondence; OpenSSL DLL byte matching does not settle these other extensions. |
| MSVCP/VCRUNTIME 14.44.35211.0 and 14.51.36247.0 | Supplier/file hashes and non-prerelease flags are known. Review exact REDIST grant and owner's qualifying rights; no Visual Studio license is invented. See WINDOWS_RUNTIME_REDISTRIBUTION.md for the unimplemented prerequisite alternative and portable/offline consequences. |
| Generated Inno Setup prefix and unins000.exe | Finish actual incorporated-object mapping to source/SBOM/notices. Optional compiler-only components cannot be counted as shipped by inference. |
| AppImage fedfad51-cactu1 static prefix | Source/patch/object/static inputs and replacement/relink test exist. Finish component-specific terms and maintained recipient access. Runtime TAR has 131 verified files, SHA 4760a8477193572c103daaa76a50258f0d0cf6fcde6d7f16e78615f39a7be459. |
| Complete binary/source/notice delivery | Approve exact source set and durable recipient location; wire the approved artifact index to an eligible release. Plumbing exists but index SHA remains null. No publication until all gates pass. |
| Manual desktop acceptance | After final artifact/source qualification, record exact hashes and Windows 11 installer/portable plus Linux desktop/GPU acceptance. Headless smoke is not a manual desktop result. |

## RC1 readiness and owner actions

Internal engineering candidates and audit testing can proceed. **RC1 promotion,
provider replacement and publication cannot proceed** until the remaining source,
license, rights, delivery and manual evidence closes. No owner approval is sought
to substitute for missing technical evidence.

Owner-only actions, when the evidence is ready: establish qualifying Microsoft
redistribution rights (or choose a reviewed prerequisite strategy), review the
final license/source set, perform or arrange exact-artifact desktop acceptance,
and explicitly approve publication. No new owner action is needed to continue
source retention, build corrections or automated validation.
