# Subtitle handling

The user selects a named subtitle track whose global index is retained in the
plan. `None` maps no subtitles. `Keep selectable` maps exactly one supported
text stream to MP4 `mov_text`; advanced ASS styling will not survive that
conversion. `Burn into video` supports ASS, SSA, and SRT text subtitles.

For burn mode, the runner extracts the exact selected stream to a constant
`subtitle.ass` or `subtitle.srt` inside a temporary workspace. The conversion
process runs from that directory and uses the constant relative basename in
the libass filter. This avoids inserting arbitrary user paths, colons, or
Unicode into FFmpeg's filter grammar. Burn mode always re-encodes video.

Bitmap formats such as PGS/VobSub are rejected before conversion. Font
attachments are parsed but **not yet extracted**; ASS fonts not installed on
the system can render with substitutions. This is a known fidelity limitation.

For a separate ASS, SSA or SRT file, choose Burn into video → External file →
Browse. The file is validated, copied into the same temporary workspace and
preflight-rendered before encoding. See [external subtitles](EXTERNAL_SUBTITLES.md).
