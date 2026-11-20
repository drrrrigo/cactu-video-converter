"""Copy notices only for native OS packages actually selected by PyInstaller."""

import shutil
import re
from pathlib import Path
from payload_inventory import collect_origins, resolve_copy_origin, host_package


def collect_native_notices(destination: Path, root: Path):
    origins = collect_origins(root)
    copied = set()
    for key in origins:
        origin = resolve_copy_origin(origins, key)
        if not origin:
            continue
        source, _ = origin
        package = host_package(source)
        if not package:
            continue
        name = package["binary_package"].split(":")[0]
        notice = Path("/usr/share/doc") / name / "copyright"
        if notice.is_file() and name not in copied:
            target = destination / "native-system" / name / "copyright"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(notice, target)
            for common_name in set(
                re.findall(
                    r"/usr/share/common-licenses/([A-Za-z0-9.+_-]+)",
                    notice.read_text(errors="replace"),
                )
            ):
                common = Path("/usr/share/common-licenses") / common_name
                if common.is_file():
                    companion = destination / "native-system/common-licenses" / common_name
                    companion.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(common, companion)
            copied.add(name)
