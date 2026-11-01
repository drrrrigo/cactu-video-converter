# Implementation report — work in progress

## Implemented

Typed FFprobe media parsing; exact stream-index selection; Web Compatibility /
Kosmi preset; compatibility analysis; settings validation; smart copy/encode
planner; safe FFmpeg argument builder; text subtitle extraction and burn;
asynchronous Qt probing/conversion; machine progress, ETA, pause/resume,
cancel, atomic partial output; rotating logs; QSettings window and directory
preferences; dark English UI; unit and generated-media integration tests.

FFmpeg/FFprobe 9.0.2 were used from the Linux development host only. Local
runtime validation checks version, libx264, AAC, subtitles and optional loudnorm
availability; release verification requires loudnorm.

## Incomplete release work

No pinned Windows/Linux binary archives or SHA-256 values have been approved.
The archive acquisition script exists but lacks approved pinned inputs. Full
license payload and source offer, native
Windows build, Linux AppImage build, and packaged smoke tests have
not been completed. Thus **no self-contained release artifact exists**.
Native Windows pause/resume and cancellation behavior remain unverified.
Embedded font extraction, richer error categorization, settings persistence
for custom options, and a full command diagnostics panel remain open.

The source application can be run locally with an explicitly selected
development FFmpeg. This report must be updated after release work; it does
not assert that the project's full definition of done has been met.

## Hardware encoding extension

The application now defines optional NVENC (Windows/Linux), AMF (Windows),
VAAPI (Linux) and QSV (Windows/Linux) H.264 backends. It probes encoder
presence and actual initialization in a Qt worker, including subtitle filter
and all quality modes. The UI lists only successful probes; x264 remains the
default. The planner keeps stream copy first, retains selected backend/device
in the plan, and rejects unavailable explicit hardware requests. Before start,
a fresh asynchronous probe rechecks the choice. A running hardware failure
offers an explicit software retry. After conversion, FFprobe verifies the
partial output before it is finalized. Progress, pause/resume and cancel still
use the common runner.

The local FFmpeg 9.0.2 exposes h264_nvenc, h264_amf, h264_vaapi and h264_qsv.
The host AMD RX 7700 XT (`/dev/dri/renderD128`) passed VAAPI detection and a
physical short HEVC Main 10 + FLAC + ASS subtitle-burn conversion to
MP4/H.264/yuv420p/AAC. The former 128x72 probe failed because its frame height
was below this GPU's encoder minimum; the 256x144 probe succeeds. The Codex
command sandbox hides `/dev/dri`, so this test ran with host device access.
Backend commands and quality profiles have unit coverage; Linux software and
synthetic media integration tests still pass. Full-length 1080p RX 7700 XT
conversion, Windows AMF, QSV and NVENC remain unverified. Drivers are external
to the package. The bundled
FFmpeg provenance and native installer/AppImage gates described above remain
open as well.

## External subtitle files

The Subtitles card now offers Embedded track or External file for Burn into
video. A separate Browse dialog accepts ASS, SSA, and SRT, remembers only the
last subtitle directory, and shows the filename in the output summary. Typed
subtitle source identity survives through settings and the conversion plan.
The planner forces video encoding. The runner extracts embedded tracks or
copies an external file unchanged to the same safe temporary workspace, then
uses the existing libass and backend filter path. External files receive a
one-frame FFmpeg/libass preflight before the movie conversion. Validation
checks format, existence, regular-file status, readability, and nonempty data.
The staged copy and partial output are removed on success, failure, or cancel.

Linux software integration tests passed for external ASS, SSA, and SRT burns,
malformed ASS rejection, and cancellation cleanup. A short external ASS burn
also passed on the host RX 7700 XT through VAAPI. The complete suite contains
49 passing tests with host GPU access. Native Windows paths, other physical
GPU backends, full-length media, and exact ASS font fidelity remain unverified.
External selectable MP4 subtitles and a custom font folder were intentionally
left outside this increment. No release installer or bundled FFmpeg artifact
has yet been completed.

## Audio volume control

The Audio card now offers a 0–300% slider, numeric value, Reset to 100%, and
Prevent clipping checkbox. The default is 100% for each new video and preset
restore; volume is not persisted between videos. Settings and the immutable
conversion plan carry typed percent and limiter decisions. The validator
enforces bounds and rejects explicit Audio Copy with non-neutral gain. The UI
switches Copy to AAC when the slider moves. At 100%, no audio filter is emitted
and AAC stream copy remains possible. Other values re-encode the selected audio
track to AAC while compatible video can still be copied.

The maximum was extended from 200% to 300%: 3.0× linear amplitude, approximately
+9.54 dB. The FFmpeg audio filter builder maps 300% to `volume=3.0`. Protected boosts
append `alimiter=limit=0.85:level=false:latency=true`; the 0.85 target leaves
headroom for AAC overshoot, disables limiter makeup gain, and compensates
lookahead latency. No limiter is added at or below 100%. This is manual linear
gain, not loudness normalization. Limiting may alter loud transients and does
not guarantee a hard ceiling after lossy AAC decoding.

Synthetic tests verified near-3× gain at 300% without limiting, silence at 0%,
reduced decoded AAC peaks with limiting, stereo and 5.1 preservation, and
video-copy/audio-encode independence. The full 49-test suite passed with host
GPU access, including a short RX 7700 XT VAAPI conversion with subtitle burn
and 300% protected gain. Range and UI tests now include 225–300%, rejection of
301%/400%/500%, exact intermediate slider values, a stronger unprotected-gain
warning at 250% and above, and resetting new media to 100%. The limiter
configuration is retained: its ceiling controls peaks independently of input
gain, with increased peak reduction possible at 300%. Native Windows,
full-length media, and other physical
GPU backends remain unverified; bundled release artifacts remain open.

## Quick Preview / Test Encode

Create Preview now opens a start-time and 10/30/60 s duration dialog, defaulting
to 30 s with Open when finished enabled. Starts are deterministic and editable;
business validation accepts 5–120 s requests and clamps at EOF. The immutable
PreviewPlan retains the full ConversionPlan and source/subtitle signatures.
Its derived execution plan uses the same encoder/device, quality, audio settings
and subtitle identity through the existing command builder, runner and output
validation. Preview encodes copied streams for accurate standalone cuts; this
exception is disclosed and does not change the full conversion's copy decisions.

Input accurate seek limits video/audio decoding to the sample. Burn rendering
restores movie timestamps around libass, then resets the output clock. Embedded
subtitle extraction reads packets through the preview end without decoding
video, preserving events crossing the start. This prefix read can add delay for
late segments of large files. Selectable preview subtitles are converted by
FFmpeg to SRT, clipped/rebased, then encoded as mov_text. External burn staging
and font behavior use the existing pipeline unchanged.

Progress/ETA use the effective preview duration. The UI locks competing launch
actions, supports cancellation including a pending GPU preflight, and ignores
late probe results from cancelled jobs. Generated samples live in a session
temporary folder. The latest success survives failed/cancelled attempts and is
replaced on a new success; source/settings changes mark it out of date. Qt opens
the file/folder without a shell. Exit cleanup is best effort if a player locks
the file; crashes can leave temporary folders.

All 49 tests passed with host GPU access. Tests include 30 s output from 10 s,
EOF truncation, decoded frame comparisons against full conversion for all text
subtitle sources, selectable event clipping, selected-audio timing and gain,
backend plans, cancellation, UI locking and snapshot/store lifecycle. A short
RX 7700 XT VAAPI preview passed with embedded and external ASS plus 300%
protected volume. Native Windows/player launch behavior, large movie performance
and other physical GPU backends remain unverified. The existing installer and
bundled FFmpeg release gates remain open.

## EBU R128 loudness normalization — 2026-10-24

Implemented a genuine two-pass selected-audio workflow. The first pass maps
only the chosen audio stream, disables video/subtitles/data, and sends loudnorm
output to the null muxer. A dedicated parser reads JSON among stderr logs into
finite, range-checked measurements. The runner resolves a typed audio plan
containing measured I/TP/LRA/threshold/offset for pass two. Missing or invalid
measurements stop the operation; there is no one-pass fallback for conversion.
FFmpeg receives `linear=true` and can fall back to dynamic mode as required.

The Audio card offers Manual Volume or Loudness Normalization. Movie / Web is
−16 LUFS, Louder −14, Conservative −18, with −1.5 dBTP and 11 LU LRA for all
three; Custom exposes I/TP/LRA. The 11 LU choice allows more movie dynamics
than loudnorm's default 7 LU. This is an application listening preset, not a
Kosmi loudness requirement or an EBU broadcast-compliance claim. Manual mode
at 100% remains the new-media/Web preset default. Normalization keeps the
inactive slider value but applies neutral effective manual gain and no manual
limiter. Summary shows targets; Loudness Details shows measured values and
available second-pass filter statistics.

AAC encoding is required for normalized audio; compatible video remains
eligible for copy. Requested channel conversion precedes loudnorm in both
passes; source channels are otherwise preserved. Explicit final resampling
preserves AAC-supported source rates (48 kHz fallback), avoiding accidental
192 kHz AAC output. All video backend command plans use this shared audio path.

Successful measurements live in a bounded 16-entry session cache keyed by
source path/size/mtime, exact audio stream, channel/rate policy, numeric targets
and FFmpeg identity/version. Source identity is checked again after analysis
and before encoding. Normalized previews analyze the full track on a miss,
then reuse the same measurements for samples and full conversion. Original
preview/conversion snapshots remain immutable. Analysis/encoding are separate
progress stages with their own duration denominator and reset elapsed/ETA.
Pause/resume/cancel use the same Qt/psutil lifecycle. Cancelling analysis never
starts pass two or caches incomplete work; cancelling pass two retains valid
measurements and removes partial output.

### Exact development runtime

Tested `/usr/bin/ffmpeg` **n9.0.2**, built with gcc 16, libavfilter 12.1.102,
and the matching local FFprobe. The host configuration enables GPL, libx264,
libx265, libass, AMF, NVENC, libvpl and shared libraries. Full `-version`
configuration and actual `-h filter=loudnorm` output are retained in
[runtime evidence](assets/loudnorm-runtime.txt). Actual supported ranges:
I −70…−5, LRA 1…50, TP −9…0; measured I/threshold −99…0, measured LRA 0…99,
measured TP and offset −99…99. Runtime filter detection disables only this
feature if missing; release verification now requires loudnorm. There is still
no pinned bundled artifact to inspect or certify.

### Verification

`tests/test_loudness.py` covers presets/custom validation, exclusivity, exact
mapping, measured filter options, independent video copy, backend planning,
noisy JSON failures, runtime unavailability, bounded cache identity and UI state.
Real fixtures test output LUFS/true peak, 5.1 channel identity, sample rate,
A/V start/duration and silent lead, requested downmix, external subtitle burn,
dynamic fallback, preview cache reuse and invalidation, both cancellation
stages, pause/resume and stage progress denominators. Test thresholds permit
0.7 LU loudness error and 0.7 dB true-peak codec overshoot; no bit-exact or
arbitrary speed requirement is imposed.

Observed quiet 12 s 5.1 output: **−16.07 LUFS**, **−16.12 dBTP**, six channels,
48 kHz, preserved channel-frequency identity and A/V timing. An observed analysis
took 1.66 s (7.2× realtime); timing varies with codec, content and host load.
The peaky fixture exercised dynamic fallback and the decoded true-peak bound.

The actual **RX 7700 XT / VAAPI renderD128** passed an 8 s HEVC Main 10 + AC3 5.1
fixture with both embedded and external Portuguese ASS. Output was
MP4/H.264/yuv420p/AAC, six channels, 48 kHz, visibly burned subtitles and
Faststart. Both measured **−16.06 LUFS / −16.43 dBTP**. Analysis took about
1.20–1.31 s in the targeted run. Subsequent 5 s normalized GPU previews reused
the full-track measurements. These tests required host device access because
the command sandbox hides `/dev/dri`.

The complete regression command
`VIDEO_CONVERTER_HARDWARE_TEST=1 PYTHONPATH=src python3 -m unittest discover -s tests -q`
passed **all 65 tests in 70.713 s**, with no skips, using host GPU access.
That final run observed 1.00–1.03 s GPU-fixture analysis and 1.56 s (7.7×)
quiet-fixture analysis. `python3 -m compileall -q src scripts tests` also passed.
The normalization controls were rendered and visually inspected offscreen;
the [Audio-card screenshot](assets/loudness-ui.png) records the current layout.

### Remaining verification limits

Native Windows, physical NVENC/AMF/QSV, full-length movie loudness/performance,
and self-contained release builds remain unverified. GPU command planning is
covered for all backends; physical execution was tested on AMD VAAPI only.
AAC/resampling can slightly change peaks; short or silent material may not
yield valid integrated measurements. Dynamic processing and preview boundaries
can change scene behavior, and filter result statistics precede AAC. No extra
compressor/dialogue enhancement was added. Ruff is unavailable in this local
environment; bytecode compilation and the unittest suite provide the current
automated checks. The original project's open release gates remain open.

## Batch conversion / queue — 2026-10-24

Implemented a queue for every input, including one file, using the existing
single-plan media pipeline. `models/job.py` adds UUID ConversionJob records,
explicit JobStatus/ValidationState, frozen settings/plans, progress/errors,
timestamps, last verified output, separate preview diagnostics and per-attempt
execution history. `models/queue.py` owns order, duplicate identity, aggregate
counts, active-row restrictions, QueueState and OutputPolicy.

`services/queue_controller.py` owns orchestration. It validates each job through
the existing planner/validator, resolves output reservations, performs fresh
asynchronous hardware preflight where required, then calls ConversionRunner.
There is one active job ID and **concurrency is exactly 1**. The next dispatch
is scheduled on a later Qt event-loop turn after the runner's terminal signal,
which follows verification/finalization/cleanup. No batch FFmpeg runner or
argument builder was introduced. Existing copy decisions, encoders, audio
filters, loudness/cache, subtitle pipeline, progress parser and output checks
remain shared. The runner additionally retains its executed command arrays.

### Import, UI and settings

`services/probe_pool.py` limits asynchronous media imports to two QProcesses,
validating readable regular files and recognized video content. Extensions are
not trusted. Stable-ID results cannot bind to removed/different jobs. An earlier
Analyzing row holds execution order even if a later probe finishes sooner.
Duplicate resolved paths are skipped; equal basenames in different directories
coexist. Native multi-file Browse and external file URL drops both add jobs.
**Adding while running is implemented** and appends pending work safely.

The dark UI now uses a persistent resizable sidebar, compact status/progress
rows, extended selection and internal UUID MIME for reorder. Internal moves
cannot re-import files; active/terminal rows are not draggable and active-row
position is locked. `ui/queue_panel.py` handles binding/bulk presentation while
MainWindow retains its settings panels and preview launch path. Loading guards
prevent cross-job writes. Active configurations are locked, pending jobs can
be edited, and terminal jobs require explicit Retry/Requeue. Cached Media
Details replaces the large source grid and retains format metadata/streams.
Selected Job Details includes snapshots, progress, commands, errors and readable
FFmpeg logs. Geometry and sidebar widths use existing QSettings persistence.

`services/batch_settings.py` applies Web presets per media and copies scalar
settings with semantic stream resolution. Language aliases, normalized titles,
audio channels/layout/codec and subtitle codec/dispositions guide matching;
ambiguous/missing matches block the affected job. It never blindly copies raw
indexes or concrete external subtitle paths. Bulk Output Folder preserves each
filename. The explicit Copy from selector retains the last single selected
source and does not follow a later highlight change accidentally.

### Controls, outputs and failure policy

Current-process Pause/Resume is independent of Pause Queue after current.
Cancel Current cleans/marks only that job and continues; Stop Queue asks for
confirmation, cancels current and preserves pending jobs. Failed jobs retain
diagnostics and do not stop later jobs. Retry is explicit, revalidates and runs
once per requested attempt; there is no retry loop or implicit software fallback.
Hardware-check cancellation waits for the worker to exit before another job
can run. Completed status follows the existing verified output lifecycle.

Default output policy deterministically renames existing/reserved destinations
with numeric suffixes. Skip existing and Require attention are available;
input identity, duplicate paths, unwritable folders and configurations are
checked up front and again before dispatch. No policy grants overwrite. A
destination appearing after start fails finalization safely. Restoring preset
defaults clears a stale collision issue when it changes the output identity.
There are no per-file success/error prompts during full queue execution; the
bottom area presents current progress and one inline queue count summary.

Each job has its own PreviewStore, while the existing shared runner serializes
preview/conversion work. Preview does not requeue jobs or alter their statuses.
Preview is disabled throughout active/paused/stopping queue work. Loudness
reports are saved per job, and the existing correctly keyed session cache cannot
cross input identities. Preview reports/history stay separate from full runs.

### Verification and actual status

The suite now contains **92 tests**, including 26 dedicated queue/domain/UI/real
media tests and a third opt-in physical GPU scenario. Domain tests cover job
identity/settings/states, order/active locks, slow-probe ordering, per-media bulk
presets, semantic matches and ambiguity, excluded external paths, output policies
and permissions, failure continuation, both pause semantics, cancel versus stop,
retry/history, hardware preflight failure/cancellation and add-while-running.
UI tests cover real Qt drop MIME, native multi-file selection, rapid binding,
stable copy source, bulk folder/preset/copy, active locks and pending edits,
per-job previews, stop confirmation, safe removal and preset collision recovery.
Unexpected Python exceptions in asynchronous Qt slots fail the queue tests.

Real FFprobe tests accepted five Unicode `.data` inputs containing valid video
and independently rejected bad/missing/directory candidates with the two-probe
limit. Real sequential conversion performed copy, malformed ASS failure,
measured normalization and 150% gain/subtitle burn; later jobs completed after
the failure. Output codecs/durations, per-job diagnostics and cleanup were
checked. Actual cancellation cleaned partial/workspace resources before the
next job began. Existing 65-feature regressions were retained.

On the actual **RX 7700 XT / VAAPI**, two queue jobs passed fresh GPU preflight
separately and executed in order using HEVC Main 10 input, external/embedded
ASS, loudness on one job and manual gain on the other. Both produced verified
outputs and cleaned resources. The existing surround/loudness/preview hardware
tests also passed. Tests used the same `/usr/bin/ffmpeg` n9.0.2 development
runtime documented above, with host device access because the sandbox hides
`/dev/dri`. UI fixtures were rendered and visually inspected at 1366×768 and
1480×1000; [overview](assets/batch-queue-ui.png) and
[settings](assets/batch-queue-settings.png) are actual Qt renders of synthetic jobs.

Final verification after the preset-collision correction:
`VIDEO_CONVERTER_HARDWARE_TEST=1 PYTHONPATH=src python3 -m unittest discover -s tests -q`
passed **all 92 tests in 71.308 s, with no skips**. Bytecode compilation with
`PYTHONPATH=src python3 -m compileall -q src tests scripts` also passed.
The intentional malformed-subtitle and synthetic-failure fixtures emit expected
error logs; the suite verifies those failures do not halt subsequent jobs.

### Remaining limitations

**Queue persistence/crash recovery is not implemented.** Queue contents,
attempt history, measurements and previews are session-only. Directory/splitter
preferences persist; application exit best-effort cleans previews. Adding while
running is supported. Concurrent conversion, folder recursion, bulk external
subtitle pairing, total queue ETA, stop-on-error and notifications are outside
this milestone. Native Windows queue/drag/cleanup, large queues, full-length
movie performance and physical NVENC/AMF/QSV remain unverified. Existing pinned
FFmpeg provenance, installer/AppImage and packaged smoke-test gates remain open;
this feature does not create a self-contained release artifact.

## Cactu visual identity / rebranding — 2026-10-24

### Scope and architecture

The visible identity changed from **Video Converter + purple/lilac** to
**Cactu Video Converter + cactus green**, retaining version **0.1.0**. The audit
and `docs/REBRANDING_PLAN.md` were written before implementation. Product names,
slug/executable and description are centralized in `product.py`; the version
continues to live in `__init__.py`. `ui/theme.py` centralizes neutral surfaces,
text, cactus normal/hover/pressed/focus/selection, disabled gray and separate
emerald success, amber warning, red error/destructive and cool information colors.
QueueDelegate now imports the shared progress tokens; file drops get a transient
brand highlight. Checkbox/radio/slider/dropdown/input/button/progress states,
Quick Preview and loudness controls share the same QSS. The primary pressed
state's text was darkened after a contrast check; primary text meets 4.5:1 in all
three fill states. Percent text is outside the main progress fill.

The header, main window, Qt identity, About, startup log heading and reinstall
message use the new name. Settings tools are in a two-column grid to avoid
clipping on narrow HiDPI desktops; About remains accessible there with application,
FFmpeg and FFprobe versions, third-party attribution and a separate licenses action.

An original geometric cactus/play SVG replaces the purple play mark. Standard
16–512 px PNGs and a seven-resolution ICO are exported by Qt SVG rendering.
This is the project's current original icon, not downloaded artwork or an external
placeholder. Source/wheel/frozen lookup covers the SVG, checkmark and notices.
The supplied old mockup and original implementation plan are explicitly historical.
Current README, queue, audio/loudness and other review screenshots were refreshed.
`BRANDING.md`, asset instructions, README, architecture/build/packaging/testing/
troubleshooting/review docs and third-party project identification were updated;
third-party names and licensing requirements were preserved.

### Preferences and compatibility

Startup migrates from the old organization/application pair `Video Converter`
into `Cactu Video Converter` only when the new store is empty. It validates an
allowlist: geometry, two splitter sizes, known encoder ID and directory hints.
It never copies arbitrary/transient job, subtitle or measurement state, changes
the old store or overlays nonempty new settings. Schema/migration markers prevent
repeat imports, including after Reset Settings. Old log files remain untouched;
new log directory naming follows Qt's new identity.

`video_converter` imports/logger namespaces, the module launch and spec filename
remain stable. The old CLI is a compatibility alias. Technical temporary/log
prefixes and queue MIME remain unchanged. Old visible strings remain only where
required for legacy settings/installer identity/shortcut cleanup and in historical
material. User output names such as `Movie-Kosmi.mp4` are unchanged.

No media planner, validator, command builder, runner, encoder adapter, subtitle
pipeline, audio filter, loudness cache, output verifier, progress parser or queue
scheduler was changed. `ffmpeg/runtime.py` changes only its reinstall-message
product name. One existing test's unused QApplication reference was renamed
`_app` to preserve its lifetime while satisfying lint; media assertions remain.

### Packaging

The Python distribution/primary CLI is `cactu-video-converter`, with packaged
branding data and notices. The native executable/collection is
`CactuVideoConverter`; generated Windows version resources identify the new
ProductName/FileDescription/InternalName/OriginalFilename/version without adding
a company. PyInstaller now includes branding assets and the ICO; its spec root
is resolved from the spec directory correctly.

The renamed Inno template produces `CactuVideoConverter-Setup-<version>.exe`,
with new display/shortcut/uninstall metadata and icon. It explicitly retains the
old implicit `AppId=Video Converter`, reuses a recognized previous directory and
removes only the exact known old executable/shortcuts. Native upgrade behavior
has not been verified here. Linux desktop/icon/AppRun and AppDir use the new names,
with hicolor exports and `CactuVideoConverter-<version>-x86_64.AppImage` derived
from the application version. CI includes portable branding checks on both OS
matrix entries; there was no release artifact upload job to rename.

### Verification and actual results

Environment: CPython **3.14.8**, PySide6/Shiboken/Qt **6.11.2**, psutil **7.2.2**,
setuptools **80.10.2**, ruff **0.13.3**, PyInstaller **6.16.0**. System development
FFmpeg/FFprobe are **9.0.2**. Pinned tools were installed into an isolated temporary
venv; the host installation was not changed. CI's Python 3.14.7 and dependency pins
remain unchanged.

Final complete test command:

```bash
VIDEO_CONVERTER_HARDWARE_TEST=1 PYTHONPATH=src /tmp/cactu-test-venv/bin/python -X faulthandler -m unittest discover -s tests -q
```

**103 tests passed in 72.074 s; no skips.** This includes all 92 previous tests
and eleven branding/migration checks. Existing real media scenarios cover single
and sequential queue conversion, Web/Kosmi, custom/copy planning, hardware,
progress/ETA/process controls, previews, loudness, manual volume/limiting,
embedded/external subtitles, Faststart, verification, failures and cleanup.
Physical RX 7700 XT / VAAPI tests passed with host device access. NVENC/AMF/QSV
command planning remains covered; these physical devices were not available.
The expected malformed-subtitle and synthetic-failure logs are intentional fixtures.

Earlier attempts with the host's unpinned **PySide6/Shiboken 6.12.0** crashed in
Shiboken/QObject cleanup, including during GPU queue preflight. Fault tracing
identified the runtime location. Both subsequent full runs on pinned 6.11.2 passed
(72.487 s, then the final 72.074 s) without changing media or queue-thread code.
The newer host runtime is not validated by this milestone.

Additional checks passed:

- `ruff check .` and bytecode compilation for source/tests/scripts.
- Portable Linux/Windows metadata checks in `scripts/check_branding.py` and
  `desktop-file-validate` on the committed Linux launcher.
- PNG sizes, all ICO payloads and actual Qt ICO decoding at 16–256 px.
- PyInstaller's pure Windows version-resource serializer accepted generated
  metadata and produced the expected UTF-16 name/version fields. On Linux its
  unused Win32 import was supplied a sentinel; no native Windows API or PE
  executable/resource embedding was tested by this check.
- Linux AppRun invoked a harmless fixture executable and forwarded Unicode and
  spaced arguments exactly. This verifies launcher wiring, not a release payload.
- A wheel built with the pinned setuptools backend contained the correct
  distribution/version, both CLI entries, all twelve icon/theme files and notices.
  It was installed only into the temporary venv. An actual installed-wheel
  startup with isolated XDG paths verified title, Qt identity, icon/theme/assets,
  one-time migration marker, readable notices and Cactu log heading. GPU startup
  detection was disabled for that short UI-only smoke; actual GPU conversion is
  established separately by the source suite above.
- Actual Qt UI fixtures were rendered at 100/125/150/200% scale and at 1366×768
  and 1480×960 logical sizes. Review covered empty/populated/selected/running/
  completed queue, audio/subtitles, loudness controls/analysis, preview, Settings,
  About, diagnostics, error and control states. The Settings grid removed the
  HiDPI action clipping. No active purple brand values remain in UI/packaging
  assets; remaining purple references are explanatory historical documentation.

See [Branding](BRANDING.md) for the screenshot gallery and token/migration rules.
Screenshots use synthetic UI jobs; they are not claimed as real full-movie runs.

### Remaining limitations

**No native Windows installer or Linux AppImage was produced.** The actual release
script was invoked and correctly stopped at the existing missing approved FFmpeg
manifest/provenance gate. Approved bundled binaries/license payload remain absent;
ISCC and appimagetool are not available on this host. Metadata/serialization/wheel
checks do not establish Windows installation/upgrade/uninstall, native icon-cache/
taskbar integration, AppImage mounting or a self-contained media runtime. Those
remain release gates. The original icon is implemented; no external art is pending.

Queue persistence and notifications remain unimplemented as documented in the
previous milestone; this rebrand adds neither. Future notifications must use the
central PRODUCT_NAME. Native file dialogs/titlebars follow the operating system,
and native Windows/font/HiDPI behavior still needs platform verification.

## Hardware Acceleration Assistant — 2026-10-27

### Implemented architecture and user behavior

`docs/HARDWARE_ASSISTANT_PLAN.md` was created after inspecting existing detection,
preflight, planner/validation, software selection, queue, Settings, packaging and
tests, before major implementation. The feature adds frozen typed hardware/
distribution/resource/finding models in `models/hardware_diagnosis.py`, with
explicit failure category, severity and responsibility. `hardware/inventory.py`
collects read-only OS evidence; `diagnosis.py` explains it; `resources.py` selects
reviewed static official support guidance; `report.py` creates sanitized reports.
The existing HardwareEncoderDetector and backend-specific initialization probes
remain the sole authority for usability. The existing startup/re-test worker adds
inventory/feature inspection/explanation without re-running a second set of actual
encoder probes. Available capabilities survive explanation/inventory failure.

Settings → Hardware Acceleration opens the persistent assistant entry point;
Hardware Details opens its technical section. The dialog shows overall hardware/
software status, per-device/backend findings, cause/responsibility, recommended
steps, official support, Test Again, explicit Software x264 and optional local
copy/details. A nonmodal Fix/Dismiss banner appears for supported-vendor GPUs only
when no actual backend works. There is no modal startup warning. Any real successful
backend suppresses the global warning, including mixed-GPU systems and intentional
software selection. Dismissal persists a hash of hardware/driver/kernel/runtime/
category/app-major identity, rather than a raw inventory. Recovery or explicit
re-detection clears/reconsiders dismissal.

Test Again refreshes OS evidence, render-node discovery and the existing probe
cache, updates dropdowns and independently validates pending jobs. Opening the
assistant is cached/read-only. Retesting is blocked during active/paused/stopping
queue work, preview or another probe; UI start/preview waits for a current hardware
test to finish. Explicit selections are not silently changed. Use Software x264
requires an editable selected job and leaves other jobs/plans alone. No Auto Prefer
Hardware mode exists or was introduced. Ordinary software plans remain valid.

A failed fresh queue preflight now replaces that failed capability and revalidates
editable pending jobs: jobs that need the same encoder become Requires Attention,
while other valid/software/copy jobs can continue. Test Again success makes those
pending jobs valid without changing their selected engine. Preview preflight adds
Fix beside the existing explicit Software/Cancel actions. Sequential scheduling,
conversion commands, encoder quality/filter paths, audio, loudness, subtitles,
progress parsing, verification and cleanup remain the existing implementation.

### Platform and classification coverage

Windows uses ctypes EnumDisplayDevicesW adapter enumeration and read-only driver
registry values. Structured PCI IDs identify NVIDIA/AMD/Intel; missing version data
is unknown, not proof that a driver is missing/old. Linux scans display-class PCI
entries, DRM render-device associations, bound drivers, device existence/access/mode
and os-release ID/ID_LIKE. All render nodes are considered. Kernel/optional local
PCI labels improve names; no database/utility is downloaded or required. Labels may
identify a shared chip family rather than a unique retail GPU. Inventory failures
remain explicit. No lspci, nvidia-smi, vainfo, WMIC or PowerShell dependency exists.

Mappings preserve NVENC on NVIDIA, AMF on Windows AMD, Linux AMD VAAPI and Intel's
existing QSV/VAAPI paths. Results bind by exact Linux render path. Several matching
same-vendor adapters using a default-device probe get an attribution warning;
overall success is still real, but individual adapters are not falsely marked
usable. Windows headless/compute-only adapters may be absent from session enumeration.

Categories: AVAILABLE, NO_SUPPORTED_GPU, GPU_DETECTED_ENCODER_UNSUPPORTED,
FFMPEG_ENCODER_MISSING, DRIVER_NOT_DETECTED, DRIVER_TOO_OLD_OR_INCOMPATIBLE,
DEVICE_NODE_MISSING, DEVICE_PERMISSION_DENIED, BACKEND_INITIALIZATION_FAILED,
MULTIPLE_GPU_AMBIGUITY, BACKEND_DEVICE_MISMATCH, MISSING_SYSTEM_COMPONENT,
APPLICATION_PACKAGING_ERROR and UNKNOWN. Narrow FFmpeg evidence supports explicit
incompatibility/unsupported/library categories; no GPU/driver minimum-version
database or generic "failed means missing driver" rule is used. Unknown causes stay
unknown. Missing required encoder/filter/API means bundled Cactu build responsibility
or a clearly labeled development runtime issue, with no incorrect driver remedy.

### Guidance, privacy and security

Static official resources cover AMD, NVIDIA and Intel support, Arch/CachyOS video
acceleration, Debian video acceleration, Ubuntu NVIDIA documentation, Fedora docs,
openSUSE graphics setup and Intel's Linux media-stack overview. Guides combine
exact issue with platform/family/vendor; unknown distributions receive generic
information and relevant vendor support without guessed package instructions.
Arch, Debian/Ubuntu, Fedora/RHEL and SUSE families are recognized. Fedora/SUSE
resources are documentation/setup entry points, not certified installation recipes.
Review metadata is **2026-10-27**. Some distribution sites blocked automated retrieval;
no current package versions/commands are asserted from those pages.

**No installation/package commands are shipped.** Every optional command list is
empty. There is no driver download, privileged helper, password prompt, installer,
sudo/package-manager invocation, permissions/groups/kernel/bootloader/repository
modification or automatic external action. Official pages open only from explicit
registered HTTPS buttons through QDesktopServices; arbitrary system/UI strings
cannot supply links. Browser-launch failure is handled, though a remote 404 or
access challenge cannot be detected without fetching the page, which Cactu does
not do. No issue URL was invented and no telemetry/upload was added.

Copy Diagnostics writes the local clipboard only. Its bounded report includes app/
OS/distro/runtime/GPU/driver/backend/encoder/device access/probe command/exit/category
and a relevant error excerpt. It scrubs home/absolute media paths, personal media/
subtitle names, error URLs and control characters while preserving useful graphics
device paths. Reports should still be reviewed before public sharing; the sanitizer
cannot promise removal of arbitrary identifiers in third-party driver prose.
New diagnosis logs record local lifecycle, device/backend results/categories and
guide IDs; no conversion-job contexts are appended to assistant exports.

### Tests and verification

The two new test modules add **31 tests** to the previous 103. They cover synthetic
Linux sysfs/DRM/distro/nodes/access, optional PCI labels, missing inventory, Windows
native API/registry-call boundary mocks, vendor/driver evidence, every failure
family, mixed/ambiguous adapters, any-success aggregation, node rediscovery,
cache refresh, guide priorities/official HTTPS registry/empty commands, sanitized
report/device paths, safe browser failure, local clipboard, dismissal identity,
asynchronous Test Again failure→success, preserved explicit backend/software
choices, queue/preview lock and failed-preflight pending-job invalidation/recovery.
The existing media suite remains intact.

Final complete gate:

```bash
VIDEO_CONVERTER_HARDWARE_TEST=1 PYTHONPATH=src /tmp/cactu-hardware-venv/bin/python -X faulthandler -m unittest discover -s tests -q
```

**All 134 tests passed in 73.857 s, with no skips.** Earlier full gates also passed
while refinements were being made. The final gate includes real RX 7700 XT/VAAPI
queue/preflight, loudness, manual gain, embedded/external subtitle burns and previews,
plus existing single-file/software/copy/planning/process/progress/cleanup/verification
regressions. Expected synthetic build/failure messages and offscreen Qt warnings
are intentional fixtures, not unhandled errors.

Environment: Python **3.14.8**, pinned PySide6/Shiboken/Qt **6.11.2**, psutil **7.2.2**,
FFmpeg/FFprobe **n9.0.2** from the development host; pinned Qt/ruff installed into a
temporary isolated venv, without changing system packages. `ruff check .`, source/
test/script bytecode compilation and the existing branding metadata smoke passed.
The host's unpinned Qt 6.12 remains outside the validated dependency pin, as recorded
in the previous milestone.

A separate real diagnosis check on the user's known **RX 7700 XT**, CachyOS/Arch,
bound **amdgpu**, and **/dev/dri/renderD128** passed actual initialization and reported
AVAILABLE with no banner eligibility. The inventory may label the shared Navi 32
PCI 1002:747e family rather than claim a uniquely identified RX 7700 XT. A sanitized
[actual report](assets/hardware-assistant-runtime.txt) and
[actual available-state render](assets/hardware-assistant-actual-amd.png) record the
final host check. Host device access was needed because the command sandbox can
hide /dev/dri. Device permissions were read only, never changed.

Synthetic UI fixtures cover missing-node, available, packaging error, Windows
NVIDIA, mixed GPUs, expanded technical details and the nonmodal banner. They were
rendered/reviewed at a 1366×768 main window and 100/150% Qt scale, retaining the
charcoal/cactus theme with amber warnings, red build errors, success text/icons and
scrollable content. Windows fixture renders are Linux Qt simulations, not native
Windows captures. See [Hardware Assistant](HARDWARE_ASSISTANT.md) for the gallery.

### Remaining limitations

Physical NVENC, AMF, Intel QSV/VAAPI, native Windows adapter enumeration/registry,
Windows driver repair and broad laptop/hybrid/multiple-same-vendor configurations
were not tested on real hardware. Windows/session enumeration and default-device
adapter attribution remain documented limitations. GPU marketing labels and driver
versions depend on available OS data; labels can be generic/shared and versions
may be absent. Error signatures are bounded heuristics; unexplained failures do
not become confident driver diagnoses. Permission evidence is for the process's
current session/container. Driver repair itself is outside the application.

No package recipes, command execution, remote issue integration, automatic driver
monitoring, Auto Prefer Hardware policy or driver installation was introduced.
Official page content/availability can change and should be maintained in the
central resource registry. The existing missing approved FFmpeg provenance,
licenses and native installer/AppImage verification gates remain open; no new
self-contained release artifact is claimed by this feature.

## Public beta release hardening — 0.1.0-beta.1 (2026-11-01)

**Status: native Windows/Linux builds and automated package smoke verified; public
binary release blocked.** No beta tag or GitHub release has been created. Owner decisions
are recorded: repository `https://github.com/drrrrigo/cactu-video-converter`, Cactu
original source **GPL-3.0-or-later**. Root LICENSE and package metadata reflect that
decision. Third-party redistribution approval remains separate and incomplete.

### Architecture and release tooling

The existing queue, planner, media processing, preview, loudness and FFmpegRunner
remain in use. Release work adds a hash-verified build-time FFmpeg staging service,
exact capability/version/configuration checks, native package builders, frozen
application smoke tests, license inventory collection, generated checksums and
fail-closed distribution/publication gates. Frozen startup never falls back to
system FFmpeg/FFprobe. No runtime downloads or telemetry were added.

One source version provides display/tag `0.1.0-beta.1`, Python package `0.1.0b1`
and Windows numeric `0.1.0.1`. ONEDIR/Inno Setup, portable ZIP and AppImage metadata
use it. Startup checks writable configuration/temp space and essential bundled
runtime capabilities. Unexpected Python exceptions retain local traceback logs
and show a generic recovery dialog with diagnostics/log-folder/issue actions.
General diagnostics omit media/job payloads and include version/platform/runtime
and recent error category. About provides explicit GitHub, issue and license links.

An output-safety audit found a race between destination existence checking and
`os.replace`. Finalization now uses an atomic no-replace rename (or safe hard-link
fallback) unless overwrite was explicitly authorized. A regression verifies that
a concurrently created destination survives and the partial remains available for
cleanup. Inputs and external subtitles are not modified by this change.

CI is defined for native Ubuntu 22.04 and Windows Server 2025 with Python 3.14.7,
full nonphysical tests, lint, branding and source/history scans. Candidate builds
test actual frozen ONEDIR/ZIP/installer/AppImage payloads with PATH empty. Binary
upload is blocked until exact dependency/source licensing is approved, including
uploads to public Actions artifacts. A beta tag promotes the same successful
candidate-run bytes from the exact same commit, retests them natively, checks
external manual evidence against all three artifact hashes and generates
SHA256SUMS before creating a pre-release. It does not rebuild after manual testing.
The `public-beta` GitHub environment requires owner review and accepts beta tags.
Private vulnerability reporting is enabled. License and final publication approvals
remain false. The bounded source/privacy audit has been approved after the current
tree/history and documentation-image checks.

### Exact inputs and local environment

Pinned versions: Python **3.14.7**, PySide6/Qt/Shiboken **6.11.2**, psutil **7.2.2**,
PyInstaller **6.16.0**, hooks **2025.9**, ruff **0.13.3**, appimagetool **1.9.1**,
Inno Setup **7.1.1**. Direct/transitive Python dependencies and native packager
downloads are recorded in `release/requirements.txt` and `release/toolchain.json`.
The AppImage type-2 runtime has its own immutable asset ID/source commit and hash;
appimagetool cannot silently fetch a moving runtime during packaging.

FFmpeg and FFprobe come from BtbN dated `autobuild-2026-11-01-12-49`, identity
**n9.0.2-42-gd7643a0fe3-20261101**. Both platforms' archive/member/license hashes,
exact configure strings and source recipe are in `vendor/ffmpeg/manifest.json`.
Linux execution verified coherent FFmpeg/FFprobe, x264/AAC/subtitles/loudnorm/
alimiter/format/mux/demux capabilities and encoder tables. The previously suggested
Martin Riedl Linux build explicitly enables nonfree and was excluded.

The local native candidate was built on CachyOS/Arch x86_64 with CPython **3.14.8**
in a clean temporary venv using pinned Qt/dependencies. The Python patch differs
from the release pin: build metadata marks this explicitly, and this candidate is
not the final public release. Host graphics tests used the existing RX 7700 XT,
amdgpu and VAAPI render node without modifying drivers or permissions.

### Completed verification

The entire existing/new suite passed: **148 tests in 65.786 seconds**, including
real RX 7700 XT/VAAPI tests with `VIDEO_CONVERTER_HARDWARE_TEST=1` and the staged,
verified FFmpeg pair. New release tests cover version mapping, mandatory capability
failure, archive/hash/path validation, generated checksums, blocked licensing,
exact tested commit/hash promotion, writable startup, frozen no-PATH fallback,
diagnostic privacy, atomic no-overwrite, exception recovery and reuse of an existing
job when preanalyzed media uses an equivalent path alias. Existing queue,
preview, loudness, audio gain/clipping, subtitle, software/hardware planning,
progress, pause/cancel, verification and cleanup regressions remain intact.
Ruff, bytecode compilation, branding checks and isolated `pip check` pass.
Current source and all available Git history scans report **zero findings**;
OCR of all 24 published documentation screenshots also found no personal labels.
This is a bounded pattern/OCR scan plus artifact review, not a claim of exhaustive
security certification. Native GitHub CI results are recorded separately below;
local Linux success alone does not establish native Windows success.

Actual frozen ONEDIR and AppImage smoke tests passed with PATH empty. They start
MainWindow offscreen, locate bundled binaries, create synthetic MKV/audio/external
subtitles, convert through the existing pipeline and verify MP4/H.264/yuv420p/AAC,
Faststart, duration, burned subtitle mode, normal exit and unchanged source.
The internal AppImage is approximately **203 MiB**. Build metadata and smoke JSON
are under gitignored `dist/candidate`; these are local evidence, not public assets.
The final local packaging run includes the startup-construction error catch,
canonical job-path lookup fix and recovered Qt license payload. It is still a private
candidate from the development workspace, with a Python patch mismatch and no
approved release-commit attestation.

### Remaining release gates and risks

- Exact FFmpeg linked-component corresponding sources/notices are not archived or
  approved. Selected archives supply a GPL text, which is insufficient to close the
  entire static dependency audit. Dated provider inputs may expire without a mirror.
- The exact Qt 6.11.2 wheel manifests provided no collected license text files;
  eight license texts were subsequently recovered from the exact official PySide
  source commit and added with provenance. Qt/module/third-party source and notice
  closure, native ELF/DLL/plugin inventory, Python third-party obligations and
  AppImage/Inno runtime/stub review remain open.
  The Python 3.14.7 combined license text is included, but audit completion is not
  inferred from it. `RELEASE_LICENSE_AUDIT.md` records evidence and missing items.
- Clean Windows 11 installer/portable/manual/uninstall and a distinct Linux desktop
  manual test have not been performed. Server CI and offscreen smoke cannot stand
  in for those required tests. No physical NVIDIA/Intel/Windows AMD test is claimed.
- Native Windows Setup/portable builds and automated install/convert/uninstall
  smoke pass on Server 2025. This does not replace clean Windows 11 interactive
  testing. Signing is optional; these candidates are unsigned, with no signing
  certificate or public-trust claim.
- No complete approved three-artifact set, manual hash attestation, final checksum
  file, public beta tag or pre-release exists. Publication and license approvals
  remain false. Queue/preview/hardware behavior and other existing limitations are
  documented in their respective feature reports and KNOWN_ISSUES.md.

README, installation, known issues, security, contributing, issue forms, release
notes, build/packaging/runtime docs, architecture/testing/review guides and the
release checklist were updated. Normal conversion remains offline; external links
open only through explicit user actions. Public beta completion must wait for the
remaining licensing and manual exact-artifact gates.

The complete source was pushed to the owner-provided GitHub repository using the
owner's working SSH credential, preserving initial README commit `55e3d27`. The
HTTPS OAuth credential lacks workflow scope; no scope restriction was bypassed or
token exported. The primary supplied checkout has an empty read-only `.git`, so
publishing used a separate temporary clone.

Native Ubuntu 22.04 / Python 3.14.7 source CI passed at `fa80b39`:
[run 41348951474](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41348951474),
**147 tests in 41.077 seconds, three optional physical-GPU skips**. Its native Linux
candidate job also passed 147 tests (42.668 seconds, same skips), built the AppImage
and completed frozen smoke tests before failing at the intentional unapproved
license gate in [candidate run 41348963526](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41348963526).
No candidate binary was uploaded. Windows native validation found that the pinned
build also exposes h264_vaapi; the manifest now records all four observed H.264 GPU
encoder identifiers without adding a Cactu Windows VAAPI backend. The first Windows
full suite then exposed a real canonical-path lookup issue in programmatic media
loading, now fixed with a regression test. Synthetic Linux device paths, filesystem
fixtures, canonical media paths and application theme setup were made portable in
tests. The readability regression now verifies every action fits its native size
hint inside a 640-logical-pixel dialog, rather than assuming all platform fonts fit
the former 400-pixel fixture.

Final native source matrix at `ccb4e33` is **green**:
[run 41350221215](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221215).
Ubuntu 22.04 image `20261025.340.1`: **148 tests / 49.691 s / 3 optional GPU skips**.
Windows Server 2025 image `20261021.278.1`: **148 tests / 69.554 s / 3 optional GPU skips**.
Both use Python 3.14.7, verified staged FFmpeg, pinned dependencies, lint, branding
and history scan. These tests do not substitute for manual Windows 11/desktop UX.
The latest local AppImage, including the canonical-path fix, passes both frozen
smoke checks; SHA-256 `cef62dfbc1bced448d663aa668a1ed29ad6cb4c726bde6e8f5d781db9ff9d8bb`.
It retains the documented local Python patch mismatch and is not a release asset.

### Native package verification and publication block

[Candidate run 41350221053](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221053)
at `ccb4e33` built all three required package formats natively with Python 3.14.7.
The Windows job passed 148 tests in 39.761 seconds (3 physical-GPU skips), validated
the exact FFmpeg pair and hash-pinned Inno Setup, built ONEDIR, created/extracted
the portable ZIP, compiled Setup and installed/converted/uninstalled it. Actual
frozen ONEDIR, extracted portable and installed application smoke all passed with
PATH empty. Setup compilation completed in 68.500 seconds. The Linux job passed
148 tests in 31.754 seconds (same skips), validated fixed appimagetool/runtime,
built AppImage and passed ONEDIR/AppImage frozen smoke.

Native candidate filenames produced:

- `CactuVideoConverter-Setup-0.1.0-beta.1.exe`
- `CactuVideoConverter-Portable-0.1.0-beta.1.zip`
- `CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage`

Both native jobs then **failed only at Verify distribution eligibility**, with
`Binary distribution blocked: exact dependency/license/source audit not approved`.
This is the intended fail-closed publication result, not a package/test success
claim for the overall release workflow. The artifacts were not uploaded and the
cloud runner files are not a retained, approved release-candidate set. No combined
final SHA256SUMS or final tag was created. After source/license closure, rebuild a
candidate from the final reviewed commit, retain it, perform the required manual
tests and promote those exact bytes through the protected release workflow.
