# Hardware H.264 encoding implementation plan

## Existing path

`ConversionSettings` → validator → `ConversionPlan` → command builder chooses
stream copy or libx264. The runner owns QProcess, subtitle extraction, progress,
pause/resume, cancellation and output finalization. The Web/Kosmi preset leaves
the video codec on Auto so compatible H.264/yuv420p is copied.

## Backend model

Add typed backend and quality enums plus an encoder selection containing a
backend ID and optional device identity. A registry owns backend-specific
initialization, software-frame/filter requirements and quality arguments.
`ConversionPlan` records the resolved selection. The command builder consumes
that selection; the runner remains independent of encoder type.

Software x264 remains the default and always available. Explicitly selectable
hardware backends are NVENC (Windows/Linux), AMF (Windows), VAAPI (Linux), and
QSV (Windows/Linux). Auto-prefer-hardware is omitted for now so no device is
chosen without the user's knowledge. Stream copy remains the first planning
decision regardless of the selected encoding engine.

## Capability detection

An asynchronous Qt worker invokes a detector after the window appears. The
detector first checks `ffmpeg -encoders`, then encodes a few synthetic frames
with each candidate and the same backend setup/filter path used in conversion.
The probes cover all quality modes, subtitle rendering, and a 10-bit input
frame converted to the backend's 8-bit H.264 format.
It captures the initialization error, caches results for the app session and
shows only successful options. Linux VAAPI and QSV candidates come from all
visible `/dev/dri/renderD*` nodes; no fixed renderD128 assumption. The detector
may label VAAPI devices using Linux sysfs vendor IDs when available. A manual
re-detect action refreshes the cache. Normal use does not require nvidia-smi,
vainfo, lspci or other vendor utilities.

An explicit hardware choice must match a currently available capability before
planning. Before launching, the selected backend receives a fresh short probe
in a worker; failure offers a switch to software. Once conversion starts,
failure never triggers an automatic full-file retry. A retry with software is
offered to the user. No GPU driver is bundled.

## Quality and media path

Hardware quality is High Quality, Balanced, or Fast, independent of x264 CRF.
Each adapter maps those labels to options confirmed by FFmpeg 9.0.2 encoder
help. x264 retains CRF 18 and medium. Hardware output remains H.264 8-bit 4:2:0
in MP4, with AAC/Faststart unchanged. Software decoding and libass subtitle
rendering remain in place. NVENC/AMF accept software yuv420p; QSV accepts
software NV12; VAAPI needs selected-device initialization plus `format=nv12,
hwupload`. Subtitle rendering precedes conversion/upload. Probes exercise the
same path with a tiny source.

## UI and persistence

Add Encoding Engine to the Video card. Show x264 immediately, then add only
successful hardware capabilities after asynchronous detection. Show CRF/preset
for software and quality mode for hardware. The output summary names the
resolved backend or says video is copied. Persist only backend ID as a
preference; a missing device is never silently restored as valid. Diagnostics
show found encoders, tested devices and failure reasons.

## Packaging, tests and limitations

No runtime download is added. Bundled release builds must have their actual
hardware encoder lists recorded; hardware availability still depends on host
GPU/driver. Unit tests cover registry, selection, quality mappings, commands,
filter order, copy priority and fallback. Optional hardware tests run only on
machines with GPUs and verify output, subtitle burn and process control.
The current Linux development environment has no render node; real VAAPI/AMF/
NVENC/QSV operation cannot be claimed here. Windows builds and GPU hardware
tests remain release gates.
