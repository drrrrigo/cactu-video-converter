"""Read-only OS graphics inventory. No external command-line utility is required."""

from __future__ import annotations

import ctypes
import os
import platform
import re
import stat
import sys
from pathlib import Path

from video_converter.models.hardware_diagnosis import (
    DistributionFamily,
    GpuDevice,
    GpuVendor,
    HardwareInventory,
    LinuxDistribution,
    RenderDevice,
)

VENDORS = {"1002": GpuVendor.AMD, "10de": GpuVendor.NVIDIA, "8086": GpuVendor.INTEL}


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")[:8192].strip()
    except OSError:
        return ""


def distribution(path: Path = Path("/etc/os-release")) -> LinuxDistribution:
    values = {}
    for line in read_text(path).splitlines():
        match = re.fullmatch(r"([A-Z_]+)=(.*)", line)
        if match:
            value = match[2].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[match[1]] = value
    identity = values.get("ID", "").lower()
    like = tuple(values.get("ID_LIKE", "").lower().split())
    family = DistributionFamily.UNKNOWN
    for token in (identity, *like):
        for names, candidate in (
            ({"arch", "cachyos", "manjaro", "endeavouros"}, DistributionFamily.ARCH),
            ({"debian", "ubuntu", "linuxmint"}, DistributionFamily.DEBIAN),
            ({"fedora", "rhel", "centos"}, DistributionFamily.FEDORA),
            (
                {"suse", "opensuse", "opensuse-tumbleweed", "opensuse-leap", "sles"},
                DistributionFamily.SUSE,
            ),
        ):
            if token in names:
                family = candidate
                break
        if family != DistributionFamily.UNKNOWN:
            break
    return LinuxDistribution(
        identity,
        like,
        values.get("NAME", "Unknown Linux distribution"),
        values.get("VERSION_ID", ""),
        family,
    )


def render_device(path: Path) -> RenderDevice:
    try:
        mode = stat.filemode(path.stat().st_mode)
    except PermissionError:
        return RenderDevice(str(path), None, False, False, "stat: permission denied")
    except FileNotFoundError:
        return RenderDevice(str(path), False, False, False)
    except OSError:
        return RenderDevice(str(path), None, False, False, "stat unavailable")
    return RenderDevice(str(path), True, os.access(path, os.R_OK), os.access(path, os.W_OK), mode)


def pci_device_name(
    vendor_id: str,
    device_id: str,
    paths=(Path("/usr/share/hwdata/pci.ids"), Path("/usr/share/misc/pci.ids")),
) -> str:
    """Optional local OS label database, never downloaded or required for detection."""
    for path in paths:
        try:
            with path.open(errors="replace") as stream:
                content = stream.read(4 * 1024 * 1024)
        except OSError:
            continue
        in_vendor = False
        for line in content.splitlines():
            if re.match(r"^[0-9a-fA-F]{4}\s", line):
                in_vendor = line[:4].lower() == vendor_id
            if in_vendor and re.match(r"^\t" + re.escape(device_id) + r"\s", line, re.I):
                return line[5:].strip()
    return ""


def linux_inventory(
    pci_root: Path = Path("/sys/bus/pci/devices"),
    drm_root: Path = Path("/sys/class/drm"),
    dri_root: Path = Path("/dev/dri"),
    release_file: Path = Path("/etc/os-release"),
) -> HardwareInventory:
    errors = []
    try:
        pci_entries = sorted(pci_root.iterdir())
    except OSError:
        pci_entries = []
        errors.append("PCI graphics inventory is unavailable in this environment.")
    try:
        renders = tuple(drm_root.glob("renderD*"))
    except OSError:
        renders = ()
    devices = []
    for entry in pci_entries:
        if not read_text(entry / "class").lower().startswith("0x03"):
            continue
        vendor_id = read_text(entry / "vendor").lower().removeprefix("0x")
        device_id = read_text(entry / "device").lower().removeprefix("0x")
        vendor = VENDORS.get(vendor_id, GpuVendor.UNKNOWN)
        driver_path = entry / "driver"
        try:
            driver = driver_path.resolve(strict=True).name
            detected = True
        except FileNotFoundError:
            driver, detected = "", False
        except OSError:
            driver, detected = "", None
        nodes = tuple(
            render_device(dri_root / node.name)
            for node in renders
            if (node / "device").resolve() == entry.resolve()
        )
        name = read_text(entry / "product_name") or read_text(entry / "label")
        label = pci_device_name(vendor_id, device_id) if not name else ""
        name = name or (
            f"{vendor.value} {label}"
            if label
            else f"{vendor.value} GPU (PCI {vendor_id}:{device_id})"
        )
        version = read_text(driver_path / "module" / "version")
        devices.append(
            GpuDevice(
                entry.name,
                vendor,
                name,
                vendor_id,
                device_id,
                driver,
                version,
                detected,
                nodes,
                "PCI display controller",
            )
        )
    return HardwareInventory(
        "linux",
        "Linux " + platform.release(),
        tuple(devices),
        distribution(release_file),
        tuple(errors),
    )


def windows_adapters() -> tuple[GpuDevice, ...]:
    """EnumDisplayDevicesW + read-only adapter registry; IDs precede model strings."""
    from ctypes import wintypes
    import winreg

    class DisplayDevice(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("DeviceName", wintypes.WCHAR * 32),
            ("DeviceString", wintypes.WCHAR * 128),
            ("StateFlags", wintypes.DWORD),
            ("DeviceID", wintypes.WCHAR * 128),
            ("DeviceKey", wintypes.WCHAR * 128),
        ]

    enum = ctypes.WinDLL("user32", use_last_error=True).EnumDisplayDevicesW
    enum.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(DisplayDevice),
        wintypes.DWORD,
    ]
    enum.restype = wintypes.BOOL
    found = []
    for index in range(64):
        item = DisplayDevice()
        item.cb = ctypes.sizeof(item)
        if not enum(None, index, ctypes.byref(item), 0):
            break
        if item.StateFlags & 8:  # DISPLAY_DEVICE_MIRRORING_DRIVER
            continue
        values = {}
        prefix = "\\Registry\\Machine\\"
        if item.DeviceKey.lower().startswith(prefix.lower()):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE, item.DeviceKey[len(prefix) :]
                ) as key:
                    for field in ("DriverVersion", "InstalledDisplayDrivers", "ProviderName"):
                        try:
                            values[field] = str(winreg.QueryValueEx(key, field)[0])
                        except OSError:
                            pass
            except OSError:
                pass
        found.append(
            windows_device(
                item.DeviceID,
                item.DeviceString,
                values.get("InstalledDisplayDrivers", ""),
                values.get("DriverVersion", ""),
                str(item.StateFlags),
            )
        )
    return tuple(found)


def windows_device(
    identifier: str, name: str, driver: str = "", version: str = "", status: str = ""
) -> GpuDevice:
    vendor_match = re.search(r"VEN_([0-9A-F]{4})", identifier, re.I)
    device_match = re.search(r"DEV_([0-9A-F]{4})", identifier, re.I)
    vendor_id = vendor_match[1].lower() if vendor_match else ""
    return GpuDevice(
        identifier or name,
        VENDORS.get(vendor_id, GpuVendor.UNKNOWN),
        name,
        vendor_id,
        device_match[1].lower() if device_match else "",
        driver,
        version,
        True if driver or version else None,
        (),
        status,
    )


def collect_inventory() -> HardwareInventory:
    if sys.platform.startswith("linux"):
        return linux_inventory()
    if sys.platform.startswith("win"):
        try:
            return HardwareInventory("win32", platform.platform(), windows_adapters())
        except (OSError, AttributeError) as exc:
            return HardwareInventory(
                "win32",
                platform.platform(),
                errors=(f"Windows adapter inventory unavailable: {type(exc).__name__}",),
            )
    return HardwareInventory(
        sys.platform, platform.system(), errors=("This OS has no built-in graphics inventory.",)
    )
