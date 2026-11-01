# Testing

Run `python -m unittest discover -s tests -v` or `python -m pytest`.
`tests/test_core.py` covers parser/index semantics, labels, FPS, compatibility,
preset filename, planning, validation, overwrite protection, command mapping,
and progress/ETA. `tests/test_integration.py` generates small synthetic media
using a development FFmpeg 9.0.2 pair. It covers Unicode/apostrophe paths,
lossless remux, HEVC/10-bit + FLAC + subtitle burn to H.264/yuv420p/AAC,
selectable subtitles, pause/resume, and cancellation cleanup, including
conversions with volume filtering.

The suite contains 92 tests; three physical GPU tests are opt-in.
The earlier 65-test baseline passed with host GPU access on 2026-10-24;
see the implementation report for the current complete queue regression run.
The final queue run passed all 92 tests with GPU access in 71.308 s, without skips.
The GPU scenarios cover RX 7700 XT VAAPI using HEVC Main 10 + FLAC + ASS input
with 300% protected gain, and AC3 5.1 with measured loudness normalization.
Native Windows
tests, the missing bundled binary, packaged startup, and AppImage/installer
smoke tests remain open.

`tests/test_hardware.py` adds GPU-free tests for all four backend commands,
quality options, copy priority, detection and unavailable hardware. The
headless UI test checks that only available hardware choices appear. The
optional physical test is skipped unless `VIDEO_CONVERTER_HARDWARE_TEST=1`;
run `python -m pytest -m hardware` on a GPU machine. The current host has no
GPU device access in the command sandbox, so run the physical test from a host
terminal or with equivalent device access.

`tests/test_external_subtitles.py` covers ASS/SSA/SRT models and validation,
Unicode and Windows-like unsafe path staging, the external-file UI summary,
actual software burns, malformed-file preflight, and cancellation cleanup.
The optional hardware test also burns external ASS on the available AMD VAAPI
device. Native Windows subtitle handling remains unverified.

`tests/test_audio_volume.py` covers 0–300% boundaries (rejecting 301% and above),
neutral stream-copy behavior, exact filter order, selected-track mapping,
video-copy independence, mute, measured near-3× linear gain at 300%, decoded
AAC peak limiting at 300%, stereo and 5.1 channel preservation, and unchanged
sample rate. The headless UI test covers
slider/reset, summary and clipping warning. The limiter integration test uses
a generated sine signal and checks the decoded AAC peak, allowing modest codec
overshoot rather than asserting an exact digital ceiling. The unprotected
300% fixture checks a 2.85–3.15 RMS ratio against the 100% output; protected
300% output must contain finite samples, peak below 1.02 after AAC decoding,
and approximately preserve duration. UI tests cover exact intermediate values,
the high-gain warning, Reset restoring copy eligibility, and new-media reset.

`tests/test_preview.py` covers parsing, defaults, limits, EOF truncation,
immutable configuration snapshots, copy exceptions, source signatures, backend
commands and managed output cleanup. Synthetic 60 s media produces a 30 s
preview from 10 s. A selected audio track is silent until movie time 12 s,
verifying a two-second silent lead in the sample, followed by 1× versus 3×
waveform gain. Burned preview frames at 0.5/2.5/4.5 s are compared with full
output at 10.5/12.5/14.5 s for embedded ASS/SRT and external ASS/SSA/SRT.
Selectable subtitle event times are checked across the cut. Cancellation and
EOF output are checked through the production runner. `tests/test_preview_ui.py`
covers dialog validation, job locking, stale labels, cancellation during GPU
preflight, late probe results, opening errors and session cleanup. The physical
hardware test also creates short VAAPI previews with embedded/external subtitles
and protected 300% volume. Native Windows/player behavior remains unverified.

## Loudness normalization

`tests/test_loudness.py` adds model/preset/range and mode-exclusivity tests,
strict two-pass filter construction, copy independence, exact selected-audio
mapping, audio-only full-file preview analysis, all video backend plans, noisy
JSON parsing and malformed/missing/nonfinite value rejection. Cache tests cover
track, target I/TP/LRA, path/stat, channel/rate policy, runtime identity and LRU
eviction. Runtime/UI tests cover missing loudnorm while manual mode works,
presets/custom targets, retained inactive volume and new-media reset.

Real FFmpeg fixtures include:

- Quiet 12 s 5.1 FLAC with distinct per-channel sine frequencies and a one-second
  silent lead. Independently analyze the decoded AAC with loudnorm: integrated
  loudness must be within 0.7 LU of −16 and true peak at most −0.8 dBTP (0.7 dB
  codec tolerance above the −1.5 target). Check six channels, 48 kHz, layout,
  per-channel frequency identity, audio/video start/duration difference and
  preservation of the silent lead. Compatible video stays copied.
- Peaky mono audio forces dynamic fallback; the decoded AAC true-peak ceiling
  uses the same 0.7 dB tolerance. An external SRT is visibly burned with x264.
- Requested stereo conversion is measured before normalization in both passes,
  then independently checked for target loudness and two channels.
- A 44.1 kHz alternate track produces two nonzero-start 5 s previews and a full
  conversion. First preview analyzes the full track, later jobs reuse cache;
  track, target and source-mtime changes cause new analysis. Explicit progress
  checks use 12 s for analysis and 5 s for preview conversion.
- Cancel analysis: one process, no output/cache/second pass. Cancel pass two:
  no output, valid cache retained and reused. Pause/resume analysis uses the
  production process controls. Silent audio fails before encoding.

The opt-in physical test adds an 8 s HEVC Main 10 + AC3 5.1 + Portuguese ASS
fixture, embedded and external, through the available hardware backend. It
checks output H.264/yuv420p/AAC, six channels, 48 kHz, independently measured
LUFS/TP, visible burned text, Faststart atom order, and normalized previews
reusing analysis. The current RX 7700 XT VAAPI path has passed this scenario.
Other physical GPU backends remain unverified.

Tests print analysis time and throughput for development observations, without
a speed gate. Synthetic short material does not validate full-movie LRA or all
mastering conditions. See the [implementation report](IMPLEMENTATION_REPORT.md)
for measured results and exact development runtime configuration.

## Batch / Queue

`test_batch_queue.py` covers UUID identity, same-name/different-directory inputs,
duplicate paths, independent settings, guarded status transitions, reordered
execution, active-row locks, per-media bulk presets and destination identity.
Semantic tests cover reordered Portuguese audio/Full ASS, aliases and regional
conflicts, missing/ambiguous audio, missing/forced/differently titled subtitles,
and external-path exclusion. Output tests cover queue collisions, existing
files, input identity, deterministic suffixes and unwritable directories.

The fake runner exercises A-success/B-failure/C-success, Cancel Current versus
Stop Queue, current-process pause versus pause-after-current, resume, retry
revalidation/no infinite retries, snapshots/attempt history, hardware preflight
failure/cancellation, late probe callbacks, adding while running and an earlier
slow probe holding execution order. Internal move MIME cannot become file import.

`test_batch_ui.py` covers rapid selection switching without cross-writes, native
multi-file selection, real Qt file-drop events into both window and sidebar,
multi-selection/bulk copy/preset/folder, an explicit copy source surviving a
highlight change, active locks with pending-job edits, preview exclusion while
running, per-job preview stores, stop confirmation and non-destructive removal.

`test_batch_integration.py` uses actual FFprobe/FFmpeg. Five Unicode `.data`
files containing valid video are recognized despite their extension, while
invalid/missing/directory candidates fail independently in the bounded two-probe
pool. Four sequential jobs perform copy, invalid ASS failure, measured loudness,
and 150% gain plus subtitle-burn conversion. Later jobs continue after the
failure, outputs are independently probed, diagnostics remain attached to the
correct job, and partial/workspace cleanup is checked before advancing. A real
Cancel Current test verifies cleanup before the next dispatch.

The third opt-in GPU test runs two jobs through QueueController on the available
hardware backend. It checks fresh preflight twice, order, separate loudness/gain
reports, subtitle burn, verified outputs and cleanup. The RX 7700 XT VAAPI path
has passed. `qt_helpers.py` makes unexpected Python exceptions in Qt callbacks
fail their owning queue test. Rendered synthetic UI fixtures were inspected at
1366×768 and 1480×1000. Native Windows and very large/full-movie queues remain
separate verification work.

## Branding and migration

`test_branding.py` adds eleven checks for Cactu metadata, window/header/icon,
About version/attribution, Settings actions at narrow widths, source/wheel/frozen
asset resolution, readable text/primary-button contrast and portable packaging
metadata. Migration tests use isolated INI stores: compatible Unicode directory/
geometry/splitter/encoder settings copy once; nonempty new preferences win;
malformed/transient values are rejected; the old store is byte-for-byte intact;
Reset Settings cannot re-import discarded legacy preferences.

`python scripts/check_branding.py` checks Linux desktop/AppRun, PNG/ICO dimensions,
Windows version/include fields, installer upgrade/icon/artifact rules and spec
asset references without claiming a native build. Run `desktop-file-validate`
on the committed desktop file on Linux. Use native Windows to verify executable
resources, installer upgrades/shortcuts/uninstall; Linux AppImage mounting and
launcher integration also need a verified release payload.

The 2026-10-24 rebrand run passed **103 tests, no skips**, with real RX 7700 XT
VAAPI access under pinned PySide6/Shiboken 6.11.2. The host's unpinned 6.12.0
crashed in Shiboken worker cleanup during earlier attempts; the pinned runtime
passed the unchanged media/queue pipeline. Do not substitute host Qt versions
for the dependency pins when evaluating regressions. See the report for exact
runtime, commands, packaging evidence and rendered 100–200% scale review.

## Hardware Acceleration Assistant

`test_hardware_assistant.py` and `test_hardware_assistant_ui.py` add **31 tests**.
They cover read-only Windows API/registry boundaries, vendor IDs before model
strings, Linux PCI/DRM/node association, distro families, permissions, optional local
PCI names, missing inventory, refreshed node discovery and session cache.
Classification cases include available, no GPU, unsupported capability, missing
FFmpeg encoder/filter/API, driver/API incompatibility, missing graphics library,
node/access/mismatch, unknown cause and default-device ambiguity. Mixed GPU tests
require any real success to make overall hardware available.

Guide tests check vendor/family/unknown-distro behavior, no driver remedy for build
errors, static HTTPS registry membership and empty command lists. Report tests
scrub user/home/media paths and URLs while retaining device paths. Qt tests verify
cached page opening, safe official links/browser failure, clipboard-only export,
warning dismissal/identity/recovery, active-operation re-test lock, actual worker
re-test unavailable→available, dropdown/independent pending-job recovery, explicit
software selection, preflight invalidation and continued software planning.

The complete suite now contains **134 tests**. Run the normal full command or
opt into physical GPU checks with `VIDEO_CONVERTER_HARDWARE_TEST=1`, using the
pinned PySide6/Shiboken 6.11.2 pair. The actual CachyOS/Arch + AMD RX 7700 XT VAAPI
inventory/diagnosis passed separately, and all existing physical/media tests remain
in the full gate. Windows API-boundary simulations and Windows UI fixtures do not
establish native Windows or physical NVENC/AMF/QSV validation. See the report for
final timing and the exact environment.

## Public beta hardening

`tests/test_release.py` adds twelve focused tests: central beta/PEP 440/Windows
version mapping, essential capability parsing/failure, HTTPS/digest/member safety,
exact-member extraction and traversal rejection, generated checksums, blocked
publication, source/artifact/manual-evidence mismatch, config/temp failure messages,
frozen no-PATH fallback, diagnostic fields/privacy, workflow pre-release guards and
atomic no-overwrite finalization. Full source suite now contains 146 tests.

`scripts/package_smoke.py` is a separate actual frozen-payload test, with PATH empty
and isolated config/data paths. It verifies a real Qt window, bundled media tools,
synthetic MKV/audio/subtitle conversion, codecs/pixel format/Faststart, output duration,
no selectable track after burn and unchanged input bytes. It is run for ONEDIR,
extracted Windows ZIP, installed Windows payload and Linux AppImage where native
builds are available. Cloud tests do not substitute for manual Windows 11/desktop
artifact testing. Physical GPUs remain optional; the existing actual RX 7700 XT
scenarios were retained. See the report for exact runs, hashes and untested gates.
