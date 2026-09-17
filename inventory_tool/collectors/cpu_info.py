from __future__ import annotations

import os
import platform

from ..models import CPUInfo
from .._optional import HAS_PSUTIL, psutil


def collect_cpu_info(warnings: list) -> CPUInfo:
    processor = platform.processor() or platform.machine() or "unknown"
    logical_cores = os.cpu_count()
    physical_cores = None
    max_frequency = None
    usage_percent = None

    if HAS_PSUTIL:
        try:
            physical_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True) or logical_cores
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"cpu: could not read core counts via psutil ({exc})")

        try:
            freq = psutil.cpu_freq()
            if freq is not None:
                max_frequency = freq.max or freq.current
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"cpu: could not read frequency via psutil ({exc})")

        try:
            # interval=0.2 costs a brief pause but returns a real sample
            # instead of psutil's meaningless 0.0% "since last call" value.
            usage_percent = psutil.cpu_percent(interval=0.2)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"cpu: could not read usage via psutil ({exc})")
    else:
        warnings.append(
            "cpu: physical core count, frequency, and live usage need psutil - skipped"
        )

    return CPUInfo(
        processor=processor,
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        max_frequency_mhz=max_frequency,
        current_usage_percent=usage_percent,
    )
