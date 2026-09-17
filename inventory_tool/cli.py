from __future__ import annotations

import argparse
import sys

from .collect import build_report
from .report import to_text, to_json, to_csv, append_csv_row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory-tool",
        description=(
            "Collect hardware, OS, storage, and network details from this "
            "machine and write an inventory report."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Report format to produce (default: text).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write the report to PATH instead of printing to stdout.",
    )
    parser.add_argument(
        "--append",
        metavar="CSV_PATH",
        help=(
            "Append this machine as one row to a running fleet-audit CSV at "
            "CSV_PATH (writes the header automatically on the first run). "
            "Ignores --format/--output."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the printed report when writing to --output or --append.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report = build_report()

    if args.append:
        append_csv_row(report, args.append)
        if not args.quiet:
            print(f"Appended {report.hostname} to {args.append}")
        return 0

    renderers = {"text": to_text, "json": to_json, "csv": to_csv}
    rendered = renderers[args.format](report)

    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as handle:
            handle.write(rendered)
        if not args.quiet:
            print(f"Wrote {args.format} report to {args.output}")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    sys.exit(main())
