# Progress and process control

QProcess runs FFprobe and FFmpeg asynchronously. The conversion runner reads
`-progress pipe:1` key/value events; the decoder tolerates split pipe chunks.
Media timestamps divided by probed duration yield percentage. The Elapsed
display uses wall clock time from process start. Remaining media time divided
by `speed` yields ETA when both values are usable. Near the end,
the UI says “Finalizing output” until FFmpeg exits and the file is finalized.

Pause/resume uses psutil suspension of the FFmpeg PID on Linux and Windows.
This code path still needs a native Windows test. Cancellation resumes a paused
process, requests termination, then kills after three seconds if needed.
The unique partial output and subtitle workspace are removed after failure or
cancel. A successful partial output is atomically renamed beside its final path.

FFmpeg stderr is retained for the error detail dialog and rotating local logs.
