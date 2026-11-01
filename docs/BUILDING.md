# Building Cactu beta candidates

Public users should use approved [Releases](https://github.com/drrrrigo/cactu-video-converter/releases),
not a developer environment. Beta source version is centralized in
`src/video_converter/__init__.py`: display/tag `0.1.0-beta.1`, derived PEP 440
`0.1.0b1`. Windows numeric metadata is derived as 0.1.0.1.

## Pinned environment

Use **CPython 3.14.7**, an isolated venv and `python -m pip install -r
release/requirements.txt`. That file pins runtime/build/test dependencies including
transitive build tools. Native packager/runtime inputs and hashes are in
release/toolchain.json. CI targets ubuntu-22.04 and windows-2025; hosted image
contents can change, so this is not a claim of bit-for-bit reproducibility across
all dates/OS images. Record produced hashes and test/promote the same bytes.

Install editable source using `python -m pip install --no-deps --no-build-isolation
-e .`. Internal imports/module launch remain `video_converter`; the primary CLI is
`cactu-video-converter`. Remove an older development distribution before installing
the renamed distribution in the same venv to avoid overlapping owned files.

## Runtime and build

`python scripts/stage_ffmpeg.py linux-x86_64` (or windows-x86_64) downloads the
exact pinned build archive, verifies it before extraction/execution, extracts only
fixed binary/license members and validates native capabilities/build identity.
`python scripts/install_packaging_tool.py` obtains fixed packager/runtime assets.
`python scripts/build_release.py --candidate` builds/tests an **internal** candidate.
It does not approve redistribution or publish a release. Windows builds natively;
Linux builds natively. Do not cross-build Windows installers from Linux.

A source-only fallback is explicit:
`PYTHONPATH=src python -m video_converter.app --dev-system-ffmpeg` with a coherent
9.0.2-family FFmpeg/FFprobe pair. A frozen build never uses PATH as fallback or
downloads anything. Startup validates essential media/config/temp resources.

## Gates

Run the complete unittest suite, `ruff check .`, compileall, branding and source/
history audit checks. Physical GPU scenarios are opt-in; no cloud GPU is required.
Packaged smoke executes the frozen app with PATH empty, not a source interpreter.
Beta publication additionally requires exact license/source closure, manual Windows
11/portable/Linux evidence and the source/artifact hashes described in
[RELEASE_CHECKLIST](RELEASE_CHECKLIST.md). Do not flip approval flags without evidence.
