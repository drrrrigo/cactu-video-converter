# Video Converter implementation plan

Historical plan written under the former product identity. Its purple accent
description and supplied mockup are superseded by [Cactu branding](BRANDING.md).
Technical implementation stages below remain useful context.

## Scope and stages

1. Build typed media and conversion models, FFprobe parsing, compatibility analysis,
   presets, planning, validation, and FFmpeg argument generation. Test these without Qt.
2. Build a responsive PySide6 interface following the supplied dark desktop mockup.
   File probing and conversion run asynchronously. The UI displays the actual plan.
3. Add subtitle preparation, process control, progress, cancellation, diagnostics,
   settings, logging, and safe output finalization.
4. Add pinned binary acquisition, platform packaging, CI, documentation, and
   release smoke tests. Verify release artifacts on both target operating systems.

Stages 1–3 have source implementations and Linux generated-media tests. Stage 4
has a fail-closed staging script, packaging configuration, CI source checks,
and documentation. The manifest values, native release builds, and packaged
smoke tests remain open.

The optional hardware H.264 extension is described in
[HARDWARE_ACCELERATION_PLAN.md](HARDWARE_ACCELERATION_PLAN.md). Its source and
GPU-free tests are implemented; physical GPU, bundled-build, and native
packaging verification remain open.

## Architecture and responsibilities

`models` holds immutable probe records and typed editable conversion settings.
`media` parses FFprobe JSON and evaluates practical browser compatibility.
`presets` creates settings; it never returns a prewritten command.
`conversion` validates settings and plans stream copy or encoding decisions.
`ffmpeg` resolves and verifies binaries, prepares subtitles, builds argument lists,
parses machine progress, and controls processes. `services` handles logs, settings,
and temporary files. `ui` contains only presentation and signal wiring.

Data flows from input path → FFprobe → MediaInfo → compatibility/UI → settings →
validation → ConversionPlan → command builder → runner → progress/UI → final file.
FFmpeg commands always use argument arrays and never a shell.

## FFmpeg integration and process management

A single runtime locator resolves adjacent packaged binaries from the application
bundle. An explicit development option may use host binaries. Release mode has no
host fallback. Startup checks matching 9.0.2 versions and required encoders and
filters. QProcess keeps probing and conversion off the UI event loop. Conversion
uses `-progress pipe:1`; stderr is retained for diagnostics. Pause/resume uses
psutil process suspension if verified on both platforms, otherwise the control is
disabled with an explanation. Cancellation requests graceful stop, then terminate,
then kill with bounded timeouts. Temporary output is moved into place only after
successful completion; existing outputs require explicit overwrite approval.

## Conversion pipeline and presets

The Web Compatibility / Kosmi preset supplies MP4, H.264, CRF 18, medium,
yuv420p, AAC 256 kbps, source channels, and Faststart. The planner copies already
compatible streams and encodes only when necessary. Subtitle burn always encodes
video. Manual changes mark the settings Custom. Validation rejects impossible
codec/container/stream selections before process launch.

## Subtitle handling

Each subtitle retains its global stream index and subtitle ordinal. Selected text
subtitles (ASS, SSA, SRT) are extracted to a safe temporary filename before
rendering, avoiding user path interpolation in FFmpeg filter syntax. Optional font
attachments can be extracted into the same workspace and passed to libass.
Bitmap subtitle burn is rejected clearly. Selectable MP4 subtitles use mov_text
and warn that ASS styling is lost. Only the chosen stream is mapped.

## UI architecture

The main window has input and source analysis, a preset and actual output summary,
four settings cards, and progress controls. Central theme tokens provide navy
surfaces, purple accent, green success, amber warning, and red cancel states.
Layouts scroll at smaller window sizes and rely on Qt scaling. The user can browse
or drop a file; probe results populate audio/subtitle choices. Settings and About
are separate dialogs. All visible text is English.

## Packaging and bundled binaries

Build on Windows 11 x86_64 and Linux x86_64 separately. CI downloads a pinned
9.0.2 archive per platform, verifies SHA-256, extracts ffmpeg and ffprobe into
`vendor/ffmpeg/9.0.2/<platform>`, validates capabilities, then runs PyInstaller
ONEDIR. Windows wraps ONEDIR with Inno Setup per-user installer; Linux packages
an AppImage, with a portable directory fallback. Neither runtime downloads files.
Provider, archive URL, checksum, build configuration, and license files must be
recorded and verified before release. Release jobs fail when any are missing.

## Testing

Unit tests cover parser/indexing/labels, compatibility, preset, planner,
validation, builder, progress/ETA, runtime lookup, and path/overwrite behavior.
Generated short FFmpeg fixtures cover remux, audio transcode, subtitle burn,
Unicode paths, cancellation, and missing runtime where tooling is available.
CI runs unit tests on Windows and Linux and smoke tests the bundled executables.

## Known limitations and review gates

Browser support varies by browser/device; the analyzer reports broad suitability,
not guaranteed playback. Bitmap subtitle burn and HDR tone mapping are outside
version 1. Font fidelity depends on available attachments and fonts. No release
artifact can be called self-contained until checksums, license review, both native
builds, and packaged smoke tests have passed. Update this plan when implementation
decisions change.
