#!/usr/bin/env python3
"""Run a bounded, machine-readable LAMMPS environment check.

This is an environment capability probe, not a validation of the inherited
peptidoglycan parameterization or of quasi-static fracture behavior.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence
REQUIRED_STYLES = (
    ("bond", "harmonic"),
    ("bond", "nonlinear"),
    ("angle", "harmonic"),
    ("fix", "bond/break"),
)


def _load_inherited_coefficients() -> tuple[
    dict[str, tuple[float, ...]], dict[str, Any]
]:
    """Load the inherited numbers through their immutable profile identity."""

    from pgworld.config.physics_profiles import load_physics_profile

    profile = load_physics_profile("legacy_python_2026_03_12_v1")
    snapshot = profile.expanded_snapshot()
    potentials = snapshot["potentials"]
    harmonic = potentials["harmonic_bond"]["parameters"]
    nonlinear = potentials["nonlinear_bond"]["parameters"]
    angle = potentials["harmonic_angle"]["parameters"]
    coefficients = {
        "harmonic_bond": (
            float(harmonic["K_pN_per_nm"]),
            float(harmonic["r0_nm"]),
        ),
        "nonlinear_bond": (
            float(nonlinear["epsilon_pN_nm"]),
            float(nonlinear["r0_nm"]),
            float(nonlinear["lambda_nm"]),
        ),
        "harmonic_angle": (
            float(angle["K_pN_nm"]),
            float(angle["theta0_degrees"]),
        ),
    }
    evidence = {
        "profile_id": profile.profile_id,
        "canonical_hash": profile.canonical_hash,
        "review_status": snapshot["review_status"],
        "units": snapshot["units"],
        "biological_parameter_certification": snapshot[
            "biological_parameter_certified"
        ],
    }
    return coefficients, evidence


def _fixture_text() -> str:
    bond_length = 1.2
    angle_degrees = 150.0
    center_x = 5.0
    center_y = 5.0
    first_x = center_x - bond_length
    third_x = center_x + bond_length * math.cos(math.radians(30.0))
    third_y = center_y + bond_length * math.sin(math.radians(30.0))
    return f"""LAMMPS doctor bonded capability fixture

3 atoms
2 bonds
1 angles

2 atom types
2 bond types
1 angle types

0.0 10.0 xlo xhi
0.0 10.0 ylo yhi
-0.5 0.5 zlo zhi

Masses

1 1.0
2 1.0

Atoms # angle

1 1 1 {first_x:.16g} {center_y:.16g} 0.0
2 1 1 {center_x:.16g} {center_y:.16g} 0.0
3 1 2 {third_x:.16g} {third_y:.16g} 0.0

Bonds

1 1 1 2
2 2 2 3

Angles

1 1 1 2 3
"""


def _expected_energies(
    coefficients: dict[str, tuple[float, ...]],
) -> dict[str, float]:
    distance = 1.2
    angle_radians = math.radians(150.0)
    harmonic_k, harmonic_r0 = coefficients["harmonic_bond"]
    nonlinear_epsilon, nonlinear_r0, nonlinear_lambda = coefficients[
        "nonlinear_bond"
    ]
    angle_k, angle_0_degrees = coefficients["harmonic_angle"]
    nonlinear_delta = distance - nonlinear_r0
    return {
        "harmonic_bond": harmonic_k * (distance - harmonic_r0) ** 2,
        "nonlinear_bond": nonlinear_epsilon
        * nonlinear_delta**2
        / (nonlinear_lambda**2 - nonlinear_delta**2),
        "harmonic_angle": angle_k
        * (angle_radians - math.radians(angle_0_degrees)) ** 2,
    }


def _component_checks(
    observed: dict[str, float], expected: dict[str, float]
) -> dict[str, bool]:
    checks = {
        name: math.isclose(
            observed[name], expected[name], rel_tol=1.0e-9, abs_tol=1.0e-9
        )
        for name in expected
    }
    checks["component_sum"] = math.isclose(
        observed["potential_total"],
        sum(observed[name] for name in expected),
        rel_tol=1.0e-9,
        abs_tol=1.0e-9,
    )
    return checks


def run_doctor() -> dict[str, Any]:
    """Return the complete doctor report; failures remain structured data."""

    report: dict[str, Any] = {
        "schema_version": 1,
        "ok": False,
        "scope": {
            "purpose": "bounded LAMMPS runtime and required-style capability probe",
            "scientific_parameter_validation": False,
            "quasistatic_fracture_validation": False,
            "physical_time_validation": False,
        },
        "python": {
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "lammps": {
            "imported": False,
            "instance_created": False,
            "closed": False,
        },
        "required_styles": {},
        "bonded_fixture": {
            "executed": False,
            "run_steps": 0,
            "minimization_performed": False,
        },
        "bond_break_check": {
            "configuration_attempted": False,
            "configuration_succeeded": False,
            "invoked_by_dynamics": False,
            "rupture_events_observed": None,
            "quasistatic_fracture_validated": False,
            "note": (
                "Availability/configuration only; fix bond/break was not run and "
                "this check does not implement or validate quasi-static fracture."
            ),
        },
        "errors": [],
    }

    solver = None
    phase = "import_lammps"
    try:
        import lammps as lammps_module
        from lammps import LMP_STYLE_GLOBAL, LMP_TYPE_VECTOR, lammps

        report["lammps"]["imported"] = True
        report["lammps"]["module_file"] = str(Path(lammps_module.__file__).resolve())

        phase = "instantiate_lammps"
        solver = lammps(cmdargs=["-log", "none", "-screen", "none"])
        report["lammps"].update(
            {
                "instance_created": True,
                "version_integer": int(solver.version()),
                "os_build_info": solver.get_os_info().strip(),
                "mpi_support": bool(solver.has_mpi_support),
                "installed_packages": sorted(solver.installed_packages),
                "accelerator_config": solver.accelerator_config,
            }
        )

        phase = "check_required_styles"
        required_styles = {
            f"{category}:{name}": bool(solver.has_style(category, name))
            for category, name in REQUIRED_STYLES
        }
        report["required_styles"] = required_styles
        missing_styles = [
            name for name, is_available in required_styles.items() if not is_available
        ]
        if missing_styles:
            raise RuntimeError(
                "Required LAMMPS styles are unavailable: " + ", ".join(missing_styles)
            )

        phase = "load_inherited_coefficients"
        coefficients, profile_evidence = _load_inherited_coefficients()
        expected = _expected_energies(coefficients)
        report["bonded_fixture"]["coefficient_source"] = (
            "packaged immutable physics profile"
        )
        report["bonded_fixture"]["physics_profile"] = profile_evidence
        report["bonded_fixture"]["coefficients_used_unchanged"] = {
            key: list(values) for key, values in coefficients.items()
        }

        phase = "run_bonded_fixture"
        with tempfile.TemporaryDirectory(prefix="mechworld-lammps-doctor-") as temp_dir:
            data_path = Path(temp_dir) / "bonded_fixture.data"
            data_path.write_text(_fixture_text(), encoding="utf-8", newline="\n")

            harmonic_k, harmonic_r0 = coefficients["harmonic_bond"]
            nonlinear_epsilon, nonlinear_r0, nonlinear_lambda = coefficients[
                "nonlinear_bond"
            ]
            angle_k, angle_0 = coefficients["harmonic_angle"]
            commands = (
                "units nano",
                "dimension 2",
                "atom_style angle",
                "boundary p p p",
                f'read_data "{data_path.as_posix()}"',
                "pair_style zero 5.0",
                "pair_coeff * *",
                "bond_style hybrid harmonic nonlinear",
                f"bond_coeff 1 harmonic {harmonic_k:.17g} {harmonic_r0:.17g}",
                "bond_coeff 2 nonlinear "
                f"{nonlinear_epsilon:.17g} {nonlinear_r0:.17g} "
                f"{nonlinear_lambda:.17g}",
                "angle_style hybrid harmonic",
                f"angle_coeff 1 harmonic {angle_k:.17g} {angle_0:.17g}",
                "compute doctor_bonds all bond",
                "compute doctor_angles all angle",
                "thermo_style custom step atoms bonds angles pe ebond eangle",
                "thermo_modify norm no",
                "run 0",
            )
            for command in commands:
                solver.command(command)

            bond_energies = solver.extract_compute(
                "doctor_bonds", LMP_STYLE_GLOBAL, LMP_TYPE_VECTOR
            )
            angle_energies = solver.extract_compute(
                "doctor_angles", LMP_STYLE_GLOBAL, LMP_TYPE_VECTOR
            )
            observed = {
                "harmonic_bond": float(bond_energies[0]),
                "nonlinear_bond": float(bond_energies[1]),
                "harmonic_angle": float(angle_energies[0]),
                "potential_total": float(solver.get_thermo("pe")),
            }
            checks = _component_checks(observed, expected)
            report["bonded_fixture"].update(
                {
                    "executed": True,
                    "atom_count": int(solver.get_natoms()),
                    "bond_count": int(solver.extract_global("nbonds")),
                    "angle_count": int(solver.extract_global("nangles")),
                    "observed_energy": observed,
                    "expected_energy": expected,
                    "energy_checks": checks,
                    "all_energy_checks_passed": all(checks.values()),
                    "note": (
                        "The fixture checks runtime evaluation of the inherited "
                        "style/coefficient tuples; it does not approve their "
                        "scientific units or parameter provenance."
                    ),
                }
            )
            expected_counts = (
                report["bonded_fixture"]["atom_count"] == 3
                and report["bonded_fixture"]["bond_count"] == 2
                and report["bonded_fixture"]["angle_count"] == 1
            )
            report["bonded_fixture"]["expected_counts_present"] = expected_counts
            if not expected_counts or not all(checks.values()):
                raise RuntimeError(
                    "The bonded fixture did not reproduce its expected topology/energy."
                )

            phase = "configure_bond_break"
            report["bond_break_check"]["configuration_attempted"] = True
            solver.command("fix doctor_break all bond/break 1 2 3.0")
            solver.command("unfix doctor_break")
            report["bond_break_check"]["configuration_succeeded"] = True

    except Exception as error:  # keep CLI failures machine-readable and actionable
        report["errors"].append(
            {
                "phase": phase,
                "type": type(error).__name__,
                "message": str(error),
            }
        )
    finally:
        if solver is not None:
            try:
                solver.close()
                report["lammps"]["closed"] = True
            except Exception as error:  # a close failure makes the doctor fail
                report["errors"].append(
                    {
                        "phase": "close_lammps",
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )

    report["ok"] = bool(
        not report["errors"]
        and report["lammps"]["closed"]
        and report["bonded_fixture"]["executed"]
        and report["bonded_fixture"].get("all_energy_checks_passed", False)
        and report["bond_break_check"]["configuration_succeeded"]
    )
    return report


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="also write the JSON report to this path",
    )
    return parser.parse_args(argv)


def emit_doctor_report(*, output: Path | None = None) -> int:
    """Print one report and optionally persist the identical JSON document."""

    report = run_doctor()
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if report["ok"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return emit_doctor_report(output=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
