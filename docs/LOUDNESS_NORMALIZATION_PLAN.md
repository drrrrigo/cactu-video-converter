# Loudness normalization implementation plan

## Architecture and targets

Extend the typed audio mode and filter plan, keeping Manual Volume as the
default. Loudness mode makes manual gain/limiting inactive, disables audio
copy, and preserves video-copy decisions. Offer Movie / Web (−16 LUFS),
Louder (−14), Conservative (−18), all with −1.5 dBTP and 11 LU LRA, plus Custom.
The 11 LU target leaves more room for film dynamics than FFmpeg's 7 LU default;
it is a product setting, not a Kosmi requirement. Validate I −70…−5, TP −9…0,
LRA 1…50 against the local FFmpeg 9.0.2 help.

## Two passes in the existing runner

Pass 1 maps the selected global audio index, disables video/subtitles/data,
and runs loudnorm with JSON statistics to the null muxer. No video is decoded
or encoded. Parse the JSON inside mixed FFmpeg stderr into finite, validated
typed measurements. Silent/too-short audio with nonfinite measurements fails
clearly rather than falling back to guessed gain.

Pass 2 resolves a new AudioProcessingPlan using measured I, TP, LRA, threshold,
and target offset, then uses the existing command builder and process runner.
Request linear=true; FFmpeg may fall back to dynamic processing when the target
LRA or true-peak constraints prevent linear scaling. Never add manual volume or
the manual alimiter after loudnorm. Apply requested channel conversion before
loudnorm in both passes so the measurements match the normalized signal.

Explicitly resample normalized output to the selected source's AAC-supported
sample rate, falling back to 48 kHz for unknown/unsupported rates. Dynamic
loudnorm can work internally at 192 kHz; that must not become the AAC rate.
Preserve channel layout unless the user requested a channel change.

## Runtime and cache

Record loudnorm availability through the existing runtime filter check. Missing
support disables the UI option and fails explicit requests; releases require
the filter. Keep successful measurements in a bounded session-memory cache.
Keys include resolved input path, size, mtime, exact audio stream, channel/rate
policy, numeric I/LRA/TP targets, and FFmpeg runtime identity. Include targets
because target_offset is target dependent. Recheck source identity after pass 1.
Never cache cancelled, invalid or failed analysis. Pass-2 cancellation retains
valid measurements.

## Preview, progress and UI

Quick Preview analyzes the entire selected audio stream on a cache miss, then
uses those full-file measurements for its sample. Reuse cache for subsequent
previews/full conversion; never analyze just the preview as an approximation.
Keep the original conversion/preview snapshot immutable and pass a separately
resolved typed audio plan to command generation.

Show analysis and encoding as distinct stages with stage-specific progress,
elapsed time and ETA. Analysis uses full media duration; preview encoding uses
segment duration. The same QProcess pause/resume/cancel controls manage both.
Do not begin pass 2 after cancelling analysis. UI mode/preset controls, summary,
and secondary diagnostics expose targets and the last measurement/result without
showing filter internals on the main screen. New media/preset restore stays in
manual mode at 100%; switching modes can retain the inactive manual slider value.

## Verification and limits

Test target validation, exclusivity, filter order, selected mapping, parser
failures, cache invalidation, preview reuse, cancellation in each pass, and all
video backend plans. Use synthetic quiet/peaky and 5.1 audio to measure output
LUFS/true peak and inspect channels, sample rate and A/V timestamps. Exercise
the real AMD VAAPI path where available. Lossy AAC can overshoot true-peak
targets slightly; dynamic fallback and short/quiet material may affect target
accuracy. Native Windows, other physical GPUs, full movie performance and
bundled release verification remain separate gates.
