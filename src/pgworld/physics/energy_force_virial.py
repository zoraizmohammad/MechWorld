"""Analytical and finite-difference oracles for native 2D PG mechanics.

Conventions
-----------
For a bond displacement ``d = x_j - x_i`` and radial derivative
``T = dU/dr``, the forces are ``F_i = T d/r`` and ``F_j = -F_i``.  The
configurational virial is

``W = sum_i x_i outer F_i = -(T/r) d outer d``.

LAMMPS ``compute pressure NULL virial`` returns ``P_conf = W/A`` in a
two-dimensional simulation.  This project reports tensile membrane resultants
as ``N = -P_conf = -W/A``: an extended spring therefore has negative pressure
and positive tension.  Kinetic pressure is deliberately excluded.

All inputs and outputs use ``nm``, ``pN``, ``pN nm``, and ``pN/nm``.  These
oracles validate implementation consistency under an immutable physics profile;
they are not a biological parameter certification.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Callable, Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pgworld.config.physics_profiles import (
    PhysicsProfile,
    validate_expanded_profile_snapshot,
    validate_profile_aggregation,
)


FloatArray = NDArray[np.float64]
_LENGTH_FLOOR_NM = 1.0e-14
# patch_2Sep2026 angle_harmonic clamps sin(theta) to 0.001 in the force
# denominator.  Reject that regime so this exact analytical oracle is never
# presented as a comparison to a deliberately clamped solver derivative.
_ANGLE_SINE_FLOOR = 1.0e-3


def _finite_scalar(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite real number")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _positive_scalar(value: float, name: str) -> float:
    converted = _finite_scalar(value, name)
    if converted <= 0.0:
        raise ValueError(f"{name} must be positive")
    return converted


def _positions(value: ArrayLike, expected_atoms: int, name: str) -> FloatArray:
    array = np.asarray(value, dtype=float)
    if array.shape != (expected_atoms, 2):
        raise ValueError(f"{name} must have shape ({expected_atoms}, 2)")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite coordinates")
    return np.array(array, dtype=float, copy=True)


def _readonly_array(value: ArrayLike, shape: tuple[int, ...], name: str) -> FloatArray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite array with shape {shape}")
    detached = np.array(array, dtype=float, copy=True)
    detached.setflags(write=False)
    return detached


def _validated_profile_json(profile: PhysicsProfile) -> str:
    if not isinstance(profile, PhysicsProfile):
        raise TypeError("profile must be a validated PhysicsProfile")
    validated = validate_expanded_profile_snapshot(profile.expanded_snapshot())
    return json.dumps(
        validated.expanded_snapshot(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def pN_per_nm_to_N_per_m(value: float) -> float:
    """Convert native membrane tension or in-plane stiffness to SI N/m."""

    return _finite_scalar(value, "pN/nm value") * 1.0e-3


def pN_nm_to_joules(value: float) -> float:
    """Convert native energy to joules."""

    return _finite_scalar(value, "pN nm value") * 1.0e-21


@dataclass(frozen=True)
class InteractionResult:
    """One analytical interaction result with complete profile provenance."""

    energy_pN_nm: float
    positions_nm: FloatArray
    forces_pN: FloatArray
    virial_pN_nm: FloatArray
    radial_derivative_pN: float | None
    interaction: str
    _physics_profile_json: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "energy_pN_nm", _finite_scalar(self.energy_pN_nm, "energy")
        )
        object.__setattr__(
            self,
            "positions_nm",
            _readonly_array(
                self.positions_nm,
                tuple(np.asarray(self.positions_nm).shape),
                "positions",
            ),
        )
        if self.positions_nm.ndim != 2 or self.positions_nm.shape[1] != 2:
            raise ValueError("positions must have shape (atom_count, 2)")
        object.__setattr__(
            self,
            "forces_pN",
            _readonly_array(
                self.forces_pN,
                tuple(np.asarray(self.forces_pN).shape),
                "forces",
            ),
        )
        if self.forces_pN.ndim != 2 or self.forces_pN.shape[1] != 2:
            raise ValueError("forces must have shape (atom_count, 2)")
        if self.forces_pN.shape != self.positions_nm.shape:
            raise ValueError("positions and forces must have matching shapes")
        object.__setattr__(
            self,
            "virial_pN_nm",
            _readonly_array(self.virial_pN_nm, (2, 2), "virial"),
        )
        if self.radial_derivative_pN is not None:
            object.__setattr__(
                self,
                "radial_derivative_pN",
                _finite_scalar(self.radial_derivative_pN, "radial derivative"),
            )
        if not isinstance(self.interaction, str) or not self.interaction:
            raise ValueError("interaction must be a nonempty string")
        snapshot = json.loads(self._physics_profile_json)
        validated = validate_expanded_profile_snapshot(snapshot)
        object.__setattr__(
            self, "_physics_profile_json", _validated_profile_json(validated)
        )

    @property
    def physics_profile(self) -> dict[str, Any]:
        """Return a detached complete validated profile snapshot."""

        return json.loads(self._physics_profile_json)

    def as_record(self) -> dict[str, Any]:
        """Return strict-JSON-ready values and complete profile provenance."""

        return {
            "interaction": self.interaction,
            "energy_pN_nm": self.energy_pN_nm,
            "positions_nm": self.positions_nm.tolist(),
            "forces_pN": self.forces_pN.tolist(),
            "configurational_virial_pN_nm": self.virial_pN_nm.tolist(),
            "radial_derivative_pN": self.radial_derivative_pN,
            "physics_profile": self.physics_profile,
        }


class PhysicsOracle:
    """Analytical mechanics evaluated from one immutable validated profile."""

    def __init__(self, profile: PhysicsProfile):
        self._profile_json = _validated_profile_json(profile)
        snapshot = json.loads(self._profile_json)
        potentials = snapshot["potentials"]
        harmonic = potentials["harmonic_bond"]["parameters"]
        nonlinear = potentials["nonlinear_bond"]["parameters"]
        angle = potentials["harmonic_angle"]["parameters"]
        self._harmonic = (
            float(harmonic["K_pN_per_nm"]),
            float(harmonic["r0_nm"]),
        )
        self._nonlinear = (
            float(nonlinear["epsilon_pN_nm"]),
            float(nonlinear["r0_nm"]),
            float(nonlinear["lambda_nm"]),
        )
        self._angle = (
            float(angle["K_pN_nm"]),
            math.radians(float(angle["theta0_degrees"])),
        )
        self._derived = snapshot["derived_numerical_facts"]
        self._angle_resolution = snapshot["angle_resolution_status"]

    @property
    def physics_profile(self) -> dict[str, Any]:
        return json.loads(self._profile_json)

    @property
    def harmonic_bond_parameters(self) -> tuple[float, float]:
        return self._harmonic

    @property
    def nonlinear_bond_parameters(self) -> tuple[float, float, float]:
        return self._nonlinear

    @property
    def harmonic_angle_parameters(self) -> tuple[float, float]:
        """Return ``(K pN nm, theta0 radians)``."""

        return self._angle

    @property
    def nonlinear_valid_radial_domain_nm(self) -> tuple[float, float]:
        """Open radial domain; zero length is independently invalid."""

        _epsilon, r0, lambd = self._nonlinear
        return max(0.0, r0 - lambd), r0 + lambd

    @property
    def two_edge_series_tangent_pN_per_nm(self) -> float:
        return float(self._derived["two_edge_series_tangent_pN_per_nm"])

    @property
    def two_edge_series_status(self) -> str:
        return "mechanical_derivation_not_molecular_mapping"

    @property
    def angle_resolution_status(self) -> str:
        if self._angle_resolution != "unreviewed":
            raise ValueError("profile angle-resolution status is not the expected pending state")
        return "unreviewed_no_rescaling_selected"

    def _bond_result(
        self,
        positions_nm: ArrayLike,
        *,
        energy_pN_nm: float,
        radial_derivative_pN: float,
        interaction: str,
    ) -> InteractionResult:
        positions = _positions(positions_nm, 2, "bond positions")
        displacement = positions[1] - positions[0]
        length = float(np.linalg.norm(displacement))
        if not math.isfinite(length) or length <= _LENGTH_FLOOR_NM:
            raise ValueError("bond must have a finite positive length")
        direction = displacement / length
        force_i = radial_derivative_pN * direction
        forces = np.vstack((force_i, -force_i))
        virial = -np.outer(displacement, force_i)
        return InteractionResult(
            energy_pN_nm=energy_pN_nm,
            positions_nm=positions,
            forces_pN=forces,
            virial_pN_nm=virial,
            radial_derivative_pN=radial_derivative_pN,
            interaction=interaction,
            _physics_profile_json=self._profile_json,
        )

    def harmonic_bond(self, positions_nm: ArrayLike) -> InteractionResult:
        positions = _positions(positions_nm, 2, "bond positions")
        distance = float(np.linalg.norm(positions[1] - positions[0]))
        if distance <= _LENGTH_FLOOR_NM:
            raise ValueError("harmonic bond must have a finite positive length")
        K, r0 = self._harmonic
        delta = distance - r0
        return self._bond_result(
            positions,
            energy_pN_nm=K * delta**2,
            radial_derivative_pN=2.0 * K * delta,
            interaction="harmonic_bond",
        )

    def nonlinear_bond(self, positions_nm: ArrayLike) -> InteractionResult:
        positions = _positions(positions_nm, 2, "bond positions")
        distance = float(np.linalg.norm(positions[1] - positions[0]))
        if distance <= _LENGTH_FLOOR_NM:
            raise ValueError("nonlinear bond must have a finite positive length")
        epsilon, r0, lambd = self._nonlinear
        delta = distance - r0
        if abs(delta) >= lambd:
            lower, upper = self.nonlinear_valid_radial_domain_nm
            raise ValueError(
                "nonlinear bond lies at or outside its open radial domain "
                f"({lower}, {upper}) nm"
            )
        denominator = lambd**2 - delta**2
        energy = epsilon * delta**2 / denominator
        derivative = 2.0 * epsilon * delta * lambd**2 / denominator**2
        return self._bond_result(
            positions,
            energy_pN_nm=energy,
            radial_derivative_pN=derivative,
            interaction="nonlinear_bond",
        )

    def harmonic_angle(self, positions_nm: ArrayLike) -> InteractionResult:
        positions = _positions(positions_nm, 3, "angle positions")
        arm_a = positions[0] - positions[1]
        arm_b = positions[2] - positions[1]
        length_a = float(np.linalg.norm(arm_a))
        length_b = float(np.linalg.norm(arm_b))
        if length_a <= _LENGTH_FLOOR_NM or length_b <= _LENGTH_FLOOR_NM:
            raise ValueError("angle legs must have finite positive length")
        unit_a = arm_a / length_a
        unit_b = arm_b / length_b
        cosine = float(np.clip(np.dot(unit_a, unit_b), -1.0, 1.0))
        theta = math.acos(cosine)
        sine = math.sin(theta)
        if sine <= _ANGLE_SINE_FLOOR:
            raise ValueError(
                "angle is collinear or inside the LAMMPS sin(theta)<=0.001 "
                "force-clamp regime"
            )

        K, theta0 = self._angle
        delta = theta - theta0
        angular_derivative = 2.0 * K * delta
        force_first = (
            angular_derivative
            * (unit_b - cosine * unit_a)
            / (length_a * sine)
        )
        force_third = (
            angular_derivative
            * (unit_a - cosine * unit_b)
            / (length_b * sine)
        )
        force_center = -force_first - force_third
        forces = np.vstack((force_first, force_center, force_third))
        # Translation-independent local expression with the center as origin.
        virial = np.outer(arm_a, force_first) + np.outer(arm_b, force_third)
        return InteractionResult(
            energy_pN_nm=K * delta**2,
            positions_nm=positions,
            forces_pN=forces,
            virial_pN_nm=virial,
            radial_derivative_pN=None,
            interaction="harmonic_angle",
            _physics_profile_json=self._profile_json,
        )


def finite_difference_forces(
    energy_function: Callable[[FloatArray], float],
    positions_nm: ArrayLike,
    *,
    step_nm: float,
) -> FloatArray:
    """Return ``-grad(U)`` from independent centered Cartesian differences."""

    positions = np.asarray(positions_nm, dtype=float)
    if positions.ndim != 2 or positions.shape[1] != 2:
        raise ValueError("finite-difference positions must have shape (atom_count, 2)")
    if not np.all(np.isfinite(positions)):
        raise ValueError("finite-difference positions must be finite")
    step = _positive_scalar(step_nm, "finite-difference step")
    forces = np.empty_like(positions, dtype=float)
    for atom in range(positions.shape[0]):
        for component in range(2):
            plus = np.array(positions, dtype=float, copy=True)
            minus = np.array(positions, dtype=float, copy=True)
            plus[atom, component] += step
            minus[atom, component] -= step
            energy_plus = _finite_scalar(energy_function(plus), "perturbed energy")
            energy_minus = _finite_scalar(energy_function(minus), "perturbed energy")
            forces[atom, component] = -(energy_plus - energy_minus) / (2.0 * step)
    return forces


def angle_resolution_energy(
    K_pN_nm: float, *, total_turn_radians: float, angle_count: int
) -> float:
    """Energy for equal sharing of a fixed turn, without approving a rescaling."""

    K = _finite_scalar(K_pN_nm, "angle coefficient")
    if K < 0.0:
        raise ValueError("angle coefficient must be nonnegative")
    turn = _finite_scalar(total_turn_radians, "total turn")
    if isinstance(angle_count, bool) or not isinstance(angle_count, int) or angle_count < 1:
        raise ValueError("angle_count must be a positive integer")
    return angle_count * K * (turn / angle_count) ** 2


def tension_from_configurational_virial_2d(
    virial_pN_nm: ArrayLike, *, area_nm2: float
) -> FloatArray:
    """Return membrane tension ``N=-W/A`` in pN/nm from a 2D virial."""

    virial = _readonly_array(virial_pN_nm, (2, 2), "configurational virial")
    area = _positive_scalar(area_nm2, "2D cell area")
    return np.array(-virial / area, dtype=float, copy=True)


@dataclass(frozen=True)
class TensionObservation:
    """Total-primary and incremental-secondary tension at one load coordinate."""

    total_pN_per_nm: FloatArray
    incremental_pN_per_nm: FloatArray
    reference_total_pN_per_nm: FloatArray
    load_coordinate: float
    _physics_profile_json: str
    primary_name: str = "total_configurational_tension_2d"
    secondary_name: str = "incremental_from_fixed_reference"

    def __post_init__(self) -> None:
        for field_name in (
            "total_pN_per_nm",
            "incremental_pN_per_nm",
            "reference_total_pN_per_nm",
        ):
            object.__setattr__(
                self,
                field_name,
                _readonly_array(getattr(self, field_name), (2, 2), field_name),
            )
        object.__setattr__(
            self,
            "load_coordinate",
            _finite_scalar(self.load_coordinate, "load coordinate"),
        )
        validated = validate_expanded_profile_snapshot(
            json.loads(self._physics_profile_json)
        )
        object.__setattr__(
            self, "_physics_profile_json", _validated_profile_json(validated)
        )

    @property
    def physics_profile(self) -> dict[str, Any]:
        return json.loads(self._physics_profile_json)


class FixedCellTensionReference:
    """A reference that can be observed but has no API for resetting strain zero."""

    def __init__(self, profile: PhysicsProfile, initial_total_pN_per_nm: ArrayLike):
        self._profile_json = _validated_profile_json(profile)
        self._reference = _readonly_array(
            initial_total_pN_per_nm, (2, 2), "initial total tension"
        )

    @property
    def reference_total_pN_per_nm(self) -> FloatArray:
        return np.array(self._reference, dtype=float, copy=True)

    def observe(
        self, total_pN_per_nm: ArrayLike, *, load_coordinate: float
    ) -> TensionObservation:
        total = _readonly_array(total_pN_per_nm, (2, 2), "total tension")
        return TensionObservation(
            total_pN_per_nm=total,
            incremental_pN_per_nm=total - self._reference,
            reference_total_pN_per_nm=self._reference,
            load_coordinate=load_coordinate,
            _physics_profile_json=self._profile_json,
        )


def validate_result_cohort(results: Iterable[InteractionResult]) -> dict[str, str]:
    """Fail closed on forged provenance or silent cross-profile aggregation."""

    snapshots: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        if not isinstance(result, InteractionResult):
            raise TypeError(f"result {index} is not an InteractionResult")
        snapshots.append(result.physics_profile)
    validated = validate_profile_aggregation(snapshots)
    profile_id, canonical_hash = next(iter(validated.items()))
    return {"profile_id": profile_id, "canonical_hash": canonical_hash}
