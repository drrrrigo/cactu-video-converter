"""Make exceptions in asynchronous Python/Qt slots fail their owning test."""

import sys
import traceback


def capture_qt_exceptions(test):
    previous = sys.excepthook
    errors = []
    sys.excepthook = lambda *args: errors.append("".join(traceback.format_exception(*args)))
    test.addCleanup(setattr, sys, "excepthook", previous)
    test.addCleanup(lambda: test.assertFalse(errors, "\n".join(errors)))
