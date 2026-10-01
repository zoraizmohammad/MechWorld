#!/usr/bin/env python3
"""Compatibility wrapper for the installable ``pgworld doctor`` command."""

from __future__ import annotations

from pathlib import Path
import sys


SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from pgworld.doctor import main, run_doctor  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit(main())
