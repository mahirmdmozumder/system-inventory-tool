import json
import os
import tempfile
import unittest

from inventory_tool.cli import main


class CliTests(unittest.TestCase):
    def test_text_format_writes_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "report.txt")
            exit_code = main(["--format", "text", "--output", out_path, "--quiet"])
            self.assertEqual(exit_code, 0)
            with open(out_path, encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("System Inventory Report", content)

    def test_json_format_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "report.json")
            exit_code = main(["--format", "json", "--output", out_path, "--quiet"])
            self.assertEqual(exit_code, 0)
            with open(out_path, encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertIn("hostname", data)
            self.assertIn("cpu", data)

    def test_append_builds_a_fleet_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "fleet.csv")
            main(["--append", csv_path, "--quiet"])
            main(["--append", csv_path, "--quiet"])
            with open(csv_path, encoding="utf-8") as handle:
                lines = [line for line in handle.read().splitlines() if line.strip()]
            # One header line + one data row per run.
            self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
