# Quick Preview / Test Encode

Configure a video as usual, then click **Create Preview** beside Start Conversion.
In the queue interface, select the job first. Preview is disabled while the
queue is running, paused or stopping, and does not requeue the selected job.
Choose a movie timestamp (`HH:MM:SS` or `HH:MM:SS.mmm`), select 10, 30, or 60
seconds, and click Create Preview. The default duration is 30 seconds. **Open
when finished** defaults on and uses the operating system's video player.
Open Preview and Open Preview Folder also remain available after completion.

For videos up to 60 seconds the initial start is zero. Longer videos start at
10% of their duration, capped at 10 minutes and leaving at least 30 seconds.
You can edit this value. A start outside the video's known duration is rejected.
Requests extending beyond the end are shortened to the remaining duration;
the dialog shows that effective length. Business validation accepts requested
durations from 5 to 120 seconds, although the dialog offers the three presets.
An end remainder shorter than 5 seconds is allowed.

## What settings are represented

`PreviewPlan` stores the immutable full `ConversionPlan` and derives an execution
plan with a temporary destination and segment duration. The same command builder,
runner, output verification, subtitle preparation and encoder adapters execute it.
The selected video backend/device, CRF or hardware quality, pixel format, audio
track, AAC bitrate/channels, audio processing mode/targets, volume, clipping protection and subtitle identity
are retained. FFmpeg's normal software audio pipeline remains in use alongside
hardware video encoding. Fonts and ASS styling use the same system-font behavior
as full conversion; embedded font extraction and custom font folders remain open.

The explicit exception is **stream copy**: previews encode mapped audio and video
to obtain an accurate cut and an independently playable sample. The dialog says
when this applies. The full conversion keeps its original copy decisions. If a
copied video has a hardware backend selected, preview still requires that backend
to be available; it never silently substitutes x264. A sample of a stream that
will be copied can therefore have a small extra compression loss. Settings for
streams already requiring encoding use the same production options.

## Seeking and subtitle timing

The shared builder uses input `-ss` with FFmpeg's accurate transcode seeking,
then output `-t` for the effective duration. Video/audio start near the cut
instead of decoding the preceding movie. FFmpeg resets their clock to zero.
For burned subtitles the video filter temporarily adds the movie start offset
before libass, renders the original event times, then subtracts the offset
before the encoder/backend upload. This also preserves an event that began
before the sample and remains visible at its start.

Embedded subtitle preparation reads subtitle packets from the beginning through
the preview end without decoding video. Seeking those packets directly can lose
an event crossing the cut. A late sample in a large MKV may therefore take extra
preparation time while that prefix is demuxed. External ASS/SSA/SRT files use the
same safe staging and preflight as full conversion; arbitrary user paths never
enter the libass filter expression.

For **Keep selectable**, FFmpeg converts the exact selected embedded text track
to canonical SRT. Preparation clips event times to the preview interval before
encoding MP4 `mov_text`, preserving events crossing the cut. Advanced ASS styling
is lost as in normal selectable MP4 conversion. External selectable subtitles
remain unsupported by the existing validator.

## Progress, output and cleanup

The existing progress/ETA calculations use the effective preview length. One
operation runs at a time; full conversion and preview launch actions are disabled
during preparation/encoding. Pause/resume and Cancel use the common runner. A
cancelled or failed candidate loses its partial output and subtitle workspace.
Cancel during GPU preflight also drops the pending launch; a finishing probe
cannot launch that cancelled job or a later replacement job. The short probe
itself can finish in the background before its worker exits.

Each job has its own generated session preview folder, away from the movie and
final destination. A successful new preview replaces that job's previous one;
other jobs retain theirs. Failed/cancelled attempts retain the previous success. Its plan,
source/subtitle size and modification time, and creation time are recorded.
Changing settings marks it out of date. Reopening a new video resets the default
preview position. Source size changes since analysis require analyzing the video
again; source/signature/readability checks run again immediately before launch.

Normal application exit removes the session previews. A player holding a file
open can prevent deletion on some systems; cleanup is best effort and may leave
a generated temporary folder. A crash can also leave temporary files. Save a
copy elsewhere before exit if you want to keep a sample.

## Errors and limits

The selected GPU receives the same fresh initialization check used for full
conversion. Initialization or encoding errors show details; software retry after
an encoding failure requires an explicit user action. Missing or changed media,
invalid start times, malformed external subtitles, verification failures and
player-launch errors are reported. Very short end remainders containing no
decodable frame may fail verification. A known source duration is required.

Synthetic Linux tests cover a 30-second sample from 10 seconds, end truncation,
subtitle clocks and overlapping events, selected-audio timing/gain, cancellation,
UI locking, and all backend plans. Native Windows player/cleanup behavior,
full-size movie performance, and physical GPU backends other than the tested
AMD VAAPI environment remain release verification work.

## Loudness normalization

When enabled, a cache miss first analyzes the full selected soundtrack. The
preview uses those measurements and the measured pass-two filter, as does final
conversion. Subsequent matching previews/full conversion skip analysis. Its
progress uses the full source duration; Creating Preview then resets progress
and uses the segment duration. Cancel during analysis never launches encoding;
cancel during encoding retains the valid analysis. See
[loudness normalization](LOUDNESS_NORMALIZATION.md) for cache identity, targets,
dynamic boundary differences and diagnostics. A scene can measure differently
from the whole movie even when both use the same normalization settings.
