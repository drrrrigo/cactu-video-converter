# Command generation

`ConversionSettings` is validated and turned into an immutable
`ConversionPlan`; `ffmpeg/command_builder.py` alone creates an argument list.
The UI preview displays arguments for review, while QProcess passes the list
directly. No shell parses file paths or metadata.

For compatible H.264/yuv420p/AAC in MKV, the plan maps exact global video and
audio indexes, chooses `-c:v copy -c:a copy`, writes MP4, and enables
`-movflags +faststart`. FLAC audio changes only `-c:a` to AAC with `-b:a 256k`.
HEVC/10-bit video changes video to `libx264 -crf 18 -preset medium -pix_fmt
yuv420p`. Burn mode prepares the chosen subtitle and adds
`-vf subtitles=subtitle.ass`, requiring video re-encoding.
An external ASS/SSA/SRT file is copied to that controlled basename before the
same command path; a one-frame libass preflight runs first. The original path
never appears inside `-vf`. See [external subtitles](EXTERNAL_SUBTITLES.md).

In manual mode at 100% volume no `-af` is emitted, so AAC stream copy stays available. At
300%, the audio filter builder emits
`-af volume=3.0,alimiter=limit=0.85:level=false:latency=true` when protection
is enabled; the planner chooses AAC encoding, while compatible H.264 video
may still use `-c:v copy`. See [audio volume](AUDIO_VOLUME.md).

Hardware H.264 commands use the same mapped streams, audio, progress and
Faststart arguments. The selected backend contributes setup, ordered filters
and quality options. For VAAPI the command initializes the chosen render
device, then applies `subtitles=subtitle.ass,format=nv12,hwupload` before
`-c:v h264_vaapi`. NVENC/AMF use software yuv420p frames; Linux QSV uses an
explicit selected-device upload. See [hardware acceleration](HARDWARE_ACCELERATION.md).

All conversions request `-progress pipe:1 -nostats` and explicit MP4 muxing.
The output is a unique partial MP4 beside the destination, replaced atomically
after FFmpeg reports success. Input and output paths remain single arguments.

Quick Preview passes a derived plan through this same builder. Input `-ss` seeks
accurately for encoded audio/video and output `-t` bounds the sample. Burn filters
restore source timestamps around libass, for example
`setpts=PTS+10/TB,subtitles=subtitle.ass,setpts=PTS-10/TB`, before the backend's
format/upload filters. Embedded extraction preserves the movie clock and reads
only through the preview end. Selectable preview text is clipped to segment
timestamps in the shared preparation service. See [Quick Preview](QUICK_PREVIEW.md).

## Two-pass loudness normalization

For global audio index 2, Movie / Web and 48 kHz, analysis arguments include:

```text
-i Movie.mkv -map 0:2 -vn -sn -dn
-af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json,aresample=48000
-progress pipe:1 -nostats -f null -
```

Preview analysis uses this full-file command too, without seek or duration limits.
No video filter/encoder is used in analysis. The final pass is built only after
validated measurements exist. An illustrative measured filter is:

```text
loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=-30.1:measured_TP=-20:measured_LRA=2.3:measured_thresh=-40.1:offset=0.1:linear=true:print_format=json,aresample=48000
```

Those measured numbers are examples, never fixed defaults. The mapped audio
uses `-c:a aac -b:a 256k`. Compatible video still uses `-c:v copy`. Requested
Stereo/5.1 conversion adds `aformat=channel_layouts=stereo`/`5.1` before loudnorm
in both passes. No volume or manual limiter is included. Command Preview shows
the analysis and explains pending pass-two measurements, or displays the fully
resolved command when valid cached values exist. See [normalization](LOUDNESS_NORMALIZATION.md).
