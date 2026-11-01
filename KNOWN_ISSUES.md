# Known beta limitations

- Beta.1 is not an approved public binary release until its release gates pass.
- Windows 11 x86_64 and Linux x86_64 are the only targets. macOS and ARM are unsupported.
- Native Windows 11 interactive install/portable/uninstall and a second Linux desktop
  require recorded exact-artifact tests; cloud automated checks are not manual tests.
- Physical hardware validation has covered an AMD RX 7700 XT on Linux/VAAPI.
  NVENC, Windows AMF, Intel QSV/VAAPI and broad hybrid/same-vendor systems remain unverified.
- Hardware needs host drivers/access. Several same-vendor default-device probes cannot
  identify the exact adapter; the assistant reports ambiguity.
- ASS rendering depends on available fonts. Embedded subtitle font extraction and
  bitmap-subtitle burn-in are not implemented.
- Queue contents, previews and attempt history are session-only; no crash-recovery database.
- No automatic updater, telemetry, driver installer or package-manager repair exists.
- Unsigned beta builds may trigger platform reputation warnings; signing status is
  disclosed per release. No Windows trust or universal Linux compatibility is claimed.
- Exact third-party source/license closure remains a binary-publication blocker;
  details are in docs/RELEASE_LICENSE_AUDIT.md.

Keep original media and report reproducible bugs with sanitized diagnostics.
