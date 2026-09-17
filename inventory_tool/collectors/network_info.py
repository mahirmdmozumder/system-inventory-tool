from __future__ import annotations

import socket

from ..models import NetworkInterface
from .._optional import HAS_PSUTIL, psutil


def _collect_via_psutil(warnings: list) -> list:
    interfaces = []
    try:
        addrs_by_iface = psutil.net_if_addrs()
        stats_by_iface = psutil.net_if_stats()
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"network: could not read interfaces via psutil ({exc})")
        return []

    for name, addrs in addrs_by_iface.items():
        ip_addresses = []
        mac_address = None
        for addr in addrs:
            family = addr.family
            if family == socket.AF_INET or family == socket.AF_INET6:
                ip_addresses.append(addr.address)
            elif hasattr(socket, "AF_LINK") and family == socket.AF_LINK:
                mac_address = addr.address
            elif addr.address and ":" in addr.address and len(addr.address) == 17:
                # psutil.AF_LINK on Windows surfaces as AF_UNSPEC/-1; a
                # colon-separated 17-char string is the MAC either way.
                mac_address = addr.address

        is_up = None
        stats = stats_by_iface.get(name)
        if stats is not None:
            is_up = stats.isup

        interfaces.append(
            NetworkInterface(
                name=name,
                ip_addresses=ip_addresses,
                mac_address=mac_address,
                is_up=is_up,
            )
        )
    return interfaces


def _collect_via_stdlib(warnings: list) -> list:
    warnings.append(
        "network: per-interface detail (MAC, up/down) needs psutil - showing hostname IPs only"
    )
    try:
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)
    except OSError as exc:
        warnings.append(f"network: could not resolve hostname IPs ({exc})")
        return []

    if not ip_list:
        return []

    return [NetworkInterface(name="(all interfaces)", ip_addresses=ip_list)]


def collect_network_info(warnings: list) -> list:
    if HAS_PSUTIL:
        interfaces = _collect_via_psutil(warnings)
        if interfaces:
            return interfaces
    return _collect_via_stdlib(warnings)
