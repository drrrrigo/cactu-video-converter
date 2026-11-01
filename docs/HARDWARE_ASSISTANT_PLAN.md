# Hardware Acceleration Assistant plan

## Existing architecture inspected before implementation

HardwareEncoderDetector inspects FFmpeg's encoder table and probes each platform
backend/device through all quality settings, subtitle rendering and 10-bit input.
HardwareDetectionWorker runs detection or selected-encoder preflight in a QThread.
MainWindow populates successful choices and preserves explicit settings. The
QueueController independently performs fresh per-job preflight; planner/validator
reject unavailable explicit selections, with x264 remaining the default. No Auto
Prefer Hardware mode exists. Probes use the existing backend adapters; conversion,
preview, loudness and subtitle execution share ConversionRunner. Current Settings
has raw diagnostics/re-detect actions, with no OS inventory/remediation layer.
Linux render nodes are discovered when the detector is constructed, so Test Again
must also refresh dynamic node discovery. Release FFmpeg provenance remains an
open gate; diagnostic text must distinguish bundled from development runtimes.

## Design and boundaries

Add frozen typed inventory, distribution, device-resource, diagnosis, finding,
responsibility/severity and guide models. Separate OS inventory, interpretation,
static support resources, report sanitization and Qt presentation. Encoder probes
remain authoritative: GPU identity or encoder presence can never establish success.
Reuse one existing startup/re-test worker and probe cache, adding inventory and
interpretation there; opening Settings must not launch duplicate probes. Retests
invalidate both inventory and probes. Selected conversion preflight remains intact.

Linux reads PCI display-class devices and DRM mappings from sysfs, bound driver,
all render nodes and access/mode evidence; model names use sysfs product strings
when supplied, otherwise readable vendor/device IDs (no downloaded ID database).
Read os-release without evaluating it; identify Arch (including CachyOS), Debian
(including Ubuntu), Fedora and SUSE families. System interfaces are injectable for
tests. No lspci/vainfo/nvidia-smi dependency. Windows uses EnumDisplayDevicesW
through ctypes and read-only adapter registry driver data, mapping PCI vendor IDs;
no WMI CLI, PowerShell, shell parser or driver installer. Display-less adapters
not exposed by the session API are an explicit limitation.

Associate Linux node-specific results by exact render path. Windows/default-device
NVENC/AMF/QSV results cannot prove which of several same-vendor adapters was used:
report that ambiguity instead of assigning success to each adapter. Intel Linux
keeps existing QSV and VAAPI options; no new backend-selection policy is introduced.

## Failure classification

Order evidence: actual successful probe; missing runtime encoder/filter/features
(application packaging or development runtime issue); absent/inaccessible exact
render node; no bound driver where confirmed; explicit driver API incompatibility,
unsupported encoder or device mismatch signatures; missing runtime component;
initialization failure; unknown/incomplete evidence. No minimum-driver database
and no assertion that all failed probes mean a missing/old driver. No-GPU systems
are informational, never blocked. Overall hardware availability is any real success,
including on mixed-GPU systems; partial failures remain visible individually.

## UI and session state

Permanent Settings → Hardware Acceleration opens a single structured, scrollable
assistant: overall status/software availability, device/backend findings, explanation,
recommended action, official help, Test Again and optional technical diagnostics/copy.
A small nonmodal amber/error banner with Fix/Dismiss appears only for detected
potentially supported GPUs with no working backend. Persist a hashed dismissal
identity including GPU/driver, diagnosis, major app version; explicit re-test clears
it. Recovery/hardware changes invalidate it. Detection remains asynchronous after
show; Test Again is disabled while queue, conversion, preview or hardware work is
active. Re-test refreshes dropdowns and independently revalidates editable queue
jobs without changing explicit selections. Use Software x264 is an explicit action
for the selected editable job; active plans cannot be changed. Preflight errors gain
a Fix action alongside explicit software/cancel.

## Remediation and external resources

Central frozen HTTPS support resources with IDs, vendor/platform, descriptions and
review dates. Guides are selected by issue first, platform/family/vendor/backend
second. Missing FFmpeg capabilities never offer driver downloads. Windows links
point to AMD/NVIDIA/Intel support; Linux guides link to official distribution docs.
No package commands are shipped in this milestone: documentation links avoid
version-sensitive installation/group advice, unsupported distro guessing and sudo.
No subprocess installation, privileges, password prompt, driver downloads or device
modification. Only bundled FFmpeg diagnostic commands run; URLs open via Qt after
registry/HTTPS/domain validation. No arbitrary system-supplied URL can be opened.

## Privacy, tests and limitations

All inventory/probing is local; no network at startup or telemetry. Copy diagnostics
contains only relevant OS/GPU/backend/resource/probe evidence, with bounded stderr,
user/home/media paths and arbitrary error URLs scrubbed. Log diagnosis lifecycle,
classifications and guide IDs, not full media contexts. Explicit Copy is local only.

Test injected Windows adapters and Linux sysfs/os-release/nodes, distro families,
classifications and responsibility, multiple nodes/GPUs/ambiguity, missing utilities,
unknowns, URL allowlist, absence of command execution, sanitized copy, banner identity,
retest cache/UI availability/queue validation and x264 continuity. Run the entire
suite with pinned PySide6 6.11.2; host 6.12.0 previously crashed in Qt worker cleanup.
Physically check this host's AMD VAAPI where access permits; no claims for absent
NVENC/AMF/QSV devices or native Windows execution. Render assistant/banner at laptop
sizes. Update user/review/architecture/testing/packaging/report documentation honestly.
