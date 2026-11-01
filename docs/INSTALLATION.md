# Installing the public beta

Download only from [Cactu's official Releases](https://github.com/drrrrigo/cactu-video-converter/releases).
A listed candidate/workflow run is not automatically an approved public beta.
Packages include Python, PySide6/Qt, FFmpeg and FFprobe; there is no runtime download.

## Windows 11 x86_64

Recommended: run the versioned Setup executable. It installs per user, creates a
Start Menu entry, offers a Desktop shortcut and registers an uninstaller. It keeps
a stable upgrade identity and can reuse a recognized previous install directory.
No GPU drivers are installed. Close Cactu before upgrading/uninstalling.

Portable alternative: extract the entire ZIP, open the CactuVideoConverter folder
and run CactuVideoConverter.exe. Preserve its _internal folder and files. Settings/
logs still use your normal per-user application-data directory; “portable” describes
the extracted application, not an isolated portable preference mode.

Beta.1 candidates are unsigned unless the release notes explicitly say otherwise.
Windows can warn about unsigned/new software. Verify the official repository,
checksum and source before deciding whether to run it. Do not disable Defender or
SmartScreen globally. No self-signed certificate is used as a public trust claim.

## Linux x86_64

Use file-manager Properties → Permissions → allow execution, then launch the
AppImage. Or run chmod +x followed by ./<the exact versioned AppImage filename>.
No root permission or system Python/FFmpeg installation is required.

The CI build baseline is Ubuntu 22.04 x86_64 with the pinned Python/Qt toolchain;
a compatible glibc/desktop graphics stack is needed. A local CachyOS-built candidate
is not evidence of compatibility with that baseline or all distributions. GPU
kernel drivers/Mesa/NVIDIA integration belong to the host OS. Hardware failures
are nonfatal: use Software x264 and the Hardware Acceleration Assistant.

For systems without FUSE, supported AppImage runtimes can use:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
```

This extracts the application temporarily, then runs the same bundled payload.
Desktop fonts/fontconfig are needed for text rendering; proprietary ASS fonts are
not supplied and embedded font extraction is not implemented.

## Verify a download

Download SHA256SUMS.txt from the same release. On Linux use `sha256sum -c
SHA256SUMS.txt` from the download folder (missing files for the other OS can be
reported; compare the file you downloaded). Windows PowerShell can use
`Get-FileHash .\CactuVideoConverter-Setup-0.1.0-beta.1.exe -Algorithm SHA256` and
compare it with the checksum line. Checksums detect mismatch/corruption, not proof
of identity beyond the trusted source that supplies them.

## First launch and errors

Cactu checks bundled executables/base capabilities and writable configuration/temp
workspaces before normal conversion. Missing/corrupt runtime components produce a
fatal configuration message, not a silent PATH fallback. Reinstall a verified
package rather than adding random FFmpeg binaries. Use Settings → Diagnostics for
sanitized report copying; review raw logs before sharing them.
