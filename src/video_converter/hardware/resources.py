"""Reviewed static support links and conservative, command-free setup guides."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from video_converter.models.hardware_diagnosis import (
    DistributionFamily,
    FailureCategory,
    GpuVendor,
    HardwareFinding,
)

REVIEWED = "2026-10-27"
APPROVED_HOSTS = frozenset(
    {
        "www.amd.com",
        "www.nvidia.com",
        "www.intel.com",
        "wiki.archlinux.org",
        "wiki.debian.org",
        "documentation.ubuntu.com",
        "docs.fedoraproject.org",
        "en.opensuse.org",
    }
)


@dataclass(frozen=True)
class DriverSupportResource:
    id: str
    vendor: GpuVendor
    platform: str
    label: str
    url: str
    description: str
    last_reviewed: str = REVIEWED


RESOURCES = (
    DriverSupportResource(
        "amd",
        GpuVendor.AMD,
        "any",
        "Official AMD Driver Support",
        "https://www.amd.com/en/support",
        "Choose the product and operating system on AMD's support site.",
    ),
    DriverSupportResource(
        "nvidia",
        GpuVendor.NVIDIA,
        "any",
        "Official NVIDIA Drivers",
        "https://www.nvidia.com/en-us/drivers/",
        "Review the official driver options for your GPU and operating system.",
    ),
    DriverSupportResource(
        "intel",
        GpuVendor.INTEL,
        "win32",
        "Official Intel Driver Support",
        "https://www.intel.com/content/www/us/en/support/detect.html",
        "Notebook and OEM systems may need the manufacturer's approved graphics driver.",
    ),
    DriverSupportResource(
        "arch",
        GpuVendor.UNKNOWN,
        "linux",
        "Arch / CachyOS Graphics Guidance",
        "https://wiki.archlinux.org/title/Hardware_video_acceleration",
        "Review your distribution's graphics stack and VAAPI/NVENC/QSV support.",
    ),
    DriverSupportResource(
        "debian",
        GpuVendor.UNKNOWN,
        "linux",
        "Debian Hardware Video Acceleration",
        "https://wiki.debian.org/HardwareVideoAcceleration",
        "Use the documentation for your installed distribution release.",
    ),
    DriverSupportResource(
        "ubuntu",
        GpuVendor.UNKNOWN,
        "linux",
        "Ubuntu Graphics Driver Documentation",
        "https://documentation.ubuntu.com/server/how-to/graphics/install-nvidia-drivers/",
        "Official Ubuntu NVIDIA setup documentation; check Desktop/OEM policy as appropriate.",
    ),
    DriverSupportResource(
        "fedora",
        GpuVendor.UNKNOWN,
        "linux",
        "Fedora Official Documentation",
        "https://docs.fedoraproject.org/en-US/quick-docs/",
        "Consult graphics and multimedia guidance for your Fedora release.",
    ),
    DriverSupportResource(
        "suse",
        GpuVendor.UNKNOWN,
        "linux",
        "openSUSE Graphics Guidance",
        "https://en.opensuse.org/SDB:Configuring_graphics_cards",
        "Consult the guidance for the installed openSUSE/SUSE release.",
    ),
    DriverSupportResource(
        "intel-linux",
        GpuVendor.INTEL,
        "linux",
        "Intel Graphics Media Stack",
        "https://www.intel.com/content/www/us/en/developer/topic-technology/open/graphics-media-stack/overview.html",
        "Official explanation of Intel's Linux media components.",
    ),
)


def resource(identifier: str) -> DriverSupportResource | None:
    return next((item for item in RESOURCES if item.id == identifier), None)


def trusted_url(item: DriverSupportResource) -> bool:
    parts = urlsplit(item.url)
    return (
        item in RESOURCES
        and parts.scheme == "https"
        and parts.hostname in APPROVED_HOSTS
        and not parts.username
        and not parts.password
        and parts.port in (None, 443)
    )


@dataclass(frozen=True)
class DriverGuide:
    id: str
    title: str
    explanation: str
    steps: tuple[str, ...]
    resources: tuple[DriverSupportResource, ...] = ()
    last_reviewed: str = REVIEWED
    optional_commands: tuple[str, ...] = ()


BUILD_CATEGORIES = {
    FailureCategory.FFMPEG_ENCODER_MISSING,
    FailureCategory.APPLICATION_PACKAGING_ERROR,
}


class DriverGuideRegistry:
    def lookup(self, finding: HardwareFinding, platform: str, distro) -> DriverGuide:
        category, device = finding.category, finding.device
        vendor = device.vendor if device else GpuVendor.UNKNOWN
        if category == FailureCategory.AVAILABLE:
            return DriverGuide(
                "available", "Ready to encode", "The actual FFmpeg initialization probe passed.", ()
            )
        if category in BUILD_CATEGORIES:
            return DriverGuide(
                "runtime-build",
                "Check the Cactu / FFmpeg build",
                "Driver changes cannot add an encoder or filter to FFmpeg.",
                (
                    "Copy Diagnostics and check the runtime/build supplied with Cactu.",
                    "Use Software x264 while obtaining a corrected application build or development runtime.",
                ),
            )
        if category == FailureCategory.GPU_DETECTED_ENCODER_UNSUPPORTED:
            return DriverGuide(
                "unsupported",
                "Use Software x264",
                "The probe reports that the requested encoder is unsupported. Updating drivers is not guaranteed to add hardware support.",
                ("Use Software x264 or another backend that passed its probe.",),
            )
        if category == FailureCategory.NO_SUPPORTED_GPU:
            return DriverGuide(
                "software",
                "Software encoding is supported",
                "A hardware encoder is optional.",
                ("Continue with Software x264.",),
            )
        steps = [
            "Review the detected device and failure details, then follow official support documentation.",
            "After any system changes, return here and choose Test Again.",
        ]
        if category == FailureCategory.DEVICE_PERMISSION_DENIED:
            steps[0] = (
                "Review device access and session/container policy with your system administrator. Device groups vary by distribution; Cactu does not change them."
            )
        if category == FailureCategory.DEVICE_NODE_MISSING:
            steps[0] = (
                "Check whether the graphics driver exposes a render device to this desktop/session or container. Cactu does not load drivers or create nodes."
            )
        if category == FailureCategory.MULTIPLE_GPU_AMBIGUITY:
            steps[0] = (
                "Several adapters match this default-device probe. Its success or failure cannot be attributed to one adapter. Node-specific results are shown separately."
            )
        if platform.startswith("win"):
            key = {GpuVendor.AMD: "amd", GpuVendor.NVIDIA: "nvidia", GpuVendor.INTEL: "intel"}.get(
                vendor
            )
            ids = [key] if key else []
            explanation = "An installed driver or media runtime may be incomplete or incompatible; a driver update is not a guaranteed fix."
            if vendor == GpuVendor.INTEL:
                steps.append(
                    "For OEM notebooks, review the manufacturer's approved graphics-driver policy first."
                )
            guide_id = f"windows-{vendor.value.lower()}"
        else:
            key = {
                DistributionFamily.ARCH: "arch",
                DistributionFamily.DEBIAN: "debian",
                DistributionFamily.FEDORA: "fedora",
                DistributionFamily.SUSE: "suse",
            }.get(distro.family)
            if distro.id == "ubuntu" and vendor == GpuVendor.NVIDIA:
                key = "ubuntu"
            fallback = {
                GpuVendor.AMD: "amd",
                GpuVendor.NVIDIA: "nvidia",
                GpuVendor.INTEL: "intel-linux",
            }.get(vendor)
            ids = [key] if key else ([fallback] if fallback else [])
            explanation = (
                "Review the distribution's graphics/media stack and session access. "
                "AMD Linux normally uses the distribution's kernel/Mesa stack; AMDGPU-PRO is not assumed."
            )
            if not key:
                explanation = "This Linux distribution has no built-in driver guide. Review the technical diagnosis and your distribution's official graphics documentation. No package commands are guessed."
            guide_id = f"linux-{distro.family.value.lower()}-{vendor.value.lower()}"
        return DriverGuide(
            guide_id,
            "Recommended action",
            explanation,
            tuple(steps),
            tuple(item for key in ids if (item := resource(key)) is not None),
        )
