"""Explicitly gated entry point for inherited elastic-tensor reproduction.

This script does not produce the validated P01-07 raw tangent artifact.  It is
retained only for forensic reproduction of the inherited positive-only,
default-pressure, symmetrized output route.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filepath", type=Path, help="legacy LAMMPS restart path")
    parser.add_argument(
        "--allow-legacy-forensic-output",
        action="store_true",
        help=(
            "explicitly run the labeled inherited output route; this is not a "
            "validated raw tangent migration"
        ),
    )
    parser.add_argument(
        "--delete-restart",
        action="store_true",
        help="delete the exact input restart only after a successful forensic run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.allow_legacy_forensic_output:
        parser.error(
            "ordinary use is disabled: the restart lacks the reference/base "
            "metadata required for a validated raw tangent migration; pass "
            "--allow-legacy-forensic-output only for labeled reproduction"
        )

    print(
        "FORENSIC LEGACY OUTPUT: positive-only/default-pressure/symmetrized; "
        "not a validated P01-07 raw tangent artifact",
        file=sys.stderr,
    )
    from run_lammps_elastic_tensor import lammps_calculate_elastic_tensor

    restart = args.filepath.absolute()
    if restart.is_symlink():
        parser.error(
            "symbolic-link restart inputs are rejected so --delete-restart can "
            "never delete a resolved target different from the lexical input"
        )
    succeeded = lammps_calculate_elastic_tensor(
        str(restart), allow_legacy_forensic_output=True
    )
    if not succeeded:
        return 1
    if args.delete_restart:
        restart.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
