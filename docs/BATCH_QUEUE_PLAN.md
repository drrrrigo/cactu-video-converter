# Batch conversion and queue implementation plan

## Existing architecture inspected

`MainWindow` currently owns one MediaInfo/settings/plan, a single asynchronous
FFprobe, a ConversionRunner and one PreviewStore. It binds settings directly to
widgets and performs GPU preflight using HardwareDetectionWorker/QThread.
The planner/validator produce immutable ConversionPlans, command_builder and
encoder adapters generate arguments, and ConversionRunner owns the QProcess,
audio-only loudness pass/cache, subtitle preparation, partial output, FFprobe
verification and atomic finalization. Existing progress parsing, audio filter
models, preview derivation, runtime discovery, QSettings and rotating logging
remain reusable. The 65-test baseline includes physical AMD VAAPI checks.
Release packaging/binary provenance and native Windows testing remain open;
the current working environment uses explicitly selected development FFmpeg.

## Domain and orchestration

Add ConversionJob with UUID identity, normalized input path, its own immutable
settings and current plan, validation warnings, explicit status, progress,
timestamps, immutable executed snapshot, error and retained command/log/loudness
diagnostics. No live Qt objects belong in the job model. Same basename from
different directories is supported; an existing resolved path is skipped.

ConversionQueue owns ordered jobs, mutation restrictions and queue state.
QueueController owns scheduling, per-job validation, terminal transitions,
retries and aggregate counts. It calls the same ConversionRunner sequentially;
it does not generate FFmpeg commands. Exactly one full conversion/preview may
own the runner. Runner terminal signals occur after verification/cleanup.
Scheduling the next job uses a queued event-loop callback, never recursion.

Job states: ANALYZING, READY, WAITING, RUNNING, PAUSED, FINALIZING, COMPLETED,
FAILED, CANCELLED, INVALID. Active snapshots are locked; terminal jobs retain
their history and require explicit Requeue/Retry to run again. FAILED is not
automatically retried. Queue states: IDLE, RUNNING, PAUSE_REQUESTED, PAUSED,
STOPPING, COMPLETED. Pause Queue allows the current file to finish; Pause
Current suspends its process. Cancel Current cleans it then advances; Stop
Queue cancels it and retains pending jobs, with a UI confirmation. Individual
failure records diagnostics and advances. Retry revalidates once per user action.

## Import and validation

Centralize asynchronous FFprobe in a pool of two QProcesses. Validate readable
regular files before probing, accept candidates regardless of extension, reject
non-video/invalid results per job. Callback identity is the stable UUID; removed
jobs and stale results are ignored. Adding files while running is supported;
they append, analyze, validate and wait without changing the selected/active job.
All domain/controller/widget changes run on Qt's GUI thread.

Before Start Queue, validate every pending job against its own media, subtitle
source, audio/loudness settings, cached GPU capabilities and output paths.
Skip invalid jobs and display ready/attention counts before launch. New/edited
pending jobs also revalidate before execution. Each hardware-encoded job gets
the existing fresh asynchronous GPU initialization probe; failure marks only
that job FAILED, without a silent software fallback. Runtime binaries must
still be present. No unrelated media preparation is overlapped with conversion.

Output policy is chosen up front: Rename automatically (default), Skip existing,
or Require attention. Detect same-output jobs and input/output identity before
execution. Automatic suffixes are deterministic and reserve names across the
queue; no overwrite is authorized. Require attention blocks every conflicting
pending job. A destination appearing after preflight fails safely. Existing
single-job atomic output finalization remains authoritative.

## Settings copy and bulk actions

BatchSettingsService copies scalar intent while retaining each destination's
input, filename, progress/history and independently created settings. Preset
application plans each media separately. Semantic matcher normalizes language
aliases and titles, ranks language/title, then uses channels/codec or subtitle
dispositions to disambiguate. Ties and missing matches produce warnings rather
than choosing an unrelated track. Subtitle burn without a safe match is INVALID.
Concrete external subtitle paths are excluded and require per-job assignment.
The UI offers Apply Web Preset, Copy from the current job to selected jobs,
Set Output Folder, Remove, Retry/Requeue and Clear Completed.

## UI restructuring and binding

Use a persistent left queue sidebar in a QSplitter, an extended-selection
QListView with compact icon/text/progress rows and internal move MIME, and the
existing settings area on the right. External file URL MIME imports all paths;
internal stable-ID MIME only reorders pending jobs. Active/terminal rows cannot
be moved or removed as an accidental side effect. Minimum widths/scrolling and
splitter persistence keep laptop layouts usable. The empty state is concise.

Selected source analysis becomes a compact summary plus Media Details using
cached MediaInfo (including retained format metadata). Reuse the existing
Output/Video/Audio/Subtitles controls and summary, bound explicitly under a
loading guard. Switching jobs loads all controls without writing interim widget
values back. Pending jobs remain editable while another runs; the active job
and completed history are inspectable and locked until explicitly requeued.

The bottom area shows current filename/output, stage-specific existing progress,
elapsed/ETA/speed, secondary job counts, and distinct current/queue controls.
Queue completion is an inline summary, with no per-file success/error modals.
Selected Job Details retains snapshots, failure, commands, logs and loudness.

## Preview and loudness

Keep a PreviewStore per job outside the domain model. Preview uses the selected
job snapshot, never changes its queue status or order, and is disabled throughout
queue execution/pause to avoid scheduling races. The shared runner's correctly
keyed loudness cache remains session scoped; per-job reports are copied into
job diagnostics before the next run. All existing mode exclusivity, full-track
preview measurements, selected streams and cleanup are preserved.

## Persistence and limitations

Persist window geometry, splitter, last Add Files and bulk output directories
using QSettings. Queue content/history/previews are session-only; no database,
crash recovery, concurrent conversions or bulk external-subtitle pairing in v1.
Structured job fields permit a future explicit serialization format. No new
desktop notification infrastructure is necessary. Native Windows and other
physical GPUs remain verification gates rather than unsupported success claims.

## Tests and verification

Add domain/import/order/duplicate tests; independent settings and rapid binding;
semantic language/title matches, ambiguity, missing subtitles and unsafe external
paths; per-media bulk planning; output conflicts/policies; deterministic fake
runner lifecycle tests for sequential order, failure continuation, pause current,
pause after current, cancel/stop/retry and retained snapshots. Exercise actual
FFprobe concurrency and invalid files, Qt file-drop versus internal-move MIME,
selected-job preview isolation, adding while active and control locks. Add real
multi-job FFmpeg conversions spanning copy, gain, loudnorm and subtitles and
verify output/cleanup. Run the entire old and new suite, including opt-in RX
7700 XT tests with host device access when permitted. Render the queue UI at
laptop dimensions, inspect it, and update all requested documentation/report.
