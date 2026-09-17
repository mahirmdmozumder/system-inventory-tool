"""Serializers that turn an InventoryReport into text, JSON, or a CSV row.

CSV is deliberately one flat row per machine (not one row per disk/interface)
because the point of an asset audit is comparing machines side by side in a
spreadsheet - a technician runs this tool on each machine in a fleet and
appends every run to the same CSV, building an audit sheet one row at a time.
"""
from __future__ import annotations

import csv
import io
import json
import os

from .models import InventoryReport

CSV_FIELDS = [
    "generated_at",
    "hostname",
    "os_system",
    "os_release",
    "os_version",
    "os_architecture",
    "os_boot_time",
    "cpu_processor",
    "cpu_physical_cores",
    "cpu_logical_cores",
    "cpu_max_frequency_mhz",
    "cpu_current_usage_percent",
    "memory_total_gb",
    "memory_available_gb",
    "memory_used_percent",
    "disk_count",
    "disk_total_gb",
    "disk_free_gb",
    "network_interfaces",
    "primary_ip",
    "warning_count",
]


def to_text(report: InventoryReport) -> str:
    lines = []
    lines.append(f"System Inventory Report - {report.hostname}")
    lines.append(f"Generated: {report.generated_at}")
    lines.append("")

    lines.append("Operating System")
    lines.append(f"  System:       {report.os.system} {report.os.release}")
    lines.append(f"  Version:      {report.os.version}")
    lines.append(f"  Architecture: {report.os.architecture}")
    lines.append(f"  Boot time:    {report.os.boot_time or 'unavailable'}")
    lines.append("")

    lines.append("CPU")
    lines.append(f"  Processor:      {report.cpu.processor}")
    lines.append(f"  Physical cores: {report.cpu.physical_cores or 'unavailable'}")
    lines.append(f"  Logical cores:  {report.cpu.logical_cores or 'unavailable'}")
    freq = report.cpu.max_frequency_mhz
    lines.append(f"  Max frequency:  {f'{freq:.0f} MHz' if freq else 'unavailable'}")
    usage = report.cpu.current_usage_percent
    lines.append(f"  Current usage:  {f'{usage:.1f}%' if usage is not None else 'unavailable'}")
    lines.append("")

    lines.append("Memory")
    if report.memory.total_gb is not None:
        lines.append(f"  Total:     {report.memory.total_gb} GB")
        lines.append(f"  Available: {report.memory.available_gb} GB")
        lines.append(f"  Used:      {report.memory.used_gb} GB ({report.memory.used_percent}%)")
    else:
        lines.append("  unavailable")
    lines.append("")

    lines.append("Storage")
    if report.disks:
        for disk in report.disks:
            lines.append(f"  {disk.mountpoint} ({disk.filesystem})")
            if disk.total_gb is not None:
                lines.append(
                    f"    {disk.used_gb} GB used / {disk.total_gb} GB total "
                    f"({disk.used_percent}% used, {disk.free_gb} GB free)"
                )
            else:
                lines.append("    size unavailable")
    else:
        lines.append("  no disks detected")
    lines.append("")

    lines.append("Network")
    if report.network:
        for iface in report.network:
            status = ""
            if iface.is_up is not None:
                status = " (up)" if iface.is_up else " (down)"
            lines.append(f"  {iface.name}{status}")
            if iface.mac_address:
                lines.append(f"    MAC: {iface.mac_address}")
            if iface.ip_addresses:
                lines.append(f"    IPs: {', '.join(iface.ip_addresses)}")
    else:
        lines.append("  no interfaces detected")
    lines.append("")

    if report.warnings:
        lines.append("Warnings")
        for warning in report.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    return "\n".join(lines)


def to_json(report: InventoryReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


def _is_routable(ip: str) -> bool:
    """Filter out loopback and link-local addresses that aren't useful for
    picking a machine out on a network (127.0.0.1, ::1, APIPA 169.254.x.x,
    and IPv6 link-local fe80::).
    """
    return bool(ip) and not (
        ip.startswith("127.") or ip == "::1" or ip.startswith("169.254.") or ip.startswith("fe80:")
    )


def _primary_ip(report: InventoryReport) -> str:
    # Prefer an IP from an interface psutil/the OS reports as up, so a
    # disconnected Ethernet port with a stale APIPA address doesn't win over
    # the Wi-Fi adapter that's actually carrying traffic.
    up_ips = [ip for iface in report.network if iface.is_up for ip in iface.ip_addresses]
    all_ips = [ip for iface in report.network for ip in iface.ip_addresses]

    for pool in (up_ips, all_ips):
        for ip in pool:
            if _is_routable(ip):
                return ip
    return ""


def to_csv_row(report: InventoryReport) -> dict:
    total_disk_gb = sum(d.total_gb for d in report.disks if d.total_gb is not None)
    free_disk_gb = sum(d.free_gb for d in report.disks if d.free_gb is not None)

    return {
        "generated_at": report.generated_at,
        "hostname": report.hostname,
        "os_system": report.os.system,
        "os_release": report.os.release,
        "os_version": report.os.version,
        "os_architecture": report.os.architecture,
        "os_boot_time": report.os.boot_time or "",
        "cpu_processor": report.cpu.processor,
        "cpu_physical_cores": report.cpu.physical_cores or "",
        "cpu_logical_cores": report.cpu.logical_cores or "",
        "cpu_max_frequency_mhz": report.cpu.max_frequency_mhz or "",
        "cpu_current_usage_percent": report.cpu.current_usage_percent or "",
        "memory_total_gb": report.memory.total_gb or "",
        "memory_available_gb": report.memory.available_gb or "",
        "memory_used_percent": report.memory.used_percent or "",
        "disk_count": len(report.disks),
        "disk_total_gb": round(total_disk_gb, 2) if report.disks else "",
        "disk_free_gb": round(free_disk_gb, 2) if report.disks else "",
        "network_interfaces": len(report.network),
        "primary_ip": _primary_ip(report),
        "warning_count": len(report.warnings),
    }


def to_csv(report: InventoryReport) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerow(to_csv_row(report))
    return buffer.getvalue()


def append_csv_row(report: InventoryReport, path: str) -> None:
    """Append one row to a fleet audit CSV, writing the header only if new.

    This is the "run it on every machine in the audit, build one sheet"
    workflow: the same file accumulates a row per machine per run.
    """
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(to_csv_row(report))
