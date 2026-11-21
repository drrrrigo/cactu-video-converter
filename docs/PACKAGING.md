# Cactu beta packaging

> Current authority: [RC1 qualification](RC1_QUALIFICATION.md), 2026-11-21. This supersedes the historical status, test counts, provider selection and open engineering lists below. Final common native source is 3b19839; human approval and Microsoft rights remain pending. No public beta is authorized.

`packaging/video_converter.spec` creates a PyInstaller ONEDIR bundle with Python,
PySide6/Qt, dependencies, bundled FFmpeg/FFprobe, branding, Cactu license and collected
third-party notices/licenses. The executable/collection is CactuVideoConverter.
Internal package/spec names remain stable. The official display version and PEP
440/numeric Windows forms derive from the single source version.

Windows Inno Setup 7.1.1 is a checksum-pinned build tool. It wraps ONEDIR as the
per-user `CactuVideoConverter-Setup-0.1.0-beta.1.exe`, with Start Menu/optional Desktop
shortcut, uninstall entry/icon and stable legacy upgrade identity. Its target is
Windows 11 x86_64 (not ARM). The build also produces the complete versioned Portable
ZIP. Native automated smoke tests run ONEDIR, extracted ZIP and an installed build,
then uninstall; manual Windows 11 testing remains a separate required gate.
Optional Authenticode hooks use an externally supplied certificate selector and
Windows SDK tool; no key/certificate is stored in source. Current candidates are unsigned.

Linux appimagetool 1.9.1 and its separate type-2 runtime asset are hash-pinned. The
runtime is passed explicitly: no unpinned continuous runtime download is allowed.
The AppDir includes AppRun, desktop/icon resources and ONEDIR payload. AppRun uses
shell builtins, so a deliberately empty PATH cannot break dirname/readlink lookup.
The AppImage includes Python/FFmpeg/Qt; kernel/GPU drivers and host graphics-stack
integration are not installed by Cactu. The supported build baseline is recorded
per artifact; a local CachyOS candidate does not prove Ubuntu/other compatibility.

`scripts/package_smoke.py` launches the exact frozen payload offscreen with PATH
empty and isolated user directories. It starts a MainWindow, uses bundled FFprobe,
generates synthetic video/audio/subtitles, converts through the existing planner/
runner, independently checks H.264/yuv420p/AAC, duration/Faststart, burned-track
absence and unchanged original bytes, and requires normal exit. AppImage smoke
uses extraction mode so FUSE is not assumed on CI hosts.

Candidate output is `dist/candidate`; it is not a public release. Binary artifact
upload is gated by exact licensing/corresponding-source approval. Public beta tags
promote artifacts from a successful same-commit candidate run, re-test them natively,
compare manual hashes, generate SHA256SUMS and create a GitHub **pre-release**.
No ordinary PR publishes binaries, no existing release is silently overwritten and
no different rebuilt candidate is substituted for the manually tested bytes.
See [release checklist](RELEASE_CHECKLIST.md), [license audit](RELEASE_LICENSE_AUDIT.md)
and [installation](INSTALLATION.md).

For final preparation, Python is strictly **3.14.7** and the source tree must be
clean/committed. Each actual extracted AppImage/portable and installed Windows
payload receives a file/hash/component inventory, embedded Python-module listing
and native dependency scan. Unknown origins/notices remain open reviews. These
reports and generated checksum text may be retained separately from binaries;
the public binary upload gate remains intact. Audit builds are explicitly not RC1.
See [BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md) for authoritative status.


## Redistribution blocker-resolution packaging policy

The final native audit is 7b7d23c, run 44845101385. All builds/frozen smoke passed;
only distribution eligibility failed and executable upload was skipped. Metadata
and comparisons are retained in release/evidence/beta1-resolution-7b7d23c.

Custom QtGui/QtNetwork hooks exclude only unused PDF/virtual keyboard chains and
Windows Qt's optional OpenSSL backend. Windows frozen smoke requires Schannel.
windows_application_binaries excludes OS-supplied UCRT/API-set contracts while
preserving Visual C++ DLLs. Linux required libmvec stays bundled. See
scripts/qt_payload_policy.py and the exact per-file comparisons; no blanket host
library exclusion or required codec/driver installation was added.

The selected type-2 runtime is built from source by build_controlled_runtime.py
inside a locked Alpine root with network disabled. Its reproducible hash is in
appimage-controlled-lock.json. prepare_runtime_source_delivery.py creates only a
local component source/relink archive; runtime-source-delivery.json retains the
verified archive/roundtrip/relink receipt. No binary build approval follows from
these technical checks. Source delivery and final terms remain separate gates.

Current hosted outputs are audit-only, not a retained RC1 set. Final exact source,
notice, conditional-grant and maintained recipient delivery records remain open;
see BETA1_BLOCKER_RESOLUTION.md. The publisher currently uploads application assets
and checksums; reviewed source assets/index wiring must be added before release.

## Controlled candidate and recipient-source qualification

Release/audit packaging selects `release/controlled-baseline.json` and invokes
`scripts/stage_controlled_runtime.py` from `build_release.py`. The generic
`vendor/ffmpeg/manifest.json` is retained only for reference fixtures; it is not
the selected release implementation. Build the native controlled pair first,
validate it against the reference for AV1/HEVC fixtures, then package it in the
same clean checkout. Generated manifests/binaries remain ignored, so Windows and
Linux `*-build.json` record the same actual source commit without synthetic
snapshot commits. No global approval follows from a successful build.

Windows notice integration reads the installed MSYS package evidence, matches
actual DLL bytes, copies only matched supplier notices and ships a FILE-MAP.
A same-named CPython DLL is accepted only when its bytes match the actual CPython
installation; it is never attributed to the MSYS package by filename. Qt Image
Formats is a separate source/notice module. The unused Windows Mesa OpenGL
fallback is excluded because this application uses raster QWidget controls,
without Qt Quick or QOpenGLWidget/Window; FFmpeg GPU processes are independent.

After both native builds succeed, run:

```
python scripts/prepare_rc1_review.py PATH_TO_BOTH_METADATA_REPORTS build/review-final
```

This requires identical clean source commits and controlled-runtime identities,
checks the actual Qt/Python/MSYS notice payload, generates a finite per-file CSV/
JSON review and prepares local source assets under `build/proposed-source-assets`.
The selection follows applicable license obligations. Permissive standalone
libraries do not automatically acquire a source duty; non-system inputs needed
for the proposed GPL FFmpeg/Qt aggregate source scope are identified separately.
Compiler-only packages and unused provider inputs are excluded. Cached archives
are hard-linked and deduplicated; none are uploaded by this command.

The output SOURCE-ASSETS index binds the exact source commit, all three binary
artifact hashes, source asset filenames/hashes, component mappings and proposed
retrieval/build instructions. Future release URLs are proposals, not a published
source offer. Every redistribution flag and complete-source approval stays false.

### Exact source-index approval without a commit cycle

The existing protected `BETA_OWNER_APPROVAL` attestation must additionally carry
`source_assets_manifest_sha256`, the SHA-256 of the reviewed SOURCE-ASSETS.json.
It remains bound to the same source commit and all manually tested artifacts.
The publisher rejects a missing owner approval/hash, different source or binary
identities, incomplete/unapproved assets, changed bytes and unsafe source names.
If release/config.json specifies a static source-index pin, it is also enforced
and cannot be overridden by the owner record. Its default null is not approval.

This external post-build attestation avoids committing a hash of an index that
contains its own Git commit (which would otherwise change that commit again).
It does not bypass technical/license/manual gates or publish anything. The
selected controlled-baseline approval fields replace irrelevant approval of the
legacy fixture provider; all selected-baseline fields remain false until reviewed.


## Final controlled candidate and source-offer preparation

The selected candidate implementation is `release/controlled-baseline.json`.
`build_release.py` packages the checked native source-built pair in the actual
clean checkout; generic provider staging remains a reference-fixture operation.
Run `scripts/prepare_rc1_review.py <raw-common-platform-metadata> <review-output>`
after downloading metadata from both native jobs. It refuses different commits
or dirty/source-mismatched packages, verifies actual notices and stages only
proposed sources in `build/proposed-source-assets`. Archive names, per-file hashes,
AMF header-layout overlay and recipient instructions are indexed. This post-build
review does not modify packaged binaries or approve delivery.

`SOURCE-ASSETS.json` is bound to the exact commit and all three artifact hashes.
The protected owner record must explicitly approve its SHA-256; the committed
optional configured pin is an additional check. All individual asset approvals,
completeness, technical/license/manual/publication gates still apply. This avoids
a Git self-reference without accepting an unpinned index. Current index and every
asset remain unapproved; proposed URLs are not a published source offer.

See [RC1 qualification](RC1_QUALIFICATION.md) for actual final evidence, finite
human decisions, candidate identities and manual tests. The current metadata-only
workflow does not preserve a downloadable application binary. Do not tell testers
to download an older provider artifact as though it were this candidate.
