# Troubleshooting

## Queue and batch jobs

- **File already in queue**: the same resolved input path is skipped. Different
  directories may contain separate jobs with the same filename.
- **Requires attention after import**: select the row and open Job Details.
  Inputs must be readable regular files recognized as video by FFprobe. Remove
  and re-add a repaired input to analyze it again.
- **Earlier job is still analyzing**: later ready jobs wait to preserve the
  displayed execution order. Import probing is limited to two processes.
- **Copied settings require attention**: semantic audio/subtitle matching could
  not resolve the intent safely. Select the affected stream explicitly. Concrete
  external subtitle paths are excluded; Browse separately for each movie.
- **Wrong source for bulk copy**: check **Copy from** in the multi-selection
  action bar. Its source is independent of the currently highlighted row.
- **Output exists or two jobs share a name**: choose Rename automatically or
  edit individual names/directories. Require attention blocks conflicts; Skip
  existing leaves those jobs skipped for review. No queue policy overwrites.
- **Pause did not pause the queue**: Pause suspends the active FFmpeg process.
  Pause Queue lets the current file finish before waiting. Resume the process
  if needed, then Resume Queue to continue pending jobs.
- **Stop waits during hardware checking**: the bounded GPU probe exits before
  cancellation is finalized. Its result cannot launch the cancelled conversion.
- **A job failed and later files ran**: this is the default queue policy.
  Inspect Job Details, Retry/Requeue, correct settings, then Start Queue. Failed
  jobs are never automatically retried or silently switched to software.
- **Preview disabled**: stop/finish the queue first. Preview generation cannot
  overlap running/paused queue work; it uses the selected job's own settings.
- **Completed settings are locked**: use Retry / Requeue to edit and convert
  again. The old output and per-attempt execution history remain intact.
- **Queue disappeared after restart**: queue/history/measurements are session
  state in this milestone. Only geometry/directories/sidebar sizes persist.

See [Batch / Queue](BATCH_QUEUE.md) for complete control and output policies.

## Media conversion

- **Bundled FFmpeg installation is incomplete**: release binaries are missing,
  have the wrong version, or lack libx264/AAC/subtitles. Reinstall a verified
  release. Source developers may explicitly use `--dev-system-ffmpeg`.
- **Output file already exists**: resolve it with the queue's output policy.
  A new file appearing during conversion aborts finalization safely.
- **Subtitle cannot be burned**: choose an ASS, SSA, or SRT text stream. Bitmap
  subtitles are not supported for burn-in.
- **External subtitle unavailable**: check that the selected file still exists,
  is readable, nonempty, and has an ASS, SSA, or SRT extension. Choose it again
  with Subtitles → Burn into video → External file → Browse.
- **External subtitle preflight failed**: the error Details show FFmpeg/libass
  output. Check that the file is valid text in an encoding your FFmpeg can read.
- **Audio Copy is unavailable after changing volume**: processing samples
  requires AAC encoding. Use Reset to 100% to restore stream-copy eligibility.
- **Boosted audio sounds distorted**: enable Prevent clipping or choose a
  lower percentage. Limiting can alter loud transients; it is not loudness
  normalization.
- **Movie mastering is too quiet**: choose Audio → Audio processing → Loudness
  Normalization → Movie / Web. It measures the soundtrack before encoding.
- **Loudness normalization unavailable**: the selected FFmpeg lacks `loudnorm`.
  Manual Volume remains usable. Source developers can inspect
  `ffmpeg -hide_banner -h filter=loudnorm`; releases must pass filter verification.
- **Analysis takes longer than the preview**: the first normalized preview
  measures the full selected audio track. Later matching previews/conversion
  reuse the session cache. Changing track, file, targets or channel policy
  requires a new analysis.
- **Invalid normalization measurements**: use Details and Loudness Details.
  Completely silent, extremely quiet or very short audio may return infinities
  that cannot be used in pass two. Choose manual mode for such material.
- **Loudness uses dynamic mode**: the target peak/range constraints prevented
  linear scaling; FFmpeg selected its dynamic algorithm. A less aggressive
  loudness target or larger Custom LRA can reduce the need to alter dynamics.
- **Normalized audio differs from the target**: a scene's LUFS can differ from
  whole-programme loudness. AAC can overshoot true peak slightly. Review the
  full output and diagnostics; no target is guaranteed for arbitrary material.
- **Preview start is outside the video**: choose a timestamp before the probed
  end. The dialog shortens a sample that would extend past that end.
- **Preview preparation takes time**: an embedded subtitle event may start before
  the cut. To retain it, subtitle packets are read through the preview end without
  decoding the earlier video. External subtitles avoid that movie-prefix read.
- **Preview is out of date**: source or settings changed since that sample was
  created. Use Create Preview to generate a new sample.
- **Preview could not be opened**: use Open Preview Folder and select the sample
  with a locally installed MP4 player. Exit removes generated previews where possible.
- **Conversion failed**: open error Details and the log folder from Settings.
  The application does not send logs or media over the network.
- **ASS font differs**: embedded fonts are not yet extracted. Install the
  needed font locally or use another subtitle track.

## Cactu branding and preferences

- **Old purple UI or old title**: close an older running process and launch the
  current source checkout or rebuilt Cactu package. Native icon caches may need
  refreshing after a real installed upgrade. The compatibility CLI alias still
  launches the same application; its technical name is intentionally retained.
- **Preferences after rename**: migration imports a small validated allowlist
  only into an empty new store. Existing Cactu preferences win. Old jobs/external
  subtitle paths are not restored, and the old preference store is not deleted.
  Reset Settings deliberately prevents another legacy import.
- **Qt test crash on a newer host installation**: use the project's pinned
  PySide6/Shiboken pair in a virtual environment. The host's 6.12.0 worker-cleanup
  crash was not reproduced by the full suite on pinned 6.11.2.
- **Release build says manifest missing**: this is the existing fail-closed
  provenance gate. The new names/icons do not supply approved FFmpeg binaries,
  license payloads or native installer/AppImage verification.

See [Branding](BRANDING.md) for paths, tokens and deliberately retained identifiers.

## Hardware Acceleration Assistant

Open **Settings → Hardware Acceleration** or **Fix Hardware Acceleration** in the
nonmodal banner. Read the explanation before changing the system; use View/Copy
Diagnostics for sanitized technical evidence, then Test Again after any repair.

| Symptom | What to check |
| --- | --- |
| GPU detected, acceleration unavailable | Actual probe result, expected backend, runtime support and device access. A GPU name alone does not prove encoding works. |
| NVIDIA NVENC unavailable | Encoder presence first; if present, inspect probe/library/API errors and official NVIDIA/distro guidance. No `nvidia-smi` dependency. |
| AMD AMF unavailable on Windows | AMF presence and actual initialization. Driver/AMF components may be incomplete; official AMD support does not guarantee a fix. |
| AMD VAAPI unavailable on Linux | Associated render node, access, bound driver, FFmpeg filters/APIs and actual probe. Do not assume AMDGPU-PRO is needed. |
| Intel Quick Sync unavailable | A visible Intel GPU, driver/device access and QSV probe. An Intel CPU alone does not establish QSV. Linux VAAPI is also reported where applicable. |
| Render device missing | Driver/session/container restrictions may hide nodes. Cactu discovers all `renderD*` nodes and does not create them. |
| Permission denied | Review access/mode evidence and your session/container/distribution policy. Cactu never changes groups/permissions or runs chmod/usermod. |
| Bundled FFmpeg encoder/filter missing | This is an application build issue; no driver remedy is offered. Development runtimes are labeled separately. |
| No supported GPU detected | Use Software x264; this is supported, informational behavior. |
| Several GPUs, one works | Overall hardware is available; inspect individual findings for failures. Same-vendor default-device attribution can be uncertain. |
| Test Again disabled | Finish/stop active queue/preview work, or wait for the current hardware test. Pausing a queue/process does not make reconfiguration safe. |
| Pending hardware jobs require attention | A fresh probe failed; fix/re-test or explicitly choose Software x264. Cactu does not silently change the job's backend. |
| Dismissed warning returned | GPU/driver/kernel/runtime/category identity changed, recovery occurred or manual re-detection was requested. |

No driver/package installation commands are built into this milestone. Official
support pages open only after clicking their buttons; local diagnosis sends no
telemetry. See [Hardware Assistant](HARDWARE_ASSISTANT.md) for evidence, resource
coverage, privacy and platform limitations.
