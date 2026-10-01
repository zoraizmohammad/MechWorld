"""Independent analytical/finite-difference/LAMMPS mechanics regressions.

The fixtures use the immutable provisional profile only as a numerical source.
Agreement in this file is implementation evidence, not biological approval.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from pgworld.config.physics_profiles import (
    ProfileMixingError,
    load_physics_profile,
)
from pgworld.physics.energy_force_virial import (
    FixedCellTensionReference,
    PhysicsOracle,
    angle_resolution_energy,
    finite_difference_forces,
    pN_nm_to_joules,
    pN_per_nm_to_N_per_m,
    tension_from_configurational_virial_2d,
    validate_result_cohort,
)
from pgworld.physics.lammps_oracle import (
    LAMMPS_REQUIRED_VERSION,
    run_lammps_angle_fixture,
    run_lammps_bond_fixture,
    run_lammps_two_bond_series_fixture,
)
from lammps_PG_objects import Atom, minimum_image_displacement_2d


PROFILE = load_physics_profile("reviewed_physics_provisional_v0")
PROFILE_IDS = (
    "legacy_python_2026_03_12_v1",
    "legacy_direct_isotropic_pre_unit_fix_v1",
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1",
    "reviewed_physics_provisional_v0",
)


def _oracle() -> PhysicsOracle:
    return PhysicsOracle(PROFILE)


def _bond_positions(distance: float, axis: int = 0) -> np.ndarray:
    positions = np.zeros((2, 2), dtype=float)
    positions[0, axis] = -distance / 2.0
    positions[1, axis] = distance / 2.0
    return positions


def _relative_error(observed: np.ndarray, expected: np.ndarray) -> float:
    scale = max(float(np.max(np.abs(expected))), 1.0e-8)
    return float(np.max(np.abs(observed - expected))) / scale


def test_native_2d_unit_conversions_are_explicit_and_fail_closed() -> None:
    assert pN_per_nm_to_N_per_m(1.0) == pytest.approx(1.0e-3, rel=0, abs=1e-15)
    assert pN_nm_to_joules(1.0) == pytest.approx(1.0e-21, rel=0, abs=1e-33)
    with pytest.raises(ValueError, match="finite"):
        pN_per_nm_to_N_per_m(math.inf)
    with pytest.raises(ValueError, match="finite"):
        pN_nm_to_joules(math.nan)


@pytest.mark.parametrize("distance", [0.83, 1.03, 1.23])
def test_single_harmonic_edge_matches_derivative_fd_virial_and_lammps(
    distance: float,
) -> None:
    oracle = _oracle()
    positions = _bond_positions(distance)
    result = oracle.harmonic_bond(positions)
    K, r0 = oracle.harmonic_bond_parameters
    displacement = distance - r0
    expected_energy = K * displacement**2
    expected_derivative = 2.0 * K * displacement

    assert result.energy_pN_nm == pytest.approx(expected_energy, rel=1e-13, abs=1e-12)
    assert result.radial_derivative_pN == pytest.approx(
        expected_derivative, rel=1e-13, abs=1e-12
    )
    assert result.forces_pN[0, 0] == pytest.approx(
        expected_derivative, rel=1e-13, abs=1e-12
    )
    assert result.virial_pN_nm[0, 0] == pytest.approx(
        -distance * expected_derivative, rel=1e-13, abs=1e-12
    )

    fd = finite_difference_forces(
        lambda coords: oracle.harmonic_bond(coords).energy_pN_nm,
        positions,
        step_nm=1.0e-6,
    )
    assert _relative_error(fd, result.forces_pN) < 2.0e-9

    lammps = run_lammps_bond_fixture(
        PROFILE, style="harmonic", positions_nm=positions, box_lengths_nm=(12.0, 10.0)
    )
    assert lammps.solver_version == LAMMPS_REQUIRED_VERSION == 20260902
    assert lammps.solver_closed is True
    assert lammps.physics_profile == PROFILE.expanded_snapshot()
    assert lammps.as_record()["physics_profile"]["canonical_hash"] == PROFILE.canonical_hash
    assert lammps.energy_pN_nm == pytest.approx(result.energy_pN_nm, rel=1e-12, abs=1e-10)
    assert np.allclose(lammps.forces_pN, result.forces_pN, rtol=1e-12, atol=1e-9)
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        result.virial_pN_nm,
        rtol=1e-12,
        atol=1e-9,
    )


def test_two_straight_edges_in_series_have_mechanical_not_molecular_result() -> None:
    oracle = _oracle()
    K, r0 = oracle.harmonic_bond_parameters
    total_rest = 2.0 * r0
    extension = 0.04
    positions = np.array(
        [[-0.5 * (total_rest + extension), 0.0], [0.0, 0.0], [0.5 * (total_rest + extension), 0.0]]
    )
    left = oracle.harmonic_bond(positions[[0, 1]])
    right = oracle.harmonic_bond(positions[[1, 2]])
    total_energy = left.energy_pN_nm + right.energy_pN_nm
    end_force = abs(left.forces_pN[0, 0])

    assert total_rest == pytest.approx(2.06, rel=0, abs=1e-15)
    assert total_energy == pytest.approx(0.5 * K * extension**2, rel=1e-13)
    assert end_force == pytest.approx(K * extension, rel=1e-13)
    assert oracle.two_edge_series_tangent_pN_per_nm == pytest.approx(5570.0)
    assert left.forces_pN[1, 0] + right.forces_pN[0, 0] == pytest.approx(0.0, abs=1e-12)
    assert oracle.two_edge_series_status == "mechanical_derivation_not_molecular_mapping"

    lammps = run_lammps_two_bond_series_fixture(
        PROFILE, positions_nm=positions, box_lengths_nm=(12.0, 10.0)
    )
    expected_forces = np.vstack(
        (left.forces_pN[0], left.forces_pN[1] + right.forces_pN[0], right.forces_pN[1])
    )
    assert lammps.energy_pN_nm == pytest.approx(total_energy, rel=1e-12, abs=1e-10)
    assert np.allclose(lammps.forces_pN, expected_forces, rtol=1e-12, atol=1e-9)
    assert lammps.forces_pN[1, 0] == pytest.approx(0.0, abs=1e-10)
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        left.virial_pN_nm + right.virial_pN_nm,
        rtol=1e-12,
        atol=1e-9,
    )


@pytest.mark.parametrize("fraction", [-0.04, 0.0, 0.12, 0.90])
def test_nonlinear_edge_matches_analytic_fd_and_lammps_across_valid_domain(
    fraction: float,
) -> None:
    oracle = _oracle()
    epsilon, r0, lambd = oracle.nonlinear_bond_parameters
    distance = r0 + fraction * lambd
    positions = _bond_positions(distance)
    result = oracle.nonlinear_bond(positions)
    delta = distance - r0
    denominator = lambd**2 - delta**2
    expected_energy = epsilon * delta**2 / denominator
    expected_derivative = 2.0 * epsilon * delta * lambd**2 / denominator**2
    assert result.energy_pN_nm == pytest.approx(expected_energy, rel=2e-13, abs=1e-11)
    assert result.radial_derivative_pN == pytest.approx(
        expected_derivative, rel=2e-13, abs=1e-10
    )

    step = 2.0e-7 if abs(fraction) < 0.5 else 2.0e-8
    fd = finite_difference_forces(
        lambda coords: oracle.nonlinear_bond(coords).energy_pN_nm,
        positions,
        step_nm=step,
    )
    assert _relative_error(fd, result.forces_pN) < 2.0e-6

    lammps = run_lammps_bond_fixture(
        PROFILE, style="nonlinear", positions_nm=positions, box_lengths_nm=(14.0, 10.0)
    )
    assert lammps.solver_closed is True
    assert lammps.energy_pN_nm == pytest.approx(result.energy_pN_nm, rel=2e-11, abs=2e-9)
    assert np.allclose(lammps.forces_pN, result.forces_pN, rtol=2e-10, atol=2e-7)
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        result.virial_pN_nm,
        rtol=2e-10,
        atol=2e-7,
    )


def test_nonlinear_valid_domain_and_all_invalid_inputs_are_rejected() -> None:
    oracle = _oracle()
    _epsilon, r0, lambd = oracle.nonlinear_bond_parameters
    assert oracle.nonlinear_valid_radial_domain_nm == pytest.approx(
        (max(0.0, r0 - lambd), r0 + lambd)
    )
    for distance in (0.0, r0 + lambd, r0 + lambd + 1.0e-8):
        with pytest.raises(ValueError, match="nonlinear|length"):
            oracle.nonlinear_bond(_bond_positions(distance))
    with pytest.raises(ValueError, match="finite"):
        oracle.nonlinear_bond(np.array([[0.0, 0.0], [math.nan, 0.0]]))
    with pytest.raises(ValueError, match="positive length"):
        oracle.harmonic_bond(np.zeros((2, 2)))


def test_noncollinear_angle_matches_cartesian_fd_lammps_and_balances() -> None:
    oracle = _oracle()
    positions = np.array([[-1.1, 0.2], [0.1, -0.1], [0.75, 1.05]])
    result = oracle.harmonic_angle(positions)
    fd = finite_difference_forces(
        lambda coords: oracle.harmonic_angle(coords).energy_pN_nm,
        positions,
        step_nm=2.0e-6,
    )
    assert _relative_error(fd, result.forces_pN) < 3.0e-8
    assert np.linalg.norm(result.forces_pN.sum(axis=0)) < 2.0e-12
    torque_z = np.sum(
        positions[:, 0] * result.forces_pN[:, 1]
        - positions[:, 1] * result.forces_pN[:, 0]
    )
    assert abs(torque_z) < 2.0e-12

    lammps = run_lammps_angle_fixture(
        PROFILE, positions_nm=positions, box_lengths_nm=(12.0, 10.0)
    )
    assert lammps.solver_closed is True
    assert lammps.energy_pN_nm == pytest.approx(result.energy_pN_nm, rel=1e-12, abs=1e-10)
    assert np.allclose(lammps.forces_pN, result.forces_pN, rtol=2e-11, atol=2e-9)
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        result.virial_pN_nm,
        rtol=2e-11,
        atol=2e-9,
    )


def test_angle_degeneracy_and_resolution_sensitivity_are_explicit() -> None:
    oracle = _oracle()
    near_collinear_sine = 5.0e-4
    invalid = (
        np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 1.0]]),
        np.array([[-1.0, 0.0], [0.0, 0.0], [1.0, 0.0]]),
        np.array([[1.0, 0.0], [0.0, 0.0], [2.0, 0.0]]),
        np.array(
            [
                [-1.0, 0.0],
                [0.0, 0.0],
                [math.sqrt(1.0 - near_collinear_sine**2), near_collinear_sine],
            ]
        ),
    )
    for positions in invalid:
        with pytest.raises(ValueError, match="angle"):
            oracle.harmonic_angle(positions)
    with pytest.raises(ValueError, match=r"sin\(theta\)<=0.001"):
        run_lammps_angle_fixture(PROFILE, positions_nm=invalid[-1])
    K, _theta0 = oracle.harmonic_angle_parameters
    one_angle = angle_resolution_energy(K, total_turn_radians=0.4, angle_count=1)
    two_angles = angle_resolution_energy(K, total_turn_radians=0.4, angle_count=2)
    assert two_angles == pytest.approx(0.5 * one_angle)
    assert oracle.angle_resolution_status == "unreviewed_no_rescaling_selected"


@pytest.mark.parametrize("axis", [0, 1])
def test_bond_virial_sign_orientation_and_virtual_cell_work(axis: int) -> None:
    oracle = _oracle()
    positions = _bond_positions(1.18, axis=axis)
    result = oracle.harmonic_bond(positions)
    other = 1 - axis
    assert result.virial_pN_nm[axis, axis] < 0.0
    assert result.virial_pN_nm[other, other] == pytest.approx(0.0, abs=1e-14)

    strain_step = 2.0e-7
    plus = positions.copy()
    minus = positions.copy()
    plus[:, axis] *= 1.0 + strain_step
    minus[:, axis] *= 1.0 - strain_step
    denergy_dstrain = (
        oracle.harmonic_bond(plus).energy_pN_nm
        - oracle.harmonic_bond(minus).energy_pN_nm
    ) / (2.0 * strain_step)
    assert denergy_dstrain == pytest.approx(
        -result.virial_pN_nm[axis, axis], rel=2e-9, abs=2e-8
    )

    lammps = run_lammps_bond_fixture(
        PROFILE, style="harmonic", positions_nm=positions, box_lengths_nm=(12.0, 10.0)
    )
    assert lammps.configurational_pressure_pN_per_nm[axis, axis] == pytest.approx(
        result.virial_pN_nm[axis, axis] / 120.0, rel=1e-12, abs=1e-10
    )


def test_oblique_shear_work_translation_invariance_and_xy_lammps_virial() -> None:
    oracle = _oracle()
    positions = np.array([[-0.45, -0.3], [0.55, 0.4]])
    result = oracle.harmonic_bond(positions)
    translated = oracle.harmonic_bond(positions + np.array([1.0e4, -2.0e4]))
    assert np.allclose(translated.forces_pN, result.forces_pN, rtol=0, atol=5e-9)
    assert np.allclose(
        translated.virial_pN_nm, result.virial_pN_nm, rtol=0, atol=8e-9
    )

    shear_step = 2.0e-7
    plus = positions.copy()
    minus = positions.copy()
    plus[:, 0] += shear_step * positions[:, 1]
    minus[:, 0] -= shear_step * positions[:, 1]
    denergy_dshear = (
        oracle.harmonic_bond(plus).energy_pN_nm
        - oracle.harmonic_bond(minus).energy_pN_nm
    ) / (2.0 * shear_step)
    assert denergy_dshear == pytest.approx(
        -result.virial_pN_nm[1, 0], rel=3e-9, abs=3e-8
    )

    lammps = run_lammps_bond_fixture(
        PROFILE, style="harmonic", positions_nm=positions, box_lengths_nm=(12.0, 10.0)
    )
    assert lammps.configurational_virial_pN_nm[0, 1] == pytest.approx(
        result.virial_pN_nm[0, 1], rel=2e-12, abs=2e-9
    )
    assert lammps.configurational_virial_pN_nm[1, 0] == pytest.approx(
        result.virial_pN_nm[1, 0], rel=2e-12, abs=2e-9
    )


def test_periodic_crossing_uses_accepted_minimum_image_and_matches_lammps() -> None:
    wrapped = np.array([[4.6, 0.0], [-4.5, 0.3]])
    first = Atom(1, 1, 1, wrapped[0, 0], wrapped[0, 1], 0.0)
    second = Atom(2, 1, 1, wrapped[1, 0], wrapped[1, 1], 0.0)
    displacement, image_offset = minimum_image_displacement_2d(
        first, second, (-5.0, 5.0, 0.0, -4.0, 4.0)
    )
    assert tuple(image_offset) == (1, 0)
    assert np.allclose(displacement, [0.9, 0.3], rtol=0, atol=1e-14)

    # The analytical oracle receives an explicit local interaction vector.  The
    # accepted helper reconstructs that vector from wrapped coordinates; the
    # persistent per-edge image identity remains P03-01 scope.
    local_positions = np.vstack((np.zeros(2), displacement))
    analytical = _oracle().harmonic_bond(local_positions)
    lammps = run_lammps_bond_fixture(
        PROFILE,
        style="harmonic",
        positions_nm=wrapped,
        box_lengths_nm=(10.0, 8.0),
    )
    assert lammps.energy_pN_nm == pytest.approx(
        analytical.energy_pN_nm, rel=1e-12, abs=1e-10
    )
    assert np.allclose(
        lammps.forces_pN, analytical.forces_pN, rtol=2e-12, atol=2e-9
    )
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        analytical.virial_pN_nm,
        rtol=2e-12,
        atol=2e-9,
    )


def test_2d_tension_normalization_z_invariance_and_kinetic_exclusion() -> None:
    positions = _bond_positions(1.18)
    zero_velocity = run_lammps_bond_fixture(
        PROFILE,
        style="harmonic",
        positions_nm=positions,
        box_lengths_nm=(12.0, 10.0),
        z_width_nm=1.0,
    )
    wide_z = run_lammps_bond_fixture(
        PROFILE,
        style="harmonic",
        positions_nm=positions,
        box_lengths_nm=(12.0, 10.0),
        z_width_nm=7.0,
    )
    moving = run_lammps_bond_fixture(
        PROFILE,
        style="harmonic",
        positions_nm=positions,
        box_lengths_nm=(12.0, 10.0),
        z_width_nm=3.0,
        velocities_nm_per_ns=np.array([[1.0, 0.0], [1.0, 0.0]]),
    )
    assert np.allclose(
        zero_velocity.configurational_pressure_pN_per_nm,
        wide_z.configurational_pressure_pN_per_nm,
        rtol=0,
        atol=1e-13,
    )
    assert np.allclose(
        moving.configurational_pressure_pN_per_nm,
        zero_velocity.configurational_pressure_pN_per_nm,
        rtol=0,
        atol=1e-14,
    )
    assert moving.default_pressure_pN_per_nm[0, 0] > moving.configurational_pressure_pN_per_nm[0, 0]
    profile_mass = PROFILE.expanded_snapshot()["mass"]["value_ag"]
    expected_kinetic_xx = 2.0 * profile_mass / 120.0
    assert moving.default_pressure_pN_per_nm[0, 0] - moving.configurational_pressure_pN_per_nm[
        0, 0
    ] == pytest.approx(expected_kinetic_xx, rel=2e-12, abs=2e-15)
    assert moving.fixture_mass_ag == profile_mass
    assert moving.fixture_mass_source == "physics_profile"
    moving_record = moving.as_record()
    assert moving_record["positions_nm"] == positions.tolist()
    assert moving_record["box_lengths_nm"] == [12.0, 10.0]
    assert moving_record["velocities_nm_per_ns"] == [[1.0, 0.0], [1.0, 0.0]]
    assert moving_record["fixture_mass_ag"] == profile_mass
    assert moving_record["physical_time_claim"] is False
    json.dumps(moving_record, allow_nan=False)
    tension = tension_from_configurational_virial_2d(
        zero_velocity.configurational_virial_pN_nm, area_nm2=120.0
    )
    assert np.allclose(tension, -zero_velocity.configurational_pressure_pN_per_nm)


def test_fixed_cell_reference_keeps_total_primary_and_never_resets() -> None:
    initial_virial = np.array([[-15.0, -2.0], [-2.0, 4.0]])
    initial = tension_from_configurational_virial_2d(
        initial_virial, area_nm2=100.0
    )
    tracker = FixedCellTensionReference(PROFILE, initial)
    first_total = tension_from_configurational_virial_2d(
        np.array([[-24.0, -3.6], [-3.6, 1.2]]), area_nm2=120.0
    )
    later_total = tension_from_configurational_virial_2d(
        np.array([[-14.3, 2.6], [2.6, -9.1]]), area_nm2=130.0
    )
    first = tracker.observe(first_total, load_coordinate=0.1)
    later = tracker.observe(later_total, load_coordinate=0.2)
    assert first.primary_name == "total_configurational_tension_2d"
    assert first.secondary_name == "incremental_from_fixed_reference"
    assert np.array_equal(first.reference_total_pN_per_nm, initial)
    assert np.array_equal(later.reference_total_pN_per_nm, initial)
    assert np.allclose(first.incremental_pN_per_nm, first.total_pN_per_nm - initial)
    assert np.allclose(later.incremental_pN_per_nm, later.total_pN_per_nm - initial)
    assert not hasattr(tracker, "reset")


def test_outputs_embed_validated_snapshot_and_silent_profile_mixing_fails() -> None:
    provisional_result = _oracle().harmonic_bond(_bond_positions(1.1))
    snapshot = provisional_result.physics_profile
    assert snapshot == PROFILE.expanded_snapshot()
    assert snapshot["canonical_hash"] == PROFILE.canonical_hash
    assert provisional_result.as_record()["physics_profile"] == snapshot
    assert provisional_result.as_record()["positions_nm"] == _bond_positions(1.1).tolist()
    detached_record = provisional_result.as_record()
    json.dumps(detached_record, allow_nan=False)
    detached_record["positions_nm"][0][0] = 999.0
    assert provisional_result.positions_nm[0, 0] != 999.0
    identity = validate_result_cohort([provisional_result, provisional_result])
    assert identity == PROFILE.identity

    legacy = PhysicsOracle(load_physics_profile("legacy_python_2026_03_12_v1"))
    legacy_result = legacy.harmonic_bond(_bond_positions(1.1))
    with pytest.raises(ProfileMixingError, match="mixed"):
        validate_result_cohort([provisional_result, legacy_result])


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_every_registered_profile_drives_oracle_and_real_lammps_with_identity(
    profile_id: str,
) -> None:
    profile = load_physics_profile(profile_id)
    oracle = PhysicsOracle(profile)
    _epsilon, r0, lambd = oracle.nonlinear_bond_parameters
    distance = r0 + 0.10 * lambd
    positions = _bond_positions(distance)
    analytical = oracle.nonlinear_bond(positions)
    profile_mass = profile.expanded_snapshot()["mass"]["value_ag"]
    fixture_mass_override = 1.0 if profile_mass is None else None
    lammps = run_lammps_bond_fixture(
        profile,
        style="nonlinear",
        positions_nm=positions,
        box_lengths_nm=(14.0, 10.0),
        fixture_mass_ag=fixture_mass_override,
    )
    assert analytical.physics_profile == profile.expanded_snapshot()
    assert lammps.physics_profile == profile.expanded_snapshot()
    assert lammps.physics_profile["profile_id"] == profile_id
    assert lammps.physics_profile["canonical_hash"] == profile.canonical_hash
    assert np.array_equal(lammps.positions_nm, positions)
    assert np.array_equal(lammps.velocities_nm_per_ns, np.zeros_like(positions))
    assert np.array_equal(lammps.box_lengths_nm, [14.0, 10.0])
    if profile_mass is None:
        assert lammps.fixture_mass_ag == 1.0
        assert lammps.fixture_mass_source == "explicit_synthetic_override"
        with pytest.raises(ValueError, match="explicit positive fixture_mass_ag"):
            run_lammps_bond_fixture(
                profile,
                style="nonlinear",
                positions_nm=positions,
                box_lengths_nm=(14.0, 10.0),
            )
    else:
        assert lammps.fixture_mass_ag == profile_mass
        assert lammps.fixture_mass_source == "physics_profile"
    assert lammps.energy_pN_nm == pytest.approx(
        analytical.energy_pN_nm, rel=2e-12, abs=2e-10
    )
    assert np.allclose(
        lammps.forces_pN, analytical.forces_pN, rtol=2e-12, atol=2e-9
    )
    assert np.allclose(
        lammps.configurational_virial_pN_nm,
        analytical.virial_pN_nm,
        rtol=2e-12,
        atol=2e-9,
    )
