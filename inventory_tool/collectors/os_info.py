from __future__ import annotations

import datetime
import platform
import socket

from ..models import OSInfo
from .._optional import HAS_PSUTIL, psutil


def collect_os_info(warnings: list) -> OSInfo:
    try:
        hostname = socket.gethostname()
    except OSError as exc:
        warnings.append(f"os: could not read hostname ({exc})")
        hostname = "unknown"

    boot_time = None
    if HAS_PSUTIL:
        try:
            boot_time = datetime.datetime.fromtimestamp(
                psutil.boot_time()
            ).isoformat(timespec="seconds")
        except Exception as exc:  # noqa: BLE001 - defensive, see module docstring
            warnings.append(f"os: could not read boot time via psutil ({exc})")
    else:
        warnings.append("os: boot time needs psutil (pip install psutil) - skipped")

    return OSInfo(
        system=platform.system() or "unknown",
        release=platform.release() or "unknown",
        version=platform.version() or "unknown",
        architecture=platform.machine() or "unknown",
        hostname=hostname,
        boot_time=boot_time,
    )
