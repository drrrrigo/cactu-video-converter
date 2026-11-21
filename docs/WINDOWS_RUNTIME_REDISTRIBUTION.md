# Windows runtime redistribution decision record

Reviewed 2026-11-21. No ownership/license eligibility is inferred from an official
wheel or CPython installer. The following exact audited files remain unchanged.
Their origins and resource versions are known, and no prerelease PE flag was found.
That is technical evidence, not the owner's redistribution grant.

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

Microsoft conditions distribution on the applicable Visual Studio license and
REDIST terms. The listed unmodified runtime files still require the relevant
edition's grant; preview components are excluded. Review the applicable
[redistribution conditions](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)
and [2026 REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution).
No qualifying Visual Studio license has been asserted for the owner. Existing
false approval fields remain unchanged; no arbitrary DLL is substituted.

## Prerequisite alternative (not implemented)

A future package could omit app-local VC runtime files and require the user to
install Microsoft's supported redistributable directly. Before proposing it,
verify actual import/ABI compatibility on clean Windows and retain clear manual
installation instructions. A supplier file's version alone does not establish the
minimum runtime required by every imported symbol.

This would make a bare-machine portable ZIP depend on a system prerequisite. Offline
users would need an already installed runtime or a separately obtained installer;
Cactu must not download/install it silently. An installer would need a preflight
check with an explicit failure/help path. Bundling Microsoft's installer would
still require permission review. This alternative has not changed Cactu's current
self-contained packaging and does not claim that a prerequisite fixes every legal
condition. Decide only after the technical tests and eligibility review.


## Owner decision recorded — 2026-11-21

The owner answered that qualifying redistribution rights are not known and
requested this remain a legal pending item. Classification: **HUMAN LEGAL / OWNER
DECISION**, not a missing compiler/source scan. Current app-local files stay in
AUDIT candidates; neither the global technical/license/publication fields nor
this supplier grant is self-approved.

A precise alternative, if the owner selects it after review, is system-only
Microsoft VC14 x64 runtime installation from Microsoft's [official supported
redistributable page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170). The user obtains it directly; Cactu would not redistribute
or silently download it. Engineering steps would be: omit only the ten mapped
app-local VC DLL paths, perform installer prerequisite detection against the
supported x64 runtime and actual import requirements, give a clear prerequisite
error/link before install, and retest on clean Windows 11 without preinstalled
runtime and again after official installation. Avoid inferring the minimum ABI
only from the largest bundled DLL's resource version.

| Workflow | Consequence / required acceptance |
| --- | --- |
| Installer | Explicit preflight and help; no hidden download, arbitrary DLL or automatic prerequisite installation. Retest install/convert/uninstall on a clean machine. |
| Portable ZIP | No longer self-contained on machines without the system runtime. Provide a visible prerequisite README; Python cannot reliably show a custom GUI if its own loader dependency is absent. Validate both missing/present runtime cases. |
| Offline | Requires runtime already installed, or an official installer obtained separately beforehand. Do not bundle that installer without its own applicable redistribution permission. |
| First launch | System loader may fail before Cactu starts when prerequisite is absent; documentation/preflight must account for that rather than promising an in-app recovery dialog. |
| Existing automated tests | Current Windows hosted runners already have runtime software and cannot prove clean-machine prerequisite handling. Add isolated clean-Windows tests for a changed strategy. Existing self-contained smoke stays applicable to audit bundles only. |

Completion criterion for the present app-local strategy: owner/legal reviewer
records the applicable edition/license/REDIST grant covering these exact files,
versions and intended redistribution. Alternative completion criterion: an
explicit owner strategy choice followed by the concrete implementation and clean-
machine tests above. This record requests no approval to compensate for an
unimplemented prerequisite strategy. No extra source publication is imposed on
the proprietary Microsoft files.
