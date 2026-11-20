# Beta.1 release checklist and promotion

**Authoritative current states:** [BETA1_RELEASE_CHECKLIST](BETA1_RELEASE_CHECKLIST.md).
The dated results below are historical. No RC1 is currently declared; technical
license/source closure remains blocked. This procedure does not authorize a tag,
release or public binary upload during preparation.

## Current owner decisions

Repository: https://github.com/drrrrigo/cactu-video-converter.
Cactu source license: GPL-3.0-or-later (owner-confirmed 2026-11-01).
No public beta tag or binary release is authorized by an incomplete audit/test.

## Recorded automated checks (2026-11-01)

Source commit `ccb4e33` passed the complete native Windows/Linux source matrix:
[CI run 41350221215](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221215).
Each ran 148 tests with three optional physical-GPU skips. The local RX 7700 XT
run passed all 148 with no skips. Current source/history/privacy scans have no
findings; `security_audit_approved` records that bounded audit, not certification.

[Candidate run 41350221053](https://github.com/drrrrigo/cactu-video-converter/actions/runs/41350221053)
successfully built/tested Windows ONEDIR/portable/Setup (including automated
install/convert/uninstall) and Linux AppImage. Both jobs then intentionally failed
the unapproved license gate before public artifact upload. No retained approved
candidate/manual test/checksum/tag/release set is claimed. License/source closure
and real Windows 11/Linux desktop manual evidence remain required below.

## Before distributing any binary candidate

- Complete docs/RELEASE_LICENSE_AUDIT.md against the exact shipped builds.
- Archive all matching FFmpeg/linked-component sources and notices, not just a
  build-script URL/GPL text. Review Qt/Python/native-library obligations.
- Set the corresponding-source/redistribution approvals in the pinned manifest
  only after actual evidence is present; approve the exact license audit in
  release/config.json. Public Actions artifact uploads are also distribution.
- Audit current source and every Git revision. Do not publish credentials/history
  or the supplied old mockup containing a personal home-directory label.
- Record/approve the audit, then commit final beta source; no unrelated features.

## Build and test candidate

Run the candidate workflow with workflow_dispatch on the intended release commit.
Separate Windows/Linux jobs stage/check pinned binaries, run the suite, build
native packages and perform frozen smoke conversions with PATH empty. Windows also
extracts/tests the portable ZIP and installs/converts/uninstalls Setup automatically.
Those cloud tests do not replace the specified manual Windows 11/desktop tests.
Candidates are uploaded only if distribution/licensing policy passes.

Workflow dispatch now defaults to an audit build, labelled AUDIT_ONLY_NOT_RC1.
It retains only generated JSON/checksum text before the binary distribution gate.
`--rc1` requires completed technical/source review and rejects actual payloads with
open reviews. The internal candidate ID becomes 0.1.0-beta.1-rc1 while the embedded
application version stays 0.1.0-beta.1, allowing the same tested bytes to be promoted.
Packaging requires a clean Git checkout, standard Python 3.14.7 and exact dependencies.
Each actual installed/extracted payload is inventoried, including embedded modules.

Download exact artifacts. Complete the manual checklist in
release/manual-evidence.example.json on clean Windows 11 and a second Linux desktop
where practical. Include source commit, OS/kernel, checks and all three SHA-256
values. Do not commit this attestation after testing and thereby change the tested
commit; store it as BETA_MANUAL_EVIDENCE in the protected public-beta environment.
Set BETA_CANDIDATE_RUN_ID to the successful candidate run. Preserve its artifacts.

Use the concrete [Windows](MANUAL_TEST_WINDOWS_BETA1.md) and
[Linux](MANUAL_TEST_LINUX_BETA1.md) guides. Required scenario IDs need PASS results,
tester/date/OS details and exact artifact hashes. A passed=true switch alone fails.
Keep results outside the tested source tree. Any changed source/binary requires a
new reviewed candidate and matching tests. Generate the complete SHA256SUMS with
`python scripts/checksums.py RC_DIRECTORY` only when all three exact files exist;
per-platform fragments alone are not the final checksum set.

Final publication approval is external: fill release/owner-approval.example.json
as BETA_OWNER_APPROVAL in the protected public-beta environment only after the owner
separately instructs **Publish the beta**. It binds owner/date/version/source SHA
and the exact three tested hashes. A committed publication_approved boolean alone
cannot publish. Do not change the tested source commit merely to record approval.
Human license/source approval must be resolved before freezing the final RC inputs;
this external record handles final publication authorization after manual testing.

## Promote without rebuilding

Once all source/audit/policy fields are approved, tag the exact tested source commit
v0.1.0-beta.1 and push that tag. Tag jobs verify the candidate run's source SHA/event/
workflow, download its exact bytes, re-smoke them on native OS runners and re-upload
unchanged files. The protected publish job verifies manual evidence and byte hashes,
generates SHA256SUMS.txt and creates a GitHub **pre-release** with the required files.
It does not overwrite an existing release or attach rebuilt/unreviewed bits.

If anything changes, create/test a new candidate from the new commit and record new
hashes. Never fake a manual test, source/license closure or a green gate. Unsigned
status must be disclosed. Signing hooks read external certificate selectors only;
no private key/certificate is committed. The final source, workflow run IDs, exact
hashes, manual evidence and release URL belong in the implementation report.

After the owner's separate explicit publication instruction, check out the **exact
tested SHA**, verify `git status --porcelain` is empty, create an annotated
v0.1.0-beta.1 tag at that SHA and push only that tag. Do not blindly tag a newer main
commit or execute this step during preparation. The protected publisher additionally
requires complete matching payload inventories, manual results and owner attestation.
