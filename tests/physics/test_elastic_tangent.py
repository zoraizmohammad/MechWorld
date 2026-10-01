"""Regression tests for the local 2D tangent contract.

The numerical profile is provisional and is used only to verify encoded
equations and solver conventions.  Nothing here certifies biological values.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import run_lammps_elastic_tensor as elastic
from pgworld.config.physics_profiles import (
    ProfileMixingError,
    load_physics_profile,
)
from process_elastic_tensor import read_raw_tangent_record, write_raw_tangent_record


PROFILE = load_physics_profile("reviewed_physics_provisional_v0")


def _base_state(
    base_total_tension: np.ndarray | None = None,
) -> elastic.TangentBaseState:
    base_total = (
        np.array([0.8, -0.3, 0.17])
        if base_total_tension is None
        else np.asarray(base_total_tension, dtype=float)
    )
    fixed_total = np.array([0.25, -0.1, 0.04])
    return elastic.TangentBaseState.create(
        profile=PROFILE,
        base_state_id="fixture-tangent-base-v1",
        cell_matrix_nm=np.array([[8.0, 0.0], [0.0, 7.0]]),
        base_total_tension_pN_per_nm=base_total,
        topology_id="topology-intact-v1",
        branch_id="smooth-minimum-a",
        load_coordinate=0.125,
        minimization_converged=True,
        fixed_reference_id="fixture-fixed-reference-v1",
        fixed_reference_cell_matrix_nm=np.array([[7.5, 0.0], [0.0, 6.8]]),
        fixed_reference_total_tension_pN_per_nm=fixed_total,
        fixed_reference_topology_id="topology-intact-v1",
        fixed_reference_branch_id="initial-minimum",
        fixed_reference_load_coordinate=0.0,
        fixed_reference_minimization_converged=True,
    )


def _observation(
    values: np.ndarray,
    *,
    increment: np.ndarray | None = None,
    topology_id: str = "topology-intact-v1",
    branch_id: str = "smooth-minimum-a",
    profile=PROFILE,
) -> elastic.TensionObservation:
    q = np.zeros(3) if increment is None else np.asarray(increment, dtype=float)
    cell = elastic.deformation_gradient(q) @ np.array([[8.0, 0.0], [0.0, 7.0]])
    return elastic.TensionObservation.create(
        total_tension_pN_per_nm=values,
        cell_matrix_nm=cell,
        topology_id=topology_id,
        branch_id=branch_id,
        profile=profile,
        minimization_converged=True,
    )


def _coupled_constitutive_fixture():
    reference_total = np.array([0.8, -0.3, 0.17])
    raw_tangent = np.array(
        [
            [11.0, 2.0, -3.0],
            [4.0, 13.0, 5.0],
            [6.0, -7.0, 17.0],
        ]
    )
    cubic = np.array(
        [
            [0.7, -0.2, 0.4],
            [0.3, 0.9, -0.5],
            [-0.8, 0.6, 1.1],
        ]
    )

    def observe(increment: np.ndarray) -> elastic.TensionObservation:
        values = reference_total + raw_tangent @ increment + cubic @ increment**3
        return _observation(values, increment=increment)

    return observe, reference_total, raw_tangent


def test_convention_is_explicit_native_2d_and_serializable() -> None:
    record = elastic.local_2d_tangent_convention().as_record()
    assert record == {
        "axes": {"x": "axial", "y": "hoop"},
        "incremental_deformation_gradient": (
            "F_inc=[[1+epsilon_xx,gamma_xy],[0,1+epsilon_yy]]"
        ),
        "incremental_cell_update": "H(q)=F_inc(q)@H_base",
        "trial_coordinate_update": "x_trial=F_inc(q)@x_base",
        "sample_coordinate_update": (
            "x_sample=relax(x_trial,H(q),same_topology_and_branch)"
        ),
        "strain_vector_order": ["epsilon_xx", "epsilon_yy", "gamma_xy"],
        "shear_definition": "engineering_simple_shear_gamma_xy_equals_F_xy",
        "tension_vector_order": ["N_xx", "N_yy", "N_xy"],
        "tension_unit": "pN/nm",
        "tension_source": "configurational_virial_only_N_equals_minus_W_over_current_area",
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
    json.dumps(record, allow_nan=False)


def test_central_tangent_converges_second_order_and_preserves_all_couplings() -> None:
    observe, reference_total, exact = _coupled_constitutive_fixture()
    steps = (1.0e-2, 5.0e-3, 2.5e-3)
    results = [
        elastic.central_difference_tangent(
            observe,
            base_state=_base_state(reference_total),
            step_sizes=np.full(3, step),
        )
        for step in steps
    ]
    errors = [np.linalg.norm(item.raw_matrix_pN_per_nm) - 0.0 for item in results]
    actual_errors = [np.linalg.norm(item.raw_matrix_pN_per_nm - exact) for item in results]
    assert errors[0] > 0.0
    assert actual_errors[1] / actual_errors[0] == pytest.approx(0.25, rel=2.0e-7)
    assert actual_errors[2] / actual_errors[1] == pytest.approx(0.25, rel=8.0e-7)
    finest = results[-1]
    np.testing.assert_allclose(finest.base_total_tension_pN_per_nm, reference_total)
    assert finest.raw_matrix_pN_per_nm[0, 1] != finest.raw_matrix_pN_per_nm[1, 0]
    assert finest.raw_matrix_pN_per_nm[0, 2] != 0.0
    assert finest.raw_matrix_pN_per_nm[2, 0] != 0.0
    assert finest.derivative_metadata["kind"] == "central_smooth_branch"
    assert finest.derivative_metadata["equilibrium_modulus_claim"] is False
    diagnostics = finest.asymmetry_diagnostics
    assert diagnostics["C12_minus_C21_pN_per_nm"] == pytest.approx(-2.0, abs=2e-4)
    assert diagnostics["max_abs_matrix_minus_transpose_pN_per_nm"] > 0.0
    assert len(finest.sample_records) == 7
    assert {sample["stencil_position"] for sample in finest.sample_records} == {
        "base",
        "minus",
        "plus",
    }


def test_fixed_reference_is_not_reset_and_total_tension_remains_primary() -> None:
    observe, reference_total, _exact = _coupled_constitutive_fixture()
    result = elastic.central_difference_tangent(
        observe,
        base_state=_base_state(reference_total),
        step_sizes=np.full(3, 1.0e-3),
    )
    record = result.as_record()
    assert record["fixed_reference"]["reference_id"] == "fixture-fixed-reference-v1"
    assert record["fixed_reference"]["load_coordinate"] == pytest.approx(0.0)
    assert record["tangent_base_state"]["base_state_id"] == "fixture-tangent-base-v1"
    assert record["tangent_base_state"]["load_coordinate"] == pytest.approx(0.125)
    assert record["base_is_fixed_reference"] is False
    np.testing.assert_allclose(record["base_total_tension_pN_per_nm"], reference_total)
    np.testing.assert_allclose(
        record["incremental_base_tension_from_fixed_reference_pN_per_nm"],
        reference_total - np.array([0.25, -0.1, 0.04]),
    )
    assert record["convention"]["primary_quantity"].startswith("total_")
    assert record["convention"]["secondary_quantity"] == "incremental_from_fixed_reference"


def test_central_difference_rejects_branch_changes_profile_mixing_and_bad_values() -> None:
    reference = _base_state(np.array([1.0, 2.0, 3.0]))

    def changed_branch(increment: np.ndarray) -> elastic.TensionObservation:
        branch = "smooth-minimum-a" if np.all(increment == 0.0) else "other-minimum"
        return _observation(
            np.array([1.0, 2.0, 3.0]), increment=increment, branch_id=branch
        )

    with pytest.raises(ValueError, match="central smooth branch"):
        elastic.central_difference_tangent(
            changed_branch, base_state=reference, step_sizes=np.full(3, 1.0e-3)
        )

    legacy = load_physics_profile("legacy_python_2026_03_12_v1")

    def mixed_profile(increment: np.ndarray) -> elastic.TensionObservation:
        profile = PROFILE if np.all(increment == 0.0) else legacy
        return _observation(
            np.array([1.0, 2.0, 3.0]), increment=increment, profile=profile
        )

    with pytest.raises(ProfileMixingError, match="profile"):
        elastic.central_difference_tangent(
            mixed_profile, base_state=reference, step_sizes=np.full(3, 1.0e-3)
        )

    for invalid in (0.0, -1.0e-3, np.nan, np.inf):
        with pytest.raises(ValueError, match="step"):
            elastic.central_difference_tangent(
                lambda q: _observation(
                    np.array([1.0, 2.0, 3.0]), increment=q
                ),
                base_state=reference,
                step_sizes=np.full(3, invalid),
            )

    with pytest.raises(ValueError, match="finite"):
        _observation(np.array([1.0, np.nan, 3.0]))

    def wrong_current_cell(increment: np.ndarray) -> elastic.TensionObservation:
        # This deliberately reuses H0/A0 instead of the perturbed H/A.
        return _observation(np.array([1.0, 2.0, 3.0]), increment=np.zeros(3))

    with pytest.raises(ValueError, match="cell|area"):
        elastic.central_difference_tangent(
            wrong_current_cell,
            base_state=reference,
            step_sizes=np.full(3, 1.0e-3),
        )


def test_one_sided_branch_changing_tangent_is_machine_labeled_not_modulus() -> None:
    matrix = np.array([[9.0, 1.0, 2.0], [3.0, 8.0, 4.0], [5.0, 6.0, 7.0]])
    base = np.array([0.4, 0.5, -0.1])
    reference = _base_state(base)

    def observe(increment: np.ndarray) -> elastic.TensionObservation:
        if np.all(increment == 0.0):
            return _observation(base, increment=increment)
        return _observation(
            base + matrix @ increment,
            increment=increment,
            topology_id="topology-after-damage",
            branch_id="irreversible-branch-b",
        )

    result = elastic.one_sided_difference_tangent(
        observe,
        base_state=reference,
        step_sizes=np.full(3, 2.0e-3),
        side="forward",
        reason="irreversible topology transition prevents a negative-side state",
    )
    np.testing.assert_allclose(result.raw_matrix_pN_per_nm, matrix, atol=1e-12)
    metadata = result.derivative_metadata
    assert metadata["kind"] == "forward_branch_changing_secant"
    assert metadata["side"] == "forward"
    assert metadata["equilibrium_modulus_claim"] is False
    assert metadata["sample_topology_ids"] == ["topology-after-damage"] * 3

    with pytest.raises(ValueError, match="transition|irreversible"):
        elastic.one_sided_difference_tangent(
            lambda q: _observation(base + matrix @ q, increment=q),
            base_state=reference,
            step_sizes=np.full(3, 2.0e-3),
            side="forward",
            reason="",
        )


def test_raw_export_round_trip_is_unsymmetrized_immutable_and_fail_closed(
    tmp_path: Path,
) -> None:
    observe, reference_total, _exact = _coupled_constitutive_fixture()
    result = elastic.central_difference_tangent(
        observe,
        base_state=_base_state(reference_total),
        step_sizes=np.full(3, 1.0e-3),
    )
    path = tmp_path / "fixture.raw_tangent.json"
    digest = write_raw_tangent_record(path, result)
    before = path.read_bytes()
    loaded = read_raw_tangent_record(path)
    assert digest.startswith("sha256:")
    assert loaded["raw_tangent"]["values"] == result.raw_matrix_pN_per_nm.tolist()
    assert loaded["raw_tangent"]["values"][0][1] != loaded["raw_tangent"]["values"][1][0]
    with pytest.raises(FileExistsError):
        write_raw_tangent_record(path, result)
    assert path.read_bytes() == before

    ambiguous = copy.deepcopy(loaded)
    ambiguous["convention"]["shear_definition"] = "tensor_shear_unspecified_factor"
    ambiguous_path = tmp_path / "ambiguous.json"
    ambiguous_path.write_text(json.dumps(ambiguous), encoding="utf-8")
    with pytest.raises(ValueError, match="convention|shear"):
        read_raw_tangent_record(ambiguous_path)

    tampered = copy.deepcopy(loaded)
    tampered["physics_profile"]["potentials"]["harmonic_bond"]["parameters"][
        "K_pN_per_nm"
    ] = 1.0
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="profile|hash|route"):
        read_raw_tangent_record(tampered_path)

    forged = copy.deepcopy(loaded)
    forged_matrix = np.asarray(forged["raw_tangent"]["values"], dtype=float)
    forged_matrix[0, 0] += 1.0
    difference = forged_matrix - forged_matrix.T
    forged["raw_tangent"]["values"] = forged_matrix.tolist()
    forged["asymmetry_diagnostics"] = {
        "matrix_minus_transpose_pN_per_nm": difference.tolist(),
        "frobenius_norm_matrix_minus_transpose_pN_per_nm": float(
            np.linalg.norm(difference)
        ),
        "max_abs_matrix_minus_transpose_pN_per_nm": float(np.max(np.abs(difference))),
        "C12_minus_C21_pN_per_nm": float(forged_matrix[0, 1] - forged_matrix[1, 0]),
        "C13_minus_C31_pN_per_nm": float(forged_matrix[0, 2] - forged_matrix[2, 0]),
        "C23_minus_C32_pN_per_nm": float(forged_matrix[1, 2] - forged_matrix[2, 1]),
        "raw_values_replaced_or_symmetrized": False,
    }
    forged_path = tmp_path / "forged_matrix.json"
    forged_path.write_text(json.dumps(forged), encoding="utf-8")
    with pytest.raises(ValueError, match="replay"):
        read_raw_tangent_record(forged_path)

    reset_reference = copy.deepcopy(loaded)
    reset_reference["fixed_reference"]["total_tension_pN_per_nm"] = list(
        reset_reference["base_total_tension_pN_per_nm"]
    )
    reset_path = tmp_path / "silently_reset_reference.json"
    reset_path.write_text(json.dumps(reset_reference), encoding="utf-8")
    with pytest.raises(ValueError, match="incremental|fixed reference"):
        read_raw_tangent_record(reset_path)

    for sample in loaded["samples"]:
        cell = np.asarray(sample["cell_matrix_nm"])
        assert sample["area_nm2"] == pytest.approx(np.linalg.det(cell))


def _independent_affine_harmonic_derivative(
    displacement_nm: np.ndarray,
    *,
    area_nm2: float,
    K_pN_per_nm: float,
    r0_nm: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Closed-form dN/dq at q=0, independent of the production differencer."""

    d = np.asarray(displacement_nm, dtype=float)
    radius = float(np.linalg.norm(d))
    beta = 2.0 * K_pN_per_nm * (1.0 - r0_nm / radius)
    alpha = beta / area_nm2
    base_tensor = alpha * np.outer(d, d)
    tangent = np.empty((3, 3), dtype=float)
    displacement_derivatives = (
        np.array([d[0], 0.0]),
        np.array([0.0, d[1]]),
        np.array([d[1], 0.0]),
    )
    area_derivatives = (area_nm2, area_nm2, 0.0)
    for column, (dprime, area_prime) in enumerate(
        zip(displacement_derivatives, area_derivatives)
    ):
        radius_prime = float(np.dot(d, dprime) / radius)
        beta_prime = 2.0 * K_pN_per_nm * r0_nm * radius_prime / radius**2
        alpha_prime = beta_prime / area_nm2 - beta * area_prime / area_nm2**2
        derivative = alpha_prime * np.outer(d, d) + alpha * (
            np.outer(dprime, d) + np.outer(d, dprime)
        )
        tangent[:, column] = [derivative[0, 0], derivative[1, 1], derivative[0, 1]]
    return np.array([base_tensor[0, 0], base_tensor[1, 1], base_tensor[0, 1]]), tangent


def test_real_serial_lammps_tangent_matches_independent_oracle_and_closes(
) -> None:
    harmonic = PROFILE.expanded_snapshot()["potentials"]["harmonic_bond"]["parameters"]
    # Eight copies close through the (a+b) periodic lattice vector.  Every
    # ring atom has equal/opposite neighbor forces, yielding a genuinely
    # fixed-cell equilibrated, oblique, prestressed reference after minimize.
    displacement = np.array([1.0, 0.875])
    positions = np.vstack((-0.5 * displacement, 0.5 * displacement))
    one_bond_tension, one_bond_exact = _independent_affine_harmonic_derivative(
        displacement,
        area_nm2=56.0,
        K_pN_per_nm=harmonic["K_pN_per_nm"],
        r0_nm=harmonic["r0_nm"],
    )
    base_tension = 8.0 * one_bond_tension
    exact = 8.0 * one_bond_exact
    reference = _base_state(base_tension)
    errors = []
    for step in (1.0e-3, 5.0e-4, 2.5e-4):
        lammps_result = elastic.run_lammps_harmonic_bond_tangent(
            PROFILE,
            base_state=reference,
            base_pair_positions_nm=positions,
            step_sizes=np.full(3, step),
        )
        errors.append(np.linalg.norm(lammps_result.raw_matrix_pN_per_nm - exact))
        solver = lammps_result.solver_validation
        assert solver == {
            "backend": "LAMMPS_serial_library",
            "solver_version": 20260902,
            "instances_started": 7,
            "instances_closed": 7,
            "all_instances_closed": True,
                "fixed_topology": True,
                "minimization_performed": True,
                "physical_time_claim": False,
                "fixture_kind": "periodic_harmonic_ring",
                "fixture_bond_count": 8,
                "fixture_base_pair_positions_nm": positions.tolist(),
        }
    assert errors[1] < 0.26 * errors[0]
    assert errors[2] < 0.27 * errors[1]
    finest = lammps_result.raw_matrix_pN_per_nm
    np.testing.assert_allclose(
        lammps_result.base_total_tension_pN_per_nm,
        base_tension,
        rtol=3e-12,
        atol=2e-10,
    )
    np.testing.assert_allclose(finest, exact, rtol=2e-6, atol=2e-7)
    # These are the smooth current-area/Cauchy-like geometric identities for
    # this q/F convention.  Raw C is not generally symmetric under prestress.
    assert finest[0, 1] - finest[1, 0] == pytest.approx(
        base_tension[1] - base_tension[0], rel=2e-5, abs=3e-7
    )
    assert finest[0, 2] - finest[2, 0] == pytest.approx(
        2.0 * base_tension[2], rel=2e-5, abs=3e-7
    )
    assert finest[1, 2] - finest[2, 1] == pytest.approx(0.0, abs=5e-6)


def test_legacy_elastic_adapter_closes_solver_on_success(monkeypatch, tmp_path: Path) -> None:
    class FakeLammps:
        def __init__(self):
            self.closed = False
            self.commands = []

        def command(self, value):
            self.commands.append(value)

        def commands_list(self, cmdlist):
            self.commands.extend(cmdlist)

        def close(self):
            self.closed = True

    fake = FakeLammps()
    monkeypatch.setattr(elastic, "lammps", lambda: fake)
    monkeypatch.setattr(elastic, "lammps_PG_simulation_settings", lambda _solver: None)
    monkeypatch.setattr(elastic, "lammps_PG_potential_settings", lambda _solver: None)
    monkeypatch.setattr(elastic, "lammps_PG_thermo_settings", lambda _solver: None)
    restart = tmp_path / "network_prestr0.0.restart"
    restart.write_bytes(b"fixture")

    assert elastic.lammps_calculate_elastic_tensor(
        str(restart), allow_legacy_forensic_output=True
    ) is True
    assert fake.closed is True


def test_new_lammps_tangent_fixture_closes_solver_on_injected_failure(monkeypatch) -> None:
    class FailingLammps:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def version(self):
            return 20260902

        def command(self, _value):
            raise RuntimeError("injected tangent fixture failure")

        def close(self):
            self.closed = True

    fake = FailingLammps()
    monkeypatch.setattr(elastic, "lammps", lambda *args, **kwargs: fake)
    displacement = np.array([1.0, 0.875])
    positions = np.vstack((-0.5 * displacement, 0.5 * displacement))
    with pytest.raises(RuntimeError, match="injected tangent fixture failure"):
        elastic.run_lammps_harmonic_bond_tangent(
            PROFILE,
            base_state=_base_state(np.array([1.0, 1.0, 1.0])),
            base_pair_positions_nm=positions,
            step_sizes=np.full(3, 1.0e-3),
        )
    assert fake.closed is True


def test_legacy_elastic_adapter_closes_solver_on_failure(monkeypatch, tmp_path: Path) -> None:
    class FailingLammps:
        def __init__(self):
            self.closed = False

        def command(self, _value):
            raise RuntimeError("synthetic solver failure")

        def close(self):
            self.closed = True

    fake = FailingLammps()
    monkeypatch.setattr(elastic, "lammps", lambda: fake)
    restart = tmp_path / "network_prestr0.0.restart"
    restart.write_bytes(b"fixture")
    with pytest.raises(RuntimeError, match="synthetic solver failure"):
        elastic.lammps_calculate_elastic_tensor(
            str(restart), allow_legacy_forensic_output=True
        )
    assert fake.closed is True


def test_legacy_elastic_adapter_is_fail_closed_without_forensic_opt_in(
    tmp_path: Path,
) -> None:
    restart = tmp_path / "network_prestr0.0.restart"
    restart.write_bytes(b"fixture")
    with pytest.raises(RuntimeError, match="disabled by default|symmetrized"):
        elastic.lammps_calculate_elastic_tensor(str(restart))
