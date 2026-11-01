# Media analysis

FFprobe runs with `-show_format -show_streams -print_format json` in an
asynchronous QProcess. `parse_probe` converts the result to frozen records.
Each audio and subtitle record has both a **global stream index** (used by
FFmpeg `-map 0:<index>`) and a per-type **ordinal** (used only for display and
diagnostics). Stream labels use title, language, codec, and channel layout.
Missing or invalid durations/FPS become `None`; progress then omits percentage
or ETA rather than inventing values.

The compatibility analyzer separately evaluates container, video codec,
pixel format, and audio codec. It offers broad browser guidance, not a guarantee.
