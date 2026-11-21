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
