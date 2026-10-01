"""Reproduce the bounded P01-07 analytical/LAMMPS convergence evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from pgworld.config.physics_profiles import load_physics_profile
from run_lammps_elastic_tensor import (
    TangentBaseState,
    local_2d_tangent_convention,
    run_lammps_harmonic_bond_tangent,
)


def independent_derivative(
    displacement_nm: np.ndarray,
    *,
    area_nm2: float,
    stiffness_pN_per_nm: float,
    rest_length_nm: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Closed-form current-area harmonic-bond derivative at q=0."""

    d = np.asarray(displacement_nm, dtype=float)
    radius = float(np.linalg.norm(d))
    beta = 2.0 * stiffness_pN_per_nm * (1.0 - rest_length_nm / radius)
    alpha = beta / area_nm2
    base_tensor = alpha * np.outer(d, d)
    tangent = np.empty((3, 3), dtype=float)
    displacement_derivatives = (
        np.array([d[0], 0.0]),
        np.array([0.0, d[1]]),
        np.array([d[1], 0.0]),
    )
    for column, (dprime, area_prime) in enumerate(
        zip(displacement_derivatives, (area_nm2, area_nm2, 0.0))
    ):
        radius_prime = float(np.dot(d, dprime) / radius)
        beta_prime = (
            2.0
            * stiffness_pN_per_nm
            * rest_length_nm
            * radius_prime
            / radius**2
        )
        alpha_prime = beta_prime / area_nm2 - beta * area_prime / area_nm2**2
        derivative = alpha_prime * np.outer(d, d) + alpha * (
            np.outer(dprime, d) + np.outer(d, dprime)
        )
        tangent[:, column] = (
            derivative[0, 0],
            derivative[1, 1],
            derivative[0, 1],
        )
    base = np.array((base_tensor[0, 0], base_tensor[1, 1], base_tensor[0, 1]))
    return base, tangent


profile = load_physics_profile("reviewed_physics_provisional_v0")
parameters = profile.expanded_snapshot()["potentials"]["harmonic_bond"]["parameters"]
displacement = np.array([1.0, 0.875])
base_pair = np.vstack((-0.5 * displacement, 0.5 * displacement))
one_base, one_tangent = independent_derivative(
    displacement,
    area_nm2=56.0,
    stiffness_pN_per_nm=parameters["K_pN_per_nm"],
    rest_length_nm=parameters["r0_nm"],
)
exact_base = 8.0 * one_base
exact_tangent = 8.0 * one_tangent
base_state = TangentBaseState.create(
    profile=profile,
    base_state_id="p01-07-periodic-ring-base",
    cell_matrix_nm=np.array([[8.0, 0.0], [0.0, 7.0]]),
    base_total_tension_pN_per_nm=exact_base,
    topology_id="periodic-ring-8-bonds",
    branch_id="balanced-oblique-ring",
    load_coordinate=0.125,
    minimization_converged=True,
    fixed_reference_id="p01-07-fixed-reference",
    fixed_reference_cell_matrix_nm=np.array([[7.5, 0.0], [0.0, 6.8]]),
    fixed_reference_total_tension_pN_per_nm=np.array([0.25, -0.1, 0.04]),
    fixed_reference_topology_id="periodic-ring-8-bonds",
    fixed_reference_branch_id="initial-balanced-ring",
    fixed_reference_load_coordinate=0.0,
    fixed_reference_minimization_converged=True,
)

rows = []
errors = []
all_samples = []
for step in (1.0e-3, 5.0e-4, 2.5e-4):
    result = run_lammps_harmonic_bond_tangent(
        profile,
        base_state=base_state,
        base_pair_positions_nm=base_pair,
        step_sizes=np.full(3, step),
    )
    error = float(np.linalg.norm(result.raw_matrix_pN_per_nm - exact_tangent))
    errors.append(error)
    record = result.as_record()
    all_samples.extend(record["samples"])
    rows.append(
        {
            "step": step,
            "raw_tangent_pN_per_nm": result.raw_matrix_pN_per_nm.tolist(),
            "frobenius_error_pN_per_nm": error,
            "base_tension_pN_per_nm": result.base_total_tension_pN_per_nm.tolist(),
            "asymmetry_diagnostics": result.asymmetry_diagnostics,
            "solver_validation": result.solver_validation,
            "max_sample_force_pN": max(
                sample["max_force_pN"] for sample in record["samples"]
            ),
            "sample_areas_nm2": [sample["area_nm2"] for sample in record["samples"]],
            "sample_cells_nm": [sample["cell_matrix_nm"] for sample in record["samples"]],
        }
    )

finest = np.asarray(rows[-1]["raw_tangent_pN_per_nm"])
identity_residuals = {
    "C12_minus_C21_minus_Nyy_minus_Nxx_pN_per_nm": float(
        finest[0, 1] - finest[1, 0] - (exact_base[1] - exact_base[0])
    ),
    "C13_minus_C31_minus_2Nxy_pN_per_nm": float(
        finest[0, 2] - finest[2, 0] - 2.0 * exact_base[2]
    ),
    "C23_minus_C32_pN_per_nm": float(finest[1, 2] - finest[2, 1]),
}
payload = {
    "task_id": "P01-07",
    "fixture": "8-bond oblique prestressed minimized periodic harmonic ring",
    "profile_identity": profile.identity,
    "convention": local_2d_tangent_convention().as_record(),
    "exact_base_tension_pN_per_nm": exact_base.tolist(),
    "exact_raw_tangent_pN_per_nm": exact_tangent.tolist(),
    "step_results": rows,
    "successive_error_ratios": [errors[1] / errors[0], errors[2] / errors[1]],
    "finest_geometric_identity_residuals": identity_residuals,
    "solver_instances_started": 21,
    "solver_instances_closed": sum(
        sample["solver_closed"] is True for sample in all_samples
    ),
    "solver_version": 20260902,
    "all_minimizations_converged": all(
        sample["minimization_converged"] is True for sample in all_samples
    ),
    "max_force_pN": max(sample["max_force_pN"] for sample in all_samples),
    "physical_time_claim": False,
    "equilibrium_modulus_claim": False,
    "biological_parameter_certification_claim": False,
    "limitations": [
        "bounded numerical fixture, not a biological parameter certification",
        "local spatial/algorithmic current-area tangent, not a general finite-strain material tensor",
        "no rupture, physical-time, three-dimensional, or production-campaign claim",
    ],
}
canonical = json.dumps(payload, allow_nan=False, separators=(",", ":"), sort_keys=True)
payload["payload_sha256_excluding_this_field"] = "sha256:" + hashlib.sha256(
    canonical.encode("utf-8")
).hexdigest()
print(json.dumps(payload, allow_nan=False, indent=2, sort_keys=True))
