# Public beta release plan — v0.1.0-beta.1

Prepared 2026-11-01 before implementation. This is release hardening, not feature work.

## Inspected state and blocking owner decisions

The source app has 134 tests and existing ONEDIR/Inno/AppImage scaffolding, but no
approved FFmpeg archive manifest, shipped license payload, release workflow or
packaged conversion smoke test. The .git directory in this workspace is empty and
read-only: there is no inspectable history, main branch, remote, tested commit or
repository identity. No Cactu LICENSE/source-license decision is present. Repository
URL and source-license choice were requested from the owner. Do not invent either,
create an unrelated GitHub project, choose a source license, tag an untested commit
or publish until the required evidence is present.

## Required deliverables and sequence

1. Audit exact third-party distributions, FFmpeg providers/configuration/source
   availability and license payloads; record evidence and unresolved obligations in
   RELEASE_LICENSE_AUDIT.md. Unknown redistribution status blocks publication.
2. Centralize official display/tag version 0.1.0-beta.1, PEP 440 package form and
   numeric Windows version mapping without conflicting manual values.
3. Pin Python, direct/transitive build tools and native packager downloads where
   practical. Record immutable HTTPS URLs and SHA-256 values. Stage archives safely
   and atomically; reject mismatches before executing anything. Preserve the
   explicit source-only system-FFmpeg development path; frozen releases never use PATH.
4. Validate FFmpeg/FFprobe coherence, exact build configuration and mandatory software,
   mux/demux, codec/filter/subtitle capabilities. Record platform hardware exposure;
   never require actual cloud GPU availability. Reject --enable-nonfree builds.
5. Add startup config/temp/runtime checks, user-friendly uncaught-error recovery and
   sanitized general diagnostics/explicit repository/issue/license links. Preserve
   media pipeline and local logging; no telemetry or unrelated product features.
6. Add a frozen executable smoke entry point that starts the Qt app offscreen,
   resolves bundled binaries with PATH unavailable, generates synthetic video/audio/
   subtitles, probes, converts through the existing runner, verifies H.264/AAC/MP4/
   Faststart/subtitle output and exits normally. Smoke the exact ONEDIR/portable/
   AppImage payloads, not a source interpreter impersonating the package.
7. Harden native packaging: complete Windows ONEDIR + per-user stable-ID Inno Setup +
   portable ZIP; Linux AppDir/AppImage with appropriate Qt/Python dependencies,
   notices/licenses and no kernel/GPU-driver installation. Optional Authenticode
   support uses external tooling/secrets only; unsigned beta status is explicit.
8. CI runs pinned Linux/Windows nonphysical tests and lint. Tag release jobs build
   natively, test packaged payloads and produce exact artifact names. A final job
   checks required assets, license/manual/secret-audit gates and SHA256SUMS before
   creating a GitHub **pre-release**. Ordinary pull requests cannot publish binaries.
9. Prepare public-facing README, installation/known issues/release notes, issue
   forms, CONTRIBUTING and a truthful private security disclosure policy. No fake
   repository/support links. Scan current source for secrets/personal artifacts;
   Git history remains unaudited until real repository history is available.
10. Run complete existing/new tests, local native package checks where available,
    and record exact evidence. Windows clean install/portable/uninstall and a second
    Linux environment require actual tests. The same tested source commit/artifact
    hashes must be approved before the final tag/release. Do not rebuild different
    bits and label them as the manually tested candidate.

## Expected artifacts

- CactuVideoConverter-Setup-0.1.0-beta.1.exe
- CactuVideoConverter-Portable-0.1.0-beta.1.zip
- CactuVideoConverter-0.1.0-beta.1-x86_64.AppImage
- SHA256SUMS.txt generated from those final files

## Release gates and reporting

Keep a machine-readable release status/configuration file and fail closed on absent
owner license/repository, exact FFmpeg provenance/notices, history/secret audit,
manual artifact smoke evidence, required build outputs and tag/commit identity.
Build-only preparation is not a public release. Never claim Windows/manual/AppImage
verification from static metadata checks. Document exact remaining blockers in the
implementation report and release checklist. No beta tag or public upload while any
mandatory licensing, privacy or platform gate remains unresolved.
