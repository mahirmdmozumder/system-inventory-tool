from __future__ import annotations

import datetime

from .collectors.os_info import collect_os_info
from .collectors.cpu_info import collect_cpu_info
from .collectors.memory_info import collect_memory_info
from .collectors.storage_info import collect_storage_info
from .collectors.network_info import collect_network_info
from .models import InventoryReport


def build_report() -> InventoryReport:
    """Run every collector and assemble one InventoryReport.

    Collectors never raise: each appends to the shared `warnings` list on
    failure and returns whatever partial data it could get. That means a
    machine with, say, a network adapter psutil can't read still produces
    a full report for its OS/CPU/memory/disks instead of crashing outright.
    """
    warnings: list = []

    os_info = collect_os_info(warnings)
    cpu_info = collect_cpu_info(warnings)
    memory_info = collect_memory_info(warnings)
    disks = collect_storage_info(warnings)
    network = collect_network_info(warnings)

    return InventoryReport(
        generated_at=datetime.datetime.now().isoformat(timespec="seconds"),
        hostname=os_info.hostname,
        os=os_info,
        cpu=cpu_info,
        memory=memory_info,
        disks=disks,
        network=network,
        warnings=warnings,
    )
