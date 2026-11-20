# Windows 11 beta.1 manual acceptance

**Current state: PENDING MANUAL OWNER TEST. No final RC1 is available yet.**
Use this guide only when [BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md) names
the approved internal candidate commit and its generated checksums. Historical
Server CI, source execution and old Linux packages do not satisfy this test.

## Record before starting

| Field | Actual value |
| --- | --- |
| Tester / test date / timezone | PENDING MANUAL |
| Windows 11 edition / version / OS build (`winver`) | PENDING MANUAL |
| Clean VM or physical machine / prior Cactu install | PENDING MANUAL |
| GPU / driver / chosen backend | PENDING MANUAL |
| Display resolution / scaling | PENDING MANUAL |
| Exact RC source commit | PENDING RC1 |
| Setup filename / SHA-256 | PENDING RC1 |
| Portable filename / SHA-256 | PENDING RC1 |
| Expected checksum source / transfer method | PENDING RC1 |
| Signature status | Expected unsigned beta; record actual result |

Prefer a clean Windows 11 VM or computer without Python, developer tools or system
FFmpeg. Obtain the exact installer/ZIP and SHA256SUMS through the approved private
or local transfer. There are no public beta downloads yet. Keep test media local.

In PowerShell, in the directory containing the candidate:

```powershell
Get-FileHash .\CactuVideoConverter-Setup-0.1.0-beta.1.exe -Algorithm SHA256
Get-FileHash .\CactuVideoConverter-Portable-0.1.0-beta.1.zip -Algorithm SHA256
Get-AuthenticodeSignature .\CactuVideoConverter-Setup-0.1.0-beta.1.exe |
    Format-List Status,StatusMessage,SignerCertificate
```

Compare both digests with the generated candidate checksum file. Stop on mismatch.
Record actual SmartScreen/Defender behavior and exact warning text if any. Do not
disable Defender, SmartScreen or signature enforcement. Unsigned status alone is
not a beta.1 policy failure; unverified origin or a malware detection requires review.

## Install and establish the runtime

1. Launch Setup interactively as the ordinary user. Record Cactu name, icon,
   version and license display. Record the selected destination (default is the
   user's local Programs directory). Note any elevation prompt.
2. Select the Desktop shortcut. Finish installation, then launch from Start Menu.
   Launch once from the Desktop shortcut too. Confirm the uninstall entry in
   Windows Installed Apps.
3. Open Settings → About. Confirm **0.1.0-beta.1**, Public Beta and both tool versions.
   Open Licenses and confirm Cactu's GPL text plus third-party material is accessible
   in the application directory. Record the exact FFmpeg build identity.
4. Open Settings → Diagnostics. Copy locally and review it. Confirm no private
   movie paths appear in the exported report. Open the local log folder. Record
   those locations privately; sanitize paths before sharing results.
5. Confirm Python and FFmpeg are not required in PATH. Do not uninstall unrelated
   system software to test this. The automated empty-PATH check is supporting
   evidence; this manual test must use the frozen application.

## Create non-sensitive fixtures with the bundled tools

Set `$AppDir` to the actual installed directory recorded above; the example below
uses the default. These commands require PowerShell and the bundled FFmpeg only.
They do not require system Python or FFmpeg. Use an empty test folder.

```powershell
$AppDir = Join-Path $env:LOCALAPPDATA 'Programs\Cactu Video Converter'
$ffmpeg = Join-Path $AppDir '_internal\ffmpeg\ffmpeg.exe'
$ffprobe = Join-Path $AppDir '_internal\ffmpeg\ffprobe.exe'
$TestRoot = Join-Path $env:TEMP 'Cactu-Beta1-Manual'
New-Item -ItemType Directory -Force $TestRoot | Out-Null
@'
1
00:00:01,000 --> 00:00:08,000
Olá Cactu — ação, português, 日本語

2
00:00:10,000 --> 00:00:20,000
Embedded and external subtitle test
'@ | Set-Content -Encoding UTF8 (Join-Path $TestRoot 'captions.pt-BR.srt')
& $ffmpeg -hide_banner -v error -f lavfi -i 'testsrc2=s=640x360:r=30:d=90' `
  -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=90,volume=0.08' `
  -i (Join-Path $TestRoot 'captions.pt-BR.srt') -map 0:v -map 1:a -map 2:s `
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a flac -c:s srt `
  -metadata:s:s:0 language=por (Join-Path $TestRoot 'Episode-A.mkv')
Copy-Item (Join-Path $TestRoot 'Episode-A.mkv') (Join-Path $TestRoot 'Episode-B.mkv')
Copy-Item (Join-Path $TestRoot 'Episode-A.mkv') (Join-Path $TestRoot 'Episode-C.mkv')
Get-ChildItem $TestRoot -File | Get-FileHash -Algorithm SHA256 |
  Select-Object Path,Hash | ConvertTo-Json | Set-Content (Join-Path $TestRoot 'original-hashes.json')
```

If FFmpeg reports a failure, stop and record it rather than testing an empty fixture.
Use a player already available on the test machine to inspect output. Installing
a player is optional test-environment setup; it is not a Cactu runtime dependency.

## Scenarios and actual results

For each row replace **PENDING MANUAL** with PASS/FAIL and add observed output or a
sanitized evidence filename. A checkbox without a result is not a completed test.

| ID | Action and expected observation | Result / notes |
| --- | --- | --- |
| W01 | Install/shortcuts/uninstall registration and ordinary-user startup as above | PENDING MANUAL |
| W02 | About/runtime version, Settings, Diagnostics, local logs, license access; no fatal startup warning | PENDING MANUAL |
| W03 | Add Episode-A. Force Video codec H.264 and Software x264, AAC, no subtitles. Convert to a new output directory. Current progress, elapsed/ETA/speed update; output completes and plays with audible audio/sync | PENDING MANUAL |
| W04 | Probe that output with bundled FFprobe (`-v error -show_streams -show_format -of json OUTPUT.mp4`); confirm H.264, yuv420p, AAC and expected duration | PENDING MANUAL |
| W05 | On a pending/requeued job choose embedded Portuguese subtitle burn. Preview 00:00:00 for 30 seconds. Correct text appears at 1–8/10–20 seconds; record unsupported glyph/font behavior honestly | PENDING MANUAL |
| W06 | Choose the external SRT instead, burn and preview. Verify correct source/timing, then generate a second preview. Open Preview/Open Preview Folder and confirm the current preview changes; closing Cactu cleans session preview files | PENDING MANUAL |
| W07 | If an authorized ASS sample with the needed fonts is available, repeat external ASS burn and inspect styling. Otherwise record NOT TESTED — NO ASS SAMPLE; do not fabricate coverage | PENDING MANUAL |
| W08 | Compare normal audio with manual volume 150% and clipping protection. Enable loudness normalization, target -16 LUFS, then preview/convert. Analysis precedes conversion; output is audible with no obvious sync regression | PENDING MANUAL |
| W09 | Multi-select or drop A/B/C. Reorder pending C ahead of B. Apply Kosmi to selected jobs. Confirm independent job settings and displayed execution order | PENDING MANUAL |
| W10 | Start queue; one full conversion at a time. Use Pause Current then Resume (choose slower encoding if necessary). Use Pause Queue during the active job; that job finishes and the next waits. Resume Queue starts the next job | PENDING MANUAL |
| W11 | With two pending jobs, Cancel Current cancels one and processing continues. Stop Queue shows confirmation and preserves pending jobs. Completed/failed/cancelled text is understandable | PENDING MANUAL |
| W12 | Keep an existing output file, then requeue. Confirm rename/attention policy; no silent overwrite or damage to original inputs/subtitle. Compare original hashes again | PENDING MANUAL |
| W13 | Settings → Hardware Acceleration: record GPU/backend/driver evidence, Test Again, diagnostics and official guidance. Keep a working production driver intact | PENDING MANUAL |
| W14 | If physical NVENC/AMF/QSV hardware is available, force H.264 encoding with its supported backend, burn a subtitle and test preview/conversion. Otherwise record NOT TESTED — NO HARDWARE; verify Software x264 still works | PENDING MANUAL |
| W15 | Extract Portable ZIP to a separate directory; run CactuVideoConverter.exe with its supporting folder intact. Repeat startup/diagnostics and W03. Confirm settings/logs writable without installing Cactu/Python/FFmpeg | PENDING MANUAL |
| W16 | Close all Cactu processes; uninstall the installed copy using Windows Installed Apps. Program files and chosen installed shortcuts removed; original media/subtitles unchanged. User settings/logs are intentionally preserved unless the user resets/removes them separately | PENDING MANUAL |
| W17 | At the actual laptop resolution and scaling, inspect queue/settings/dialogs and scrolling. Record exactly which scaling was tested | PENDING MANUAL |

## Sign-off

Overall Windows installer: **PENDING MANUAL**. Portable: **PENDING MANUAL**.
Blocking failures: **not evaluated**. Physical backend: **not evaluated**.
Tester/date/artifact SHA fields above must be complete before a PASS sign-off.

Fill a copy of release/manual-evidence.example.json outside the tested checkout.
Record each scenario's result, actual Windows build, tested commit and both exact
hashes. Preserve the same bytes. Rebuilding after manual tests requires new tests.
Store approved evidence in the protected `BETA_MANUAL_EVIDENCE` environment variable
only after review. Publication still requires a separate explicit owner instruction
and `BETA_OWNER_APPROVAL`; this guide does not authorize tagging or uploading binaries.
