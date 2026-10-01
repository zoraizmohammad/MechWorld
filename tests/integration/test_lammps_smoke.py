"""Integration coverage for the real, locally installed LAMMPS library."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DOCTOR = ROOT / "tools" / "doctor.py"


def test_lammps_doctor_runs_known_bonded_model() -> None:
    completed = subprocess.run(
        [sys.executable, str(DOCTOR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, (
        f"doctor exited {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    report = json.loads(completed.stdout)

    assert report["ok"] is True
    assert report["lammps"]["imported"] is True
    assert report["lammps"]["instance_created"] is True
    assert report["lammps"]["closed"] is True
    assert report["lammps"]["version_integer"] > 0
    assert all(report["required_styles"].values())

    fixture = report["bonded_fixture"]
    assert fixture["executed"] is True
    assert fixture["run_steps"] == 0
    assert fixture["minimization_performed"] is False
    assert fixture["atom_count"] == 3
    assert fixture["bond_count"] == 2
    assert fixture["angle_count"] == 1
    assert fixture["expected_counts_present"] is True
    assert fixture["all_energy_checks_passed"] is True
    for component in ("harmonic_bond", "nonlinear_bond", "harmonic_angle"):
        assert fixture["observed_energy"][component] == pytest.approx(
            fixture["expected_energy"][component], rel=1.0e-9, abs=1.0e-9
        )
        assert fixture["observed_energy"][component] > 0.0

    bond_break = report["bond_break_check"]
    assert bond_break["configuration_attempted"] is True
    assert bond_break["configuration_succeeded"] is True
    assert bond_break["invoked_by_dynamics"] is False
    assert bond_break["rupture_events_observed"] is None
    assert bond_break["quasistatic_fracture_validated"] is False


def test_lammps_doctor_fails_nonzero_and_closes_after_instance_error(
    tmp_path: Path,
) -> None:
    fake_module = tmp_path / "lammps.py"
    close_marker = tmp_path / "closed.txt"
    fake_module.write_text(
        """\
import os
from pathlib import Path

LMP_STYLE_GLOBAL = 0
LMP_TYPE_VECTOR = 1

class lammps:
    has_mpi_support = False
    installed_packages = []
    accelerator_config = {}

    def __init__(self, **kwargs):
        pass

    def version(self):
        return 1

    def get_os_info(self):
        return "doctor negative-path fake"

    def has_style(self, category, name):
        return False

    def close(self):
        Path(os.environ["LAMMPS_DOCTOR_CLOSE_MARKER"]).write_text(
            "closed", encoding="utf-8"
        )
""",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (str(tmp_path), environment.get("PYTHONPATH", ""))
        if value
    )
    environment["LAMMPS_DOCTOR_CLOSE_MARKER"] = str(close_marker)

    completed = subprocess.run(
        [sys.executable, str(DOCTOR)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )
    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["ok"] is False
    assert report["lammps"]["instance_created"] is True
    assert report["lammps"]["closed"] is True
    assert close_marker.read_text(encoding="utf-8") == "closed"
    assert report["errors"] == [
        {
            "phase": "check_required_styles",
            "type": "RuntimeError",
            "message": (
                "Required LAMMPS styles are unavailable: bond:harmonic, "
                "bond:nonlinear, angle:harmonic, fix:bond/break"
            ),
        }
    ]
