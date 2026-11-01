# External subtitle files

Select a video, choose **Burn into video** in the Subtitles card, choose
**External file**, then use **Browse** to select an `.ass`, `.ssa`, or `.srt`
file. Extensions are case insensitive. The Output Summary names the selected
file. The source analysis count still refers only to subtitles embedded in the
video. **Keep selectable** continues to use embedded tracks only.

Burning changes video pixels, so the video is encoded even when it could
otherwise be copied. The Web Compatibility / Kosmi output remains MP4,
H.264/yuv420p, AAC when audio is present, and Faststart. The chosen software
or hardware encoding backend uses the same filter graph after subtitle
preparation. The burned output contains no selectable subtitle stream.

The file must exist, be readable, be nonempty, and have a supported extension.
The app checks these conditions before starting and again when preparing the
conversion. It copies the file bytes unchanged to a temporary conversion
workspace under a controlled name such as `subtitle.ass`. FFmpeg/libass then
renders a synthetic frame as a quick preflight. A parsing or text encoding
error stops the conversion before the movie encode begins. The staged copy is
used for the full conversion, so edits to the original after Start do not
change an in-progress burn. The original is never modified.

This staging is deliberate: arbitrary Windows drive colons, backslashes,
quotes, Unicode, spaces, and FFmpeg filter characters in the user's path never
enter the `subtitles=` filter expression. FFmpeg receives arguments directly,
without a shell. The existing runner removes staged files on success, failure,
or cancellation and removes any partial output.

ASS/SSA styling is rendered by libass. Fonts installed on the system are
available; missing fonts may be substituted. SRT is rendered with libass's
default text styling. A custom external font folder and embedded Matroska font
attachment extraction are not implemented. The app does not automatically
transcode legacy subtitle encodings; if libass cannot parse a file, check its
encoding and the error details. External selectable MP4 subtitles are outside
this feature.

The short preflight catches many malformed files, but it does not guarantee
every subtitle event in a long file will render as intended. Test a short
section when exact styling matters. Native Windows paths and all GPU backends
still need tests on their respective machines; the Linux RX 7700 XT VAAPI path
has a short external ASS integration test.
