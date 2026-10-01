"""Command-line interface for bounded MechWorld-PG utilities."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from pgworld.doctor import emit_doctor_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pgworld")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser(
        "doctor",
        help="run the bounded machine-readable LAMMPS capability probe",
    )
    doctor.add_argument(
        "--output",
        type=Path,
        help="also write the JSON report to this path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the sole supported command, ``pgworld doctor``."""

    args = _parser().parse_args(argv)
    if args.command == "doctor":
        return emit_doctor_report(output=args.output)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

