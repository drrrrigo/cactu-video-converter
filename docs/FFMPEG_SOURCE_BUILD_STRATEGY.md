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


## Blocker-resolution evidence — 2026-11-20

The same n9.0.2-61-gd59078794d-20261120 executable inputs remain selected for audits.
No replacement FFmpeg build or provider swap is claimed. Source acquisition now
retains **132/133** top-level recipe entries, with hashes/methods/license-file
hashes in release/ffmpeg-source-lock.json. These are a recipe superset, including
inputs for other variants; they are not a list of all libraries linked into the
GPL executables. Do not declare unshipped nonfree-library inputs incorporated.

The one unavailable entry is Xvid SVN r2204: the official HTTPS endpoint returns
E170013/E215004 authentication failure to the isolated SVN client. LAME r7153 was
successfully exported. Git fetches verify exact object IDs; explicit version tags
are resolved to commits and preserved in the retained lock. Cached modifications
are rejected rather than silently receiving new hashes. Git-export entries record
unretained gitlinks; archive retrieval alone does not retain submodules, Cargo or
other generated/vendor source inputs.

Actual provider run 44733376281 at recipe 7f2a6b1050d302144de8366afa37a75e46f326aa
identifies the dependency image indexes used by the FFmpeg jobs:

* Linux: sha256:9ccf2c7186810ffcdf440a9f9919b83fbc27e4644917413b9f36f57189d2b315
* Windows: sha256:825f50514aeddcaa70bea5b5f5ca77ef4e26ff62d78852ac4da63361ff8c2492

Target base digests, variant manifests, log hashes and exact public job IDs are in
release/ffmpeg-provider-build-evidence.json. This resolves the image-identity gap
for the observed build, despite floating recipe tags. It does not prove complete
source correspondence or make the daily binary archive durably available.

The next concrete controlled-build work is to replace recipe tags with those
reviewed digests, retain the exact generated/vendor/toolchain inputs and notices,
then generate source/link/configuration manifests during clean native Windows and
Linux builds. Validate all existing tests and frozen smoke/capability checks before
selecting new binaries. Current scripts acquire evidence; they do not implement
that controlled FFmpeg pipeline. No required decoding/remuxing, preview, batch,
subtitle/audio or NVENC/AMF/VAAPI/QSV capability has been removed.

Recipient delivery must include the reviewed source/patch/configuration/notices
set and hashes beside retained binary inputs. verify_source_delivery.py verifies
local bytes and still fails --require-complete. Current publication tooling needs
source-asset integration before an approved release. The separate controlled
AppImage runtime TAR does not satisfy FFmpeg obligations.
