# Beta.1 redistribution blocker resolution

This milestone changes packaging/provenance and release diagnostics only. No beta
tag, release or unapproved application/source-bundle upload is authorized.

## Work and evidence

The baseline is clean source fe10aa1 and actual audit payloads from eabc092.
Those metadata-only reports remain retained unchanged. New builds generate exact
per-file comparisons against them, rather than replacing historical evidence.

The pinned PyInstaller QtGui hook collected every optional image/input plugin.
The PDF image plugin pulls QtPdf; the virtual keyboard input plugin pulls
VirtualKeyboard/QML/Quick. Cactu imports QtCore/QtGui/QtWidgets, uses native desktop
input methods and has no PDF renderer/QML interface. A narrow custom hook filters
only qpdf and qtvirtualkeyboardplugin before native dependency discovery. Desktop
platform plugins, native input methods, styles, raster/SVG support and QtNetwork
remain. Native package builds/smokes and exact reductions must be recorded below.

libmvec.so.1 is **required by both current FFmpeg executables** (actual ELF NEEDED
records), not safely removable contamination. It stays. The source/notice problem
is addressed as a glibc distribution-library obligation, not by breaking startup.

Inventory attribution now follows COLLECT alias chains, verifies copy-source
bytes, resolves merged-/usr Debian package paths, records Windows PE supplier/file
versions and distinguishes Microsoft runtime terms from Qt/Cactu terms. Known
supplier/version metadata does not assert an approved redistribution grant.
Actual copied Debian-library copyright notices are included after collection.

Exact QtBase, QtSvg, QtWayland and PySide 6.11.2 source archives are retained with
immutable commits and hashes in release/qt-source-lock.json. 196 source notice/
attribution files are packaged, with a provenance manifest. This is a conservative
superset for these source modules, not a claim every attributed dependency ships.
Each actual Qt binary/plugin receives source-module/version/license-option/notice
mapping. Exact wheel build configuration and third-party correspondence remain a
separate review; source version agreement alone is insufficient.

The official Inno 7.1.1 SBOM and Pascal Script/LZMA component terms are retained.
THIRD_PARTY_NOTICES now supplies the documentation acknowledgement required by
Pascal Script. LZMA 26.02 public-domain code and the older size decoder's linking
exception are identified separately. Optional 7-Zip/compiler/IDE components are
not automatically described as embedded in Setup; final linkage still needs review.

## Corresponding-source acquisition and delivery

retain_ffmpeg_sources.py actively acquires immutable source archives from the
exact retained provider recipe, with bounded downloads, archive validation, hashes
and license-file hashes. Mutable refs, unsupported hosts, missing inputs and size
bounds remain explicit failures. The result is a recipe-input superset, **not**
proof that every input was incorporated or that cargo/non-git/toolchain source
closure is complete. release/ffmpeg-source-lock.json records each outcome.

All archives stay in ignored release/evidence/local/sources on the workspace disk.
They are not published. The intended recipient package must contain exact archives,
patches, build configuration/instructions, static relinking inputs where needed,
notices and a hash manifest; it must be retained alongside eventual approved beta
assets rather than depend on daily provider URLs. A local verification/staging
tool and remaining gaps are recorded in this milestone's final evidence.

An isolated Alpine 3.21.10 rootfs has been verified against the official release
SHA-256. A controlled AppImage runtime experiment retains compiler/static-library
APKs and compiles inside a rootless namespace, leaving the host untouched. Its
outcome and source/relinking limitations must be recorded before any replacement
is selected. The existing runtime remains selected until that review/tests pass.

## Test scope and current decision

The source regression suite currently passes 162 tests locally, including physical
RX 7700 XT checks. Frozen smoke now exercises external burn/volume/Faststart,
Quick Preview, and a sequential two-job queue with embedded burn and loudness
analysis. Native installer/portable/AppImage builds and inventories are pending
for this source revision. CI GPU presence must not be inferred from encoder tables.

Technical closure, human license approval and publication approval remain separate.
No approval flags are set by acquisition or tests. **RC1 may not proceed until the
remaining exact source/terms/build/relinking evidence is closed.** New audit builds
are permitted under the existing policy without uploading executable payloads.
