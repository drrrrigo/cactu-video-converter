# Code review guide

Recommended order for a manual audit:

1. `models/media.py`, `models/conversion.py`: inspect typed stream identities,
   global indexes versus ordinals, settings, and immutable plans.
2. `media/ffprobe_service.py`: inspect JSON parsing, missing data handling,
   FPS calculation, and human-readable labels.
3. `media/compatibility.py` and `presets/web_kosmi.py`: inspect browser
   guidance and preset defaults.
4. `conversion/validator.py`, `conversion/planner.py`: inspect output safety,
   selected-stream checks, copy decisions, and forced encoding for burn-in.
5. `ffmpeg/command_builder.py`: inspect exact `-map` arguments, codec options,
   subtitle filter input, and argument-array safety.
6. `ffmpeg/progress.py`, `ffmpeg/runner.py`: inspect progress parsing, temporary
   output, state transitions, pause/resume, termination, and atomic finalization.
7. `ffmpeg/runtime.py`: inspect PyInstaller path resolution and release fallback
   prevention. `scripts/verify_ffmpeg.py` is the release integrity gate.
8. `ui/main_window.py`, `ui/theme.py`: inspect signal wiring, English text,
   settings synchronization, summary, and dark layout.
9. `packaging/`, `scripts/build_release.py`, `docs/FFMPEG_BUNDLING.md`:
   inspect the **open** release provenance, native build, licensing, and smoke
   test gates before any distribution.
10. `tests/`: review synthetic scenarios and add cancellation and Windows
    packaged tests before release.

## Hardware acceleration

- `models/encoder.py`: backend IDs, quality levels, selected device identity,
  and structured capability results.
- `ffmpeg/encoders.py`: registry, backend quality profiles, hardware setup,
  8-bit format conversion, device upload, and subtitle filter ordering.
- `ffmpeg/hardware_detector.py`: encoder-table inspection, Linux render-node
  discovery, runtime initialization probes, session caching and failure reasons.
- `ui/hardware_worker.py` and `ui/main_window.py`: asynchronous detection,
  available-only options, preflight, diagnostics, summary, and explicit
  software retry. Check thread lifetime and the selection/preset interaction.
- `conversion/planner.py` and `conversion/validator.py`: copy priority,
  capability matching and the backend/device placed in `ConversionPlan`.
- `ffmpeg/command_builder.py`: hardware arguments derived from the plan;
  `ffmpeg/runner.py`: encoder-independent execution and post-conversion probe.
- `tests/test_hardware.py`, `tests/test_ui_hardware.py`, and
  `tests/test_hardware_optional.py`: command and detector simulation, UI
  availability, and opt-in physical GPU conversion. The RX 7700 XT VAAPI path
  has a short physical test; other GPU backends remain unverified here.

## External subtitle support

- `models/subtitle.py`: typed ASS/SSA/SRT formats and embedded/external source
  identity. `models/conversion.py` and `conversion/planner.py` carry the chosen
  source into the immutable plan; the planner still forces encode for burn.
- `conversion/validator.py`: source and format checks, missing/unreadable/empty
  external file errors, and embedded stream validation.
- `ui/main_window.py`: source choice, separate subtitle browse directory,
  basename and tooltip, summary, and command preview.
- `ffmpeg/subtitle_pipeline.py`: exact embedded-stream extraction versus
  byte-for-byte external staging and one-frame libass preflight.
- `ffmpeg/runner.py`: preparation/preflight phases, common cancellation and
  temporary-workspace cleanup. `ffmpeg/command_builder.py` uses only the safe
  staged basename; `ffmpeg/encoders.py` appends backend-specific filters.
- `tests/test_external_subtitles.py`: format, validation, Unicode and unsafe
  paths, source UI, backend command planning, ASS/SSA/SRT integration, malformed
  file failure and cleanup. `tests/test_hardware_optional.py` includes an
  external ASS burn on an available physical backend. Windows paths are covered
  by the staging design; native Windows execution remains to be tested.

## Audio volume control

- `models/conversion.py` stores the 0–300% setting and clipping preference;
  `models/audio.py` defines the shared `MAX_VOLUME_PERCENT = 300` limit and
  typed gain and limiter processing plan.
- `conversion/validator.py` checks bounds and rejects Copy with filtering;
  `conversion/planner.py` disables audio copy independently of video copy.
- `ffmpeg/audio_filters.py` converts integer percent to stable FFmpeg syntax,
  placing `alimiter` after `volume`; `ffmpeg/command_builder.py` attaches the
  graph to the selected mapped audio stream only when AAC is encoded.
- `ui/main_window.py` provides the slider, reset, Copy-to-AAC transition,
  clipping warning, and output summary.
- `tests/test_audio_volume.py` covers boundaries, planner/command behavior,
  gain ratio, limiter ceiling, mute, stereo and 5.1 output, including 225–300%
  planning and a measured 3× gain/limiter test at 300%. The opt-in
  `tests/test_hardware_optional.py` covers the VAAPI subtitle burn with 300%
  protected volume on this host.

## Quick Preview

- `models/preview.py`: settings, immutable full-plan snapshot and derived encoding
  plan. `conversion/preview_planner.py`: strict timestamp parsing, 5–120 s limits,
  EOF truncation, deterministic defaults, signatures and selected-GPU checks.
- `ui/preview_dialog.py`: options and effective duration. `ui/main_window.py`:
  shared launch/hardware preflight, mutually exclusive jobs, playback, stale state,
  error handling and session cleanup.
- `ffmpeg/command_builder.py`: optional seek/duration arguments and movie-clock
  restoration around libass. `ffmpeg/subtitle_pipeline.py`: shared external staging,
  embedded prefix extraction, and selectable event clipping. Check an event
  crossing the preview start; direct subtitle seeking loses it.
- `ffmpeg/runner.py`: normal process/validation/cleanup with preview context and
  segment-duration progress. `services/preview_store.py`: retain last success,
  remove failed candidates, replace on success, and best-effort exit cleanup.
- `tests/test_preview.py`: derivation, parsing, copy exception, all backend plans,
  source identity, real 30 s/EOF output, decoded subtitle timing, audio gain/sync
  and cancellation. `tests/test_preview_ui.py`: dialog, job locks, snapshots,
  stale status and player launch errors. The optional hardware test also executes
  short previews. Full conversion's copy rules are deliberately preserved.

## Loudness Normalization

1. `models/loudness.py`: presets, supported target ranges, finite measured
   I/TP/LRA/threshold/offset and typed result/report. `models/audio.py`: exclusive
   modes, neutral effective manual gain, no manual limiter with loudnorm, ordered
   channel-layout/loudnorm/resample nodes.
2. `conversion/validator.py` and `conversion/planner.py`: selected audio required,
   explicit Copy rejected, AAC encode forced, video copy independent.
3. `ffmpeg/loudness.py`: selected global audio mapping, `-vn -sn -dn`, null sink,
   full-file preview analysis; JSONDecoder scanning noisy stderr; invalid values
   rejected without substituting measurements.
4. `services/loudness_cache.py`: bounded session LRU with source stat, stream,
   channel/rate, numeric targets (offset is target dependent) and runtime identity.
   `ffmpeg/runner.py`: cache miss → analysis → validated measurements → resolved
   typed AudioProcessingPlan → normal conversion. Check source revalidation,
   cache insertion only after successful analysis and cancellation before parse.
5. `ffmpeg/audio_filters.py` and `ffmpeg/command_builder.py`: measured pass-two
   options, linear request/dynamic fallback, same pre-channel conversion, explicit
   final rate, selected AAC stream and measurement-only plan override.
6. `ui/main_window.py` and `ui/preview_dialog.py`: opt-in mode/presets/custom,
   retained inactive slider, new-media reset, summary and diagnostics, full-track
   preview disclosure. Stage signal resets progress/elapsed; analysis denominator
   is source duration and second-pass preview denominator is effective duration.
7. `ffmpeg/runtime.py`, `scripts/verify_ffmpeg.py`: missing filter disables the
   feature without disabling manual mode; release verification requires it.
8. `tests/test_loudness.py`: ranges, parser failures, mode exclusivity, copy and
   backend plans, cache invalidation, independently measured output loudness and
   peak, 5.1 channel frequencies, sample rate, A/V timestamps, preview reuse,
   silent audio, cancellation and pause. `tests/test_hardware_optional.py` adds
   real HEVC Main 10 + AC3 5.1 + embedded/external ASS and normalized GPU previews.

See [normalization details](LOUDNESS_NORMALIZATION.md) and
[implementation report](IMPLEMENTATION_REPORT.md) for actual verification limits.

## Batch Conversion / Queue

1. `models/job.py`: UUID ConversionJob, explicit JobStatus/ValidationState,
   independent frozen settings/plans, diagnostics, timestamps and per-attempt
   immutable execution records. Check that no widget/process/temp-directory
   object enters domain state, and terminal edits require explicit requeue.
2. `models/queue.py`: normalized duplicate identity, ordered collection, active
   removal/reorder restrictions, aggregate counts and separate QueueState.
   An earlier ANALYZING job must block later ready jobs from overtaking it.
3. `services/probe_pool.py`: centralized concurrency=2, readable regular-file
   checks, asynchronous QProcess/timeout, UUID callbacks and failed-start cleanup.
   `QueueController` ignores callbacks for removed jobs.
4. `services/batch_settings.py`: scalar intent copy preserving destination
   filenames, per-job preset application, language/title normalization, semantic
   audio/subtitle ranking and ambiguity rejection. External subtitle paths are
   excluded. Unresolved fields stay blocked until the affected selection changes.
5. `services/queue_controller.py`: output reservations/policy and per-job plan
   validation; one active ID and immutable snapshot; fresh GPU worker preflight;
   existing runner dispatch; terminal diagnostics/history then deferred next-job
   scheduling. Inspect continue-on-failure, pause after current, separate process
   pause, cancel current versus stop, cancellation of pending GPU checks and
   explicit retry. The controller builds no FFmpeg command.
6. `ui/queue_view.py`: model roles/UUID MIME, compact accessible status/progress,
   extended selection, external URLs versus internal moves and active anchors.
   `ui/queue_panel.py`: explicit guarded settings binding, stable bulk-copy source,
   per-job PreviewStore ownership, bulk actions, details and queue controls.
   MainWindow retains existing configuration panels, preview/GPU launch and
   progress presentation; it no longer schedules full conversions or probes.
7. `ffmpeg/runner.py`: shared commands/history capture and terminal signals after
   output verification/cleanup. The existing planner/validator, command builder,
   backend adapters, audio filters, loudness cache, subtitle pipeline and progress
   parser remain the media-processing implementation. There is no batch runner.
8. `tests/test_batch_queue.py`, `test_batch_ui.py`, `test_batch_integration.py` and
   the third opt-in test in `test_hardware_optional.py`: state/order/control,
   independent settings, semantic failure safety, collisions, MIME/binding,
   real sequential output/cleanup and physical GPU preflight coverage.
   `tests/qt_helpers.py` catches unexpected asynchronous Python/Qt exceptions.

Use [BATCH_QUEUE_PLAN](BATCH_QUEUE_PLAN.md) for design decisions and
[BATCH_QUEUE](BATCH_QUEUE.md) for product semantics and remaining limits.

## Branding / Theme

1. `product.py` and `__init__.py`: official name, stable slug/executable and
   unchanged version; no invented legal publisher or domain.
2. `ui/theme.py`: centralized brand/semantic colors, hover/pressed/focus/disabled
   states, neutral surfaces, readable selection, slider/check/radio styling and
   progress fill. `ui/queue_view.py` must import tokens rather than literals;
   file-drop highlighting changes presentation only. Inspect status text/icons.
3. `ui/branding.py`, `assets/branding/`: original SVG, small PNG sizes, ICO,
   source/wheel/frozen paths, Settings grid and About's FFmpeg/FFprobe attribution.
   `scripts/generate_branding_icons.py` reproduces exports from the SVG.
4. `app.py`, `services/settings_migration.py`: identity before preference reads,
   empty-new-store-only allowlist, validated values, unchanged old store and
   migration markers preserved on Reset Settings. No job/subtitle state import.
5. `scripts/branding_metadata.py`, `packaging/video_converter.spec`,
   `packaging/windows/CactuVideoConverter.iss`: executable/file version/icon,
   frozen asset payload, legacy installer AppId and previous-directory reuse.
   Native Windows install/upgrade/uninstall remains unverified; do not infer it
   from structural metadata checks.
6. `packaging/linux/`, `scripts/build_release.py`, `pyproject.toml`: desktop/icon/
   AppRun consistency, version-derived AppImage name and wheel data/CLI. The
   release manifest/license gates remain unchanged. CI runs metadata checks on
   both OS targets; there is no existing release artifact upload workflow.
7. `tests/test_branding.py`, `scripts/check_branding.py`: migration/repeat/reset/
   malformed cases, title/About/settings/assets, text contrast and platform
   metadata checks. Review actual Qt screenshots linked from `BRANDING.md`.

Intentional legacy identifiers include Python imports/logger namespaces/spec,
compatibility CLI, temporary/log prefixes and queue MIME. The old visible name
occurs only in migration/upgrade keys, exact shortcut cleanup and clearly labeled
historical material. User output filenames and all media-processing semantics
are preserved. Compare [REBRANDING_PLAN](REBRANDING_PLAN.md) with
[BRANDING](BRANDING.md) and the report's exact verification/limitations.

## Hardware Acceleration Assistant

1. `models/hardware_diagnosis.py`: frozen inventory/resources/findings, explicit
   categories, severity/responsibility, any-success aggregation and hashed banner
   identity. GPU presence or encoder-table presence must not establish availability.
2. `hardware/inventory.py`: read-only Linux PCI/DRM/render access/os-release,
   optional local label database, Windows EnumDisplayDevicesW/adapter registry,
   structured vendor IDs and incomplete-inventory handling. No CLI/privilege or
   driver-version guessing. Review same-vendor/headless adapter limitations.
3. `ffmpeg/hardware_detector.py`: original probes/quality/filter path retained;
   dynamic nodes refreshed on re-test, session cache, probe command/exit evidence.
   `ui/hardware_worker.py` extends the same background worker with explanations;
   selected-conversion preflight remains unchanged. Explanation failure must not
   discard a successful capability or prevent software use.
4. `hardware/diagnosis.py`: expected platform/vendor backends, exact node matching,
   successful probe priority, build versus system responsibility, narrow error
   signatures and explicit uncertainty/adapter ambiguity. No minimum-driver DB.
5. `hardware/resources.py`: issue-first guide registry, static reviewed HTTPS
   resources/exact host allowlist and empty command lists. Missing build capability
   gets no driver remedy; unknown distro gets no guessed installation commands.
6. `hardware/report.py`: bounded, path/media/URL/control-character sanitization;
   useful device paths remain. Clipboard only, no telemetry or automatic issue
   upload. Do not append conversion/job logs to these diagnostics.
7. `ui/hardware_assistant.py`, `ui/hardware_assistant_panel.py`, MainWindow/settings
   wiring: plain text, cached read-only opening, safe official links, banner
   dismissal/recovery, explicit software action, disabled re-test during queue/
   preview/probing and refreshed dropdown/pending-job validation.
8. `services/queue_controller.py`: failed fresh preflight invalidates that cached
   capability and revalidates editable pending jobs. No silent backend switch;
   other valid jobs continue through the existing sequential scheduler/runner.
9. `tests/test_hardware_assistant.py` and `test_hardware_assistant_ui.py`: injected
   OS boundary, categories/guides, multiple nodes/adapters, privacy/security,
   asynchronous re-test, banner identity, software usability and queue recovery.
   Windows API-boundary simulation is not native Windows or physical GPU proof.

Read [plan](HARDWARE_ASSISTANT_PLAN.md), [user/architecture guide](HARDWARE_ASSISTANT.md)
and the report for exact physical checks and remaining limitations. No driver
installer, package-manager/sudo execution or new media-processing path exists.

## Public beta release hardening

Review `PUBLIC_BETA_RELEASE_PLAN.md`, `RELEASE_LICENSE_AUDIT.md` and
`RELEASE_CHECKLIST.md` first. `__init__.py` is the single version source, with
PEP 440/numeric derivation in package/native metadata. Inspect pinned release
requirements/toolchain/actions, safe archive staging, exact FFmpeg build/capability
checks and rejection of nonfree builds. Verify no runtime download/PATH fallback.

Review startup/config/temp checks, ErrorReporter logging/recovery, general sanitized
diagnostics and explicit repository/issue/license links. The narrow output_commit
helper fixes check-then-replace overwrite races; it uses atomic no-replace semantics
unless overwrite is explicitly authorized. No FFmpeg command/filter changes are
part of this milestone.

The frozen release-smoke entry point uses existing MainWindow/planner/runner with
synthetic media and bundled FFprobe. `package_smoke.py` empties PATH and requires
frozen/bundled output evidence. Native installer/portable/AppImage testing must not
be inferred from PyInstaller success or source unit tests. License collection is
not license closure; inspect missing texts/sources and preserve fail-closed approval.

Workflows must never upload binaries from ordinary PRs or before license approval.
Tag promotion reuses same-commit candidate artifacts, checks native smoke and exact
manual hashes, generates SHA256SUMS, requires protected environment review and
publishes only a GitHub pre-release. Inspect source/history secret audits, ignored
personal mockup/development artifacts and private security reporting. Release tests
cover versions, tables, archive paths/hashes, writable environment, frozen fallback,
diagnostic privacy, publication blockers and atomic no-overwrite behavior.
