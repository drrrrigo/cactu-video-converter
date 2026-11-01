# Contributing

Beta.1 is in release hardening: prioritize reproducible bug fixes, packaging,
security, tests and documentation. Defer unrelated new product features.

Use Python 3.14.7 in a virtual environment, then install the exact pins in
`release/requirements.txt` and install the source with
`python -m pip install --no-deps --no-build-isolation -e .`.
Stage the pinned native FFmpeg pair with `python scripts/stage_ffmpeg.py
linux-x86_64` (or windows-x86_64), or use the explicit source-only development flag
with a compatible FFmpeg 9.0.2 pair. Release builds never use a system runtime.

Run `python -m unittest discover -s tests -v`, `ruff check .`,
`python scripts/check_branding.py` and `python scripts/audit_source.py --history`.
Physical GPU tests are opt-in using VIDEO_CONVERTER_HARDWARE_TEST=1 and do not gate
cloud CI. Format changed Python using the pinned ruff version; avoid unrelated
formatting churn in media-processing code.

Read docs/ARCHITECTURE.md and docs/CODE_REVIEW_GUIDE.md before changing FFmpeg
commands, selected stream mapping, subtitles, loudness or queue lifecycle. Include
meaningful synthetic regressions for changed behavior and preserve original input/
subtitle files. Describe what changed, why, tests and known limits in a focused PR.
Do not commit binaries, environments, generated conversions, personal logs/settings,
API credentials or signing material. See SECURITY.md for private vulnerability reports.
