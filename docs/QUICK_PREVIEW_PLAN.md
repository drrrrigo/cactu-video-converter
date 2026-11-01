# Quick Preview implementation plan

## Shared execution

Derive an immutable `PreviewPlan` from the current validated `ConversionPlan`.
Keep the original plan as the configuration snapshot and derive an execution
plan with a temporary destination and effective segment duration. Reuse the
normal command builder, subtitle preparation, hardware adapters, audio filters,
runner, output verification, progress, pause and cancellation. Preview overrides
stream copy by encoding both mapped audio and video for accurate, independently
playable cuts. The selected encoder and its quality settings stay in use; an
unavailable selected GPU is an error. The final plan is never changed.

## Timing

Use accurate input seeking and output duration limiting. Restore source-time
video timestamps around the common libass subtitle filter when a staged subtitle
uses the movie timeline, then restore segment-relative timestamps for encoding.
Confirm this with fixtures containing early events, events at a nonzero preview
start, and an event crossing the cut. Embedded subtitle extraction demuxes from
the beginning through the preview end while retaining original event times;
seeking subtitle packets directly can lose an event crossing the cut. This
reads a prefix without decoding video, and can add preparation time for late
segments in large movies. Keep external subtitle bytes and font behavior unchanged.

The start field accepts `HH:MM:SS[.fraction]`; requested duration is 5–120 s,
default 30 s with 10/30/60 choices. Clamp the effective duration to the remaining
media length, including a remainder shorter than 5 s. Require a known finite
media duration and a start before its end. Default start is zero for files up
to 60 s; otherwise 10% of duration, capped at 600 s and leaving 30 s remaining.
Progress and ETA use the effective segment length.

## UI and resources

Add Create Preview beside Start Conversion and a small options dialog with
start, duration, effective duration, copy-policy note, and Open when finished.
Use the existing one-job runner and disable both launch actions while preparing
or encoding either operation. Reuse fresh hardware preflight, identify each
probe by its pending plan, and ignore late results after cancellation/replacement.

A session preview store allocates a generated temporary candidate path. Retain
the previous successful preview until a new candidate succeeds; delete failed
or cancelled candidates. Keep only the latest successful result, its exact plan,
input signature and creation time. Mark it out of date after settings/input
changes. Open files/folders through QDesktopServices and check launch errors.
Delete session previews on normal application exit; original media and final
conversion output are never cleanup targets.

## Validation and tests

Revalidate readable source and external subtitle paths, compare source size to
the probe where available, and reject changes between preview planning/start.
Test parsing, duration boundaries, clamping, defaults, original-plan immutability,
all backend commands, audio gain, source/track identity, and dialog/job locking.
Generate a 30 s preview at 10 s from synthetic media and inspect duration, streams,
decoded video frames/subtitles and audio timing/levels. Test EOF, cancellation,
failure cleanup, and optional real-GPU preview through the common runner.
Document native Windows/player integration and full-length media limits honestly.
