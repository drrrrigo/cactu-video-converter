# Output audio volume

In **Manual Volume** mode, the Audio card has a **Volume** slider from 0% to 300%, a live percentage,
**Reset**, and **Prevent clipping**. Each newly loaded video and a fresh Web
Compatibility / Kosmi preset start at **100%**, which leaves the audio
unchanged. The volume value is not saved as a default for future videos.
Each queue job retains its own value when switching selection. Bulk copying is
explicit; changing one job never changes another's volume automatically.

The percentage multiplies linear sample amplitude. 0% produces a silent
audio track; 50% is 0.5×; 125% is 1.25×; 150% is 1.5×; 200% is 2.0×;
250% is 2.5×; and 300% is 3.0×. Using `20 × log10(multiplier)`, 150% is
about +3.52 dB, 200% about +6.02 dB, 250% about +7.96 dB, and 300% about
+9.54 dB. This control does not analyze or normalize perceived loudness.

At 100%, no audio filter is added and compatible AAC may still be copied.
Every other setting decodes the selected audio track, applies `volume`, and
encodes AAC for the Web/Kosmi target. A compatible video can still be copied
without re-encoding. Only the one selected audio track is mapped. When the
slider moves away from 100% while Audio Codec is Copy, the UI selects AAC;
the validator also rejects an explicit Copy plus non-neutral volume setting.

Boosting a signal already near full scale can clip. Above 100%, **Prevent
clipping** adds FFmpeg's `alimiter` after the gain. The chosen FFmpeg 9.0.2
chain for 300% is:

```text
volume=3.0,alimiter=limit=0.85:level=false:latency=true
```

The 0.85 peak target leaves room for overshoot from lossy AAC encoding.
`level=false` disables the limiter's automatic makeup gain, and
`latency=true` compensates its lookahead delay. The FFmpeg defaults provide
5 ms attack and 50 ms release. This reduces hard clipping but can change
loud transients and cannot guarantee that every decoded AAC sample stays
below a particular ceiling. At or below 100%, no limiter is added. Turning
protection off above 100% allows the requested gain but may distort peaks;
the Audio card shows a warning, with stronger wording at 250% and above.
Clipping risk increases above 200%. The existing limiter settings remain
appropriate at 300% because the target ceiling is independent of gain:
larger peaks trigger more reduction. Limiting can therefore affect more
of a loud soundtrack at high gain; 300% will not always sound better.

The same audio filter chain works while software x264 or an available GPU
encodes video, and while embedded or external subtitles are burned. Video
progress, pause/resume and cancellation continue through the common runner.
The application currently supports AAC output only. [Loudness Normalization](LOUDNESS_NORMALIZATION.md)
is a separate, mutually exclusive audio processing mode: it measures the full
track, leaves manual gain/limiting inactive and retains the stored slider value
for switching back. Per-track output gain for multiple simultaneous tracks and
advanced manual limiter controls remain outside this feature.
