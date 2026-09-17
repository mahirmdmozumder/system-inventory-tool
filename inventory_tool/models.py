"""Plain data containers for one machine's inventory snapshot.

Kept dependency-free on purpose: these classes only describe shape, so
report.py can serialize them to text/JSON/CSV without caring where the
values came from (psutil or a stdlib fallback).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class OSInfo:
    system: str = "unknown"
    release: str = "unknown"
    version: str = "unknown"
    architecture: str = "unknown"
    hostname: str = "unknown"
    boot_time: Optional[str] = None


@dataclass
class CPUInfo:
    processor: str = "unknown"
    physical_cores: Optional[int] = None
    logical_cores: Optional[int] = None
    max_frequency_mhz: Optional[float] = None
    current_usage_percent: Optional[float] = None


@dataclass
class MemoryInfo:
    total_gb: Optional[float] = None
    available_gb: Optional[float] = None
    used_gb: Optional[float] = None
    used_percent: Optional[float] = None


@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    filesystem: str = "unknown"
    total_gb: Optional[float] = None
    used_gb: Optional[float] = None
    free_gb: Optional[float] = None
    used_percent: Optional[float] = None


@dataclass
class NetworkInterface:
    name: str
    ip_addresses: List[str] = field(default_factory=list)
    mac_address: Optional[str] = None
    is_up: Optional[bool] = None


@dataclass
class InventoryReport:
    generated_at: str
    hostname: str
    os: OSInfo
    cpu: CPUInfo
    memory: MemoryInfo
    disks: List[DiskInfo]
    network: List[NetworkInterface]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
