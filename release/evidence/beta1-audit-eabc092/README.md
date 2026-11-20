# Retained beta.1 audit reports — not RC1

These files contain metadata/checksums only, not executable archives, source
archives or private media. They were downloaded from the metadata-only artifacts
of [run 44810167815](https://github.com/drrrrigo/cactu-video-converter/actions/runs/44810167815)
at clean source `eabc0920b4d091cba3b6670b263182babca7e539`.

Both native build/smoke steps passed. The overall run failed at the intended
technical distribution gate; application binary uploads were skipped. The Windows
runner's installer/ZIP were not retained as a transferable owner-test RC set.
An audit artifact hash does not make missing bytes available for manual testing.

Each platform directory retains the original JSON and generated checksum fragment.
The payload files describe actual extracted/installed files and embedded modules,
including separate outer executable container records. Runtime-evidence files
retain actual FFmpeg/FFprobe version/configuration/license/capability output.
Build receipts describe Python/dependency versions, source SHA and runner image.
`receipt.json` hashes every original report and records the run/artifact/job IDs.

Report field `technical_license_complete` is false. Origins/terms/source/notices
remain incomplete, as explained in [the license audit](../../../docs/RELEASE_LICENSE_AUDIT.md).
No report is a final RC approval, owner attestation or complete source offer.
Do not promote these hashes as beta download checksums.

To check that the retained report bytes match their receipt from the repository
root (Python source tooling only; no dependencies required):

```python
import hashlib
import json
from pathlib import Path

root = Path('release/evidence/beta1-audit-eabc092')
receipt = json.loads((root / 'receipt.json').read_text())
for name, expected in receipt['report_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
```

Current readiness and manual guides are linked by
[BETA1_RELEASE_CHECKLIST](../../../docs/BETA1_RELEASE_CHECKLIST.md).
