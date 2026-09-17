import csv
import io
import json
import os
import tempfile
import unittest

from inventory_tool.models import (
    CPUInfo,
    DiskInfo,
    InventoryReport,
    MemoryInfo,
    NetworkInterface,
    OSInfo,
)
from inventory_tool.report import CSV_FIELDS, append_csv_row, to_csv, to_csv_row, to_json, to_text


def make_sample_report() -> InventoryReport:
    """A fixed, hand-built report so serializer tests don't depend on the
    machine actually running them (real host details are already exercised
    in test_collectors.py).
    """
    return InventoryReport(
        generated_at="2026-01-01T00:00:00",
        hostname="TEST-PC",
        os=OSInfo(
            system="Windows",
            release="11",
            version="10.0.26200",
            architecture="AMD64",
            hostname="TEST-PC",
            boot_time="2025-12-31T08:00:00",
        ),
        cpu=CPUInfo(
            processor="Intel64 Family 6",
            physical_cores=4,
            logical_cores=8,
            max_frequency_mhz=3600.0,
            current_usage_percent=12.5,
        ),
        memory=MemoryInfo(total_gb=16.0, available_gb=9.5, used_gb=6.5, used_percent=40.6),
        disks=[
            DiskInfo(
                device="C:\\",
                mountpoint="C:\\",
                filesystem="NTFS",
                total_gb=476.9,
                used_gb=200.0,
                free_gb=276.9,
                used_percent=41.9,
            )
        ],
        network=[
            NetworkInterface(
                name="Ethernet",
                ip_addresses=["192.168.1.20"],
                mac_address="AA:BB:CC:DD:EE:FF",
                is_up=True,
            )
        ],
        warnings=["example: something to note"],
    )


class TextReportTests(unittest.TestCase):
    def test_includes_key_sections_and_values(self):
        text = to_text(make_sample_report())
        self.assertIn("TEST-PC", text)
        self.assertIn("Windows 11", text)
        self.assertIn("16.0 GB", text)
        self.assertIn("C:\\", text)
        self.assertIn("192.168.1.20", text)
        self.assertIn("example: something to note", text)


class JsonReportTests(unittest.TestCase):
    def test_round_trips_through_json(self):
        report = make_sample_report()
        parsed = json.loads(to_json(report))
        self.assertEqual(parsed["hostname"], "TEST-PC")
        self.assertEqual(parsed["cpu"]["logical_cores"], 8)
        self.assertEqual(parsed["disks"][0]["filesystem"], "NTFS")


class CsvReportTests(unittest.TestCase):
    def test_row_matches_declared_fields(self):
        row = to_csv_row(make_sample_report())
        self.assertEqual(set(row.keys()), set(CSV_FIELDS))
        self.assertEqual(row["hostname"], "TEST-PC")
        self.assertEqual(row["disk_count"], 1)
        self.assertEqual(row["primary_ip"], "192.168.1.20")

    def test_primary_ip_prefers_up_interface_over_stale_apipa(self):
        report = make_sample_report()
        report.network = [
            NetworkInterface(name="Ethernet", ip_addresses=["169.254.1.5"], is_up=False),
            NetworkInterface(name="Wi-Fi", ip_addresses=["10.0.0.42"], is_up=True),
        ]
        row = to_csv_row(report)
        self.assertEqual(row["primary_ip"], "10.0.0.42")

    def test_to_csv_produces_parseable_csv_with_header(self):
        rendered = to_csv(make_sample_report())
        reader = csv.DictReader(io.StringIO(rendered))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["hostname"], "TEST-PC")

    def test_append_writes_header_once_across_multiple_machines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "fleet.csv")
            report_a = make_sample_report()
            report_b = make_sample_report()
            report_b.hostname = "TEST-PC-2"

            append_csv_row(report_a, path)
            append_csv_row(report_b, path)

            with open(path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["hostname"], "TEST-PC")
            self.assertEqual(rows[1]["hostname"], "TEST-PC-2")

            with open(path, encoding="utf-8") as handle:
                header_count = sum(1 for line in handle if line.startswith("generated_at,"))
            self.assertEqual(header_count, 1)


if __name__ == "__main__":
    unittest.main()
