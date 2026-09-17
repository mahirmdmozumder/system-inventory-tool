from __future__ import annotations

import ctypes
import platform

from ..models import MemoryInfo
from .._optional import HAS_PSUTIL, psutil

_BYTES_PER_GB = 1024 ** 3


def _windows_memory_fallback():
    """Read total/available RAM via the Win32 API when psutil isn't installed.

    Windows has no stdlib module for this, but GlobalMemoryStatusEx is a
    documented kernel32 call, so ctypes alone (no third-party package) is
    enough to get real numbers instead of leaving memory blank.
    """

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]

    total = stat.ullTotalPhys / _BYTES_PER_GB
    available = stat.ullAvailPhys / _BYTES_PER_GB
    used = total - available
    used_percent = float(stat.dwMemoryLoad)
    return total, available, used, used_percent


def collect_memory_info(warnings: list) -> MemoryInfo:
    if HAS_PSUTIL:
        try:
            vm = psutil.virtual_memory()
            return MemoryInfo(
                total_gb=round(vm.total / _BYTES_PER_GB, 2),
                available_gb=round(vm.available / _BYTES_PER_GB, 2),
                used_gb=round((vm.total - vm.available) / _BYTES_PER_GB, 2),
                used_percent=vm.percent,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"memory: could not read memory via psutil ({exc})")

    if platform.system() == "Windows":
        try:
            total, available, used, used_percent = _windows_memory_fallback()
            warnings.append("memory: used Win32 API fallback (psutil not installed)")
            return MemoryInfo(
                total_gb=round(total, 2),
                available_gb=round(available, 2),
                used_gb=round(used, 2),
                used_percent=round(used_percent, 1),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"memory: Win32 fallback failed ({exc})")
    else:
        warnings.append("memory: no psutil and no fallback for this OS - skipped")

    return MemoryInfo()
