from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from typing import Any, Callable, Literal, Mapping
import warnings

from lammps import lammps
import numpy as np
import re
from os.path import exists, splitext, dirname, join
from simulation_constants_settings import *
from run_lammps_isotropic_strain import lammps_PG_simulation_settings, lammps_PG_potential_settings, lammps_PG_thermo_settings

from pgworld.config.physics_profiles import (
    PhysicsProfile,
    ProfileMixingError,
    validate_expanded_profile_snapshot,
)


TANGENT_SCHEMA_VERSION = "pgworld.raw_elastic_tangent.v1"
LAMMPS_REQUIRED_VERSION = 20260902
_STRAIN_ORDER = ("epsilon_xx", "epsilon_yy", "gamma_xy")
_TENSION_ORDER = ("N_xx", "N_yy", "N_xy")


def _finite_array(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with shape {shape}")
    result = np.array(array, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _positive_area(cell_matrix_nm: Any, name: str = "cell matrix") -> tuple[np.ndarray, float]:
    cell = _finite_array(cell_matrix_nm, (2, 2), name)
    area = float(np.linalg.det(cell))
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError(f"{name} must have a finite positive determinant/area")
    return cell, area


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _canonical_profile_json(profile: PhysicsProfile | Mapping[str, Any]) -> str:
    if isinstance(profile, PhysicsProfile):
        validated = validate_expanded_profile_snapshot(profile.expanded_snapshot())
    elif isinstance(profile, Mapping):
        validated = validate_expanded_profile_snapshot(profile)
    else:
        raise TypeError("physics profile must be a PhysicsProfile or expanded snapshot")
    return json.dumps(
        validated.expanded_snapshot(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


@dataclass(frozen=True)
class TangentConvention:
    """Exact local deformation and 2D configurational-tension convention."""

    def as_record(self) -> dict[str, Any]:
        return {
            "axes": {"x": "axial", "y": "hoop"},
            "incremental_deformation_gradient": (
                "F_inc=[[1+epsilon_xx,gamma_xy],[0,1+epsilon_yy]]"
            ),
            "incremental_cell_update": "H(q)=F_inc(q)@H_base",
            "trial_coordinate_update": "x_trial=F_inc(q)@x_base",
            "sample_coordinate_update": (
                "x_sample=relax(x_trial,H(q),same_topology_and_branch)"
            ),
            "strain_vector_order": list(_STRAIN_ORDER),
            "shear_definition": "engineering_simple_shear_gamma_xy_equals_F_xy",
            "tension_vector_order": list(_TENSION_ORDER),
            "tension_unit": "pN/nm",
            "tension_source": (
                "configurational_virial_only_N_equals_minus_W_over_current_area"
            ),
            "tension_measure": "current_area_cauchy_like_membrane_tension",
            "raw_derivative_interpretation": (
                "local_spatial_algorithmic_tangent_not_general_finite_strain_material_tensor"
            ),
            "primary_quantity": "total_configurational_tension_2d",
            "secondary_quantity": "incremental_from_fixed_reference",
            "incremental_derivative_relation": (
                "dN_total_dq_equals_dDeltaN_dq_because_N_fixed_reference_is_constant"
            ),
            "reference_state": "fixed_cell_equilibrated_not_zero_tension",
            "load_coordinate_kind": "quasi_static_not_physical_time",
            "dimensional_scope": "native_2d_no_thickness_conversion",
        }


def local_2d_tangent_convention() -> TangentConvention:
    return TangentConvention()


def deformation_gradient(increment: Any) -> np.ndarray:
    """Return F for q=[epsilon_xx, epsilon_yy, engineering gamma_xy]."""

    q = _finite_array(increment, (3,), "strain increment")
    deformation = np.array(
        [[1.0 + q[0], q[2]], [0.0, 1.0 + q[1]]], dtype=float
    )
    determinant = float(np.linalg.det(deformation))
    if not math.isfinite(determinant) or determinant <= 0.0:
        raise ValueError("strain increment produces a non-positive cell area")
    return deformation


@dataclass(frozen=True)
class TangentBaseState:
    """Local tangent base plus the immutable initial fixed-cell reference."""

    base_state_id: str
    cell_matrix_nm: np.ndarray
    area_nm2: float
    base_total_tension_pN_per_nm: np.ndarray
    topology_id: str
    branch_id: str
    load_coordinate: float
    minimization_converged: bool
    fixed_reference_id: str
    fixed_reference_cell_matrix_nm: np.ndarray
    fixed_reference_area_nm2: float
    fixed_reference_total_tension_pN_per_nm: np.ndarray
    fixed_reference_topology_id: str
    fixed_reference_branch_id: str
    fixed_reference_load_coordinate: float
    fixed_reference_minimization_converged: bool
    _physics_profile_json: str

    def __post_init__(self) -> None:
        cell, area = _positive_area(self.cell_matrix_nm, "tangent base cell matrix")
        if not math.isclose(float(self.area_nm2), area, rel_tol=2e-14, abs_tol=2e-14):
            raise ValueError("tangent base area must equal det(tangent base cell)")
        base_tension = _finite_array(
            self.base_total_tension_pN_per_nm, (3,), "tangent base total tension"
        )
        fixed_cell, fixed_area = _positive_area(
            self.fixed_reference_cell_matrix_nm, "fixed reference cell matrix"
        )
        if not math.isclose(
            float(self.fixed_reference_area_nm2),
            fixed_area,
            rel_tol=2e-14,
            abs_tol=2e-14,
        ):
            raise ValueError("fixed reference area must equal det(fixed reference cell)")
        fixed_tension = _finite_array(
            self.fixed_reference_total_tension_pN_per_nm,
            (3,),
            "fixed reference total tension",
        )
        _nonempty(self.base_state_id, "tangent base state ID")
        _nonempty(self.topology_id, "tangent base topology ID")
        _nonempty(self.branch_id, "tangent base branch ID")
        _nonempty(self.fixed_reference_id, "fixed reference ID")
        _nonempty(self.fixed_reference_topology_id, "fixed reference topology ID")
        _nonempty(self.fixed_reference_branch_id, "fixed reference branch ID")
        if not math.isfinite(float(self.load_coordinate)):
            raise ValueError("tangent base load coordinate must be finite")
        if not math.isfinite(float(self.fixed_reference_load_coordinate)):
            raise ValueError("fixed reference load coordinate must be finite")
        if self.minimization_converged is not True:
            raise ValueError("tangent base state must be converged")
        if self.fixed_reference_minimization_converged is not True:
            raise ValueError("fixed-cell equilibrated reference must be converged")
        canonical = _canonical_profile_json(json.loads(self._physics_profile_json))
        object.__setattr__(self, "cell_matrix_nm", cell)
        object.__setattr__(self, "area_nm2", area)
        object.__setattr__(self, "base_total_tension_pN_per_nm", base_tension)
        object.__setattr__(self, "fixed_reference_cell_matrix_nm", fixed_cell)
        object.__setattr__(self, "fixed_reference_area_nm2", fixed_area)
        object.__setattr__(
            self, "fixed_reference_total_tension_pN_per_nm", fixed_tension
        )
        object.__setattr__(self, "_physics_profile_json", canonical)

    @classmethod
    def create(
        cls,
        *,
        profile: PhysicsProfile | Mapping[str, Any],
        base_state_id: str,
        cell_matrix_nm: Any,
        base_total_tension_pN_per_nm: Any,
        topology_id: str,
        branch_id: str,
        load_coordinate: float,
        minimization_converged: bool,
        fixed_reference_id: str,
        fixed_reference_cell_matrix_nm: Any,
        fixed_reference_total_tension_pN_per_nm: Any,
        fixed_reference_topology_id: str,
        fixed_reference_branch_id: str,
        fixed_reference_load_coordinate: float,
        fixed_reference_minimization_converged: bool,
    ) -> "TangentBaseState":
        cell, area = _positive_area(cell_matrix_nm, "tangent base cell matrix")
        base_tension = _finite_array(
            base_total_tension_pN_per_nm, (3,), "tangent base total tension"
        )
        fixed_cell, fixed_area = _positive_area(
            fixed_reference_cell_matrix_nm, "fixed reference cell matrix"
        )
        fixed_tension = _finite_array(
            fixed_reference_total_tension_pN_per_nm,
            (3,),
            "fixed reference total tension",
        )
        coordinate = float(load_coordinate)
        if not math.isfinite(coordinate):
            raise ValueError("tangent base load coordinate must be finite")
        fixed_coordinate = float(fixed_reference_load_coordinate)
        if not math.isfinite(fixed_coordinate):
            raise ValueError("fixed reference load coordinate must be finite")
        if minimization_converged is not True:
            raise ValueError("tangent base state must have converged minimization")
        if fixed_reference_minimization_converged is not True:
            raise ValueError("fixed reference must have converged minimization")
        return cls(
            base_state_id=_nonempty(base_state_id, "tangent base state ID"),
            cell_matrix_nm=cell,
            area_nm2=area,
            base_total_tension_pN_per_nm=base_tension,
            topology_id=_nonempty(topology_id, "tangent base topology ID"),
            branch_id=_nonempty(branch_id, "tangent base branch ID"),
            load_coordinate=coordinate,
            minimization_converged=True,
            fixed_reference_id=_nonempty(fixed_reference_id, "fixed reference ID"),
            fixed_reference_cell_matrix_nm=fixed_cell,
            fixed_reference_area_nm2=fixed_area,
            fixed_reference_total_tension_pN_per_nm=fixed_tension,
            fixed_reference_topology_id=_nonempty(
                fixed_reference_topology_id, "fixed reference topology ID"
            ),
            fixed_reference_branch_id=_nonempty(
                fixed_reference_branch_id, "fixed reference branch ID"
            ),
            fixed_reference_load_coordinate=fixed_coordinate,
            fixed_reference_minimization_converged=True,
            _physics_profile_json=_canonical_profile_json(profile),
        )

    @property
    def physics_profile(self) -> dict[str, Any]:
        return json.loads(self._physics_profile_json)

    @property
    def profile_identity(self) -> dict[str, str]:
        snapshot = self.physics_profile
        return {
            "profile_id": snapshot["profile_id"],
            "canonical_hash": snapshot["canonical_hash"],
        }

    @property
    def base_is_fixed_reference(self) -> bool:
        return (
            self.base_state_id == self.fixed_reference_id
            and np.array_equal(self.cell_matrix_nm, self.fixed_reference_cell_matrix_nm)
            and np.array_equal(
                self.base_total_tension_pN_per_nm,
                self.fixed_reference_total_tension_pN_per_nm,
            )
            and self.topology_id == self.fixed_reference_topology_id
            and self.branch_id == self.fixed_reference_branch_id
            and self.load_coordinate == self.fixed_reference_load_coordinate
        )

    def base_record(self) -> dict[str, Any]:
        return {
            "base_state_id": self.base_state_id,
            "cell_matrix_nm": self.cell_matrix_nm.tolist(),
            "area_nm2": self.area_nm2,
            "total_tension_pN_per_nm": self.base_total_tension_pN_per_nm.tolist(),
            "cell_policy": "fixed_cell",
            "zero_tension_claim": False,
            "topology_id": self.topology_id,
            "branch_id": self.branch_id,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_kind": "quasi_static_not_physical_time",
            "minimization_converged": self.minimization_converged,
        }

    def fixed_reference_record(self) -> dict[str, Any]:
        return {
            "reference_id": self.fixed_reference_id,
            "cell_matrix_nm": self.fixed_reference_cell_matrix_nm.tolist(),
            "area_nm2": self.fixed_reference_area_nm2,
            "total_tension_pN_per_nm": (
                self.fixed_reference_total_tension_pN_per_nm.tolist()
            ),
            "cell_policy": "fixed_cell",
            "zero_tension_claim": False,
            "topology_id": self.fixed_reference_topology_id,
            "branch_id": self.fixed_reference_branch_id,
            "load_coordinate": self.fixed_reference_load_coordinate,
            "load_coordinate_kind": "quasi_static_not_physical_time",
            "minimization_converged": (
                self.fixed_reference_minimization_converged
            ),
        }


@dataclass(frozen=True)
class TensionObservation:
    """One replayable total-tension observation at its actual current cell."""

    total_tension_pN_per_nm: np.ndarray
    cell_matrix_nm: np.ndarray
    area_nm2: float
    topology_id: str
    branch_id: str
    minimization_performed: bool
    minimization_converged: bool | None
    max_force_pN: float | None
    state_evaluation: str
    solver_version: int | None
    solver_closed: bool | None
    _physics_profile_json: str

    def __post_init__(self) -> None:
        tension = _finite_array(
            self.total_tension_pN_per_nm, (3,), "total 2D tension"
        )
        cell, area = _positive_area(self.cell_matrix_nm, "observation cell matrix")
        if not math.isclose(float(self.area_nm2), area, rel_tol=2e-14, abs_tol=2e-14):
            raise ValueError("observation area must equal det(observation cell)")
        _nonempty(self.topology_id, "observation topology ID")
        _nonempty(self.branch_id, "observation branch ID")
        _nonempty(self.state_evaluation, "observation state evaluation")
        if self.minimization_performed is True:
            if self.minimization_converged is not True:
                raise ValueError("performed minimization must be recorded as converged")
            if self.max_force_pN is None or not math.isfinite(float(self.max_force_pN)):
                raise ValueError("converged minimization requires a finite max force")
            if float(self.max_force_pN) < 0.0:
                raise ValueError("converged minimization max force cannot be negative")
        elif self.minimization_performed is False:
            if self.minimization_converged is not None or self.max_force_pN is not None:
                raise ValueError("unperformed minimization must record convergence/force as null")
        else:
            raise ValueError("minimization_performed must be a boolean")
        if (self.solver_version is None) != (self.solver_closed is None):
            raise ValueError("solver version and closure status must be recorded together")
        if self.solver_version is not None:
            if int(self.solver_version) != LAMMPS_REQUIRED_VERSION:
                raise RuntimeError(
                    f"expected LAMMPS {LAMMPS_REQUIRED_VERSION}, found {self.solver_version}"
                )
            if self.solver_closed is not True:
                raise RuntimeError("solver-backed observation must confirm solver closure")
        canonical = _canonical_profile_json(json.loads(self._physics_profile_json))
        object.__setattr__(self, "total_tension_pN_per_nm", tension)
        object.__setattr__(self, "cell_matrix_nm", cell)
        object.__setattr__(self, "area_nm2", area)
        object.__setattr__(self, "_physics_profile_json", canonical)

    @classmethod
    def create(
        cls,
        *,
        total_tension_pN_per_nm: Any,
        cell_matrix_nm: Any,
        topology_id: str,
        branch_id: str,
        profile: PhysicsProfile | Mapping[str, Any],
        minimization_converged: bool,
        minimization_performed: bool = True,
        max_force_pN: float | None = 0.0,
        state_evaluation: str = "converged_fixed_cell_state",
        solver_version: int | None = None,
        solver_closed: bool | None = None,
    ) -> "TensionObservation":
        tension = _finite_array(
            total_tension_pN_per_nm, (3,), "total 2D tension"
        )
        cell, area = _positive_area(cell_matrix_nm, "observation cell matrix")
        if minimization_performed is not True or minimization_converged is not True:
            raise ValueError(
                "scientific tangent observations require a performed, converged minimization"
            )
        return cls(
            total_tension_pN_per_nm=tension,
            cell_matrix_nm=cell,
            area_nm2=area,
            topology_id=_nonempty(topology_id, "observation topology ID"),
            branch_id=_nonempty(branch_id, "observation branch ID"),
            minimization_performed=True,
            minimization_converged=True,
            max_force_pN=max_force_pN,
            state_evaluation=_nonempty(state_evaluation, "state evaluation"),
            solver_version=None if solver_version is None else int(solver_version),
            solver_closed=solver_closed,
            _physics_profile_json=_canonical_profile_json(profile),
        )

    @property
    def physics_profile(self) -> dict[str, Any]:
        return json.loads(self._physics_profile_json)

    @property
    def profile_identity(self) -> dict[str, str]:
        snapshot = self.physics_profile
        return {
            "profile_id": snapshot["profile_id"],
            "canonical_hash": snapshot["canonical_hash"],
        }


def _step_vector(step_sizes: Any) -> np.ndarray:
    steps = _finite_array(step_sizes, (3,), "finite-difference step sizes")
    if np.any(steps <= 0.0):
        raise ValueError("finite-difference step sizes must be positive")
    # The local convention must not accidentally become a finite-strain sweep.
    if np.any(steps >= 0.1):
        raise ValueError("finite-difference step sizes must be smaller than 0.1")
    return steps


def _validate_observation(
    observation: Any,
    *,
    reference: TangentBaseState,
    increment: np.ndarray,
    require_same_branch: bool,
) -> TensionObservation:
    if not isinstance(observation, TensionObservation):
        raise TypeError("observer must return TensionObservation")
    if observation.profile_identity != reference.profile_identity:
        raise ProfileMixingError(
            "tangent observation physics profile does not match the reference profile"
        )
    expected_cell = deformation_gradient(increment) @ reference.cell_matrix_nm
    expected_area = float(np.linalg.det(expected_cell))
    if not np.allclose(
        observation.cell_matrix_nm, expected_cell, rtol=2.0e-14, atol=2.0e-14
    ) or not math.isclose(
        observation.area_nm2, expected_area, rel_tol=2.0e-14, abs_tol=2.0e-14
    ):
        raise ValueError(
            "observation cell/area must equal the current H=F@H0 cell, not H0/A0"
        )
    if require_same_branch and (
        observation.topology_id != reference.topology_id
        or observation.branch_id != reference.branch_id
    ):
        raise ValueError(
            "central smooth branch stencil changed topology or equilibrium branch"
        )
    return observation


def _sample_record(
    observation: TensionObservation,
    *,
    increment: np.ndarray,
    stencil_position: str,
    component_index: int | None,
    step_size: float | None,
) -> dict[str, Any]:
    return {
        "stencil_position": stencil_position,
        "component_index": component_index,
        "component_name": None if component_index is None else _STRAIN_ORDER[component_index],
        "step_size": step_size,
        "strain_increment": increment.tolist(),
        "total_tension_pN_per_nm": observation.total_tension_pN_per_nm.tolist(),
        "cell_matrix_nm": observation.cell_matrix_nm.tolist(),
        "area_nm2": observation.area_nm2,
        "topology_id": observation.topology_id,
        "branch_id": observation.branch_id,
        "minimization_performed": observation.minimization_performed,
        "minimization_converged": observation.minimization_converged,
        "max_force_pN": observation.max_force_pN,
        "state_evaluation": observation.state_evaluation,
        "profile_id": observation.profile_identity["profile_id"],
        "profile_hash": observation.profile_identity["canonical_hash"],
        "solver_version": observation.solver_version,
        "solver_closed": observation.solver_closed,
    }


def _asymmetry_diagnostics(matrix: np.ndarray) -> dict[str, Any]:
    difference = matrix - matrix.T
    return {
        "matrix_minus_transpose_pN_per_nm": difference.tolist(),
        "frobenius_norm_matrix_minus_transpose_pN_per_nm": float(
            np.linalg.norm(difference)
        ),
        "max_abs_matrix_minus_transpose_pN_per_nm": float(
            np.max(np.abs(difference))
        ),
        "C12_minus_C21_pN_per_nm": float(matrix[0, 1] - matrix[1, 0]),
        "C13_minus_C31_pN_per_nm": float(matrix[0, 2] - matrix[2, 0]),
        "C23_minus_C32_pN_per_nm": float(matrix[1, 2] - matrix[2, 1]),
        "raw_values_replaced_or_symmetrized": False,
    }


@dataclass(frozen=True)
class TangentEstimate:
    """Raw local derivative estimate with replayable stencil observations."""

    raw_matrix_pN_per_nm: np.ndarray
    base_total_tension_pN_per_nm: np.ndarray
    step_sizes: np.ndarray
    base_state: TangentBaseState
    derivative_metadata: dict[str, Any]
    sample_records: tuple[dict[str, Any], ...]
    solver_validation: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "raw_matrix_pN_per_nm",
            _finite_array(self.raw_matrix_pN_per_nm, (3, 3), "raw tangent matrix"),
        )
        object.__setattr__(
            self,
            "base_total_tension_pN_per_nm",
            _finite_array(
                self.base_total_tension_pN_per_nm,
                (3,),
                "tangent base total tension",
            ),
        )
        if not np.array_equal(
            self.base_total_tension_pN_per_nm,
            self.base_state.base_total_tension_pN_per_nm,
        ):
            raise ValueError("result base tension does not match tangent base state")
        object.__setattr__(self, "step_sizes", _step_vector(self.step_sizes))

    @property
    def physics_profile(self) -> dict[str, Any]:
        return self.base_state.physics_profile

    @property
    def asymmetry_diagnostics(self) -> dict[str, Any]:
        return _asymmetry_diagnostics(self.raw_matrix_pN_per_nm)

    def as_record(self) -> dict[str, Any]:
        record = {
            "schema_version": TANGENT_SCHEMA_VERSION,
            "convention": local_2d_tangent_convention().as_record(),
            "fixed_reference": self.base_state.fixed_reference_record(),
            "tangent_base_state": self.base_state.base_record(),
            "base_total_tension_pN_per_nm": self.base_total_tension_pN_per_nm.tolist(),
            "incremental_base_tension_from_fixed_reference_pN_per_nm": (
                self.base_total_tension_pN_per_nm
                - self.base_state.fixed_reference_total_tension_pN_per_nm
            ).tolist(),
            "base_is_fixed_reference": self.base_state.base_is_fixed_reference,
            "raw_tangent": {
                "values": self.raw_matrix_pN_per_nm.tolist(),
                "row_order": list(_TENSION_ORDER),
                "column_order": list(_STRAIN_ORDER),
                "unit": "pN/nm",
                "symmetrized": False,
            },
            "step_sizes": self.step_sizes.tolist(),
            "derivative": json.loads(
                json.dumps(self.derivative_metadata, allow_nan=False)
            ),
            "samples": json.loads(json.dumps(self.sample_records, allow_nan=False)),
            "asymmetry_diagnostics": self.asymmetry_diagnostics,
            "solver_validation": self.solver_validation,
            "physics_profile": self.physics_profile,
            "physical_time_claim": False,
            "biological_parameter_certification_claim": False,
            "three_dimensional_modulus_claim": False,
        }
        validate_raw_tangent_record(record)
        return record


def _estimate_derivative(
    observe: Callable[[np.ndarray], TensionObservation],
    *,
    reference: TangentBaseState,
    step_sizes: Any,
    kind: Literal["central", "forward", "backward"],
    reason: str | None = None,
) -> TangentEstimate:
    steps = _step_vector(step_sizes)
    zero = np.zeros(3, dtype=float)
    base = _validate_observation(
        observe(zero.copy()),
        reference=reference,
        increment=zero,
        require_same_branch=True,
    )
    if not np.allclose(
        base.total_tension_pN_per_nm,
        reference.base_total_tension_pN_per_nm,
        rtol=2.0e-13,
        atol=2.0e-12,
    ):
        raise ValueError(
            "zero-stencil tension does not match the declared tangent base state"
        )
    resolved_base_state = replace(
        reference,
        base_total_tension_pN_per_nm=base.total_tension_pN_per_nm,
    )
    sample_records = [
        _sample_record(
            base,
            increment=zero,
            stencil_position="base",
            component_index=None,
            step_size=None,
        )
    ]
    matrix = np.empty((3, 3), dtype=float)
    noncentral_observations: list[TensionObservation] = []
    for component, step in enumerate(steps):
        if kind == "central":
            minus_q = zero.copy()
            plus_q = zero.copy()
            minus_q[component] = -step
            plus_q[component] = step
            minus = _validate_observation(
                observe(minus_q.copy()),
                reference=reference,
                increment=minus_q,
                require_same_branch=True,
            )
            plus = _validate_observation(
                observe(plus_q.copy()),
                reference=reference,
                increment=plus_q,
                require_same_branch=True,
            )
            matrix[:, component] = (
                plus.total_tension_pN_per_nm - minus.total_tension_pN_per_nm
            ) / (2.0 * step)
            sample_records.extend(
                [
                    _sample_record(
                        minus,
                        increment=minus_q,
                        stencil_position="minus",
                        component_index=component,
                        step_size=float(step),
                    ),
                    _sample_record(
                        plus,
                        increment=plus_q,
                        stencil_position="plus",
                        component_index=component,
                        step_size=float(step),
                    ),
                ]
            )
        else:
            signed_step = step if kind == "forward" else -step
            q = zero.copy()
            q[component] = signed_step
            sample = _validate_observation(
                observe(q.copy()),
                reference=reference,
                increment=q,
                require_same_branch=False,
            )
            noncentral_observations.append(sample)
            matrix[:, component] = (
                sample.total_tension_pN_per_nm - base.total_tension_pN_per_nm
            ) / signed_step
            sample_records.append(
                _sample_record(
                    sample,
                    increment=q,
                    stencil_position=kind,
                    component_index=component,
                    step_size=float(step),
                )
            )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("finite-difference result must be finite")

    if kind == "central":
        derivative = {
            "kind": "central_smooth_branch",
            "stencil": "three_point_central",
            "base_topology_id": reference.topology_id,
            "base_branch_id": reference.branch_id,
            "sample_topology_ids": [reference.topology_id] * 6,
            "sample_branch_ids": [reference.branch_id] * 6,
            "smooth_fixed_topology_branch": True,
            "equilibrium_modulus_claim": False,
            "label": "local_total_tension_derivative",
        }
    else:
        reason_text = "" if reason is None else reason.strip()
        changed = any(
            item.topology_id != reference.topology_id
            or item.branch_id != reference.branch_id
            for item in noncentral_observations
        )
        if not reason_text or not changed:
            raise ValueError(
                "one-sided branch-changing secant requires an explicit irreversible "
                "reason and an observed topology/branch transition"
            )
        derivative = {
            "kind": f"{kind}_branch_changing_secant",
            "stencil": f"base_and_{kind}_sample",
            "side": kind,
            "reason": reason_text,
            "base_topology_id": reference.topology_id,
            "base_branch_id": reference.branch_id,
            "sample_topology_ids": [item.topology_id for item in noncentral_observations],
            "sample_branch_ids": [item.branch_id for item in noncentral_observations],
            "smooth_fixed_topology_branch": False,
            "equilibrium_modulus_claim": False,
            "label": "directional_secant_not_elastic_tangent_or_modulus",
        }
    return TangentEstimate(
        raw_matrix_pN_per_nm=matrix,
        base_total_tension_pN_per_nm=base.total_tension_pN_per_nm,
        step_sizes=steps,
        base_state=resolved_base_state,
        derivative_metadata=derivative,
        sample_records=tuple(sample_records),
    )


def central_difference_tangent(
    observe: Callable[[np.ndarray], TensionObservation],
    *,
    base_state: TangentBaseState,
    step_sizes: Any,
) -> TangentEstimate:
    """Estimate all nine raw entries on one smooth fixed-topology branch."""

    return _estimate_derivative(
        observe, reference=base_state, step_sizes=step_sizes, kind="central"
    )


def one_sided_difference_tangent(
    observe: Callable[[np.ndarray], TensionObservation],
    *,
    base_state: TangentBaseState,
    step_sizes: Any,
    side: Literal["forward", "backward"],
    reason: str,
) -> TangentEstimate:
    """Record a branch-changing directional secant without a modulus claim."""

    if side not in ("forward", "backward"):
        raise ValueError("one-sided direction must be 'forward' or 'backward'")
    return _estimate_derivative(
        observe,
        reference=base_state,
        step_sizes=step_sizes,
        kind=side,
        reason=reason,
    )


_RAW_RECORD_FIELDS = {
    "schema_version",
    "convention",
    "fixed_reference",
    "tangent_base_state",
    "base_total_tension_pN_per_nm",
    "incremental_base_tension_from_fixed_reference_pN_per_nm",
    "base_is_fixed_reference",
    "raw_tangent",
    "step_sizes",
    "derivative",
    "samples",
    "asymmetry_diagnostics",
    "solver_validation",
    "physics_profile",
    "physical_time_claim",
    "biological_parameter_certification_claim",
    "three_dimensional_modulus_claim",
}


def validate_raw_tangent_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when a persisted raw derivative loses its convention/provenance."""

    if not isinstance(record, Mapping) or set(record) != _RAW_RECORD_FIELDS:
        raise ValueError("raw tangent record has missing or unknown fields")
    if record["schema_version"] != TANGENT_SCHEMA_VERSION:
        raise ValueError("unsupported raw tangent schema version")
    if record["convention"] != local_2d_tangent_convention().as_record():
        raise ValueError("raw tangent convention/shear definition is ambiguous or changed")
    if any(
        record[field] is not False
        for field in (
            "physical_time_claim",
            "biological_parameter_certification_claim",
            "three_dimensional_modulus_claim",
        )
    ):
        raise ValueError("unsupported physical-time, biological, or 3D claim")
    profile = validate_expanded_profile_snapshot(record["physics_profile"])
    identity = profile.identity

    raw = record["raw_tangent"]
    if not isinstance(raw, Mapping) or set(raw) != {
        "values",
        "row_order",
        "column_order",
        "unit",
        "symmetrized",
    }:
        raise ValueError("raw tangent matrix metadata is incomplete")
    if raw["row_order"] != list(_TENSION_ORDER) or raw["column_order"] != list(
        _STRAIN_ORDER
    ):
        raise ValueError("raw tangent row/column convention is invalid")
    if raw["unit"] != "pN/nm" or raw["symmetrized"] is not False:
        raise ValueError("raw tangent units or symmetrization flag is invalid")
    matrix = _finite_array(raw["values"], (3, 3), "raw tangent values")
    steps = _step_vector(record["step_sizes"])
    persisted_base_tension = _finite_array(
        record["base_total_tension_pN_per_nm"],
        (3,),
        "tangent base total tension",
    )
    persisted_incremental = _finite_array(
        record["incremental_base_tension_from_fixed_reference_pN_per_nm"],
        (3,),
        "incremental base tension from fixed reference",
    )

    fixed_reference_record = record["fixed_reference"]
    expected_fixed_reference_fields = {
        "reference_id",
        "cell_matrix_nm",
        "area_nm2",
        "total_tension_pN_per_nm",
        "cell_policy",
        "zero_tension_claim",
        "topology_id",
        "branch_id",
        "load_coordinate",
        "load_coordinate_kind",
        "minimization_converged",
    }
    if not isinstance(fixed_reference_record, Mapping) or set(
        fixed_reference_record
    ) != expected_fixed_reference_fields:
        raise ValueError("fixed reference metadata is incomplete")
    fixed_reference_cell, fixed_reference_area = _positive_area(
        fixed_reference_record["cell_matrix_nm"], "persisted fixed reference cell"
    )
    if not math.isclose(
        float(fixed_reference_record["area_nm2"]),
        fixed_reference_area,
        rel_tol=2.0e-14,
        abs_tol=2.0e-14,
    ):
        raise ValueError("persisted fixed reference area does not match its cell")
    fixed_reference_tension = _finite_array(
        fixed_reference_record["total_tension_pN_per_nm"],
        (3,),
        "fixed reference total tension",
    )
    if (
        fixed_reference_record["cell_policy"] != "fixed_cell"
        or fixed_reference_record["zero_tension_claim"] is not False
        or fixed_reference_record["load_coordinate_kind"]
        != "quasi_static_not_physical_time"
        or fixed_reference_record["minimization_converged"] is not True
    ):
        raise ValueError("persisted fixed-cell reference semantics are invalid")
    if not math.isfinite(float(fixed_reference_record["load_coordinate"])):
        raise ValueError("persisted reference load coordinate must be finite")
    for field in ("reference_id", "topology_id", "branch_id"):
        _nonempty(fixed_reference_record[field], f"fixed reference {field}")

    tangent_base_record = record["tangent_base_state"]
    expected_base_fields = {
        "base_state_id",
        "cell_matrix_nm",
        "area_nm2",
        "total_tension_pN_per_nm",
        "cell_policy",
        "zero_tension_claim",
        "topology_id",
        "branch_id",
        "load_coordinate",
        "load_coordinate_kind",
        "minimization_converged",
    }
    if not isinstance(tangent_base_record, Mapping) or set(
        tangent_base_record
    ) != expected_base_fields:
        raise ValueError("tangent base-state metadata is incomplete")
    base_cell, base_area = _positive_area(
        tangent_base_record["cell_matrix_nm"], "persisted tangent base cell"
    )
    if not math.isclose(
        float(tangent_base_record["area_nm2"]),
        base_area,
        rel_tol=2.0e-14,
        abs_tol=2.0e-14,
    ):
        raise ValueError("persisted tangent base area does not match its cell")
    base_record_tension = _finite_array(
        tangent_base_record["total_tension_pN_per_nm"],
        (3,),
        "tangent base record total tension",
    )
    if (
        tangent_base_record["cell_policy"] != "fixed_cell"
        or tangent_base_record["zero_tension_claim"] is not False
        or tangent_base_record["load_coordinate_kind"]
        != "quasi_static_not_physical_time"
        or tangent_base_record["minimization_converged"] is not True
        or not math.isfinite(float(tangent_base_record["load_coordinate"]))
    ):
        raise ValueError("persisted tangent base-state semantics are invalid")
    for field in ("base_state_id", "topology_id", "branch_id"):
        _nonempty(tangent_base_record[field], f"tangent base {field}")
    if not np.array_equal(base_record_tension, persisted_base_tension):
        raise ValueError("top-level and base-state total tensions differ")
    if not np.allclose(
        persisted_incremental,
        persisted_base_tension - fixed_reference_tension,
        rtol=2.0e-14,
        atol=2.0e-14,
    ):
        raise ValueError("incremental base tension does not use the fixed reference")
    expected_same_reference = (
        tangent_base_record["base_state_id"]
        == fixed_reference_record["reference_id"]
        and np.array_equal(base_cell, fixed_reference_cell)
        and np.array_equal(base_record_tension, fixed_reference_tension)
        and tangent_base_record["topology_id"]
        == fixed_reference_record["topology_id"]
        and tangent_base_record["branch_id"] == fixed_reference_record["branch_id"]
        and tangent_base_record["load_coordinate"]
        == fixed_reference_record["load_coordinate"]
    )
    if record["base_is_fixed_reference"] is not expected_same_reference:
        raise ValueError("base_is_fixed_reference flag is inconsistent")

    # Downstream stencil checks are deliberately relative to H_base/topology_base,
    # never the immutable fixed reference.
    reference_record = tangent_base_record
    reference_cell = base_cell

    derivative = record["derivative"]
    if not isinstance(derivative, Mapping):
        raise ValueError("derivative metadata must be an object")
    derivative_kind = derivative.get("kind")
    if derivative_kind == "central_smooth_branch":
        expected_derivative_fields = {
            "kind",
            "stencil",
            "base_topology_id",
            "base_branch_id",
            "sample_topology_ids",
            "sample_branch_ids",
            "smooth_fixed_topology_branch",
            "equilibrium_modulus_claim",
            "label",
        }
        if set(derivative) != expected_derivative_fields:
            raise ValueError("central derivative metadata has missing or unknown fields")
        if len(record["samples"]) != 7 or derivative.get(
            "smooth_fixed_topology_branch"
        ) is not True:
            raise ValueError("central smooth derivative needs seven same-branch samples")
    elif derivative_kind in (
        "forward_branch_changing_secant",
        "backward_branch_changing_secant",
    ):
        expected_derivative_fields = {
            "kind",
            "stencil",
            "side",
            "reason",
            "base_topology_id",
            "base_branch_id",
            "sample_topology_ids",
            "sample_branch_ids",
            "smooth_fixed_topology_branch",
            "equilibrium_modulus_claim",
            "label",
        }
        if set(derivative) != expected_derivative_fields:
            raise ValueError("secant metadata has missing or unknown fields")
        if len(record["samples"]) != 4 or derivative.get(
            "smooth_fixed_topology_branch"
        ) is not False:
            raise ValueError("branch-changing secant needs four labeled samples")
        if derivative.get("label") != "directional_secant_not_elastic_tangent_or_modulus":
            raise ValueError("branch-changing result must be labeled directional secant")
    else:
        raise ValueError("unsupported derivative kind")
    if derivative.get("equilibrium_modulus_claim") is not False:
        raise ValueError("raw derivative record must not make an equilibrium modulus claim")

    sample_fields = {
        "stencil_position",
        "component_index",
        "component_name",
        "step_size",
        "strain_increment",
        "total_tension_pN_per_nm",
        "cell_matrix_nm",
        "area_nm2",
        "topology_id",
        "branch_id",
        "minimization_performed",
        "minimization_converged",
        "max_force_pN",
        "state_evaluation",
        "profile_id",
        "profile_hash",
        "solver_version",
        "solver_closed",
    }
    if not isinstance(record["samples"], list):
        raise ValueError("samples must be an array")
    parsed_samples: list[dict[str, Any]] = []
    for sample in record["samples"]:
        if not isinstance(sample, Mapping) or set(sample) != sample_fields:
            raise ValueError("sample metadata is incomplete")
        increment = _finite_array(sample["strain_increment"], (3,), "sample increment")
        expected_cell = deformation_gradient(increment) @ reference_cell
        cell, area = _positive_area(sample["cell_matrix_nm"], "sample cell")
        if not np.allclose(cell, expected_cell, rtol=2.0e-14, atol=2.0e-14):
            raise ValueError("sample cell does not match H=F@H0")
        if not math.isclose(
            float(sample["area_nm2"]), area, rel_tol=2.0e-14, abs_tol=2.0e-14
        ):
            raise ValueError("sample area does not match its current cell")
        tension = _finite_array(
            sample["total_tension_pN_per_nm"], (3,), "sample tension"
        )
        if (
            sample["profile_id"] != identity["profile_id"]
            or sample["profile_hash"] != identity["canonical_hash"]
        ):
            raise ProfileMixingError("persisted sample profile identity is mixed")
        if (
            sample["minimization_performed"] is not True
            or sample["minimization_converged"] is not True
            or sample["max_force_pN"] is None
            or not math.isfinite(float(sample["max_force_pN"]))
            or float(sample["max_force_pN"]) < 0.0
        ):
            raise ValueError("persisted scientific tangent sample is not minimized/converged")
        _nonempty(sample["state_evaluation"], "sample state evaluation")
        if sample["solver_version"] is None:
            if sample["solver_closed"] is not None:
                raise ValueError("solver version/closure must both be null")
        else:
            if sample["solver_version"] != LAMMPS_REQUIRED_VERSION or sample[
                "solver_closed"
            ] is not True:
                raise ValueError("persisted solver version/closure is invalid")
        parsed_samples.append(
            {
                "record": sample,
                "increment": increment,
                "tension": tension,
            }
        )

    base = parsed_samples[0]
    base_record = base["record"]
    if (
        base_record["stencil_position"] != "base"
        or base_record["component_index"] is not None
        or base_record["component_name"] is not None
        or base_record["step_size"] is not None
        or not np.array_equal(base["increment"], np.zeros(3))
        or base_record["topology_id"] != reference_record["topology_id"]
        or base_record["branch_id"] != reference_record["branch_id"]
    ):
        raise ValueError("reference stencil sample metadata is inconsistent")
    if not np.array_equal(base["tension"], persisted_base_tension):
        raise ValueError("tangent base total tension does not match the zero sample")

    replayed = np.empty((3, 3), dtype=float)
    if derivative_kind == "central_smooth_branch":
        topology_ids: list[str] = []
        branch_ids: list[str] = []
        for component, step in enumerate(steps):
            minus = parsed_samples[1 + 2 * component]
            plus = parsed_samples[2 + 2 * component]
            expected_minus = np.zeros(3)
            expected_plus = np.zeros(3)
            expected_minus[component] = -step
            expected_plus[component] = step
            for parsed, position, expected_increment in (
                (minus, "minus", expected_minus),
                (plus, "plus", expected_plus),
            ):
                sample = parsed["record"]
                if (
                    sample["stencil_position"] != position
                    or sample["component_index"] != component
                    or sample["component_name"] != _STRAIN_ORDER[component]
                    or not math.isclose(
                        float(sample["step_size"]),
                        float(step),
                        rel_tol=0.0,
                        abs_tol=0.0,
                    )
                    or not np.array_equal(parsed["increment"], expected_increment)
                    or sample["topology_id"] != reference_record["topology_id"]
                    or sample["branch_id"] != reference_record["branch_id"]
                ):
                    raise ValueError(
                        "central stencil component/topology/branch metadata is inconsistent"
                    )
                topology_ids.append(sample["topology_id"])
                branch_ids.append(sample["branch_id"])
            replayed[:, component] = (
                plus["tension"] - minus["tension"]
            ) / (2.0 * step)
        if (
            derivative.get("base_topology_id")
            != reference_record["topology_id"]
            or derivative.get("base_branch_id") != reference_record["branch_id"]
            or derivative.get("sample_topology_ids") != topology_ids
            or derivative.get("sample_branch_ids") != branch_ids
            or derivative.get("stencil") != "three_point_central"
            or derivative.get("label") != "local_total_tension_derivative"
        ):
            raise ValueError("central derivative metadata does not match its samples")
    else:
        side = "forward" if derivative_kind.startswith("forward") else "backward"
        signed = 1.0 if side == "forward" else -1.0
        topology_ids = []
        branch_ids = []
        changed = False
        for component, step in enumerate(steps):
            parsed = parsed_samples[1 + component]
            sample = parsed["record"]
            expected_increment = np.zeros(3)
            expected_increment[component] = signed * step
            if (
                sample["stencil_position"] != side
                or sample["component_index"] != component
                or sample["component_name"] != _STRAIN_ORDER[component]
                or not math.isclose(
                    float(sample["step_size"]),
                    float(step),
                    rel_tol=0.0,
                    abs_tol=0.0,
                )
                or not np.array_equal(parsed["increment"], expected_increment)
            ):
                raise ValueError("branch-changing secant stencil metadata is inconsistent")
            topology_ids.append(sample["topology_id"])
            branch_ids.append(sample["branch_id"])
            changed = changed or (
                sample["topology_id"] != reference_record["topology_id"]
                or sample["branch_id"] != reference_record["branch_id"]
            )
            replayed[:, component] = (
                parsed["tension"] - base["tension"]
            ) / (signed * step)
        if (
            not changed
            or derivative.get("side") != side
            or not isinstance(derivative.get("reason"), str)
            or not derivative["reason"].strip()
            or derivative.get("base_topology_id")
            != reference_record["topology_id"]
            or derivative.get("base_branch_id") != reference_record["branch_id"]
            or derivative.get("sample_topology_ids") != topology_ids
            or derivative.get("sample_branch_ids") != branch_ids
            or derivative.get("stencil") != f"base_and_{side}_sample"
        ):
            raise ValueError("branch-changing secant metadata does not match its samples")
    if not np.allclose(replayed, matrix, rtol=2.0e-14, atol=2.0e-14):
        raise ValueError("raw matrix does not replay from persisted stencil observations")

    expected_asymmetry = _asymmetry_diagnostics(matrix)
    if record["asymmetry_diagnostics"] != expected_asymmetry:
        raise ValueError("asymmetry diagnostics do not match the raw matrix")
    solver_validation = record["solver_validation"]
    if solver_validation is not None:
        expected_solver_fields = {
            "backend",
            "solver_version",
            "instances_started",
            "instances_closed",
            "all_instances_closed",
            "fixed_topology",
            "minimization_performed",
            "physical_time_claim",
            "fixture_kind",
            "fixture_bond_count",
            "fixture_base_pair_positions_nm",
        }
        if not isinstance(solver_validation, Mapping) or set(
            solver_validation
        ) != expected_solver_fields:
            raise ValueError("solver validation metadata is incomplete")
        if (
            solver_validation["backend"] != "LAMMPS_serial_library"
            or solver_validation["solver_version"] != LAMMPS_REQUIRED_VERSION
            or solver_validation["instances_started"]
            != solver_validation["instances_closed"]
            or solver_validation["all_instances_closed"] is not True
            or solver_validation["fixed_topology"] is not True
            or solver_validation["minimization_performed"] is not True
            or solver_validation["physical_time_claim"] is not False
            or solver_validation["fixture_kind"] != "periodic_harmonic_ring"
            or not isinstance(solver_validation["fixture_bond_count"], int)
            or solver_validation["fixture_bond_count"] < 3
        ):
            raise ValueError("solver validation metadata is inconsistent")
        _finite_array(
            solver_validation["fixture_base_pair_positions_nm"],
            (2, 2),
            "solver fixture reference pair positions",
        )
        solver_samples = [
            sample
            for sample in record["samples"]
            if sample["solver_version"] is not None
        ]
        if (
            len(solver_samples) != solver_validation["instances_started"]
            or any(
                sample["solver_version"] != LAMMPS_REQUIRED_VERSION
                or sample["solver_closed"] is not True
                for sample in solver_samples
            )
        ):
            raise ValueError("solver summary does not match per-sample closure evidence")

    # JSON normalization rejects non-serializable values and aliases.
    try:
        return json.loads(json.dumps(record, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError(f"raw tangent record is not finite canonical JSON: {error}") from error


def _run_lammps_harmonic_observation(
    profile: PhysicsProfile,
    *,
    reference: TangentBaseState,
    base_pair_positions_nm: np.ndarray,
    increment: np.ndarray,
) -> TensionObservation:
    """Run one serial two-atom fixed-topology affine LAMMPS state."""

    deformation = deformation_gradient(increment)
    cell = deformation @ reference.cell_matrix_nm
    if abs(float(cell[1, 0])) > 1.0e-14:
        raise ValueError("LAMMPS tangent fixture requires a restricted upper-triangular cell")
    length_x = float(cell[0, 0])
    length_y = float(cell[1, 1])
    tilt_xy = float(cell[0, 1])
    if length_x <= 0.0 or length_y <= 0.0:
        raise ValueError("LAMMPS tangent fixture cell lengths must be positive")
    if abs(tilt_xy) >= 0.5 * length_x:
        raise ValueError("LAMMPS tangent fixture tilt must stay inside the restricted domain")
    base_pair = np.asarray(base_pair_positions_nm, dtype=float)
    if base_pair.shape != (2, 2) or not np.all(np.isfinite(base_pair)):
        raise ValueError("LAMMPS tangent fixture needs two finite base-state positions")
    primitive_displacement = base_pair[1] - base_pair[0]
    fractional_step = np.linalg.solve(
        reference.cell_matrix_nm, primitive_displacement
    )
    ring_count = None
    closure_vector = None
    for candidate in range(3, 33):
        candidate_closure = candidate * fractional_step
        rounded = np.rint(candidate_closure)
        if np.allclose(candidate_closure, rounded, rtol=0.0, atol=2.0e-13) and np.any(
            rounded != 0.0
        ):
            ring_count = candidate
            closure_vector = rounded
            break
    if ring_count is None or closure_vector is None:
        raise ValueError(
            "base pair displacement must close a periodic ring within 32 bonds"
        )
    if np.any(np.abs(fractional_step) >= 0.5):
        raise ValueError("periodic ring primitive step must be a unique minimum image")
    fractional_origin = np.array([0.037, -0.041])
    fractional_positions = np.array(
        [fractional_origin + index * fractional_step for index in range(ring_count)]
    )
    fractional_positions -= np.floor(fractional_positions + 0.5)
    positions = fractional_positions @ cell.T

    snapshot = profile.expanded_snapshot()
    if profile.identity != reference.profile_identity:
        raise ProfileMixingError("LAMMPS tangent profile does not match reference profile")
    mass = snapshot["mass"]["value_ag"]
    if mass is None or not math.isfinite(float(mass)) or float(mass) <= 0.0:
        raise ValueError("LAMMPS tangent fixture requires a recorded positive profile mass")
    parameters = snapshot["potentials"]["harmonic_bond"]["parameters"]

    # Center the restricted triclinic parallelogram about the origin.
    xlo = -0.5 * (length_x + tilt_xy)
    xhi = xlo + length_x
    ylo = -0.5 * length_y
    yhi = ylo + length_y
    solver = None
    solver_closed = False
    observed_tension: np.ndarray | None = None
    solver_version: int | None = None
    try:
        solver = lammps(cmdargs=["-log", "none", "-screen", "none"])
        solver_version = int(solver.version())
        if solver_version != LAMMPS_REQUIRED_VERSION:
            raise RuntimeError(
                f"expected LAMMPS {LAMMPS_REQUIRED_VERSION}, found {solver_version}"
            )
        solver.command("units nano")
        solver.command("dimension 2")
        solver.command("boundary p p p")
        solver.command("atom_style bond")
        solver.command(
            "region p01_tangent prism "
            f"{xlo:.17g} {xhi:.17g} {ylo:.17g} {yhi:.17g} -0.5 0.5 "
            f"{tilt_xy:.17g} 0.0 0.0 units box"
        )
        solver.command(
            "create_box 1 p01_tangent bond/types 1 extra/bond/per/atom 2"
        )
        solver.command(f"mass 1 {float(mass):.17g}")
        for x_value, y_value in positions:
            solver.command(
                f"create_atoms 1 single {x_value:.17g} {y_value:.17g} 0.0 units box"
            )
        for atom_id in range(1, ring_count):
            solver.command(f"create_bonds single/bond 1 {atom_id} {atom_id + 1}")
        solver.command(f"create_bonds single/bond 1 {ring_count} 1")
        solver.command("bond_style harmonic")
        solver.command(
            "bond_coeff 1 "
            f"{parameters['K_pN_per_nm']:.17g} {parameters['r0_nm']:.17g}"
        )
        solver.command("pair_style zero 1.0")
        solver.command("pair_coeff * *")
        solver.command("compute p01_tangent_pressure all pressure NULL virial")
        solver.command(
            "thermo_style custom step pe ebond fmax "
            "c_p01_tangent_pressure c_p01_tangent_pressure[1] "
            "c_p01_tangent_pressure[2] c_p01_tangent_pressure[4]"
        )
        solver.command("thermo_modify norm no")
        solver.command("min_style cg")
        solver.command("minimize 1.0e-14 1.0e-10 100 1000")
        solver.command("run 0")
        if int(solver.extract_global("nlocal")) != ring_count:
            raise RuntimeError(
                "serial LAMMPS tangent fixture must own every periodic-ring atom"
            )
        max_force = float(solver.get_thermo("fmax"))
        if not math.isfinite(max_force) or max_force > 1.0e-10:
            raise RuntimeError(
                "LAMMPS periodic-ring reference did not meet the force tolerance"
            )
        pressure_view = solver.extract_compute("p01_tangent_pressure", 0, 1)
        pressure = np.array(
            [float(pressure_view[0]), float(pressure_view[1]), float(pressure_view[3])]
        )
        observed_tension = -pressure
    finally:
        if solver is not None:
            solver.close()
            solver_closed = True

    if observed_tension is None or solver_version is None:
        raise RuntimeError("LAMMPS tangent fixture produced no observation")
    return TensionObservation.create(
        total_tension_pN_per_nm=observed_tension,
        cell_matrix_nm=cell,
        topology_id=reference.topology_id,
        branch_id=reference.branch_id,
        profile=profile,
        minimization_converged=True,
        minimization_performed=True,
        max_force_pN=max_force,
        state_evaluation="fixed_cell_minimized_periodic_harmonic_ring",
        solver_version=solver_version,
        solver_closed=solver_closed,
    )


def run_lammps_harmonic_bond_tangent(
    profile: PhysicsProfile,
    *,
    base_state: TangentBaseState,
    base_pair_positions_nm: Any,
    step_sizes: Any,
) -> TangentEstimate:
    """Central raw tangent for one bounded oblique affine harmonic fixture."""

    positions = _finite_array(base_pair_positions_nm, (2, 2), "base pair positions")
    primitive_displacement = positions[1] - positions[0]
    fractional_step = np.linalg.solve(base_state.cell_matrix_nm, primitive_displacement)
    ring_count = next(
        (
            candidate
            for candidate in range(3, 33)
            if np.allclose(
                candidate * fractional_step,
                np.rint(candidate * fractional_step),
                rtol=0.0,
                atol=2.0e-13,
            )
            and np.any(np.rint(candidate * fractional_step) != 0.0)
        ),
        None,
    )
    if ring_count is None:
        raise ValueError("base displacement does not define a bounded periodic ring")
    started = 0
    closed = 0
    versions: set[int] = set()

    def observe(increment: np.ndarray) -> TensionObservation:
        nonlocal started, closed
        started += 1
        observation = _run_lammps_harmonic_observation(
            profile,
            reference=base_state,
            base_pair_positions_nm=positions,
            increment=increment,
        )
        if observation.solver_closed is True:
            closed += 1
        if observation.solver_version is not None:
            versions.add(observation.solver_version)
        return observation

    result = central_difference_tangent(
        observe, base_state=base_state, step_sizes=step_sizes
    )
    if versions != {LAMMPS_REQUIRED_VERSION} or started != 7 or closed != started:
        raise RuntimeError("LAMMPS tangent stencil did not close every expected instance")
    return replace(
        result,
        solver_validation={
            "backend": "LAMMPS_serial_library",
            "solver_version": LAMMPS_REQUIRED_VERSION,
            "instances_started": started,
            "instances_closed": closed,
            "all_instances_closed": True,
            "fixed_topology": True,
            "minimization_performed": True,
            "physical_time_claim": False,
            "fixture_kind": "periodic_harmonic_ring",
            "fixture_bond_count": ring_count,
            "fixture_base_pair_positions_nm": positions.tolist(),
        },
    )

def lammps_PG_displacement(L : lammps, filepath_restart, dir):
    # Considering positive displacement only

    L.command(f"variable dir equal {dir}");

    ### Positive Displacement
    L.command("clear");
    L.command("box tilt large");
    L.command(f"read_restart {filepath_restart}");
    lammps_PG_potential_settings(L);
    lammps_PG_thermo_settings(L);

    # Now the file is loaded and configured, apply deformation
    L.commands_list(cmdlist=[
        # Determine reference length
        "if \"${dir} == 1\" then &",
        "\"variable len0 equal ${lx0}\"", 
        "if \"${dir} == 2\" then &",
        "\"variable len0 equal ${ly0}\"", 
        "if \"${dir} == 3\" then &",
        "\"variable len0 equal ${ly0}\"",

        # Deformation
        "variable delta equal ${up}*${len0}",
        "variable deltaxy equal ${up}*xy",

        "if \"${dir} == 1\" then &",
        "\"change_box all x delta 0 ${delta} xy delta ${deltaxy} remap units box\"",
        "if \"${dir} == 2\" then &",
        "\"change_box all y delta 0 ${delta} remap units box\"",
        "if \"${dir} == 3\" then &",
        "\"change_box all xy delta ${delta} remap units box\"",

        # Relax atoms positions
        "minimize ${etol} ${ftol} ${maxiter} ${maxeval}",
        "write_dump all image dump.post.positive.${dir}.jpg type type",

        # Obtain new stress tensor
        "variable tmp equal pxx",
        "variable pxx1 equal ${tmp}",
        "variable tmp equal pyy",
        "variable pyy1 equal ${tmp}",
        "variable tmp equal pxy",
        "variable pxy1 equal ${tmp}",

        # Compute elastic constant from pressure tensor
        "variable C1pos equal ${d1}",
        "variable C2pos equal ${d2}",
        "variable C3pos equal ${d3}",
    ])

    L.commands_list(cmdlist=[
        "variable C1${dir} equal ${C1pos}",
        "variable C2${dir} equal ${C2pos}",
        "variable C3${dir} equal ${C3pos}"
    ])

    # Delete dir to make sure it is not reused
    L.command("variable dir delete");

def _run_legacy_elastic_tensor_commands(
    L: lammps,
    *,
    filepath_restart: str,
    prestrain: str,
    coefficients_filepath: str,
) -> None:
    """Execute the inherited positive-difference compatibility route.

    This adapter retains the historical six-value, symmetrized file so old
    analysis scripts continue to load it.  It is not the P01-07 scientific raw
    tangent path; callers needing all nine entries and stencil provenance must
    use ``central_difference_tangent`` and ``write_raw_tangent_record``.
    """

    warnings.warn(
        "legacy .elastic_constants output is positive-difference and "
        "symmetrized; use the raw P01-07 tangent API for scientific output",
        DeprecationWarning,
        stacklevel=2,
    )
    lammps_PG_simulation_settings(L)
    L.command(
        "variable cfac equal "
        f"{u_2D_VIRIAL_PRESSURE_to_NEWTON_PER_METER * u_NEWTON_PER_METER_to_MEGAPASCAL_TIMES_NANOMETER}"
    )
    L.command("variable cunits string MPa*nm")
    L.command(f"variable prestrain equal {prestrain}")
    L.command("variable up equal 1E-3")

    L.command(f"variable etol equal {str(MODULI_ENERGY_TOLERANCE)}")
    L.command(f"variable ftol equal {str(MODULI_FORCE_TOLERANCE)}")
    L.command(f"variable maxiter equal {str(MODULI_MINIMIZATION_MAX_ITERATIONS)}")
    L.command(f"variable maxeval equal {str(MODULI_MINIMIZATION_MAX_EVALUATIONS)}")

    L.command(f"read_restart {filepath_restart}")
    L.command(f"variable print_filename string \"{coefficients_filepath}\"")
    lammps_PG_potential_settings(L)

    L.command("thermo 1")
    L.command("thermo_style custom step temp pe press pxx pyy pxy lx ly vol")
    L.command("thermo_modify norm no")
    L.command("minimize ${etol} ${ftol} ${maxiter} ${maxeval}")

    L.command("variable tmp equal pxx")
    L.command("variable pxx0 equal ${tmp}")
    L.command("variable tmp equal pyy")
    L.command("variable pyy0 equal ${tmp}")
    L.command("variable tmp equal pxy")
    L.command("variable pxy0 equal ${tmp}")

    L.command("variable tmp equal lx")
    L.command("variable lx0 equal ${tmp}")
    L.command("variable tmp equal ly")
    L.command("variable ly0 equal ${tmp}")
    L.command("variable tmp equal lz")
    L.command("variable lz0 equal ${tmp}")

    L.command("variable d1 equal -(v_pxx1-${pxx0})/(v_delta/v_len0)*${cfac}")
    L.command("variable d2 equal -(v_pyy1-${pyy0})/(v_delta/v_len0)*${cfac}")
    L.command("variable d3 equal -(v_pxy1-${pxy0})/(v_delta/v_len0)*${cfac}")

    lammps_PG_displacement(L, filepath_restart, 1)
    lammps_PG_displacement(L, filepath_restart, 2)
    lammps_PG_displacement(L, filepath_restart, 3)

    L.command("variable C11all equal ${C11}")
    L.command("variable C22all equal ${C22}")
    L.command("variable C33all equal ${C33}")
    L.command("variable C12all equal 0.5*(${C12}+${C21})")
    L.command("variable C13all equal 0.5*(${C13}+${C31})")
    L.command("variable C23all equal 0.5*(${C23}+${C32})")
    L.command(
        "print \"${prestrain} ${C11all} ${C22all} ${C33all} "
        "${C12all} ${C13all} ${C23all} ${cunits}\" file ${print_filename}"
    )


def lammps_calculate_elastic_tensor(
    filepath_restart: str, *, allow_legacy_forensic_output: bool = False
) -> bool:
    """Run the inherited forensic adapter only after explicit opt-in.

    Its positive-only/default-pressure/symmetrized record is retained solely
    for reproducing inherited files.  It is deliberately fail-closed by
    default and is not accepted as a P01-07 raw tangent artifact.
    """

    if allow_legacy_forensic_output is not True:
        raise RuntimeError(
            "legacy elastic output is disabled by default because it is "
            "positive-only, default-pressure, and symmetrized; pass "
            "allow_legacy_forensic_output=True only for labeled reproduction"
        )
    # Extract basis information about the restart from the filename:
    # https://regex101.com/
    re_prestrain = r".+_prestr(\d\.\d+)"
    prestrain = re.match(re_prestrain, filepath_restart);

    if not exists(filepath_restart):
        raise FileExistsError(f"File could not be found: {filepath_restart}");

    if prestrain == None:
        raise ValueError(f"Strain could not be found in filename: {filepath_restart}");
    else:
        prestrain = prestrain.group(1); # i.e. 0.1

    coefficients_filepath = splitext(filepath_restart)[0] + ".elastic_constants"
    L = lammps()
    try:
        _run_legacy_elastic_tensor_commands(
            L,
            filepath_restart=filepath_restart,
            prestrain=prestrain,
            coefficients_filepath=coefficients_filepath,
        )
        return True
    finally:
        L.close()
