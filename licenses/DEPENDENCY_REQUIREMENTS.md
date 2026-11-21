# Applicable redistribution requirements

This is an engineering classification, not human redistribution approval.
The selected release candidate uses release/controlled-baseline.json, not the
legacy FFmpeg provider manifest retained for test fixture generation.

* GPL-3.0 FFmpeg with static x264: provide the corresponding source of the
  combined executable, including the required source/build inputs and headers.
  The controlled source lock supplies exact FFmpeg, x264, libass, dav1d, oneVPL,
  NV headers and Windows AMF inputs. Including permissive static inputs here is
  for reconstructing that GPL executable, not an independent MIT source duty.
* Dynamically bundled LGPL libraries: supply the relevant library sources and
  changes, retain licenses/notices, and preserve replacement rights. Libraries
  remain separate files; no Cactu key is needed to replace/rebuild them. See
  NATIVE_LIBRARY_REPLACEMENT.md. Do not describe a deterministic rebuild as a
  universal legal prerequisite.
* MIT/BSD/Zlib/FTL/Apache libraries: retain their applicable notices, copyright,
  attribution/patent/license conditions. They do not generally require separate
  source publication merely because a retained source archive exists.
* GCC runtime code: assess the actual Runtime Library Exception; do not apply
  the compiler's GPL to the application automatically. Compiler-only programs
  and documentation are not declared shipped. Exception eligibility is distinct
  from the fact that a compiler package was downloaded.
* Python Windows _bz2 uses bzip2; _lzma incorporates public-domain liblzma from
  XZ 5.2.5, not the GPL xz scripts/tools; zlib-ng uses its permissive license;
  OpenSSL 3.5.7 uses Apache-2.0 and its incorporated notices. Their retained exact
  source identities support attribution; missing byte-identical extension
  reproduction is not itself a source-publication obligation under these terms.
* MSYS2 liblzma 5.8.4 is 0BSD, unlike the GPL tool/script options elsewhere in
  the same source package. gettext libintl is LGPL, unlike gettext programs.
  Actual DLLs and selected terms are mapped by hash in native-msys2/FILE-MAP.json
  on Windows. These records cover shipped libraries only.
* Qt/PySide eligible components use the recorded GPL v3 option with exact module
  source snapshots. Independent third-party terms (including ICU's permissive
  terms) remain applicable. Version/source attribution is not a claim that all
  optional Qt modules or all upstream third-party sources are incorporated.
* Inno-generated Setup/uninstaller preserve their original copyright/web UI.
  The documentation credits RemObjects Pascal Script. The LZMA2 compression
  setting selects LZMA runtime decoding; compiler-only compressor/SBOM entries
  are not automatically redistributed. Source-project tracing is recorded in
  the qualification evidence; no universal source offer is imposed by the Inno
  permissive license.
* The controlled AppImage prefix uses its actual link-map components only.
  LGPL source/relink material for libfuse/squashfuse is retained with objects,
  build information and replacement instructions. zstd uses BSD, zlib its own
  license, musl/mimalloc permissive terms, GCC its runtime exception and Linux
  UAPI headers the syscall exception. Ninety-nine bootstrap APKs are not ninety-
  nine shipped runtime components.
* Microsoft app-local runtime DLLs require their applicable redistribution grant
  and conditions. Their official supplier and non-preview flags alone do not
  establish the owner's qualifying rights. Current packages remain audit-only
  pending that owner/legal decision; no arbitrary DLL download is performed.

Global technical, human license and publication approval remain separate and
false. Proposed recipient assets and manual testing are bound to exact candidate
hashes before any promotion.
