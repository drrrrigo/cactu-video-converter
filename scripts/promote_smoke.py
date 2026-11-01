"""Re-test exact candidate artifacts on native runners without rebuilding bytes."""

import sys
import tempfile
import zipfile
from pathlib import Path
from branding_metadata import EXECUTABLE_NAME, __version__, appimage_filename
from package_smoke import smoke
from smoke_installer import test_installer

if __name__ == "__main__":
    directory = Path(sys.argv[1])
    if sys.platform == "win32":
        with tempfile.TemporaryDirectory() as temporary:
            with zipfile.ZipFile(directory / f"{EXECUTABLE_NAME}-Portable-{__version__}.zip") as z:
                z.extractall(temporary)
            smoke(Path(temporary) / EXECUTABLE_NAME / (EXECUTABLE_NAME + ".exe"))
        test_installer(directory / f"{EXECUTABLE_NAME}-Setup-{__version__}.exe")
    else:
        image = directory / appimage_filename()
        image.chmod(0o755)
        smoke(image)
