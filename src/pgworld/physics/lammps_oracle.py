"""Bounded real-LAMMPS fixtures for independent mechanics comparisons.

The functions create tiny serial, two-dimensional systems under LAMMPS
2 Sep 2026, copy all solver-owned arrays before closing the instance, and embed
the complete validated physics-profile snapshot in their result.  They never
run minimization or dynamics and do not establish biological parameter validity.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pgworld.config.physics_profiles import (
    PhysicsProfile,
    validate_expanded_profile_snapshot,
)


FloatArray = NDArray[np.float64]
LAMMPS_REQUIRED_VERSION = 20260902


def _profile_json(profile: PhysicsProfile) -> str:
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


def _finite_positions(value: ArrayLike, atom_count: int) -> FloatArray:
    positions = np.asarray(value, dtype=float)
    if positions.shape != (atom_count, 2) or not np.all(np.isfinite(positions)):
        raise ValueError(f"positions must be finite with shape ({atom_count}, 2)")
    return np.array(positions, dtype=float, copy=True)


def _positive_pair(value: tuple[float, float], name: str) -> tuple[float, float]:
    converted = tuple(float(component) for component in value)
    if len(converted) != 2 or not all(math.isfinite(item) and item > 0 for item in converted):
        raise ValueError(f"{name} must contain two finite positive values")
    return converted[0], converted[1]


def _orthogonal_minimum_image_displacement(
    first_nm: FloatArray,
    second_nm: FloatArray,
    box_lengths_nm: tuple[float, float],
) -> FloatArray:
    """Return the local first-to-second vector for an orthogonal periodic box."""

    box = np.asarray(box_lengths_nm, dtype=float)
    displacement = np.asarray(second_nm, dtype=float) - np.asarray(
        first_nm, dtype=float
    )
    return displacement - box * np.floor(displacement / box + 0.5)


def _tensor_from_lammps_vector(values: list[float]) -> FloatArray:
    # LAMMPS order is xx, yy, zz, xy, xz, yz.  Only native x/y components
    # belong in this 2D result.
    return np.array(
        [[values[0], values[3]], [values[3], values[1]]], dtype=float
    )


def _readonly(value: ArrayLike, shape: tuple[int, ...], name: str) -> FloatArray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with shape {shape}")
    copied = np.array(array, dtype=float, copy=True)
    copied.setflags(write=False)
    return copied


@dataclass(frozen=True)
class LammpsFixtureResult:
    """Copied solver observations with explicit 2D pressure/virial semantics."""

    interaction: str
    energy_pN_nm: float
    positions_nm: FloatArray
    box_lengths_nm: FloatArray
    velocities_nm_per_ns: FloatArray
    forces_pN: FloatArray
    configurational_pressure_pN_per_nm: FloatArray
    configurational_virial_pN_nm: FloatArray
    default_pressure_pN_per_nm: FloatArray
    area_nm2: float
    z_width_nm: float
    fixture_mass_ag: float
    fixture_mass_source: str
    velocities_present: bool
    solver_version: int
    solver_closed: bool
    _physics_profile_json: str

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.energy_pN_nm)):
            raise ValueError("LAMMPS energy must be finite")
        if not math.isfinite(float(self.fixture_mass_ag)) or self.fixture_mass_ag <= 0:
            raise ValueError("LAMMPS fixture mass must be finite and positive")
        if self.fixture_mass_source not in (
            "physics_profile",
            "explicit_synthetic_override",
        ):
            raise ValueError("unsupported LAMMPS fixture mass provenance")
        atom_count = np.asarray(self.forces_pN).shape[0]
        object.__setattr__(
            self,
            "positions_nm",
            _readonly(self.positions_nm, (atom_count, 2), "positions"),
        )
        object.__setattr__(
            self,
            "box_lengths_nm",
            _readonly(self.box_lengths_nm, (2,), "box lengths"),
        )
        object.__setattr__(
            self,
            "velocities_nm_per_ns",
            _readonly(
                self.velocities_nm_per_ns,
                (atom_count, 2),
                "velocities",
            ),
        )
        object.__setattr__(
            self, "forces_pN", _readonly(self.forces_pN, (atom_count, 2), "forces")
        )
        for field_name in (
            "configurational_pressure_pN_per_nm",
            "configurational_virial_pN_nm",
            "default_pressure_pN_per_nm",
        ):
            object.__setattr__(
                self,
                field_name,
                _readonly(getattr(self, field_name), (2, 2), field_name),
            )
        if self.solver_version != LAMMPS_REQUIRED_VERSION:
            raise RuntimeError(
                f"expected LAMMPS {LAMMPS_REQUIRED_VERSION}, found {self.solver_version}"
            )
        if self.solver_closed is not True:
            raise RuntimeError("LAMMPS fixture result requires a confirmed closed solver")
        if not math.isclose(
            float(np.prod(self.box_lengths_nm)),
            float(self.area_nm2),
            rel_tol=1.0e-14,
            abs_tol=1.0e-14,
        ):
            raise ValueError("fixture area must equal the recorded xy box area")
        validated = validate_expanded_profile_snapshot(
            json.loads(self._physics_profile_json)
        )
        object.__setattr__(self, "_physics_profile_json", _profile_json(validated))

    @property
    def physics_profile(self) -> dict[str, Any]:
        return json.loads(self._physics_profile_json)

    def as_record(self) -> dict[str, Any]:
        return {
            "interaction": self.interaction,
            "energy_pN_nm": float(self.energy_pN_nm),
            "positions_nm": self.positions_nm.tolist(),
            "box_lengths_nm": self.box_lengths_nm.tolist(),
            "velocities_nm_per_ns": self.velocities_nm_per_ns.tolist(),
            "forces_pN": self.forces_pN.tolist(),
            "configurational_pressure_pN_per_nm": (
                self.configurational_pressure_pN_per_nm.tolist()
            ),
            "configurational_virial_pN_nm": (
                self.configurational_virial_pN_nm.tolist()
            ),
            "default_pressure_pN_per_nm": self.default_pressure_pN_per_nm.tolist(),
            "area_nm2": float(self.area_nm2),
            "z_width_nm": float(self.z_width_nm),
            "fixture_mass_ag": float(self.fixture_mass_ag),
            "fixture_mass_source": self.fixture_mass_source,
            "velocities_present": self.velocities_present,
            "physical_time_claim": False,
            "solver_version": self.solver_version,
            "solver_closed": self.solver_closed,
            "physics_profile": self.physics_profile,
        }


def _run_fixture(
    profile: PhysicsProfile,
    *,
    interaction: Literal[
        "harmonic_bond",
        "nonlinear_bond",
        "two_harmonic_bonds",
        "harmonic_angle",
    ],
    positions_nm: FloatArray,
    box_lengths_nm: tuple[float, float],
    z_width_nm: float,
    velocities_nm_per_ns: ArrayLike | None,
    fixture_mass_ag: float | None,
) -> LammpsFixtureResult:
    profile_snapshot_json = _profile_json(profile)
    snapshot = json.loads(profile_snapshot_json)
    length_x, length_y = _positive_pair(box_lengths_nm, "box lengths")
    z_width = float(z_width_nm)
    if not math.isfinite(z_width) or z_width <= 0.0:
        raise ValueError("z width must be finite and positive")
    if np.any(np.abs(positions_nm[:, 0]) >= length_x / 2.0) or np.any(
        np.abs(positions_nm[:, 1]) >= length_y / 2.0
    ):
        raise ValueError("all fixture atoms must lie strictly inside the 2D box")

    is_angle = interaction == "harmonic_angle"
    is_series = interaction == "two_harmonic_bonds"
    if not is_angle:
        bond_pairs = ((0, 1), (1, 2)) if is_series else ((0, 1),)
        minimum_image_lengths: list[float] = []
        for first_index, second_index in bond_pairs:
            displacement = _orthogonal_minimum_image_displacement(
                positions_nm[first_index],
                positions_nm[second_index],
                (length_x, length_y),
            )
            distance = float(np.linalg.norm(displacement))
            if not math.isfinite(distance) or distance <= 1.0e-14:
                raise ValueError(
                    "LAMMPS bond fixture requires a finite positive "
                    "minimum-image length"
                )
            minimum_image_lengths.append(distance)
        if interaction == "nonlinear_bond":
            parameters = snapshot["potentials"]["nonlinear_bond"]["parameters"]
            delta = minimum_image_lengths[0] - float(parameters["r0_nm"])
            lambd = float(parameters["lambda_nm"])
            if abs(delta) >= lambd:
                raise ValueError(
                    "nonlinear LAMMPS fixture minimum-image length must be "
                    "strictly inside |r-r0| < lambda"
                )

    velocities: FloatArray | None = None
    if velocities_nm_per_ns is not None:
        velocities = np.asarray(velocities_nm_per_ns, dtype=float)
        if velocities.shape != positions_nm.shape or not np.all(np.isfinite(velocities)):
            raise ValueError("velocities must be finite and match the position shape")
        velocities = np.array(velocities, dtype=float, copy=True)

    profile_mass = snapshot["mass"]["value_ag"]
    if fixture_mass_ag is not None:
        fixture_mass = float(fixture_mass_ag)
        if not math.isfinite(fixture_mass) or fixture_mass <= 0.0:
            raise ValueError("explicit fixture mass must be finite and positive")
        fixture_mass_source = "explicit_synthetic_override"
    elif profile_mass is None:
        raise ValueError(
            "this profile has no recovered mass; pass an explicit positive "
            "fixture_mass_ag for a synthetic static solver fixture"
        )
    else:
        fixture_mass = float(profile_mass)
        if not math.isfinite(fixture_mass) or fixture_mass <= 0.0:
            raise ValueError("profile mass must be finite and positive")
        fixture_mass_source = "physics_profile"

    atom_count = positions_nm.shape[0]
    solver = None
    closed = False
    observed: dict[str, Any] = {}
    try:
        from lammps import lammps

        solver = lammps(cmdargs=["-log", "none", "-screen", "none"])
        solver_version = int(solver.version())
        if solver_version != LAMMPS_REQUIRED_VERSION:
            raise RuntimeError(
                f"expected LAMMPS {LAMMPS_REQUIRED_VERSION}, found {solver_version}"
            )

        atom_style = "angle" if is_angle else "bond"
        solver.command("units nano")
        solver.command("dimension 2")
        solver.command("boundary p p p")
        solver.command(f"atom_style {atom_style}")
        solver.command(
            "region p01_box block "
            f"{-length_x / 2.0:.17g} {length_x / 2.0:.17g} "
            f"{-length_y / 2.0:.17g} {length_y / 2.0:.17g} "
            f"{-z_width / 2.0:.17g} {z_width / 2.0:.17g} units box"
        )
        if is_angle:
            solver.command(
                "create_box 1 p01_box bond/types 1 angle/types 1 "
                "extra/bond/per/atom 2 extra/angle/per/atom 1 "
                "extra/special/per/atom 4"
            )
        else:
            extra_bonds = 2 if is_series else 1
            solver.command(
                "create_box 1 p01_box bond/types 1 "
                f"extra/bond/per/atom {extra_bonds}"
            )
        solver.command(f"mass 1 {fixture_mass:.17g}")
        for x, y in positions_nm:
            solver.command(f"create_atoms 1 single {x:.17g} {y:.17g} 0.0 units box")

        if is_angle:
            solver.command("create_bonds single/bond 1 1 2")
            solver.command("create_bonds single/bond 1 2 3")
            solver.command("create_bonds single/angle 1 1 2 3")
            solver.command("bond_style zero")
            solver.command("bond_coeff 1")
            parameters = snapshot["potentials"]["harmonic_angle"]["parameters"]
            solver.command("angle_style harmonic")
            solver.command(
                "angle_coeff 1 "
                f"{parameters['K_pN_nm']:.17g} "
                f"{parameters['theta0_degrees']:.17g}"
            )
        elif is_series:
            solver.command("create_bonds single/bond 1 1 2")
            solver.command("create_bonds single/bond 1 2 3")
            parameters = snapshot["potentials"]["harmonic_bond"]["parameters"]
            solver.command("bond_style harmonic")
            solver.command(
                "bond_coeff 1 "
                f"{parameters['K_pN_per_nm']:.17g} "
                f"{parameters['r0_nm']:.17g}"
            )
        else:
            solver.command("create_bonds single/bond 1 1 2")
            if interaction == "harmonic_bond":
                parameters = snapshot["potentials"]["harmonic_bond"]["parameters"]
                solver.command("bond_style harmonic")
                solver.command(
                    "bond_coeff 1 "
                    f"{parameters['K_pN_per_nm']:.17g} "
                    f"{parameters['r0_nm']:.17g}"
                )
            else:
                parameters = snapshot["potentials"]["nonlinear_bond"]["parameters"]
                solver.command("bond_style nonlinear")
                solver.command(
                    "bond_coeff 1 "
                    f"{parameters['epsilon_pN_nm']:.17g} "
                    f"{parameters['r0_nm']:.17g} "
                    f"{parameters['lambda_nm']:.17g}"
                )

        solver.command("pair_style zero 1.0")
        solver.command("pair_coeff * *")
        if velocities is not None:
            for atom_id, (velocity_x, velocity_y) in enumerate(velocities, start=1):
                group_id = f"p01_velocity_{atom_id}"
                solver.command(f"group {group_id} id {atom_id}")
                solver.command(
                    f"velocity {group_id} set {velocity_x:.17g} "
                    f"{velocity_y:.17g} 0.0 sum yes units box"
                )
        solver.command("compute p01_config all pressure NULL virial")
        solver.command("compute p01_default all pressure thermo_temp")
        solver.command(
            "thermo_style custom step pe ebond eangle "
            "c_p01_config c_p01_config[1] c_p01_config[2] c_p01_config[4] "
            "c_p01_default c_p01_default[1] c_p01_default[2] c_p01_default[4]"
        )
        solver.command("thermo_modify norm no")
        solver.command("run 0")

        nlocal = int(solver.extract_global("nlocal"))
        if nlocal != atom_count:
            raise RuntimeError(
                "serial LAMMPS fixture must own exactly all expected atoms; "
                f"expected {atom_count}, found nlocal={nlocal}"
            )
        force_view = solver.numpy.extract_atom("f")
        atom_id_view = solver.numpy.extract_atom("id")
        local_ids = np.array(atom_id_view[:nlocal], dtype=np.int64, copy=True)
        local_forces = np.array(
            force_view[:nlocal, :2], dtype=float, copy=True
        )
        expected_ids = np.arange(1, atom_count + 1, dtype=np.int64)
        if set(local_ids.tolist()) != set(expected_ids.tolist()):
            raise RuntimeError(
                "LAMMPS fixture did not retain exactly the expected atom IDs"
            )
        # LAMMPS may spatially reorder local atoms even in serial.  Output is
        # explicitly mapped back to persistent atom-ID order before closing.
        order = np.argsort(local_ids)
        forces = local_forces[order]
        config_vector_view = solver.extract_compute("p01_config", 0, 1)
        default_vector_view = solver.extract_compute("p01_default", 0, 1)
        config_vector = [float(config_vector_view[index]) for index in range(6)]
        default_vector = [float(default_vector_view[index]) for index in range(6)]
        config_pressure = _tensor_from_lammps_vector(config_vector)
        default_pressure = _tensor_from_lammps_vector(default_vector)
        area = length_x * length_y
        energy_key = "eangle" if is_angle else "ebond"
        observed = {
            "interaction": interaction,
            "energy_pN_nm": float(solver.get_thermo(energy_key)),
            "positions_nm": positions_nm,
            "box_lengths_nm": np.array([length_x, length_y]),
            "velocities_nm_per_ns": (
                np.zeros_like(positions_nm) if velocities is None else velocities
            ),
            "forces_pN": forces,
            "configurational_pressure_pN_per_nm": config_pressure,
            "configurational_virial_pN_nm": config_pressure * area,
            "default_pressure_pN_per_nm": default_pressure,
            "area_nm2": area,
            "z_width_nm": z_width,
            "fixture_mass_ag": fixture_mass,
            "fixture_mass_source": fixture_mass_source,
            "velocities_present": velocities is not None,
            "solver_version": solver_version,
        }
    finally:
        if solver is not None:
            solver.close()
            closed = True

    return LammpsFixtureResult(
        **observed,
        solver_closed=closed,
        _physics_profile_json=profile_snapshot_json,
    )


def run_lammps_bond_fixture(
    profile: PhysicsProfile,
    *,
    style: Literal["harmonic", "nonlinear"],
    positions_nm: ArrayLike,
    box_lengths_nm: tuple[float, float] = (10.0, 10.0),
    z_width_nm: float = 1.0,
    velocities_nm_per_ns: ArrayLike | None = None,
    fixture_mass_ag: float | None = None,
) -> LammpsFixtureResult:
    """Evaluate one valid bond and both configurational/default pressures."""

    if style not in ("harmonic", "nonlinear"):
        raise ValueError("bond style must be 'harmonic' or 'nonlinear'")
    positions = _finite_positions(positions_nm, 2)
    return _run_fixture(
        profile,
        interaction=f"{style}_bond",  # type: ignore[arg-type]
        positions_nm=positions,
        box_lengths_nm=box_lengths_nm,
        z_width_nm=z_width_nm,
        velocities_nm_per_ns=velocities_nm_per_ns,
        fixture_mass_ag=fixture_mass_ag,
    )


def run_lammps_angle_fixture(
    profile: PhysicsProfile,
    *,
    positions_nm: ArrayLike,
    box_lengths_nm: tuple[float, float] = (10.0, 10.0),
    z_width_nm: float = 1.0,
    fixture_mass_ag: float | None = None,
) -> LammpsFixtureResult:
    """Evaluate one nondegenerate harmonic angle with zero-energy bonds."""

    positions = _finite_positions(positions_nm, 3)
    arm_a = positions[0] - positions[1]
    arm_b = positions[2] - positions[1]
    norm_product = float(np.linalg.norm(arm_a) * np.linalg.norm(arm_b))
    if norm_product <= 1.0e-14:
        raise ValueError("angle legs must have positive length")
    cosine = float(np.clip(np.dot(arm_a, arm_b) / norm_product, -1.0, 1.0))
    if math.sqrt(max(0.0, 1.0 - cosine**2)) <= 1.0e-3:
        raise ValueError(
            "LAMMPS angle fixture rejects the sin(theta)<=0.001 force-clamp regime"
        )
    return _run_fixture(
        profile,
        interaction="harmonic_angle",
        positions_nm=positions,
        box_lengths_nm=box_lengths_nm,
        z_width_nm=z_width_nm,
        velocities_nm_per_ns=None,
        fixture_mass_ag=fixture_mass_ag,
    )


def run_lammps_two_bond_series_fixture(
    profile: PhysicsProfile,
    *,
    positions_nm: ArrayLike,
    box_lengths_nm: tuple[float, float] = (10.0, 10.0),
    z_width_nm: float = 1.0,
    fixture_mass_ag: float | None = None,
) -> LammpsFixtureResult:
    """Evaluate a three-atom harmonic series with no angle interaction."""

    positions = _finite_positions(positions_nm, 3)
    first_length = float(np.linalg.norm(positions[1] - positions[0]))
    second_length = float(np.linalg.norm(positions[2] - positions[1]))
    if min(first_length, second_length) <= 1.0e-14:
        raise ValueError("both series bonds must have positive length")
    return _run_fixture(
        profile,
        interaction="two_harmonic_bonds",
        positions_nm=positions,
        box_lengths_nm=box_lengths_nm,
        z_width_nm=z_width_nm,
        velocities_nm_per_ns=None,
        fixture_mass_ag=fixture_mass_ag,
    )
