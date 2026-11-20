# Native library replacement and source information

Cactu's ONEDIR/portable/AppImage application payload uses separate native Qt,
Python and other shared libraries. Cactu adds no signature or hash enforcement
that prevents replacing these libraries. Their licenses retain any applicable
rights to modify/reverse engineer for debugging modifications. This document does
not change their terms or assert that every native component is LGPL licensed.

Close Cactu and keep a backup before replacing a library. The replacement must
match the target architecture, Python extension ABI and Qt module ABI, as well as
the dependencies of the replaced file. Use the actual payload inventory to find
the module and relative path, including aliases and plugins. Qt is pinned to
6.11.2; PySide/Shiboken must remain mutually compatible. Keep associated native
dependencies and plugins together. Cactu does not supply a replacement warranty.

Windows portable/installed files are beneath `_internal/`. For an AppImage,
extract a copy with `--appimage-extract`; its application files are under
`squashfs-root/usr/bin/_internal/`. Launch the extracted AppDir's `AppRun` to test
library replacements without changing the original AppImage. Preserve notices
and source/relinking terms for any redistribution of modified components.

Versioned source references, input hashes and notice provenance are in the source
lock and per-file payload records. The license directory includes source-module
license texts and a conservative attribution superset. For copied Debian libraries,
the native-system directory retains package copyright files and referenced common
license texts. A source URL or text collection alone does not establish complete
matching source delivery; unresolved correspondence blocks beta distribution.

The outer AppImage ELF runtime is statically linked and requires a separate
relinking review. Replacing a Qt shared library does not replace that runtime.
The experimental controlled-runtime build retains runtime.o, linker script/map,
static-input provenance and build instructions locally; it is not yet an approved
source/relinking distribution. Public source/binary delivery remains gated.
