# FFmpeg source-closure contingency

Current decision (2026-11-20): provider binaries remain **unapproved for RC1**.
Neither successful conversion nor a GPL label establishes the full source set.
The active manifest is an audit/testing input, with corresponding-source and
redistribution approvals false. No public binary mirror has been created.

## Evaluated options

| Option | Evidence / tradeoff | Decision |
| --- | --- | --- |
| Existing Nov 1 provider archives | Exact local copies/hashes, but upstream daily release expired and complete linked-source set is missing | Cannot use as reproducible final RC input |
| Retained Oct 31 month-end archives | Longer upstream retention, but three earlier missing fixes including Vorbis parsing behavior | Rejected as a final-input downgrade |
| Current dated 9.0.2 provider build | Restores current native test acquisition and includes later branch fixes; exact hashes/source revision recorded | Audit only; short retention and source closure still block RC |
| Another provider | Must provide complete matching sources/notices, all required software/encoder capabilities and durable immutable inputs | No unverified provider substitution approved; nonfree builds remain excluded |
| Cactu-controlled builds | Known source revisions, patches, toolchain/container digests, configure flags and source archives; more build engineering and native regression work | Preferred resolution if provider cannot supply sufficient correspondence evidence |
| Reduced compliant build | Could reduce the linked dependency surface | May be considered only after a capability audit; no required codec/input/subtitle/hardware capability may silently disappear |

## Requirements for controlled builds

Pin FFmpeg revision and every external library/header/compiler/runtime input by
immutable source/hash. Retain patches, build recipes, configuration, notices and
source archives. Record the actual toolchain/container digest, not a moving base
image tag. Generate a source/dependency manifest from the build itself and retain
the exact corresponding-source bundle for recipients. Keep driver implementations
host supplied; SDK headers and runtime interfaces need their own terms.

Preserve Cactu's supported input decoding/remuxing, H.264 software x264/AAC,
ASS/SSA/SRT/libass, loudnorm/alimiter/aresample/format, MP4/Matroska and Faststart.
Retain Windows NVENC/AMF/QSV and Linux NVENC/VAAPI/QSV paths with actual probe/filter
behavior; no physical GPU is required on cloud build runners. Re-run all existing
software/hardware command, subtitle, preview, loudness, queue and frozen smoke tests.
Native Windows packaging and Linux packaging remain separate jobs.

This document is a release-blocker resolution plan, not an implemented or approved
FFmpeg replacement. A new build needs complete inventories, source review, fresh
manual tests and new hashes before it can become the release candidate. No public
tag/release/upload is authorized by this plan.
