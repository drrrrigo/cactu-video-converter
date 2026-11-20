# Build-time pinned FFmpeg candidates

See manifest.json for exact dated archive/binary/license/configuration pins and
unresolved redistribution/source review. Stage native candidates with
`scripts/stage_ffmpeg.py <platform>`. Downloads/executables are not source-controlled.
No normal application runtime download or frozen PATH fallback exists.

The active audit family is 9.0.2; exact build **n9.0.2-61-gd59078794d-20261120**,
from FFmpeg-Builds/FFmpeg-Builds. The previous Nov 1 daily input expired. A retained
Oct 31 build was inspected and rejected because it excluded later fixes. The
current daily input is not an approved final RC or a durable binary mirror.
Archive validation success is not public redistribution approval. Both explicit
approval fields stay false until full corresponding-source/license evidence exists.
