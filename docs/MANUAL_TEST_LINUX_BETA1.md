# Linux beta.1 manual acceptance

**Current state: PENDING MANUAL OWNER TEST. No final RC1 is available yet.**
Test the exact approved internal AppImage named by
[BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md). Do not substitute Python
source execution or the superseded local Python 3.14.8 package.

## Record before starting

| Field | Development hardware test | Second environment |
| --- | --- | --- |
| Tester / date / timezone | PENDING MANUAL | PENDING MANUAL |
| Distribution / version (`/etc/os-release`) | PENDING MANUAL | PENDING MANUAL |
| Kernel / architecture (`uname -r`, `uname -m`) | PENDING MANUAL | PENDING MANUAL |
| GPU / driver / encoder | PENDING MANUAL | Software x264 is sufficient |
| Physical / VM | PENDING MANUAL | PENDING MANUAL |
| Wayland/X11 (`echo "$XDG_SESSION_TYPE"`) | PENDING MANUAL | PENDING MANUAL |
| Resolution / scaling | PENDING MANUAL | PENDING MANUAL |
| Exact RC source commit | PENDING RC1 | PENDING RC1 |
| AppImage filename / SHA-256 | PENDING RC1 | PENDING RC1 |
| Expected checksum source / transfer method | PENDING RC1 | PENDING RC1 |

Use CachyOS with the known RX 7700 XT for the first test, when available. Prefer a
clean Ubuntu LTS VM or another mainstream Linux desktop for the second. Record
unavailable environments rather than claim both. Offscreen Ubuntu CI is supporting
evidence, not an interactive desktop test.

## Verify and launch the actual package

Copy the exact AppImage and generated SHA256SUMS through the approved private or
local transfer. In an otherwise empty candidate directory:

```bash
sha256sum CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
chmod +x CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
./CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
```

Compare the computed digest with the generated candidate record. Stop on mismatch.
Record startup behavior, icon, name, version, Settings, About and Diagnostics.
If FUSE is unavailable, record that fact and repeat using extraction mode:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
```

Do not install Python or system FFmpeg to make Cactu work. Host display/graphics
integration remains necessary. Record any missing system library/error precisely.

## Prove bundled-runtime use without changing host software

Launch the package with an empty PATH after closing the normal instance:

```bash
mkdir -p empty-path
PATH="$PWD/empty-path" APPIMAGE_EXTRACT_AND_RUN=1 \
  ./CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
```

Analyze and convert the synthetic sample from the normal launched window as well
as this instance. Inspect Settings → Hardware Details / Diagnostics and Job Details:
the command/runtime must resolve within the mounted/extracted AppImage, never
`/usr/bin/ffmpeg` or `/usr/bin/ffprobe`. Version text alone is insufficient if the
host has the same build. Record the bundled-path observation privately, sanitized
in public reports. An external player may not open with PATH empty; test playback
from the normal desktop session. Restore PATH by closing this instance; no shell
startup file or system executable is changed.

## Create fixtures with the packaged tools

Extract a copy to a new test directory; the original AppImage hash stays unchanged.
These files are for manual testing, not a second application installation.

```bash
mkdir -p Cactu-Beta1-Manual
cd Cactu-Beta1-Manual
../CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage --appimage-extract >/dev/null
ffmpeg="$PWD/squashfs-root/usr/bin/_internal/ffmpeg/ffmpeg"
ffprobe="$PWD/squashfs-root/usr/bin/_internal/ffmpeg/ffprobe"
cat > captions.pt-BR.srt <<'SRT'
1
00:00:01,000 --> 00:00:08,000
Olá Cactu — ação, português, 日本語

2
00:00:10,000 --> 00:00:20,000
Embedded and external subtitle test
SRT
"$ffmpeg" -hide_banner -v error -f lavfi -i testsrc2=s=640x360:r=30:d=90 \
  -f lavfi -i sine=frequency=440:sample_rate=48000:duration=90,volume=0.08 \
  -i captions.pt-BR.srt -map 0:v -map 1:a -map 2:s -c:v libx264 \
  -preset ultrafast -pix_fmt yuv420p -c:a flac -c:s srt \
  -metadata:s:s:0 language=por Episode-A.mkv
cp Episode-A.mkv Episode-B.mkv
cp Episode-A.mkv Episode-C.mkv
sha256sum Episode-*.mkv captions.pt-BR.srt > ORIGINAL-SHA256SUMS.txt
```

Stop if fixture creation fails. Do not replace a fixture with private/copyrighted
media merely to complete the record. A normal desktop player is sufficient for
playback checks; record which one was used.

## Scenario results

Replace PENDING MANUAL with PASS/FAIL and actual evidence/notes for **each** tested
environment. For unavailable optional hardware, write NOT TESTED — NO HARDWARE.

| ID | Action and expected observation | CachyOS result / notes | Second environment result / notes |
| --- | --- | --- | --- |
| L01 | AppImage startup, branding/version, Settings/About/Diagnostics/licenses/log access; no fatal runtime warning | PENDING MANUAL | PENDING MANUAL |
| L02 | Empty-PATH analyze and convert; observed commands point inside AppImage, not system media tools | PENDING MANUAL | PENDING MANUAL |
| L03 | Add A, explicitly force H.264 / Software x264 / AAC / no subtitles. Convert to a new directory; progress/ETA/speed and completed state update | PENDING MANUAL | PENDING MANUAL |
| L04 | Play output: video, audible audio, sync. Use bundled FFprobe to confirm H.264/yuv420p/AAC and expected duration | PENDING MANUAL | PENDING MANUAL |
| L05 | Embedded Portuguese burn, then external SRT burn; 30-second previews from 00:00:00 show correct timing/text. Record font/glyph issues. Authorized ASS sample if available; otherwise note no ASS coverage | PENDING MANUAL | PENDING MANUAL |
| L06 | Normal audio, manual volume 150% with clipping protection, then -16 LUFS loudness normalization. Observe analysis before conversion and playback sync | PENDING MANUAL | PENDING MANUAL |
| L07 | Regenerate preview with changed settings, open preview/folder, confirm current preview replaced. Close app and confirm session preview cleanup | PENDING MANUAL | PENDING MANUAL |
| L08 | Add/drop A/B/C, reorder pending C before B, apply preset to selected. One full conversion at a time in displayed order; settings remain independent | PENDING MANUAL | PENDING MANUAL |
| L09 | Pause/Resume Current during a sufficiently slow encode; Pause Queue lets current finish and next wait; Resume Queue starts next | PENDING MANUAL | PENDING MANUAL |
| L10 | Cancel Current cleans its partial and continues; Stop Queue confirms and preserves pending jobs. Inspect final statuses | PENDING MANUAL | PENDING MANUAL |
| L11 | Existing output resolves through configured rename/attention policy; `sha256sum -c ORIGINAL-SHA256SUMS.txt` still passes | PENDING MANUAL | PENDING MANUAL |
| L12 | RX 7700 XT VAAPI: force H.264 encode, subtitles and Quick Preview. Record driver/node/backend and actual conversion result; other physical backends only if available | PENDING MANUAL | NOT TESTED — VM GPU availability must be recorded |
| L13 | Hardware Assistant inventory/status/Test Again/official guidance and reviewed clipboard diagnostics work. Software x264 works without available GPU | PENDING MANUAL | PENDING MANUAL |
| L14 | Inspect actual display stack at recorded scaling: queue, settings, dialogs, scrolling. Claim only the tested Wayland or X11 session | PENDING MANUAL | PENDING MANUAL |
| L15 | Review payload inventory for kernel modules/DRI/ICD/vendor driver files. Confirm no driver install/package-manager action occurs | PENDING MANUAL | PENDING MANUAL |

Kernel modules, Mesa GPU drivers and NVIDIA drivers must remain host supplied.
Do not modify render-node permissions, install/replace drivers, or break a working
production driver to produce a missing-driver test.

## Sign-off

CachyOS desktop: **PENDING MANUAL**. Second desktop: **PENDING MANUAL**.
Actual display stacks tested: **not recorded**. Blocking failures: **not evaluated**.
No universal Linux compatibility claim is made.

Complete tester/date/environment/commit/hash fields before signing PASS. Fill a
copy of release/manual-evidence.example.json outside the tested checkout and
preserve exact artifact bytes. Record a second-environment limitation explicitly
if unavailable. Approved manual evidence goes in protected BETA_MANUAL_EVIDENCE;
final publication additionally requires a separate explicit owner instruction and
BETA_OWNER_APPROVAL. No command in this guide creates a tag or public release.
