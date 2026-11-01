# Audio volume implementation plan

## Current pipeline

`ConversionSettings` stores audio codec, bitrate, channels and one selected
global audio stream index. The planner copies compatible AAC, otherwise emits
AAC encoding. `ffmpeg/command_builder.py` maps only that selected track.
Video copy and audio copy are decided independently. The runner owns FFmpeg
progress, pause/resume, cancellation and output cleanup.

## Proposed model and planning

Use integer `volume_percent` (0–300, default 100) and boolean
`prevent_clipping` (default true) to settings. An immutable audio processing
plan will carry typed volume gain and optional limiter stages into the
conversion plan. `100%` produces no filters. Every other value, including
`0%`, requires selected-audio decoding and AAC encoding. Explicit Audio Copy
with a non-neutral volume is invalid; the UI will change Copy to AAC when the
slider moves and explain the choice. Video copy remains independent.

## FFmpeg filter policy

The centralized audio filter builder converts integer percent to a stable
linear multiplier: `150%` becomes `volume=1.5`, `200%` becomes `volume=2.0`,
and `300%` becomes `volume=3.0` (approximately +9.54 dB).
For gains above 100% with protection enabled, append
`alimiter=limit=0.85:level=false:latency=true`. The local FFmpeg 9.0.2 build
supports these options. `limit=0.85` leaves headroom for AAC codec overshoot;
`level=false` avoids the limiter's automatic output makeup gain;
`latency=true` compensates its lookahead delay. Defaults are attack 5 ms and
release 50 ms. Limiting can change transients and does not normalize loudness.
No limiter is applied at or below 100%, since no boost can create new peaks.

## UI and preset

The Audio card uses a 0–300 slider, live percentage label, Reset to 100%
button, and Prevent clipping checkbox. A subtle warning appears only when
boosting without protection. The output summary shows the chosen volume and
whether limiting is active. Loading a new video and restoring the Web/Kosmi
preset reset volume to 100%; the value is not persisted across movies.

## Tests and limits

Unit tests will cover boundaries, copy decisions, exact filter syntax,
selected-track mapping, and all video backends. Synthetic FFmpeg integration
tests will measure gain, limiter ceiling, video-copy independence, channels,
and subtitle combinations. Existing progress and cancellation tests remain
in force. A limiter reduces hard clipping but cannot guarantee ideal loudness
or restore audio already clipped in the source. Native packaged FFmpeg builds
and full-length media still need platform release verification.

## 300% refinement

Extend the existing maximum from 200% to a shared 300% constant used by both
the slider and validator. Retain the gain/limiter architecture and current
limiter settings: the ceiling is independent of the requested gain, so a
higher gain requires more peak reduction rather than a different ceiling.
Verify that choice with decoded AAC peaks at 300%. Strengthen the optional
unprotected-gain warning at 250% and above. Extend boundary, 3× waveform,
stereo/5.1, backend/subtitle, reset and lifecycle tests to the new maximum.
