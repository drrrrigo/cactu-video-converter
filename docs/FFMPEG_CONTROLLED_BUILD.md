# Controlled FFmpeg candidate implementation

This is an implemented, isolated candidate pipeline, not a promoted runtime.
The existing provider manifest and release binaries remain unchanged.

`release/ffmpeg-controlled-lock.json` pins FFmpeg d59078794d80, x264, libass,
NV codec headers and Windows AMF headers by archive SHA-256 and source revision.
`acquire_controlled_ffmpeg.py` acquires only these inputs; Linux excludes AMF.
`build_controlled_ffmpeg.py` compiles x264/libass/FFmpeg and emits configuration,
compiler/tool hashes and executable hashes/version/buildconf/license evidence.
No nonfree option is enabled. Native decoders/demuxers/muxers/filters remain;
autodetection of other external libraries is disabled. libxvid/libx265 and many
unused external encoding/protocol/rendering libraries are absent. Native MPEG-4
and HEVC input decoding remain. Linux exposes NVENC/VAAPI/QSV; Windows requests
NVENC/AMF/QSV. AMF extraction excludes SDK media/example binaries.

The first local Linux compile used GCC 16.2.1, host font/shaping/VAAPI/VPL packages
and disabled assembly because no assembler was available. It is a functional
bootstrap, not the Ubuntu release baseline or a reproducible approved toolchain.
Those host dependencies need locked source/build correspondence. There is no
bit-identical reproduction claim. Native Windows bootstrap is a manual-only CI
workflow; it records packages and uploads metadata only. Its initial package
acquisition is explicitly unapproved and not yet a replay-locked environment.

An upstream version-script problem discovered during actual tests was fixed:
a source export nested inside the Cactu checkout inherited Cactu's Git version.
A retained generated VERSION input now labels the exact FFmpeg revision instead.
The validator retains missing-runtime guards and routes only HEVC *fixture creation*
through the unchanged provider; candidate decoding/conversion remains under test.
Cactu does not need external HEVC encoding for its H.264 output workflow.

Local FFmpeg source review preparation excludes the large Windows AMF archive
from the Linux component bundle. It is explicitly incomplete/unapproved until
host dependency/compiler sources and final terms are covered. It is not uploaded.
The release publisher now requires a same-commit Approved-sources artifact,
SOURCE-ASSETS.json completeness/per-file approvals/hashes, and the exact index hash
approved in release/config.json. No default approves an asset. Global technical,
license/publication flags stay false; source and binary uploads remain blocked.

Reproduce the current experiment only in a prepared native build environment:

```sh
python scripts/acquire_controlled_ffmpeg.py linux-x86_64
python scripts/build_controlled_ffmpeg.py linux-x86_64
python scripts/validate_controlled_ffmpeg.py build/ffmpeg-controlled/prefix/bin build/ffmpeg-controlled/compatibility.json
python scripts/prepare_ffmpeg_source_delivery.py
```

Do not promote candidates before native Windows/Linux tests and frozen tests,
source/toolchain closure and dependency license review. Qt/ICU/Python native,
MSVC grant, Inno incorporated scope and recipient delivery review are unchanged
open items; this work does not certify them. All historical evidence is preserved.


## Additional native-component evidence

release/python-native-source-lock.json now records the immutable CPython source-deps
and binary-deps commits used by 3.14.7 PCbuild/get_externals.bat. The actual audited
libssl-3.dll and libcrypto-3.dll hashes both match the official openssl-bin-3.5.7
archive exactly. OpenSSL 3.5.7, bzip2 1.0.8, XZ 5.2.5 and zlib-ng 2.2.4 sources
and legal files are retained. This closes the exact OpenSSL supplier-file gap;
static compression-extension build correspondence is still a separate review.

The Qt ICU library exports version 73.2. Three library files and their three
payload aliases map to immutable unicode-org/icu commit
680f521746a3bd6a86f25f25ee50a62d88b489cf and retained upstream license text in
release/qt-icu-source-lock.json. Exact wheel build configuration/correspondence is
still not proven. acquire_native_source_evidence.py revalidates source/supplier
archive hashes, actual DLL matches and legal bytes; verify_source_delivery.py now
covers these additional source records. No license approval follows automatically.

The capability comparison exposed missing compression-dependent native decoders,
so zlib/bzip2/lzma/iconv are now explicitly requested and common MPEG-4/AV1/VP8/
VP9/PNG/FLAC/AC3/Opus decoding is guarded. A real XVID-fourcc MPEG-4 AVI fixture
was converted to H.264 with the candidate without external libxvid. Unused
optional external decoders remain listed in the exact capability difference.


## Recorded Linux results

The selected provider passes 170 tests (91.940 s). The reduced initial candidate
passes 170 tests (78.769 s); the compression-enabled final candidate passes all
170 sequentially (73.760 s), including the RX 7700 XT VAAPI scenarios. One parallel
packaging/test run timed out creating an HEVC fixture with the old provider; no
product timeout was changed and its failed log is retained locally.

Final hashes:

* ffmpeg: 933f98b976b3d21ed851a4eb6b99849c57e00ddcf0f8f64531dafbbf753ba937
* ffprobe: 5a641097502b5b8c21413b95343c268c8d31fd13f699aaccd2109000cb04f2df
* isolated AppImage: afa79a91147d2e50ea3cf339e34f08ac1f736796af5136cd0ac32dd3602de087

Frozen ONEDIR/AppImage smoke passes x264/AAC/Faststart/subtitles/preview and the
two-job loudness queue. Its isolated snapshot SHA is retained in the receipt; it
is not represented as a public main commit. Metadata and exact capability diff:
release/evidence/controlled-ffmpeg-linux. The final dynamic dependency manifest
fingerprints 24 host shared libraries; it does not assert their source closure.

The ffmpeg executable shrinks from roughly 168 MiB to 31 MiB. The initial isolated
AppImage is about 113 MiB versus the preceding local 211 MiB audit image; these
are local CachyOS experiments with different legal payloads, not an approved
Ubuntu/Windows package size comparison. No approved runtime promotion occurred.

Windows native bootstrap: run 44857435005 at a688638; its compile and native
software-conversion result are recorded separately when available. Package
acquisition is not replay-locked, so even a successful bootstrap is not RC-ready.

### Remaining / RC1 / owner actions

RC1 remains blocked: finish Ubuntu-baseline and Windows candidate verification,
lock/rebuild font/shaping/compression/QSV/VAAPI/toolchain inputs, retain their source
and notices, and revalidate the exact frozen packages. The recipe's initial local
incremental corrections are recorded; no exact-output reproduction proof is claimed.
The selected provider is intentionally unchanged until these checks pass.

The ICU and OpenSSL source/supplier gaps are reduced as documented above; exact Qt
wheel build provenance and Python compression-extension correspondence remain open.
MSVC eligibility/REDIST conditions and Inno actual incorporated-component scope
remain open. Controlled AppImage source/relink evidence is preserved unchanged;
its final individual terms and recipient hosting review remains separate.

No new source-hosting service or publication approval is assumed. Only after the
technical/source set closes should the owner provide qualifying redistribution
rights review, exact-artifact Windows/Linux manual acceptance and final release
approval. None is requested to compensate for missing evidence. No beta tag,
release, binary artifact or source-bundle upload has been made.


## Native Windows bootstrap and source-built SDK follow-up — 2026-11-21

Native Windows bootstrap run 44857435005 at a688638 completed successfully with
MSYS2 GCC 16.2.0 and an actual software H.264/AAC conversion. Its ffmpeg SHA-256 is
758bc9dc4010d697bad7b23465e86db8ddc466c17aadbdb1e9b26f949fbe8451;
ffprobe is b1f8e3735c3875bfae01da33b4dbe97a392579d9a42c87b935c68c352ff59147.
Only JSON/package metadata was uploaded/downloaded. This first bootstrap did not
include the full candidate suite or frozen Windows tests; it is not a final RC.
Exact evidence: release/evidence/controlled-ffmpeg-windows-bootstrap.

The subsequent recipe builds the pinned oneVPL source instead of linking the host
oneVPL binary. CMake/Ninja identities are recorded; the local build-only CMake wheel
is SHA-256 pinned in ffmpeg-build-tool-lock.json. A real static-link failure exposed
missing C++ runtime linkage in oneVPL's pkg-config metadata, fixed with explicit
-lstdc++. No SDK driver implementation is bundled. The expanded manual workflow
adds Ubuntu 22.04 and full native candidate/frozen/installer tests on both targets;
results must be assessed separately from the successful initial bootstrap.

Source-root notices for the actual controlled inputs are retained under
licenses/ffmpeg-controlled with immutable source/notice hashes. AMF is a Windows
header input, not an active Linux input. native-file-source-mapping.json explicitly
maps six audited Windows Python files to supplier/source/notice evidence. This is
not blanket per-file legal clearance. All source/technical/publication flags remain
false and source-asset index approval remains unset.
