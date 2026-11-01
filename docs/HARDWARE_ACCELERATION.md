# Optional hardware H.264 encoding

## Scope

Hardware acceleration here means **encoding H.264 on a supported GPU**. FFmpeg
still decodes and renders ASS/SRT subtitles in software. This preserves the
existing subtitle workflow and avoids a platform-specific zero-copy filter
pipeline. Software x264 remains available and is the default.

The Web Compatibility / Kosmi target remains MP4, H.264 8-bit 4:2:0, AAC when
audio is present, and Faststart. If the source video is already H.264/yuv420p
and no subtitle is burned, the planner copies it even when a hardware engine
is selected. A subtitle burn forces encoding.

## Backends and platforms

| UI name | FFmpeg encoder | Platforms | Input path |
| --- | --- | --- | --- |
| Software — x264 | `libx264` | Windows, Linux | Software yuv420p |
| NVIDIA NVENC | `h264_nvenc` | Windows, Linux | Software yuv420p |
| AMD AMF | `h264_amf` | Windows | Software yuv420p |
| VAAPI Hardware Encoder | `h264_vaapi` | Linux | Software NV12 → selected-device `hwupload` |
| Intel Quick Sync | `h264_qsv` | Windows, Linux | Windows: software NV12; Linux: selected-device upload |

On Linux, VAAPI labels include a detected AMD/Intel/NVIDIA vendor where the
DRM sysfs vendor ID is readable. Every visible `/dev/dri/renderD*` node is
probed individually. A selected device path is retained in the conversion
plan. There is no permanent renderD128 assumption.

## Detection and fallback

After the window appears, a Qt worker checks FFmpeg's encoder table and runs a
three-frame initialization encode for each candidate/device. The probe uses
the same subtitle → 8-bit format → upload path as conversion. It tests all
three quality profiles plus a 10-bit software-frame input and captures errors.
Results are cached for the session.
Only successful hardware choices appear in the Encoding Engine list. Settings
contains Hardware Diagnostics and Re-detect Hardware.

A fresh probe runs asynchronously before an explicitly selected hardware
conversion starts. If it fails, the user can choose Software — x264. A failure
after conversion starts removes the partial output and offers an explicit
**Retry with Software Encoding** action. The app never silently restarts a
long movie. GPU drivers are supplied by the operating system, not the app.
No external GPU utility is needed for normal detection. No FFmpeg download is
performed at runtime.
Pause/resume and cancellation use the existing process controls; pausing FFmpeg
may keep GPU resources allocated until conversion resumes or ends.

## Quality mapping

Quality labels are **backend-specific controls**, not equal numerical quality
claims. The following options were checked against the available FFmpeg 9.0.2
encoder help in the Linux development environment. Bundled builds must be
validated separately. Other x264 settings retain CRF 18 and preset medium.

| Backend | High Quality | Balanced | Fast |
| --- | --- | --- | --- |
| NVENC | `-preset p6 -tune hq -rc vbr -cq 19 -b:v 0` | `p4`, CQ 23 | `p2`, CQ 27 |
| AMF | `-quality high_quality -rc cqp -qp_i 19 -qp_p 21 -qp_b 23` | balanced, QP 23/25/27 | speed, QP 28/30/32 |
| VAAPI | `-rc_mode CQP -qp 20` | QP 24 | QP 28 |
| QSV | `-preset slow -global_quality 20` | medium, 24 | fast, 28 |

Each hardware backend also requests H.264 High profile. These values target
good viewing quality with reasonable size. They are not calibrated to x264
CRF 18, and actual visual quality and speed depend on GPU and driver.

## Subtitle and 10-bit path

The selected subtitle stream is extracted to a fixed temporary basename, so
filter arguments never contain an arbitrary user path. The filter order is:

`subtitles=subtitle.ass` → software `format=yuv420p` (NVENC/AMF), or
`format=nv12` → device `hwupload` (VAAPI/Linux QSV).

Windows QSV receives software NV12 frames. FFmpeg performs software decode of
HEVC Main 10; the format step converts frames to 8-bit before hardware H.264
encoding. The runner then probes the partial MP4 and requires MP4/H.264,
yuv420p and AAC when audio was selected before finalizing it.

## Testing and limits

Pure tests cover registry, capability models, two-stage detection, per-device
selection, all quality mappings, backend commands, filter order, exact stream
mapping, Faststart, no-GPU behavior, copy priority and the UI summary. Set
`VIDEO_CONVERTER_HARDWARE_TEST=1` on a GPU machine and run
`python -m pytest -m hardware` for an optional short subtitle-burn conversion.

The Linux host has an AMD RX 7700 XT at `/dev/dri/renderD128`. A physical
VAAPI test passed with a short HEVC Main 10 + FLAC + ASS input and verified
H.264/yuv420p/AAC output with the subtitle burned. The original 128x72
initialization probe falsely rejected this GPU because its VAAPI encoder
requires at least 128 pixels of frame height; the probe now uses 256x144.
Windows AMF, Windows/Linux QSV, and NVENC still need native GPU tests with the
final bundled builds. The Codex command sandbox may hide `/dev/dri`; launch
the desktop app from a normal host terminal to let its FFmpeg probe use the GPU.
The previous release packaging gates remain open; no self-contained installer
has been produced. Embedded subtitle fonts are still not extracted.

## Hardware Acceleration Assistant

Settings → Hardware Acceleration explains GPU/driver/render access, missing FFmpeg
capabilities and failed initialization, with official vendor/distribution guidance.
Test Again refreshes devices/probes and pending-job validation without a restart.
The existing Hardware Details action opens its sanitized technical section.
A nonmodal Fix/Dismiss banner appears only for detected supported-vendor GPUs
when no backend works. One working backend suppresses the global warning.

The assistant does not install drivers or execute package-manager/privileged
commands. It distinguishes bundled application capability errors from development
runtime and system issues. Explicit hardware choices are retained; Use Software
x264 is a deliberate per-job action. See [Hardware Assistant](HARDWARE_ASSISTANT.md)
for guide coverage, privacy, Windows detection and known limitations.
