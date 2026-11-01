"""Atomic output publication that cannot clobber a concurrently created file."""

from __future__ import annotations

import ctypes
import errno
import os
import sys
from pathlib import Path


def commit_output(partial: Path, destination: Path, *, overwrite: bool = False) -> None:
    if overwrite:
        os.replace(partial, destination)
        return
    if os.name == "nt":
        os.rename(partial, destination)  # Windows rename fails if destination exists.
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is not None:
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename.restype = ctypes.c_int
            if rename(-100, os.fsencode(partial), -100, os.fsencode(destination), 1) == 0:
                return
            code = ctypes.get_errno()
            if code not in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise OSError(code, os.strerror(code), str(destination))
    # Safe fallback; never substitute a check-then-replace race. If the filesystem
    # cannot provide a no-clobber operation, fail rather than overwrite user data.
    os.link(partial, destination)
    partial.unlink()
