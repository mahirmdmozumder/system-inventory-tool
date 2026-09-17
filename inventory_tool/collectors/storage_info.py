from __future__ import annotations

import ctypes
import platform
import shutil
import string

from ..models import DiskInfo
from .._optional import HAS_PSUTIL, psutil

_BYTES_PER_GB = 1024 ** 3


def _windows_drive_letters():
    """List mounted drive letters (C:\\, D:\\, ...) via GetLogicalDrives.

    Stdlib has no direct call for "which drive letters exist," but the
    bitmask GetLogicalDrives returns is documented and simple to decode,
    so this avoids a psutil dependency just to find mount points.
    """
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
    return [
        f"{letter}:\\"
        for i, letter in enumerate(string.ascii_uppercase)
        if bitmask & (1 << i)
    ]


def _disk_from_usage(device: str, mountpoint: str, filesystem: str) -> DiskInfo:
    usage = shutil.disk_usage(mountpoint)
    return DiskInfo(
        device=device,
        mountpoint=mountpoint,
        filesystem=filesystem,
        total_gb=round(usage.total / _BYTES_PER_GB, 2),
        used_gb=round(usage.used / _BYTES_PER_GB, 2),
        free_gb=round(usage.free / _BYTES_PER_GB, 2),
        used_percent=round(usage.used / usage.total * 100, 1) if usage.total else None,
    )


def collect_storage_info(warnings: list) -> list:
    disks = []

    if HAS_PSUTIL:
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"storage: could not list partitions via psutil ({exc})")
            partitions = []

        for part in partitions:
            try:
                disks.append(
                    _disk_from_usage(part.device, part.mountpoint, part.fstype or "unknown")
                )
            except (OSError, PermissionError) as exc:
                # Common on removable/optical drives with no media inserted.
                warnings.append(f"storage: skipped {part.mountpoint} ({exc})")

        if disks:
            return disks

    # Fall back to stdlib-only enumeration if psutil is missing or returned nothing.
    if platform.system() == "Windows":
        warnings.append("storage: used drive-letter fallback (psutil not installed or empty)")
        for mountpoint in _windows_drive_letters():
            try:
                disks.append(_disk_from_usage(mountpoint, mountpoint, "unknown"))
            except OSError as exc:
                warnings.append(f"storage: skipped {mountpoint} ({exc})")
    else:
        warnings.append("storage: used single root-mount fallback (psutil not installed)")
        try:
            disks.append(_disk_from_usage("/", "/", "unknown"))
        except OSError as exc:
            warnings.append(f"storage: could not read root mount ({exc})")

    return disks
