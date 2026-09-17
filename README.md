# System Inventory Tool

A command-line tool that reads a Windows machine's OS, CPU, memory, storage and network
details and writes them out as a text report, JSON, or a CSV row you can append to a
running spreadsheet — the way you'd actually want to work through an asset audit across
more than one machine.

No install required to get useful output. Clone it, run it with the Python that's
already on the machine, and it produces a full report even with nothing else installed.

```
System Inventory Report - DESKTOP-7T9TNRB
Generated: 2026-09-16T23:27:21

Operating System
  System:       Windows 11
  Version:      10.0.26200
  Architecture: AMD64
  Boot time:    2026-09-16T21:17:53

CPU
  Processor:      AMD64 Family 26 Model 68 Stepping 0, AuthenticAMD
  Physical cores: 8
  Logical cores:  16
  Max frequency:  3800 MHz
  Current usage:  22.6%

Memory
  Total:     31.14 GB
  Available: 13.76 GB
  Used:      17.37 GB (55.8%)

Storage
  C:\ (NTFS)
    1271.18 GB used / 1861.94 GB total (68.3% used, 590.76 GB free)
  D:\ (NTFS)
    577.19 GB used / 953.87 GB total (60.5% used, 376.67 GB free)

Network
  Wi-Fi (up)
    IPs: 192.168.2.64, fe80::f5cb:52fb:f3c1:65
  Loopback Pseudo-Interface 1 (up)
    IPs: 127.0.0.1, ::1
```

(Full sample output, generated on the machine I developed this on, is checked in under
[`sample_output/`](sample_output/).)

## Why I built it

Between PC Builders and the ISP job, "what's actually on this machine" was a question I
answered by hand more times than I'd like to admit — open Device Manager, check drive
properties, run `ipconfig`, write it all down somewhere. An asset audit across more than
one or two machines turns that into real, repetitive time.

So the point of this tool isn't the individual data points — `platform` and `psutil`
already know all of that. It's `--append`: run it on every machine in a fleet and it
builds one CSV, one row per machine, that you can open directly in Excel when the audit
is done. That's the part that actually saves the time the resume line says it does.

## What it does

- **Collects five categories** per machine: operating system, CPU, memory, storage
  (per-drive usage), and network interfaces (IPs, MAC address, up/down status).
- **Three output formats** — human-readable text, JSON, or CSV — chosen with `--format`.
- **Builds a fleet audit CSV** with `--append`: each run adds one row to the same file,
  writing the header only the first time, so you can point it at a shared CSV and run it
  on machine after machine.
- **Runs with zero dependencies.** Every collector has a stdlib-only fallback, so a bare
  Python install still produces hostname, OS, CPU core count, real memory totals (via a
  direct Win32 API call on Windows), drive usage for every mounted drive, and the
  machine's IP addresses.
- **Gets richer with `psutil` installed** (optional): physical vs. logical core counts,
  live CPU usage, per-partition filesystem type, and per-interface MAC address / link
  status.
- **Never crashes on a partial failure.** Each collector catches its own exceptions and
  records a warning instead of raising, so one adapter psutil can't read still leaves
  you with a full report for everything else.

## Installing and running

Needs Python 3.9+. Nothing else, to start:

```bash
git clone <this-repo>
cd system-inventory-tool
python -m inventory_tool
```

That prints a text report using stdlib-only fallbacks. For the fuller detail:

```bash
pip install -r requirements.txt      # installs psutil
python -m inventory_tool
```

Or install it as a command:

```bash
pip install -e .
inventory-tool --format json --output report.json
```

### CLI reference

```
python -m inventory_tool [--format text|json|csv] [--output PATH] [--append CSV_PATH] [--quiet]
```

| Flag | What it does |
| --- | --- |
| `--format` | `text` (default), `json`, or `csv` — a single machine's report |
| `--output PATH` | Write the report to a file instead of printing it |
| `--append CSV_PATH` | Append this machine as one row to a running fleet CSV; ignores `--format`/`--output` |
| `--quiet` | Suppress the printed confirmation when writing to a file |

Examples:

```bash
python -m inventory_tool                                   # print a text report
python -m inventory_tool --format json --output report.json
python -m inventory_tool --append fleet_audit.csv           # run per machine during an audit
```

## How it's organised

```
inventory_tool/
  _optional.py        one place that decides whether psutil is importable
  models.py            dataclasses describing a report's shape (OSInfo, CPUInfo, ...)
  collect.py            runs every collector, assembles one InventoryReport
  report.py            serializes a report to text / JSON / CSV, and the CSV-append logic
  cli.py               argparse wiring, entry point
  collectors/
    os_info.py         hostname, platform, boot time
    cpu_info.py         processor name, core counts, frequency, usage
    memory_info.py      total/available/used RAM, with a Win32 fallback
    storage_info.py     per-drive usage, with a drive-letter-enumeration fallback
    network_info.py     interfaces, IPs, MAC addresses, up/down status
tests/                 unittest suite, stdlib-only, no test framework dependency
sample_output/         real output from a run on the dev machine
```

`collect.py` is the only file that knows about all five collectors; `cli.py` is the only
file that knows about argparse; `report.py` is the only file that knows what text/JSON/
CSV look like. Swapping the CLI for a scheduled task or a small web endpoint would mean
writing a new thin front end that calls `build_report()` — none of the collectors or
serializers would change.

## Design decisions

### psutil is optional, not required

I didn't want "clone it, but first go fight with a dependency" to be step one of running
this. `_optional.py` is the single place that checks whether `psutil` is importable, and
every collector branches on that flag: try `psutil` first, fall back to something built
from `platform`, `socket`, `shutil`, and — on Windows, where the stdlib genuinely has no
answer for total physical memory — a direct `ctypes` call into `kernel32.
GlobalMemoryStatusEx`. That's a documented Win32 API, not psutil's internals reimplemented
badly; it's the same call psutil itself would end up making on Windows.

The fallback path isn't a stub for when the "real" path is missing — it's tested exactly
like the psutil path (see [Tests](#tests)), because it's what actually runs on a bare
install and it has to be correct, not just present.

### A collector reports a warning instead of raising

`collect.py` calls all five collectors and always gets back a full `InventoryReport`,
even if, say, a removable drive has no media in it and raises `PermissionError` on
`shutil.disk_usage`. Each collector appends a plain-English note to a shared `warnings`
list and keeps going. The alternative — one unhandled exception taking down the whole
run — means an audit across twenty machines stops at the first flaky USB drive instead
of skipping it and moving on.

### CSV is one flat row per machine, not one row per disk or interface

The natural way to model "a machine has many disks" is one row per disk. I didn't do
that, because the CSV's actual job is being opened next to the other rows in an audit
spreadsheet, and a spreadsheet where machine boundaries are implicit (some machines take
three rows, some take one) is worse to work with than a wider row that summarizes disks
and network interfaces as counts and totals (`disk_count`, `disk_total_gb`,
`network_interfaces`, `primary_ip`). One row, one machine, sortable and filterable
immediately.

### Picking a "primary IP" has to account for stale adapters

The first version of `_primary_ip()` just returned the first non-loopback address it
found. On my own machine that picked a `169.254.x.x` APIPA address off a disconnected
Ethernet port instead of the real LAN address on Wi-Fi — technically "not loopback,"
completely useless for finding the machine on the network. The fix checks
`is_up` first and only falls back to a down interface's address if nothing usable is
up, and filters out both APIPA (`169.254.`) and IPv6 link-local (`fe80:`) ranges either
way. There's a regression test for this exact case
(`test_primary_ip_prefers_up_interface_over_stale_apipa`) because I found it by actually
looking at my own report output, not by reasoning about it in the abstract.

### Report shape lives in dataclasses, not dicts

`models.py` defines `OSInfo`, `CPUInfo`, `MemoryInfo`, `DiskInfo`, `NetworkInterface`,
and `InventoryReport` as plain dataclasses. A collector that forgets a field, or a
typo'd key, is a bug `mypy`/the IDE can catch before the tool runs, instead of a
silent `KeyError` or a missing column three layers away in the CSV writer.

## Tests

```bash
python -m unittest discover -s tests -t .
```

18 tests, stdlib `unittest` only — no `pytest` or mocking library beyond
`unittest.mock`, which ships with Python. I ran the whole suite twice while building
this: once with `psutil` installed, once with it uninstalled, to make sure the fallback
path is real working code and not just something that looks plausible.

| File | What it checks |
| --- | --- |
| `test_collectors.py` | Each collector against whatever backend is installed, and again with `HAS_PSUTIL` patched to `False` to force the stdlib fallback |
| `test_report.py` | Text output contains the right sections; JSON round-trips; CSV row matches the declared column list; `--append` writes the header exactly once across multiple runs; the primary-IP preference logic |
| `test_cli.py` | `--format`/`--output` for text and JSON produce real files; `--append` builds a two-row fleet CSV from two runs |

## Things that bit me

- **`psutil.cpu_percent()` with no interval returns `0.0`** on the very first call — it's
  measuring against the last call, and there isn't one yet. `cpu_info.py` passes
  `interval=0.2`, a short, deliberate pause, so the number in the report reflects
  something real instead of a meaningless zero.
- **There's no stdlib way to ask Windows "what drive letters are mounted."** I first
  reached for hardcoding `C:` through `Z:` and checking `os.path.exists`, which works but
  probes 26 paths for what's usually two drives. `GetLogicalDrives()` returns the exact
  set in one call as a bitmask — `storage_info.py` decodes it directly with `ctypes`
  rather than pulling in a package for one function.
- **`unittest discover` refused to run** the first time, with `Start directory is not
  importable`. Newer `unittest` needs `tests/` to actually be a package — an empty
  `__init__.py` fixed it. Small, but it's the kind of thing that looks like a broken
  test suite from the error message alone.
- **The primary-IP bug above** — worth repeating here because it's the one that would
  have shipped quietly. Nothing crashed; the CSV just silently contained a useless
  address until I actually read my own output.

## What I'd do next

- **Linux/macOS testing on real hardware.** The stdlib fallback for storage and network
  has non-Windows branches (`shutil.disk_usage("/")`, hostname-based IP resolution), and
  the psutil path is cross-platform by design, but I built and tested this on Windows —
  I'd want time on an actual Linux box before calling those paths verified rather than
  "should work."
- **A `--compare` mode** that diffs two JSON reports from the same machine, so re-running
  this monthly could flag drive space dropping fast or a new network adapter appearing,
  instead of only ever showing a single point in time.
- **An HTML report**, since the audience for an audit is often someone who wants to open
  a link, not a CSV.
- **Asset-tag input.** Right now a fleet CSV is keyed by hostname; a real asset audit
  usually wants an asset tag or serial number attached too, which would mean an optional
  `--asset-tag` flag passed in per machine.

## License

MIT — see [LICENSE](LICENSE).
