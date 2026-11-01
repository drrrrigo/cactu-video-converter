# External subtitle support plan

## Current path

FFprobe records embedded subtitle tracks and global stream indexes. Settings
keep the selected index; the planner validates it and forces video encoding for
burn mode. The runner extracts the exact track to a short filename in a
temporary workspace, then the command builder passes that basename to libass.
The encoder backend appends its pixel conversion and hardware upload filters.

## Extension

Use a typed subtitle source in settings and plans: an embedded stream identity
or an external file identity with an ASS, SSA or SRT format. Keep existing
stream indexes for selectable MP4 subtitles. The UI will offer Embedded Track
and External File under Burn into video, with a native browse dialog and a
separate last subtitle directory. External selection is not restored on launch.

Validation will check the external path, supported suffix, regular file,
readability and nonempty content. At conversion start the source is checked
again, copied into the existing temporary workspace as `subtitle.ass`,
`subtitle.ssa` or `subtitle.srt`, and rendered in a short asynchronous FFmpeg
preflight. The original file is never modified. Embedded tracks continue to
be extracted to the same workspace. A single preparation service returns the
safe staged filename for either source. The command builder and all software
and GPU filter chains then use the same `subtitles=` filter path. The workspace
is deleted by the existing runner cleanup on success, failure and cancel.

The constant relative basename keeps Windows drive colons, quotes, Unicode,
spaces and FFmpeg filter characters out of the filter grammar. File bytes are
copied unchanged; FFmpeg/libass handles text decoding and reports parse errors.
System fonts remain in use. A custom font folder and embedded attachment
extraction are outside this increment. ASS styling depends on available fonts.

Tests will cover source models, validation, UI selection, staged safe names,
malformed and missing files, external ASS/SSA/SRT conversion, backend filter
commands, cleanup, and the existing embedded/copy paths. The optional GPU test
will exercise external burn on a real backend where one is accessible. Native
Windows execution and full-length movie conversion remain separate release
checks.
