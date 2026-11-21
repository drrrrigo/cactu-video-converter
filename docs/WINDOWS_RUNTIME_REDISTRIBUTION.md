# Windows runtime redistribution decision record

Reviewed 2026-11-21 against the actual official Community 2026 and VC++ v14
runtime agreements. **Recommendation: use the implemented system-prerequisite
strategy for beta. Do not buy Visual Studio Professional merely for this issue.**
Free Community can supply redistribution rights for an eligible individual who
accepts its terms, but it does not automatically establish rights over every
third-party wheel copy. Owner acceptance and final license approval are not asserted.

The following ten files identify the historical app-local `3b19839` audit payloads
(ten paths in each of portable/installed inventories). New system-prerequisite
builds exclude these DLLs. The original hashes remain evidence, not new artifact
identities. All ten had zero prerelease flags. That flag alone does not establish
a redistribution grant.

| Exact payload file | Version | Supplier package | SHA-256 |
| --- | --- | --- | --- |
| _internal/PySide6/MSVCP140.dll | 14.44.35211.0 | PySide6_Essentials | 4c667b706893593812cd111b369ba6a77f54d1f1b1ae87cf3bf37692663cfba2 |
| _internal/PySide6/MSVCP140_1.dll | 14.44.35211.0 | PySide6_Essentials | d419d24b0a76366f5c9d908b0e45fe70e9e9154bb8ad5f3de42070f2337f857b |
| _internal/PySide6/MSVCP140_2.dll | 14.44.35211.0 | PySide6_Essentials | 89917964abb6ca16a260cab258e180c3abc239b5af00eed659d0edf0efdd339c |
| _internal/PySide6/VCRUNTIME140.dll | 14.44.35211.0 | PySide6_Essentials | f893ae75a1a24eea174d982f94bc80ce2448201eaa919a73c0653a5657685de4 |
| _internal/PySide6/VCRUNTIME140_1.dll | 14.44.35211.0 | PySide6_Essentials | 48aa2783793ea18ab3c2c71d420d4fff9814e662a1ff810053c6e5250061a716 |
| _internal/shiboken6/MSVCP140.dll | 14.44.35211.0 | shiboken6 | fd4a8c046fa3fea9ca6132f50cf8a56cf1e783b2d3093ba5c85fa063bc6b3845 |
| _internal/shiboken6/VCRUNTIME140.dll | 14.44.35211.0 | shiboken6 | de617641d82eac15595d2e39394163ac33e49bb032cf2c2ea0044ed39d3675e9 |
| _internal/shiboken6/VCRUNTIME140_1.dll | 14.44.35211.0 | shiboken6 | fa577d54bd10a91e52472da784a619da6cf241af45f0a0c48b27e91fa0fe6104 |
| _internal/VCRUNTIME140.dll | 14.51.36247.0 | CPython | d1f4225df2cd877dbf130d5668a021dce3f94118455ff5ec952061c30afc9ce7 |
| _internal/VCRUNTIME140_1.dll | 14.51.36247.0 | CPython | a7146c08f89fe5b04541ab507cdb59ff7b44534d4ba3c668a426c6450a03434e |


## Official terms and what Community establishes

Primary sources reviewed:

- [Community 2026 agreement](https://visualstudio.microsoft.com/license-terms/vs2026-ga-community/), official DOCX last updated October 1, 2025: Installation and Use Rights (individual license), Distributable Code, and Scope of License.
- [2026 REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution), explicitly including Community and the unmodified files under the installed `VC\redist` tree; preview/debug-nonredist files are excluded.
- [Microsoft redistribution guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files): a qualifying Visual Studio license is required for redistribution, not just receipt of a wheel.
- [VC++ v14 end-user runtime agreement](https://visualstudio.microsoft.com/license-terms/vs2026-ga-visualcpp-v14-redist-runtime/): installation/use rights are separate from a developer redistribution grant.
- [Community eligibility](https://visualstudio.microsoft.com/vs/community/) and [v14 compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017): individual own-application development is eligible; supported newer v14 runtimes serve older supported v14 binaries, with the documented version restrictions.

On the owner's stated individual/own-application facts, the free Community route
is available in principle. Free/open-source status is not a paid-license trigger.
The grant is conditional: meaningful application functionality, protection of the
Microsoft code in downstream terms, the stated indemnity, no preview/Insiders
redistribution, no misleading Microsoft branding, preservation of notices, and
no subjecting Microsoft code to source/copyleft obligations. These obligations
apply to Microsoft code; they must not be imposed on Cactu's GPL source itself.
Human review must assess that separation and the actual distribution agreement, using the applicable GPLv3 System Library provisions for the actual components. This is not a blanket conclusion that GPLv3 forbids Microsoft runtime use or requires a paid compiler license. No GPL exception or upstream license is changed.
A Community entitlement does not automatically cover every old release or altered
supplier file merely because its basename appears familiar.

The official agreement DOCX hashes, download identities and per-file comparison
are retained in `release/evidence/microsoft-runtime-review/files-and-official-terms.json`.
The DOCX documents and downloaded installers/wheels remain local audit inputs;
no installer was executed, no owner's terms accepted, and no Microsoft binary was
committed or published. The audit does not require a paid edition or byte-identical
rebuilding of CPython/Qt.

## Exact-file findings, including wheel origins

| Files above | Provenance / byte evidence | Grant conclusion |
| --- | --- | --- |
| Eight PySide6/Shiboken6 DLLs, 14.44.35211.0 | Re-extracted from exact hash-pinned 6.11.2 wheels; all match the historical payload hashes. Normalized images match Microsoft's official 14.44 redistributable; certificate tables include The QT Company Oy. Whole files differ from the Microsoft copies. | Executable-content identity supports origin attribution. It does not itself settle whether re-signing meets Microsoft's unmodified-file condition or establish Qt's downstream permission to this owner. Do not approve these exact wheel copies automatically. |
| Two CPython DLLs, 14.51.36247.0 | Exact SHA-256 matches to the official CPython 3.14.7 embeddable ZIP. No exact same-revision Microsoft-direct copy was located in the reviewed downloads. | CPython origin is established; the supplier package alone is not proof of the owner's redistribution grant for these bytes. |
| Current official Microsoft downloads | Reviewed `vs/17/release` archive is 14.44.35211; current `vc14` archive is 14.52.37029. The 14.52 sample differs from the original 14.51 pair. | These are potential canonical inputs after valid entitlement and terms review, not automatic authorization of current wheel files. |

The normalized comparison excludes only the PE checksum, security-directory entry
and certificate table, leaving all other file bytes intact. It shows matching
content for the eight Qt DLLs, **not** identical whole files, cryptographic
Authenticode-chain validation, or proof that re-signing was unauthorized.
`scripts/review_windows_runtime_files.py` reproduces the comparison from cached
extracted inputs and checks each supplier file against its exact payload SHA.
The Python ZIP SHA is `d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15`.

## Optional free Community route to self-contained packages

No paid upgrade is recommended. If the owner prefers to restore app-local runtime
packaging later, the concrete steps are:

1. Obtain stable **Visual Studio Community 2026** from Microsoft (not VS Code,
   a trial/Insiders build, or an assumed entitlement from GitHub runners). Review
   and personally accept its terms; record the edition, installed version,
   acceptance date, license-document identity and individual own-application
   eligibility. Activate/sign in if the product requests it. No acceptance is
   performed by this project or its CI.
2. Install the relevant C++ redistributable workload/components and identify the
   actual installed `VC\Redist` files or the officially supplied redistributable
   covered by that license. Record Microsoft source, exact versions/hashes and
   signature verification. For 14.44, establish the applicable version-specific
   grant (for example a valid free Community 2022 entitlement or actual 2026
   REDIST contents); do not infer retroactive coverage from a 2026 URL alone.
3. Prefer canonical **unaltered Microsoft files**, replacing wheel re-signed
   copies when required. A supported newer official v14 set can avoid keeping
   multiple older supplier revisions, subject to ABI/import and frozen tests.
   Do not patch signatures, rename arbitrary internet DLLs, or treat normalized
   hashes as whole-file approval. Canonical replacement changes artifact hashes.
4. Review and integrate the applicable Microsoft terms/notices and required
   downstream protection for Microsoft components in installer **and portable**
   distribution, separately from Cactu's GPL permissions. The scoped CPython notice now shown by Setup is not itself an approval to add standalone runtime DLLs.
   Confirm the legal treatment of the standard runtime/system-library boundary.
5. Make an explicit human strategy/license decision, implement the reviewed
   app-local policy, rebuild, re-inventory, re-qualify on clean Windows, and bind
   approvals/manual results to the **new** binaries/source index. No flags turn
   true merely because Community was downloaded or installed.

This preserves a feasible free path to self-contained installer/portable packages.
It is optional; it is not the selected implementation for the present fallback.

## Embedded CPython code remains a separate condition

The official CPython Windows ZIP also contains **Additional Conditions for this
Windows binary build** in LICENSE.txt, covering Microsoft Distributable Code
incorporated by the linker into interpreter/extensions. Removing the separate
runtime DLLs does not remove that notice or its downstream obligations. The PSF
statement describes redistribution conditions for its Windows build; it does not
require Cactu's developer to buy Visual Studio.

The exact full upstream Windows LICENSE.txt is retained as
`licenses/python-native/CPython-3.14.7-WINDOWS-LICENSE.txt`, SHA-256
`935cf13e19f8c31b497d20b05d73623431a226b230c3599bc30fa3348979bc68`.
It is copied unchanged into the Windows license payload. Setup's explicit license
page separates Cactu's GPL text from the CPython Windows binary terms; the portable
folder includes `WINDOWS-THIRD-PARTY-LICENSES.txt` and points to it before use.
These terms protect their Microsoft code, not Cactu's source or Python programs.
Final human review remains required; retaining this notice is not automatic
license approval. The Qt wheel notice files did not establish a separate Microsoft
runtime sublicense; the limited notice search is recorded in wheel-notice-review.json.

## Implemented fallback: Microsoft runtime installed by the end user

`release/windows-runtime-policy.json` selects `system-prerequisite`. The build
filters MSVCP/VCRUNTIME DLLs out of PyInstaller collection at **every path**, then
rejects any remaining copies before packaging. GCC/MSYS runtime dependencies,
Qt/Python and FFmpeg remain included; their independent source/notices are retained.
No Microsoft redistributable installer is bundled.

A small GPL C launcher is installed as `CactuVideoConverter.exe`; the existing
PyInstaller program is `CactuVideoConverter-core.exe` in the same folder. The
launcher is compiled with `-nostdlib` and verified to import only Windows APIs
(kernel32/user32/shell32/version), so it can explain a missing VC++ dependency
**before Python/Qt is loaded**. It checks the actual x64 System32 versions and
loadability of all five required runtime DLL names, not just an uninstall/registry
flag. It then forwards the original command arguments and child exit code.
The test-only directory override is absent from the production binary.

The conservative qualification floor is **14.51.36247.0**, based on the CPython
supplier runtime. It is not presented as a proven minimum ABI for every component.
The current Microsoft v14 x64 package can be obtained directly from the
[official guidance page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
X86 alone is insufficient for this x64 application. An existing newer compatible
x64 runtime is accepted. Repair/upgrade is the user's explicit action.

| Workflow | Behavior |
| --- | --- |
| Setup | Extracts the CRT-independent check to a temporary folder and blocks installation before copying application files if it fails. Displays the required version, X64 architecture and official guidance; no downloader or prerequisite installer invocation. Silent install fails nonzero. |
| Portable | Same visible `.exe` checks before loading Python. Offers to open Microsoft's guidance page only after an explicit Yes. `PREREQUISITES.txt` explains the requirement. Do not launch `-core.exe` directly. |
| Offline | Works when the system prerequisite is installed. Otherwise obtain Microsoft's installer separately beforehand and install it directly under its own terms. The archive is no longer fully self-contained on a bare machine. |
| Existing machines | Native hosted smoke exercises the installed-runtime case; it does not establish absence behavior on clean Windows. |
| Publication | Existing gates remain; an additional gate requires exact-artifact missing/installed clean-guest receipts in protected manual evidence. No legal or publication approval is auto-completed. |

No Visual Studio purchase or developer redistribution grant for these omitted
Microsoft DLLs is needed for **this fallback**. The user installs Microsoft's
runtime directly under Microsoft's end-user agreement. This does not waive the
independent approvals for Cactu's other bundled components.

## Clean Windows qualification: pending, by owner instruction

The owner answered on 2026-11-21 that no clean Windows machine/VM is available and
requested this validation remain pending. There is no local Windows VM/KVM here;
GitHub Windows runners have preinstalled software. No clean-machine pass is claimed.

Prepared validation:

- `packaging/windows/New-RuntimeSandbox.ps1` creates an offline WSB mapping
  artifacts/scripts read-only and an evidence folder writable. An eligible
  Windows Sandbox host is one option; a clean Windows 11 x64 VM works too.
- Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\CactuScripts\Test-CleanWindowsRuntime.ps1 -Phase Missing -ArtifactFolder C:\CactuArtifacts` (process-local script policy, no global change).
  It refuses a baseline with any relevant system VC DLL already present, checks
  portable exit 10 and Setup refusal, and records exact ZIP/Setup hashes.
- The tester obtains Microsoft's official x64 installer separately, reads/accepts
  its terms and installs it **interactively**. No test script installs it.
- In the **same guest**, run the script with `-Phase Installed`. It requires the
  earlier exact-artifact/guest receipt, checks portable and installed conversion,
  preview, loudness/subtitle queue smoke, absence of bundled Microsoft runtimes,
  and uninstallation. Receipts are `runtime-missing.json` and `runtime-installed.json`.
- Insert those full receipts under `windows_runtime.missing` and
  `windows_runtime.installed` in the protected exact-candidate manual record.
  Mismatched binaries/guests, older/partial runtimes, missing scenarios or a hosted
  machine falsely submitted as the missing baseline are rejected. Ordinary manual
  desktop tests and owner approval are still required separately.

**Concrete remaining engineering criterion:** obtain both PASS receipts for the
same new Windows portable/installer hashes on a genuinely clean Windows 11 x64
guest. Responsible: owner/tester with such a guest. Prepared automation is not an
executed clean-machine result. The previous `3b19839` binaries and their source
index are not receipts for the changed packaging.

## Native verification

Final prerequisite packaging source: `dd1570a`. The earlier focused launcher diagnostic used `c8b95c4`.
194 local controlled tests passed, including physical AMD VAAPI, in 74.357 seconds. The later notice-only packaging change is checked by the native package test.
The focused native launcher checks passed in
[44936706596](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44936706596):
only KERNEL32/SHELL32/USER32/VERSION imports, production System32 prerequisite
accepted, isolated missing/older directories rejected; PowerShell 5.1 parsed both
clean-guest helpers. These are not clean-machine acceptance results.

Controlled package refresh attempts 44936430729 and 44936760492 failed during MSYS
source acquisition, before compilation. Attempt
[44937153110](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44937153110)
used native CPython instead and still received connection refusal. In a fresh
checkout the first requested source is the locked FFmpeg codeload.github.com TAR.
The transport change is not reported as resolving the external access
problem. No source hash, recipe, selected controlled baseline or approval was
weakened. No further blind retries are used.

A separate packaging experiment exercises the existing build_release code with
the exact pinned reference-provider **test fixture** via a scoped test double.
It is labelled `PREREQUISITE_TEST_FIXTURE_NOT_RELEASE`, cannot establish controlled
FFmpeg provenance and does not alter the release's selected implementation. Its
metadata-only results are recorded below. Cleanup of all ten exact old app-local
paths on upgrade is also tested; no system directory is modified. A successful fixture
must not be promoted as the new controlled candidate or use the old 3b19839 source
index for changed packages.

Remaining engineering verification in addition to the owner-deferred clean test:
re-run the normal Windows controlled build once access to the locked upstream
sources is available, then retain new source/artifact inventories and hashes.
Responsible: build infrastructure/maintainer; criterion: successful normal native
controlled source/build/frozen/installer run with zero bundled MSVCP/VCRUNTIME.
The existing local caches remain retained; unapproved source archives are not
uploaded merely to bypass the network failure. No beta tag, Release, public binary, Microsoft
installer upload or automatically accepted license is created.


Final prerequisite packaging experiment: [44938875061](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44938875061),
clean source `dd1570afacb2e12df7976f22128221e1e51f9b1b`, **SUCCESS**.
It exercises the actual build_release/PyInstaller/Inno pipeline with a scoped
reference-runtime test fixture. Portable has 488 files, installed has 490; neither
contains MSVCP/VCRUNTIME DLLs. Both contain the exact upstream Windows CPython
notice SHA above, the scoped root notice, native launcher and frozen core.
ONEDIR/portable/installed software conversion, preview, subtitle/loudness queue
and uninstall passed. Ten harmless legacy DLL-path placeholders were seeded to
verify upgrade cleanup; both application executables are checked after uninstall.
PowerShell 5.1 parsed the clean-guest scripts. Metadata-only receipt/inventories:
`release/evidence/microsoft-runtime-review/prerequisite-fixture-dd1570a/`.

This result establishes the prerequisite packaging behavior on the hosted system.
It is **not RC1, not clean-Windows evidence, not a controlled-FFmpeg refresh, and
not a downloadable binary**. Normal release gates remain false. Source CI [44938875257](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44938875257) passed for the same final source on both Windows 2025 and Ubuntu 22.04: 194 discovered tests, 191 passed plus three physical-GPU skips on each; Ruff, branding and full source/history pattern scans passed. Current-tree source/privacy scanning also passed. A later report-only commit does not change the tested package parent.
