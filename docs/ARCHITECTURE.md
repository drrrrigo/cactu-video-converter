# Architecture

Input paths → UUID ConversionJobs in ConversionQueue → bounded asynchronous
FFprobe pool → typed MediaInfo and per-job settings/plans → QueueController →
existing ConversionRunner → progress, verification, atomic finalization and
cleanup → next job.

`models/media.py` separates global FFmpeg stream indexes from per-type ordinals.
`media/ffprobe_service.py` is the sole JSON parser. `presets/web_kosmi.py` creates
settings rather than commands. `conversion/planner.py` decides copy versus encode.
`ffmpeg/command_builder.py` is the sole argument builder. `ffmpeg/runner.py` owns
the subprocess and temporary workspace. `ffmpeg/runtime.py` alone resolves
executables. `ui/main_window.py` presents typed plans and routes user actions.

Hardware encoding extends this path through `models/encoder.py` (identity and
quality), `ffmpeg/encoders.py` (backend registry and command/filter options),
`ffmpeg/hardware_detector.py` (two-stage probes), and
`ui/hardware_worker.py` (asynchronous detection). The plan carries the exact
backend and device; the runner does not choose an encoder.

External and embedded burn sources share `models/subtitle.py` identities and
`ffmpeg/subtitle_pipeline.py` preparation. The runner stages or extracts into
one workspace, optionally preflights an external file with libass, then sends
the same safe basename through `ffmpeg/command_builder.py` and the chosen
encoder backend. See [external subtitles](EXTERNAL_SUBTITLES.md).

Manual volume gain is typed in `models/audio.py`; the planner attaches an
`AudioProcessingPlan` and disables audio copy only when filtering is required.
`ffmpeg/audio_filters.py` generates the gain and optional limiter chain for
the one mapped audio track. Video copy remains independent. See
[audio volume](AUDIO_VOLUME.md).

`models/preview.py` records an immutable original conversion snapshot and its
derived segment execution plan. `conversion/preview_planner.py` validates times,
source signatures and preview encoding availability. The existing builder and
runner receive this optional preview context; full conversion uses no segment
arguments. `services/preview_store.py` owns generated session outputs, while
`ui/preview_dialog.py` and `ui/main_window.py` handle options, job locking and
playback. See [Quick Preview](QUICK_PREVIEW.md) for timestamp/copy policies.

The current UI class is the primary integration point. Further decomposition
into reusable panels would improve reviewability as the interface grows.

## Loudness normalization

`models/loudness.py` holds validated targets, presets, measurements and result
reports. `models/audio.py` enforces exclusive manual/normalization modes and
types channel-layout, loudnorm and final resample filters. The planner disables
audio copy for normalization independently of video copy.

The runner first uses `ffmpeg/loudness.py` to build a full-track audio-only null
pass and parse mixed stderr JSON. `services/loudness_cache.py` caches only valid
complete measurements by source, track, targets, channel/rate policy and runtime.
The runner resolves a separate `AudioProcessingPlan` with those measurements;
`ffmpeg/audio_filters.py` generates measured loudnorm arguments through the
existing command builder. The original ConversionPlan/PreviewPlan snapshot is
never mutated. Subtitle staging and partial output allocation follow analysis.
Stage signals reset progress and elapsed/ETA; cancellation and pause use the
same process lifecycle for analysis and conversion. See
[loudness normalization](LOUDNESS_NORMALIZATION.md).

## Batch orchestration

`models/job.py` and `models/queue.py` define job/attempt records, explicit states,
stable identity and ordered operations. `services/queue_controller.py` owns the
one-at-a-time scheduler and controls; it never constructs FFmpeg arguments.
`services/probe_pool.py` limits imports to two FFprobes. `services/batch_settings.py`
copies scalar intent, matching destination streams instead of copying indexes.
`ui/queue_view.py` handles file versus internal move MIME; `ui/queue_panel.py`
handles selection binding and bulk presentation. Preview stores live outside
the job model, keyed by job UUID. The shared runner remains the only conversion
executor, including loudness, subtitle preparation, backend filters, verification
and cleanup. See [Batch / Queue](BATCH_QUEUE.md) for states and policies.

## Product identity and presentation

`product.py` centralizes Cactu names/slug/executable/description; `__init__.py`
retains the version. `ui/theme.py` supplies shared charcoal/green design tokens,
QSS states and the link/selection palette. Custom queue painting imports these
tokens. `ui/branding.py` resolves source/wheel/frozen assets and builds the
Settings/About presentation. Startup sets Qt identity/icon, applies the theme
and runs the one-time allowlisted migration before creating MainWindow.
`services/settings_migration.py` preserves new preferences and leaves the old
store intact. `scripts/branding_metadata.py` derives native file/version metadata.
The internal `video_converter` package and all media pipeline boundaries remain
unchanged. See [Branding](BRANDING.md).

## Hardware explanations

The existing encoder detector remains the usability authority. The same startup/
re-test worker adds `hardware/inventory.py` OS evidence and `diagnosis.py` typed
interpretation, then sends immutable results to the UI. `models/hardware_diagnosis.py`
separates device/runtime evidence, category, responsibility and severity.
`resources.py` chooses static official guidance; `report.py` creates bounded
sanitized clipboard diagnostics. The assistant dialog/panel present cached results,
re-test state and persistent banner identity without running OS installation work.
Fresh queue preflight can invalidate an encoder and revalidate pending jobs; the
planner, command builder, encoder options and sequential conversion runner are
reused. See [Hardware Assistant](HARDWARE_ASSISTANT.md) for the platform boundaries,
cache, security and multi-adapter uncertainty.

## Beta package/startup boundary

The frozen entry point checks config/temp access and the exact bundled runtime;
release-only essential capability tables are shared with build verification. The
source development fallback stays explicit. ErrorReporter logs uncaught exceptions
and offers local diagnostics/log-folder/issue recovery. General reports exclude
media/job payloads and use the established sanitizer. The dedicated release smoke
entry point exercises the existing conversion pipeline with synthetic inputs.

A narrow output_commit helper uses atomic no-clobber publication to eliminate the
previous check-then-replace race; verified output replaces an existing target only
when explicitly authorized. Build tooling, license/source/manual gates and exact
candidate promotion live under scripts/ and release/. No updater, telemetry or new
media-processing workflow was introduced.
