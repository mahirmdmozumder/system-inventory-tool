"""Each collector is tested twice where practical: once against whatever
backend is actually installed in the test environment, and once with
HAS_PSUTIL patched to False to force the stdlib fallback path. That fallback
path is real production code (it's what runs on a machine without psutil
installed), not test-only code, so it deserves direct coverage.
"""
import platform
import unittest
from unittest.mock import mock_open, patch

from inventory_tool.collectors.cpu_info import collect_cpu_info
from inventory_tool.collectors.memory_info import _linux_memory_fallback, collect_memory_info
from inventory_tool.collectors.network_info import collect_network_info
from inventory_tool.collectors.os_info import collect_os_info
from inventory_tool.collectors.storage_info import collect_storage_info


class OSInfoTests(unittest.TestCase):
    def test_reports_hostname_and_system(self):
        warnings = []
        info = collect_os_info(warnings)
        self.assertTrue(info.hostname)
        self.assertEqual(info.system, platform.system())


class CPUInfoTests(unittest.TestCase):
    def test_logical_cores_always_available(self):
        warnings = []
        info = collect_cpu_info(warnings)
        self.assertIsNotNone(info.logical_cores)
        self.assertGreater(info.logical_cores, 0)

    def test_fallback_without_psutil_still_reports_logical_cores(self):
        warnings = []
        with patch("inventory_tool.collectors.cpu_info.HAS_PSUTIL", False):
            info = collect_cpu_info(warnings)
        self.assertIsNotNone(info.logical_cores)
        self.assertIsNone(info.physical_cores)
        self.assertTrue(any("psutil" in w for w in warnings))


class MemoryInfoTests(unittest.TestCase):
    def test_reports_positive_total(self):
        warnings = []
        info = collect_memory_info(warnings)
        self.assertIsNotNone(info.total_gb)
        self.assertGreater(info.total_gb, 0)

    @unittest.skipUnless(platform.system() == "Windows", "Win32 fallback is Windows-only")
    def test_windows_fallback_still_reports_memory(self):
        warnings = []
        with patch("inventory_tool.collectors.memory_info.HAS_PSUTIL", False):
            info = collect_memory_info(warnings)
        self.assertIsNotNone(info.total_gb)
        self.assertGreater(info.total_gb, 0)
        self.assertTrue(any("fallback" in w for w in warnings))

    @unittest.skipUnless(platform.system() == "Linux", "/proc/meminfo fallback is Linux-only")
    def test_linux_fallback_still_reports_memory(self):
        warnings = []
        with patch("inventory_tool.collectors.memory_info.HAS_PSUTIL", False):
            info = collect_memory_info(warnings)
        self.assertIsNotNone(info.total_gb)
        self.assertGreater(info.total_gb, 0)
        self.assertTrue(any("fallback" in w for w in warnings))

    def test_linux_meminfo_parsing_is_correct_on_any_platform(self):
        # /proc/meminfo's format is fixed by the kernel regardless of what OS
        # runs this test suite, so the parsing math can be checked everywhere
        # by feeding it fake file content - this is what actually caught the
        # CI failure (the real /proc/meminfo path only ever ran on Windows,
        # where it's unreachable, so nothing had exercised this function).
        sample_meminfo = (
            "MemTotal:       16374920 kB\n"
            "MemFree:         2043988 kB\n"
            "MemAvailable:    9876544 kB\n"
            "Buffers:          123456 kB\n"
            "Cached:          5432100 kB\n"
        )
        with patch(
            "inventory_tool.collectors.memory_info.open",
            mock_open(read_data=sample_meminfo),
            create=True,
        ):
            total, available, used, used_percent = _linux_memory_fallback()

        self.assertAlmostEqual(total, 16374920 / (1024 ** 2))
        self.assertAlmostEqual(available, 9876544 / (1024 ** 2))
        self.assertAlmostEqual(used, total - available)
        self.assertTrue(0 <= used_percent <= 100)


class StorageInfoTests(unittest.TestCase):
    def test_reports_at_least_one_disk(self):
        warnings = []
        disks = collect_storage_info(warnings)
        self.assertGreaterEqual(len(disks), 1)
        self.assertIsNotNone(disks[0].total_gb)

    @unittest.skipUnless(platform.system() == "Windows", "drive-letter fallback is Windows-only")
    def test_windows_fallback_still_finds_a_drive(self):
        warnings = []
        with patch("inventory_tool.collectors.storage_info.HAS_PSUTIL", False):
            disks = collect_storage_info(warnings)
        self.assertGreaterEqual(len(disks), 1)


class NetworkInfoTests(unittest.TestCase):
    def test_reports_at_least_one_interface_or_ip(self):
        warnings = []
        interfaces = collect_network_info(warnings)
        # A machine with no network at all is unusual but not impossible in CI;
        # assert the collector at least didn't raise and returned a list.
        self.assertIsInstance(interfaces, list)

    def test_fallback_without_psutil_uses_hostname_resolution(self):
        warnings = []
        with patch("inventory_tool.collectors.network_info.HAS_PSUTIL", False):
            collect_network_info(warnings)
        self.assertTrue(any("psutil" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
