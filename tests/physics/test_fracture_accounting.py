"""P02-04 deterministic event localization and phase accounting regressions."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from pgworld.config.physics_profiles import load_physics_profile
from pgworld.physics.damage import (
    CriterionObservation,
    DamageLaw,
    initialize_damage_state,
    materialize_thresholds,
)
from pgworld.simulation.controls import AxisFrame, QuasiStaticControlStep
from pgworld.simulation.fracture import (
    BackendObservation,
    CascadeBudget,
    CascadeDiagnostic,
    ConvergenceDiagnostics,
    EventLocalizationRecord,
    FractureEnergyAccounting,
    FractureExecutionError,
    LammpsFractureBackend,
    LocalizationBudget,
    LocalizationDiagnostic,
    LocalizationStatus,
    LocalizedCascadeResult,
    QuasiStaticFractureCascade,
    TrialDomainCertificate,
)
from pgworld.simulation.topology import (
    AngleTopology,
    BondTopology,
    Cell2D,
    NodeTopology,
    TopologyRegistry,
)


PROFILE = load_physics_profile("reviewed_physics_provisional_v0")
REFERENCE_ID = "p0204-fixed-reference"


def _record_hash(body: dict[str, object]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _registry(*, peptide: bool = False) -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    positions = {"n1": (1.0, 2.0), "n2": (2.0, 2.0), "n3": (3.0, 2.0)}
    chemical = "peptide" if peptide else "glycan"
    bonds = (
        BondTopology("b12", "n1", "n2", 1, chemical, (0, 0), (1.0, 0.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.0, 0.0)),
    )
    angles = () if peptide else (
        AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),
    )
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _periodic_registry() -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    positions = {"n1": (11.00, 2.0), "n2": (0.03, 2.0), "n3": (1.06, 2.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (1, 0), (1.03, 0.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.03, 0.0)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _bounded_shape_registry(*, bent: bool = False, skew_cell: bool = False) -> TopologyRegistry:
    cell = Cell2D(
        ((12.0, 1.0 if skew_cell else 0.0), (0.0, 10.0)),
        (0.0, 0.0),
        (True, True),
    )
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    middle_y = 2.5 if bent else 2.0
    positions = {"n1": (1.0, 2.0), "n2": (2.0, middle_y), "n3": (3.0, 2.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (0, 0), (1.0, middle_y - 2.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.0, 2.0 - middle_y)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _folded_orientation_registry() -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    positions = {"n1": (1.0, 2.0), "n2": (3.0, 2.0), "n3": (2.0, 2.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (0, 0), (2.0, 0.0)),
        BondTopology("b23", "n3", "n2", 1, "glycan", (0, 0), (1.0, 0.0)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _damage(registry: TopologyRegistry, *, threshold: float = 1.113):
    law = DamageLaw(
        law_id="p0204-extension-v1",
        law_kind="deterministic_threshold",
        criterion="bond_extension_ratio",
        criterion_unit="dimensionless",
        base_threshold=threshold,
        distribution=None,
        predictor_visibility="hidden_from_predictor",
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
    )
    field = materialize_thresholds(
        law, [bond.stable_bond_id for bond in registry.bonds]
    )
    state = initialize_damage_state(
        law,
        field,
        [
            CriterionObservation(
                bond.stable_bond_id, law.criterion, law.criterion_unit, 1.0
            )
            for bond in registry.bonds
        ],
    )
    return law, field, state


def _control(
    lambda_load: float,
    path_progress: float,
    *,
    step_index: int,
    previous_lambda: float = 0.0,
    previous_progress: float = 0.0,
    loading_mode: str = "axial",
) -> QuasiStaticControlStep:
    absolute = np.diag((1.0 + lambda_load, 1.0))
    previous = np.diag((1.0 + previous_lambda, 1.0))
    incremental = absolute @ np.linalg.inv(previous)
    return QuasiStaticControlStep(
        control_id=f"{loading_mode}:{step_index}:{lambda_load:.17g}:{path_progress:.17g}",
        step_index=step_index,
        control_kind="deformation_gradient",
        loading_mode=loading_mode,
        axes=AxisFrame(),
        reference_state_id=REFERENCE_ID,
        lambda_load=lambda_load,
        load_coordinate_unit="dimensionless",
        progress_unit="dimensionless",
        path_progress=path_progress,
        progress_increment=path_progress - previous_progress,
        absolute_deformation_gradient=absolute,
        incremental_deformation_gradient=incremental,
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
    )


def _control_with_step(
    control: QuasiStaticControlStep, step_index: int
) -> QuasiStaticControlStep:
    return QuasiStaticControlStep(
        control_id=f"{control.control_id}:step-forgery:{step_index}",
        step_index=step_index, control_kind=control.control_kind,
        loading_mode=control.loading_mode, axes=control.axes,
        reference_state_id=control.reference_state_id,
        lambda_load=control.lambda_load,
        load_coordinate_unit=control.load_coordinate_unit,
        progress_unit=control.progress_unit,
        path_progress=control.path_progress,
        progress_increment=control.progress_increment,
        absolute_deformation_gradient=control.absolute_deformation_gradient,
        incremental_deformation_gradient=control.incremental_deformation_gradient,
        absolute_tension_target_pN_per_nm=control.absolute_tension_target_pN_per_nm,
        incremental_tension_target_pN_per_nm=control.incremental_tension_target_pN_per_nm,
        pressure_derivation=control.pressure_derivation,
    )


def _certificate(registry: TopologyRegistry) -> TrialDomainCertificate:
    return TrialDomainCertificate.bounded_harmonic_fixture(
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
        registry_id=registry.registry_id,
        physical_bond_ids=tuple(bond.stable_bond_id for bond in registry.bonds),
    )


class AnalyticalLocalizationBackend:
    """Deterministic conservative fixture with an exact checkpoint contract."""

    def __init__(
        self,
        registry: TopologyRegistry,
        *,
        base_progress: float = 0.0,
        simultaneous_tie: bool = False,
        nonconverged_progress_attempts: dict[float, int] | None = None,
        nonconvergence_reason: str = "diagnosed_transient_solver_interruption",
        fail_delete: bool = False,
        failure_phase: str | None = None,
        nonmonotone_response: bool = False,
    ) -> None:
        self.registry = registry
        self.base_progress = base_progress
        self.simultaneous_tie = simultaneous_tie
        self.nonconverged_progress_attempts = dict(nonconverged_progress_attempts or {})
        self.nonconvergence_reason = nonconvergence_reason
        self.fail_delete = fail_delete
        self.failure_phase = failure_phase
        self.nonmonotone_response = nonmonotone_response
        certified = _certificate(registry).backend_response_contract_id
        self.localization_response_contract_id = (
            "sha256:" + "0" * 64 if nonmonotone_response else certified
        )
        self.checkpoint_count = 0
        self.commands: list[tuple[Any, ...]] = []
        self.closed = False
        self.restore_count = 0
        self.solver_trials = 0
        self.deleted_bonds: set[str] = set()
        self.deleted_angles: set[str] = set()
        self.temporary_groups: set[str] = set()
        self.runtime_constraint = "analytical_fixed_boundary"
        self.current_control: QuasiStaticControlStep | None = None
        self.positions = np.vstack(
            [
                registry.source_wrapped_positions_nm[node.stable_node_id]
                for node in sorted(registry.nodes, key=lambda item: item.solver_atom_id)
            ]
        )

    def _exposure(self, control: QuasiStaticControlStep) -> float:
        return control.path_progress - self.base_progress

    def _set_trial_geometry(self, control: QuasiStaticControlStep) -> None:
        exposure = self._exposure(control)
        if self.nonmonotone_response:
            exposure = exposure + 0.12 * np.sin(4.0 * np.pi * exposure / 0.2)
        self.positions = np.array(((1.0, 2.0), (2.0 + exposure, 2.0), (3.0 + exposure, 2.0)))
        if self.simultaneous_tie:
            self.positions[2, 0] = 3.0 + 2.0 * exposure

    def _energy(self, phase: str, control: QuasiStaticControlStep) -> float:
        exposure = self._exposure(control)
        coefficient = {
            "after_control_before_relax": 100.0,
            "pre_delete_relaxed": 50.0,
            "post_delete_unrelaxed": 25.0,
            "post_event_relaxed": 10.0,
        }[phase]
        return coefficient * exposure * exposure

    def _observation(
        self,
        *,
        phase: str,
        control: QuasiStaticControlStep,
        topology_state,
        damage_state,
        converged: bool,
    ) -> BackendObservation:
        rows = sorted(self.registry.nodes, key=lambda item: item.solver_atom_id)
        index = {node.stable_node_id: offset for offset, node in enumerate(rows)}
        criteria: dict[str, float] = {}
        for bond_id in topology_state.alive_bond_ids:
            bond = self.registry.bond(bond_id)
            displacement = self.positions[index[bond.node_j]] - self.positions[index[bond.node_i]]
            criteria[bond_id] = float(np.linalg.norm(displacement)) / float(
                np.linalg.norm(bond.source_displacement_nm)
            )
        cell = Cell2D(
            np.asarray(control.absolute_deformation_gradient) @ self.registry.cell.matrix_nm,
            self.registry.cell.origin_nm,
            self.registry.cell.periodic,
        )
        convergence = (
            ConvergenceDiagnostics.successful(0.0, 1, 100)
            if converged
            else ConvergenceDiagnostics.rejected("phase_not_relaxed", 1.0, 0, 100)
        )
        energy = self._energy(phase, control)
        return BackendObservation.from_solver_rows(
            phase=phase,
            registry=self.registry,
            topology_state=topology_state,
            solver_atom_ids=tuple(node.solver_atom_id for node in rows),
            positions_nm=self.positions,
            forces_pN=np.zeros_like(self.positions),
            criterion_values=criteria,
            criterion_unit="dimensionless",
            cell=cell,
            total_tension_pN_per_nm=np.zeros((2, 2)),
            reference_total_tension_pN_per_nm=np.zeros((2, 2)),
            raw_energies_pN_nm={"pe": energy, "ebond": energy, "eangle": 0.0},
            convergence=convergence,
            control=control,
            profile_id=PROFILE.profile_id,
            profile_hash=PROFILE.canonical_hash,
            reference_state_id=REFERENCE_ID,
            damage_state=damage_state,
        )

    def apply_control(self, control: QuasiStaticControlStep) -> None:
        self.commands.append(("apply_control", control.lambda_load, control.path_progress))
        if self.failure_phase == "apply":
            self.positions[1, 0] += 9.0
            raise FractureExecutionError("injected apply failure after partial mutation")
        self.current_control = control
        self._set_trial_geometry(control)

    def observe_after_control_unrelaxed(self, *, control, topology_state, damage_state):
        self.commands.append(("observe", "after_control_before_relax"))
        return self._observation(
            phase="after_control_before_relax",
            control=control,
            topology_state=topology_state,
            damage_state=damage_state,
            converged=False,
        )

    def relax_and_observe(self, *, phase, control, topology_state, damage_state):
        self.commands.append(("relax", phase, control.lambda_load, control.path_progress))
        self.solver_trials += 1
        if self.failure_phase == "relax" and phase == "pre_delete_relaxed":
            self.positions[1, 0] += 8.0
            raise FractureExecutionError("injected relax failure after partial mutation")
        if phase == "pre_delete_relaxed":
            remaining = self.nonconverged_progress_attempts.get(control.path_progress, 0)
            if remaining:
                self.nonconverged_progress_attempts[control.path_progress] = remaining - 1
                observation = self._observation(
                    phase=phase,
                    control=control,
                    topology_state=topology_state,
                    damage_state=damage_state,
                    converged=False,
                )
                body = observation._constructor_body()
                body["convergence"] = ConvergenceDiagnostics.rejected(
                    self.nonconvergence_reason, 2.0, 100, 100, 1.0e-8
                )
                return BackendObservation._create(**body)
        if phase == "post_event_relaxed" and "b12" not in topology_state.alive_bond_ids:
            self.positions[1] = (2.0, 2.0)
            self.positions[2] = (3.0, 2.0)
        return self._observation(
            phase=phase,
            control=control,
            topology_state=topology_state,
            damage_state=damage_state,
            converged=True,
        )

    def observe_unrelaxed(self, *, control, topology_state, damage_state):
        self.commands.append(("observe", "post_delete_unrelaxed"))
        return self._observation(
            phase="post_delete_unrelaxed",
            control=control,
            topology_state=topology_state,
            damage_state=damage_state,
            converged=False,
        )

    def delete_angle(self, angle) -> None:
        self.commands.append(("delete_angle", angle.stable_angle_id))
        self.deleted_angles.add(angle.stable_angle_id)

    def delete_bond(self, bond) -> None:
        self.commands.append(("delete_bond", bond.stable_bond_id))
        if self.fail_delete:
            raise FractureExecutionError("injected final delete failure")
        self.deleted_bonds.add(bond.stable_bond_id)

    def audit_topology(self, topology_state) -> None:
        self.commands.append(("audit", topology_state.topology_state_id))
        assert self.deleted_bonds == set(self.registry.initial_state.alive_bond_ids) - set(
            topology_state.alive_bond_ids
        )
        assert self.deleted_angles == set(self.registry.initial_state.alive_angle_ids) - set(
            topology_state.alive_angle_ids
        )

    def checkpoint(self):
        self.checkpoint_count += 1
        self.commands.append(("checkpoint",))
        if self.failure_phase == "checkpoint" and self.checkpoint_count > 1:
            self.positions[1, 0] += 7.0
            raise FractureExecutionError("injected trial checkpoint failure")
        return {
            "control": self.current_control,
            "positions": np.array(self.positions, copy=True),
            "bonds": set(self.deleted_bonds),
            "angles": set(self.deleted_angles),
            "runtime_constraint": self.runtime_constraint,
        }

    def restore(self, checkpoint) -> None:
        self.restore_count += 1
        self.commands.append(("restore",))
        if self.failure_phase == "restore" or (
            self.failure_phase == "final_restore" and self.deleted_angles
        ):
            raise FractureExecutionError("injected restore failure")
        self.current_control = checkpoint["control"]
        self.positions = np.array(checkpoint["positions"], copy=True)
        self.deleted_bonds = set(checkpoint["bonds"])
        self.deleted_angles = set(checkpoint["angles"])
        self.runtime_constraint = checkpoint["runtime_constraint"]

    def observe_restored(self, *, control, topology_state, damage_state):
        assert self.current_control is None or self.current_control.as_record() == control.as_record()
        return self._observation(
            phase="pre_delete_relaxed",
            control=control,
            topology_state=topology_state,
            damage_state=damage_state,
            converged=True,
        )

    def audit_trial_runtime(self) -> None:
        assert not self.temporary_groups
        assert self.runtime_constraint == "analytical_fixed_boundary"

    def close(self) -> None:
        self.commands.append(("close",))
        self.closed = True


def _previous_snapshot(backend, lower, registry, state):
    backend.current_control = lower
    backend._set_trial_geometry(lower)
    return backend.observe_restored(
        control=lower, topology_state=registry.initial_state, damage_state=state
    )


def _run_fake(
    *,
    threshold: float = 1.113,
    tolerance: float = 0.003125,
    backend_kwargs: dict[str, object] | None = None,
    lower: QuasiStaticControlStep | None = None,
    upper: QuasiStaticControlStep | None = None,
    budget_kwargs: dict[str, object] | None = None,
):
    registry = _registry()
    law, field, state = _damage(registry, threshold=threshold)
    lower = lower or _control(0.0, 0.0, step_index=0)
    upper = upper or _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry, **(backend_kwargs or {}))
    previous = _previous_snapshot(backend, lower, registry, state)
    budget_values = {
        "max_refinements": 12,
        "max_solver_trials": 16,
        "max_retries_per_trial": 1,
        "load_tolerance": tolerance,
        "path_tolerance": tolerance,
    }
    budget_values.update(budget_kwargs or {})
    result = QuasiStaticFractureCascade(
        backend, registry, law, field, CascadeBudget(2, 8)
    ).run_localized_step(
        lower_control=lower,
        upper_control=upper,
        previous_accepted=previous,
        damage_state=state,
        topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(**budget_values),
        domain_certificate=_certificate(registry),
    )
    return result, backend, registry, law, field, state, previous


def test_localizes_first_crossing_and_binds_event_and_five_phase_accounting() -> None:
    result, backend, _registry_value, _law, field, state, _previous = _run_fake()
    assert result.localization.status is LocalizationStatus.LOCALIZED
    assert result.cascade_result is not None
    assert len(result.cascade_result.transitions) == 1
    event = result.cascade_result.transitions[0].material_event
    localized = result.localization.localized_control
    assert localized is not None
    assert event.control_id == localized.control_id
    assert event.load_coordinate == localized.lambda_load
    assert event.path_progress == localized.path_progress
    assert event.physical_bond_id == "b12"
    assert state.as_record()["accepted_material_event_ids"] == []
    assert field.as_record() == result.as_record()["privileged_reference_metadata"]["threshold_field"]
    assert len(result.energy_accounting) == 1
    accounting = result.energy_accounting[0]
    assert tuple(accounting.phase_energies_pN_nm) == (
        "U_previous_accepted",
        "U_after_control_before_relax",
        "U_pre_event_relaxed",
        "U_post_delete_unrelaxed",
        "U_post_event_relaxed",
    )
    energies = accounting.phase_energies_pN_nm
    assert accounting.fixed_topology_conservative_loading_work_pN_nm == pytest.approx(energies["U_after_control_before_relax"] - energies["U_previous_accepted"])
    assert accounting.equilibrium_stored_energy_change_pN_nm == pytest.approx(energies["U_pre_event_relaxed"] - energies["U_previous_accepted"])
    assert accounting.fixed_topology_conservative_loading_work_pN_nm == pytest.approx(
        accounting.equilibrium_stored_energy_change_pN_nm
        + accounting.pre_event_relaxation_loss_pN_nm
    )
    assert accounting.same_coordinate_deletion_energy_change_pN_nm == pytest.approx(energies["U_post_delete_unrelaxed"] - energies["U_pre_event_relaxed"])
    assert accounting.held_control_boundary_work_pN_nm == 0.0
    assert accounting.post_delete_relaxation_loss_pN_nm == pytest.approx(energies["U_post_delete_unrelaxed"] - energies["U_post_event_relaxed"])
    assert accounting.same_coordinate_deletion_energy_change_pN_nm < 0.0
    assert accounting.post_delete_relaxation_loss_pN_nm >= 0.0
    assert backend.closed is True


def test_coarse_and_fine_refinement_converge_without_publishing_trial_states() -> None:
    coarse, coarse_backend, *_ = _run_fake(tolerance=0.025)
    fine, fine_backend, *_ = _run_fake(tolerance=0.003125)
    threshold_lambda = 0.113
    coarse_event = coarse.cascade_result.transitions[0].material_event
    fine_event = fine.cascade_result.transitions[0].material_event
    assert threshold_lambda <= coarse_event.load_coordinate <= threshold_lambda + 0.025
    assert threshold_lambda <= fine_event.load_coordinate <= threshold_lambda + 0.003125
    assert abs(fine_event.load_coordinate - threshold_lambda) <= abs(coarse_event.load_coordinate - threshold_lambda)
    assert fine.localization.solver_trials > coarse.localization.solver_trials
    first_delete = next(index for index, row in enumerate(fine_backend.commands) if row[0] in {"delete_angle", "delete_bond"})
    assert all(row[0] not in {"delete_angle", "delete_bond"} for row in fine_backend.commands[:first_delete])
    text = repr(fine.as_observable_record()).lower()
    assert "threshold" not in text and "trial" not in text
    assert coarse_backend.closed and fine_backend.closed


def test_nonconverged_trial_retries_from_exact_lower_without_moving_bracket() -> None:
    result, backend, *_ = _run_fake(threshold=1.15, backend_kwargs={"nonconverged_progress_attempts": {0.1: 1}})
    assert result.localization.status is LocalizationStatus.LOCALIZED
    assert result.localization.retries == 1
    assert backend.restore_count >= result.localization.refinements
    assert result.localization.lower_bracket_control.path_progress >= 0.1
    assert result.localization.lower_bracket_control.path_progress < 0.15


def test_reproducible_nonconvergence_is_not_blindly_retried() -> None:
    result, backend, *_ = _run_fake(
        threshold=1.15,
        backend_kwargs={
            "nonconverged_progress_attempts": {0.2: 1},
            "nonconvergence_reason": "max_iterations_or_residual_above_tolerance",
        },
        budget_kwargs={"max_retries_per_trial": 1},
    )
    assert result.localization.status is LocalizationStatus.NONCONVERGENCE_REJECTED
    assert result.localization.diagnostic.kind == "nonretryable_nonconvergence"
    assert result.localization.solver_trials == 1
    upper_relaxes = [
        row for row in backend.commands
        if row[:2] == ("relax", "pre_delete_relaxed") and row[2] == pytest.approx(0.2)
    ]
    assert len(upper_relaxes) == 1
    assert result.cascade_result is None and result.energy_accounting == ()


def test_retry_budget_for_diagnosed_transient_is_capped_at_one() -> None:
    with pytest.raises(FractureExecutionError, match="at most one"):
        LocalizationBudget(8, 12, 2, 0.005, 0.005)


def test_second_diagnosed_transient_on_new_coordinate_does_not_retry() -> None:
    result, backend, *_ = _run_fake(
        threshold=1.15,
        backend_kwargs={
            "nonconverged_progress_attempts": {0.2: 1, 0.1: 1},
        },
        budget_kwargs={"max_retries_per_trial": 1},
    )
    assert result.localization.status is LocalizationStatus.RETRY_BUDGET_EXHAUSTED
    assert result.localization.retries == 1
    assert result.localization.solver_trials == 3
    midpoint_relaxes = [
        row for row in backend.commands
        if row[:2] == ("relax", "pre_delete_relaxed")
        and row[2] == pytest.approx(0.1)
    ]
    assert len(midpoint_relaxes) == 1
    assert result.cascade_result is None and result.energy_accounting == ()
    assert backend.deleted_bonds == set() and backend.closed


def test_exhausted_refinement_solver_and_retry_budgets_are_typed_and_restore_lower() -> None:
    refinement, refinement_backend, *_ = _run_fake(budget_kwargs={"max_refinements": 0})
    assert refinement.localization.status is LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED
    assert refinement.cascade_result is None and refinement.energy_accounting == ()
    assert refinement.localization.diagnostic.kind == "refinement_budget_exhausted"
    assert refinement_backend.deleted_bonds == set() and refinement_backend.closed
    solver, solver_backend, *_ = _run_fake(budget_kwargs={"max_solver_trials": 1})
    assert solver.localization.status is LocalizationStatus.SOLVER_BUDGET_EXHAUSTED
    assert solver.localization.diagnostic.kind == "solver_budget_exhausted"
    assert solver_backend.deleted_bonds == set() and solver_backend.closed
    retry, retry_backend, *_ = _run_fake(threshold=1.15, backend_kwargs={"nonconverged_progress_attempts": {0.1: 3}}, budget_kwargs={"max_retries_per_trial": 1})
    assert retry.localization.status is LocalizationStatus.RETRY_BUDGET_EXHAUSTED
    assert retry.localization.diagnostic.kind == "trial_nonconvergence"
    assert retry.cascade_result is None and retry_backend.deleted_bonds == set()
    assert retry_backend.closed


def test_initial_violation_and_non_crossing_upper_never_publish_an_event() -> None:
    registry = _registry()
    law, field, state = _damage(registry, threshold=0.9)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    invalid = QuasiStaticFractureCascade(
        backend, registry, law, field, CascadeBudget(2, 8)
    ).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
        domain_certificate=_certificate(registry),
    )
    assert invalid.localization.status is LocalizationStatus.INVALID_LOWER_BRACKET
    assert invalid.cascade_result is None and invalid.energy_accounting == ()
    assert all(row[0] != "apply_control" for row in backend.commands)

    noncrossing, noncrossing_backend, *_ = _run_fake(threshold=1.3)
    assert noncrossing.localization.status is LocalizationStatus.UPPER_DOES_NOT_CROSS
    assert noncrossing.cascade_result is None and noncrossing.energy_accounting == ()
    assert noncrossing_backend.deleted_bonds == set()
    assert noncrossing_backend.closed


def test_cyclic_unloading_lambda_decreases_while_progress_and_event_exposure_increase() -> None:
    lower = _control(0.2, 0.2, step_index=4, previous_lambda=0.0, loading_mode="cyclic")
    upper = _control(0.0, 0.4, step_index=5, previous_lambda=0.2, previous_progress=0.2, loading_mode="cyclic")
    result, _backend, *_ = _run_fake(threshold=1.1, lower=lower, upper=upper, backend_kwargs={"base_progress": 0.2}, tolerance=0.003125)
    localized = result.localization.localized_control
    assert localized is not None
    assert localized.lambda_load < lower.lambda_load
    assert localized.path_progress > lower.path_progress
    assert localized.path_progress == pytest.approx(lower.path_progress + abs(localized.lambda_load - lower.lambda_load))
    event = result.cascade_result.transitions[0].material_event
    assert event.load_coordinate == localized.lambda_load
    assert event.path_progress == localized.path_progress


def test_simultaneous_crossing_uses_p0202_stable_id_tie_order_once() -> None:
    result, _backend, *_ = _run_fake(threshold=1.1, backend_kwargs={"simultaneous_tie": True})
    assert result.localization.status is LocalizationStatus.LOCALIZED
    assert [transition.material_event.physical_bond_id for transition in result.cascade_result.transitions] == ["b12"]


def test_final_transaction_failure_restores_original_lower_and_publishes_no_event() -> None:
    result, backend, registry, _law, _field, state, previous = _run_fake(backend_kwargs={"fail_delete": True})
    assert result.localization.status is LocalizationStatus.FINAL_TRANSACTION_ROLLED_BACK
    assert result.cascade_result is None and result.energy_accounting == ()
    assert result.final_damage_state == state
    assert result.final_topology_state == registry.initial_state
    assert result.final_snapshot == previous
    assert backend.deleted_bonds == set() and backend.deleted_angles == set()
    assert backend.temporary_groups == set() and backend.closed


@pytest.mark.parametrize("phase", ["apply", "relax", "checkpoint"])
def test_trial_phase_exception_restores_lower_and_returns_typed_no_publication(phase: str) -> None:
    result, backend, registry, _law, _field, state, previous = _run_fake(
        backend_kwargs={"failure_phase": phase}
    )
    assert result.localization.status is LocalizationStatus.TRIAL_REJECTED
    assert result.localization.diagnostic.kind == "trial_rejected"
    assert result.cascade_result is None and result.energy_accounting == ()
    assert result.final_damage_state == state
    assert result.final_topology_state == registry.initial_state
    assert result.final_snapshot == previous
    assert backend.deleted_bonds == set() and backend.deleted_angles == set()
    assert backend.restore_count >= 1 and backend.closed


def test_trial_restore_failure_is_distinct_and_never_publishes_event() -> None:
    result, backend, *_ = _run_fake(backend_kwargs={"failure_phase": "restore"})
    assert result.localization.status is LocalizationStatus.RESTORE_FAILED
    assert result.localization.diagnostic.kind == "restore_failed"
    assert result.cascade_result is None and result.energy_accounting == ()
    assert backend.closed


def test_live_backend_lower_mismatch_is_rejected_before_any_trial_control() -> None:
    registry = _registry()
    law, field, state = _damage(registry)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    backend.positions[1, 0] += 0.25
    result = QuasiStaticFractureCascade(
        backend, registry, law, field, CascadeBudget(2, 8)
    ).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
        domain_certificate=_certificate(registry),
    )
    assert result.localization.status is LocalizationStatus.LIVE_LOWER_MISMATCH
    assert all(row[0] != "apply_control" for row in backend.commands)
    assert result.cascade_result is None and result.energy_accounting == ()
    assert backend.closed


def test_harmonic_certificate_cannot_bypass_peptide_or_nonmonotone_response() -> None:
    peptide = _registry(peptide=True)
    law, field, state = _damage(peptide, threshold=1.1)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    peptide_backend = AnalyticalLocalizationBackend(peptide)
    previous = _previous_snapshot(peptide_backend, lower, peptide, state)
    peptide_result = QuasiStaticFractureCascade(
        peptide_backend, peptide, law, field, CascadeBudget(1)
    ).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=peptide.initial_state,
        localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
        domain_certificate=_certificate(peptide),
    )
    assert peptide_result.localization.status is LocalizationStatus.DOMAIN_REJECTED
    assert all(row[0] != "apply_control" for row in peptide_backend.commands)

    nonmonotone, nonmonotone_backend, *_ = _run_fake(
        threshold=1.1, backend_kwargs={"nonmonotone_response": True}
    )
    assert nonmonotone.localization.status is LocalizationStatus.DOMAIN_REJECTED
    assert all(row[0] != "apply_control" for row in nonmonotone_backend.commands)


@pytest.mark.parametrize(
    "registry",
    [_bounded_shape_registry(bent=True), _bounded_shape_registry(skew_cell=True)],
    ids=["bent-chain", "skew-cell"],
)
def test_harmonic_monotone_certificate_rejects_uncertified_geometry_before_control(
    registry: TopologyRegistry,
) -> None:
    law, field, state = _damage(registry, threshold=1.1)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    result = QuasiStaticFractureCascade(
        backend, registry, law, field, CascadeBudget(1)
    ).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
        domain_certificate=_certificate(registry),
    )
    assert result.localization.status is LocalizationStatus.DOMAIN_REJECTED
    assert all(row[0] != "apply_control" for row in backend.commands)


def test_harmonic_certificate_uses_angle_order_not_arbitrary_bond_orientation() -> None:
    registry = _folded_orientation_registry()
    law, field, state = _damage(registry, threshold=1.1)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    result = QuasiStaticFractureCascade(
        backend, registry, law, field, CascadeBudget(1)
    ).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
        domain_certificate=_certificate(registry),
    )
    assert result.localization.status is LocalizationStatus.DOMAIN_REJECTED
    assert all(row[0] != "apply_control" for row in backend.commands)


def test_nonlocalized_observable_records_are_explicitly_nonlabels() -> None:
    failed = [
        _run_fake(budget_kwargs={"max_refinements": 0})[0],
        _run_fake(budget_kwargs={"max_solver_trials": 1})[0],
        _run_fake(
            threshold=1.15,
            backend_kwargs={"nonconverged_progress_attempts": {0.1: 3}},
            budget_kwargs={"max_retries_per_trial": 1},
        )[0],
        _run_fake(
            threshold=1.15,
            backend_kwargs={
                "nonconverged_progress_attempts": {0.2: 1},
                "nonconvergence_reason": "max_iterations_or_residual_above_tolerance",
            },
        )[0],
        _run_fake(backend_kwargs={"failure_phase": "apply"})[0],
        _run_fake(backend_kwargs={"failure_phase": "restore"})[0],
        _run_fake(backend_kwargs={"fail_delete": True})[0],
        _run_fake(
            backend_kwargs={"fail_delete": True, "failure_phase": "final_restore"}
        )[0],
        _run_fake(threshold=1.3)[0],
    ]
    for result in failed:
        record = result.as_observable_record()
        assert record["accepted_label"] is False
        assert record["label_eligible"] is False
        assert record["localization_status"] == result.localization.status.value
        assert record["cascade"] is None
        text = repr(record).lower()
        assert "threshold" not in text and "criterion" not in text
        assert "lower_bracket" not in text and "solver_trials" not in text

    accepted, *_ = _run_fake()
    accepted_record = accepted.as_observable_record()
    assert accepted_record["accepted_label"] is True
    assert accepted_record["label_eligible"] is True
    assert accepted_record["localization_status"] == "localized"


def test_nonlinear_peptide_without_per_evaluation_domain_guard_rejects_before_commands() -> None:
    registry = _registry(peptide=True)
    law, field, state = _damage(registry, threshold=1.1)
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    backend.commands.clear()
    certificate = TrialDomainCertificate.unvalidated_nonlinear_endpoint_margin(
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
        registry_id=registry.registry_id,
        physical_bond_ids=("b12", "b23"),
        stated_minimum_margin_nm=0.01,
    )
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(1)).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(8, 10, 0, 0.005, 0.005), domain_certificate=certificate,
    )
    assert result.localization.status is LocalizationStatus.DOMAIN_REJECTED
    assert result.localization.diagnostic.kind == "nonlinear_iteration_domain_unvalidated"
    assert [row[0] for row in backend.commands] == ["close"]
    assert result.cascade_result is None and result.energy_accounting == ()


def test_accounting_replay_rejects_mixed_phase_event_and_reference_records() -> None:
    result, *_ = _run_fake()
    accounting = result.energy_accounting[0]
    assert FractureEnergyAccounting.from_record(accounting.as_record()) == accounting
    record = deepcopy(accounting.as_record())
    record["transition"]["post_event_relaxed"]["reference_state_id"] = "foreign"
    with pytest.raises(FractureExecutionError):
        FractureEnergyAccounting.from_record(record)
    record = deepcopy(accounting.as_record())
    record["transition"]["material_event"]["event_source"] = "prescribed_intervention"
    with pytest.raises((FractureExecutionError, ValueError)):
        FractureEnergyAccounting.from_record(record)


def test_localization_records_are_hash_bound_strict_and_deeply_immutable() -> None:
    result, *_ = _run_fake()
    assert LocalizedCascadeResult.from_record(result.as_record()) == result
    assert EventLocalizationRecord.from_record(result.localization.as_record()) == result.localization
    diagnostic = LocalizationDiagnostic.create("fixture", "bounded")
    assert LocalizationDiagnostic.from_record(diagnostic.as_record()).kind == "fixture"
    with pytest.raises(TypeError):
        result.privileged_reference_metadata["threshold_field"] = {}  # type: ignore[index]
    tampered = deepcopy(result.as_record())
    tampered["localization"]["upper_bracket_control"]["lambda_load"] += 0.01
    with pytest.raises(FractureExecutionError):
        LocalizedCascadeResult.from_record(tampered)
    with pytest.raises(FractureExecutionError):
        LocalizationBudget.from_record({**result.localization.budget.as_record(), "unexpected": True})


def test_upper_incremental_F_must_map_exact_original_lower_before_commands() -> None:
    registry = _registry()
    law, field, state = _damage(registry)
    lower = _control(0.0, 0.0, step_index=0)
    valid_upper = _control(0.2, 0.2, step_index=1)
    upper = QuasiStaticControlStep(
        control_id="forged-incremental-F", step_index=valid_upper.step_index,
        control_kind=valid_upper.control_kind, loading_mode=valid_upper.loading_mode,
        axes=valid_upper.axes, reference_state_id=valid_upper.reference_state_id,
        lambda_load=valid_upper.lambda_load,
        load_coordinate_unit=valid_upper.load_coordinate_unit,
        progress_unit=valid_upper.progress_unit,
        path_progress=valid_upper.path_progress,
        progress_increment=valid_upper.progress_increment,
        absolute_deformation_gradient=valid_upper.absolute_deformation_gradient,
        incremental_deformation_gradient=np.eye(2),
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
    )
    backend = AnalyticalLocalizationBackend(registry)
    previous = _previous_snapshot(backend, lower, registry, state)
    with pytest.raises(FractureExecutionError, match="incremental F"):
        QuasiStaticFractureCascade(
            backend, registry, law, field, CascadeBudget(2, 8)
        ).run_localized_step(
            lower_control=lower, upper_control=upper,
            previous_accepted=previous, damage_state=state,
            topology_state=registry.initial_state,
            localization_budget=LocalizationBudget(8, 12, 0, 0.005, 0.005),
            domain_certificate=_certificate(registry),
        )
    assert all(row[0] != "apply_control" for row in backend.commands)
    assert backend.closed


def test_localized_result_binds_failure_and_success_to_original_lower_ids() -> None:
    failed, _backend, registry, *_ = _run_fake(
        budget_kwargs={"max_refinements": 0}
    )
    forged_topology = registry.apply_plan(
        registry.initial_state,
        registry.plan_bond_removal(registry.initial_state, "b12"),
    )
    with pytest.raises(FractureExecutionError, match="provenance|final snapshot"):
        LocalizedCascadeResult.create(
            localization=failed.localization, cascade_result=None,
            energy_accounting=(), final_damage_state=failed.final_damage_state,
            final_topology_state=forged_topology,
            final_snapshot=failed.final_snapshot,
            privileged_reference_metadata=failed.privileged_reference_metadata,
            backend_closed=True,
        )


def _localization_create_kwargs(loc) -> dict[str, object]:
    return {
        "status": loc.status, "budget": loc.budget,
        "domain_certificate": loc.domain_certificate,
        "initial_lower_control": loc.initial_lower_control,
        "initial_upper_control": loc.initial_upper_control,
        "lower_bracket_control": loc.lower_bracket_control,
        "upper_bracket_control": loc.upper_bracket_control,
        "localized_control": loc.localized_control,
        "solver_trials": loc.solver_trials, "refinements": loc.refinements,
        "previous_accepted_observation_id": loc.previous_accepted_observation_id,
        "topology_state_id": loc.topology_state_id,
        "damage_state_id": loc.damage_state_id, "diagnostic": None,
    }


@pytest.mark.parametrize(
    "target,step_source",
    [
        ("initial_upper_control", "far_future"),
        ("initial_upper_control", "not_after_lower"),
        ("lower_bracket_control", "far_future"),
        ("upper_bracket_control", "far_future"),
    ],
)
def test_localization_replay_binds_one_step_lineage(
    target: str, step_source: str
) -> None:
    success, *_ = _run_fake()
    loc = success.localization
    common = _localization_create_kwargs(loc)
    source = common[target]
    assert isinstance(source, QuasiStaticControlStep)
    step_index = (
        loc.initial_lower_control.step_index
        if step_source == "not_after_lower"
        else 999
    )
    common[target] = _control_with_step(source, step_index)
    with pytest.raises(FractureExecutionError, match="step"):
        EventLocalizationRecord.create(**common, retries=loc.retries)


def test_localization_replay_binds_retry_count_to_solver_trials() -> None:
    success, *_ = _run_fake()
    loc = success.localization
    common = _localization_create_kwargs(loc)
    with pytest.raises(FractureExecutionError, match="retries"):
        EventLocalizationRecord.create(**common, retries=loc.solver_trials + 1)


def test_localized_and_upper_no_cross_records_require_a_solver_trial() -> None:
    localized, *_ = _run_fake()
    loc = localized.localization
    common = _localization_create_kwargs(loc)
    with pytest.raises(FractureExecutionError, match="solver trial"):
        EventLocalizationRecord.create(
            **{**common, "solver_trials": 0}, retries=0
        )
    noncrossing, *_ = _run_fake(threshold=1.3)
    loc = noncrossing.localization
    common = _localization_create_kwargs(loc)
    common["diagnostic"] = loc.diagnostic
    with pytest.raises(FractureExecutionError, match="solver trial"):
        EventLocalizationRecord.create(
            **{**common, "solver_trials": 0}, retries=0
        )


def test_exhausted_status_records_bind_exact_budget_boundary() -> None:
    refinement, *_ = _run_fake(budget_kwargs={"max_refinements": 0})
    loc = refinement.localization
    common = _localization_create_kwargs(loc)
    common["diagnostic"] = loc.diagnostic
    with pytest.raises(FractureExecutionError, match="refinement budget"):
        EventLocalizationRecord.create(
            **{**common, "budget": LocalizationBudget(1, 16, 1, 0.003125, 0.003125)},
            retries=loc.retries,
        )
    solver, *_ = _run_fake(budget_kwargs={"max_solver_trials": 1})
    loc = solver.localization
    common = _localization_create_kwargs(loc)
    common["diagnostic"] = loc.diagnostic
    with pytest.raises(FractureExecutionError, match="solver budget"):
        EventLocalizationRecord.create(
            **{**common, "budget": LocalizationBudget(12, 2, 1, 0.003125, 0.003125)},
            retries=loc.retries,
        )


@pytest.mark.parametrize("status_kind", ["solver", "refinement", "retry"])
def test_budget_terminal_records_reject_unreachable_counts_or_stale_details(
    status_kind: str,
) -> None:
    if status_kind == "solver":
        result, *_ = _run_fake(budget_kwargs={"max_solver_trials": 1})
        loc = result.localization
        common = _localization_create_kwargs(loc)
        common["diagnostic"] = loc.diagnostic
        common["budget"] = LocalizationBudget(12, 10, 1, 0.003125, 0.003125)
        common["solver_trials"] = 10
        expectation = "reachable|diagnostic"
    elif status_kind == "refinement":
        result, *_ = _run_fake(budget_kwargs={"max_refinements": 0})
        loc = result.localization
        common = _localization_create_kwargs(loc)
        common["diagnostic"] = loc.diagnostic
        common["budget"] = LocalizationBudget(1, 16, 1, 0.003125, 0.003125)
        common["refinements"] = 1
        common["solver_trials"] = 2
        expectation = "diagnostic|refinement"
    else:
        result, *_ = _run_fake(
            threshold=1.15,
            backend_kwargs={"nonconverged_progress_attempts": {0.1: 3}},
            budget_kwargs={"max_retries_per_trial": 1},
        )
        loc = result.localization
        common = _localization_create_kwargs(loc)
        common["diagnostic"] = LocalizationDiagnostic.create(
            "trial_nonconvergence", "max_retries_per_trial=0"
        )
        expectation = "diagnostic|retry"
    with pytest.raises(FractureExecutionError, match=expectation):
        EventLocalizationRecord.create(**common, retries=loc.retries)


def test_executed_localization_record_rejects_nonlinear_unvalidated_certificate() -> None:
    success, _backend, registry, *_ = _run_fake()
    loc = success.localization
    nonlinear = TrialDomainCertificate.unvalidated_nonlinear_endpoint_margin(
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
        registry_id=registry.registry_id,
        physical_bond_ids=("b12", "b23"),
        stated_minimum_margin_nm=0.01,
    )
    common = _localization_create_kwargs(loc)
    common["domain_certificate"] = nonlinear
    with pytest.raises(FractureExecutionError, match="executable|certificate"):
        EventLocalizationRecord.create(**common, retries=loc.retries)


def test_localized_result_rejects_nonlinear_certificate_swap() -> None:
    success, _backend, registry, *_ = _run_fake()
    loc = success.localization
    nonlinear = TrialDomainCertificate.unvalidated_nonlinear_endpoint_margin(
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
        registry_id=registry.registry_id,
        physical_bond_ids=("b12", "b23"),
        stated_minimum_margin_nm=0.01,
    )
    record = deepcopy(success.as_record())
    localization = record["localization"]
    localization["domain_certificate"] = nonlinear.as_record()
    localization_body = {
        key: value for key, value in localization.items()
        if key != "localization_id"
    }
    localization["localization_id"] = _record_hash(localization_body)
    result_body = {key: value for key, value in record.items() if key != "result_id"}
    record["result_id"] = _record_hash(result_body)
    with pytest.raises(FractureExecutionError, match="executable|certificate"):
        LocalizedCascadeResult.from_record(record)


@pytest.mark.parametrize(
    ("status", "kind", "detail"),
    [
        ("event_budget_exhausted", "event_budget_exhausted", "max_events=1"),
        ("rolled_back", "rolled_back", "post-event transaction failed"),
    ],
)
def test_localized_result_rejects_nonstable_cascade_status(
    status: str, kind: str, detail: str
) -> None:
    success, *_ = _run_fake()
    record = deepcopy(success.as_record())
    cascade = record["cascade_result"]
    assert isinstance(cascade, dict)
    cascade["status"] = status
    cascade["diagnostic"] = CascadeDiagnostic.create(kind, detail).as_record()
    cascade["result_id"] = _record_hash(
        {key: value for key, value in cascade.items() if key != "result_id"}
    )
    record["result_id"] = _record_hash(
        {key: value for key, value in record.items() if key != "result_id"}
    )
    with pytest.raises(FractureExecutionError, match="stable cascade"):
        LocalizedCascadeResult.from_record(record)


def test_localized_result_binds_complete_original_lower_control() -> None:
    success, *_ = _run_fake()
    loc = success.localization
    common = _localization_create_kwargs(loc)
    lower = loc.initial_lower_control
    forged_lower = QuasiStaticControlStep(
        control_id="forged-lower-control", step_index=lower.step_index,
        control_kind=lower.control_kind, loading_mode=lower.loading_mode,
        axes=lower.axes, reference_state_id=lower.reference_state_id,
        lambda_load=lower.lambda_load,
        load_coordinate_unit=lower.load_coordinate_unit,
        progress_unit=lower.progress_unit, path_progress=lower.path_progress,
        progress_increment=lower.progress_increment,
        absolute_deformation_gradient=lower.absolute_deformation_gradient,
        incremental_deformation_gradient=lower.incremental_deformation_gradient,
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
    )
    forged_control_loc = EventLocalizationRecord.create(
        **{**common, "initial_lower_control": forged_lower}, retries=loc.retries
    )
    with pytest.raises(FractureExecutionError, match="lower control|accounting bindings"):
        LocalizedCascadeResult.create(
            localization=forged_control_loc,
            cascade_result=success.cascade_result,
            energy_accounting=success.energy_accounting,
            final_damage_state=success.final_damage_state,
            final_topology_state=success.final_topology_state,
            final_snapshot=success.final_snapshot,
            privileged_reference_metadata=success.privileged_reference_metadata,
            backend_closed=True,
        )


def test_localized_result_binds_domain_certificate_to_privileged_registry() -> None:
    success, *_ = _run_fake()
    loc = success.localization
    common = _localization_create_kwargs(loc)
    foreign_registry_id = "sha256:" + "f" * 64
    foreign_certificate = TrialDomainCertificate.bounded_harmonic_fixture(
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
        registry_id=foreign_registry_id,
        physical_bond_ids=("b12", "b23"),
    )
    forged_certificate_loc = EventLocalizationRecord.create(
        **{**common, "domain_certificate": foreign_certificate},
        retries=loc.retries,
    )
    with pytest.raises(FractureExecutionError, match="certificate|registry"):
        LocalizedCascadeResult.create(
            localization=forged_certificate_loc,
            cascade_result=success.cascade_result,
            energy_accounting=success.energy_accounting,
            final_damage_state=success.final_damage_state,
            final_topology_state=success.final_topology_state,
            final_snapshot=success.final_snapshot,
            privileged_reference_metadata=success.privileged_reference_metadata,
            backend_closed=True,
        )


def test_success_result_binds_lower_observation_damage_and_topology_ids() -> None:
    success, *_ = _run_fake()
    loc = success.localization
    forged_localization = EventLocalizationRecord.create(
        status=loc.status, budget=loc.budget,
        domain_certificate=loc.domain_certificate,
        initial_lower_control=loc.initial_lower_control,
        initial_upper_control=loc.initial_upper_control,
        lower_bracket_control=loc.lower_bracket_control,
        upper_bracket_control=loc.upper_bracket_control,
        localized_control=loc.localized_control,
        solver_trials=loc.solver_trials, refinements=loc.refinements,
        retries=loc.retries,
        previous_accepted_observation_id=success.final_snapshot.observation_id,
        topology_state_id=success.final_topology_state.topology_state_id,
        damage_state_id=success.final_damage_state.state_id,
        diagnostic=None,
    )
    with pytest.raises(FractureExecutionError, match="accounting bindings"):
        LocalizedCascadeResult.create(
            localization=forged_localization,
            cascade_result=success.cascade_result,
            energy_accounting=success.energy_accounting,
            final_damage_state=success.final_damage_state,
            final_topology_state=success.final_topology_state,
            final_snapshot=success.final_snapshot,
            privileged_reference_metadata=success.privileged_reference_metadata,
            backend_closed=True,
        )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, True])
def test_localization_budget_rejects_nonfinite_negative_or_boolean_tolerance(bad) -> None:
    with pytest.raises(FractureExecutionError):
        LocalizationBudget(4, 5, 1, bad, 0.01)


def test_real_serial_lammps_localization_and_raw_phase_accounting(
    tmp_path: Path, record_property: Any
) -> None:
    pytest.importorskip("lammps")
    registry = _periodic_registry()
    backend = LammpsFractureBackend.tiny_harmonic_fixture(registry=registry, profile=PROFILE, work_directory=tmp_path)
    law = DamageLaw(
        law_id="p0204-real-extension-v1", law_kind="deterministic_threshold",
        criterion="bond_extension_ratio", criterion_unit="dimensionless", base_threshold=1.1,
        distribution=None, predictor_visibility="hidden_from_predictor",
        physics_profile_id=PROFILE.profile_id, physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
    )
    field = materialize_thresholds(law, ("b12", "b23"))
    state = initialize_damage_state(law, field, [CriterionObservation(bond_id, law.criterion, law.criterion_unit, value) for bond_id, value in backend.fixed_reference_criterion_values.items()])
    lower = _control(0.0, 0.0, step_index=0)
    upper = _control(0.2, 0.2, step_index=1)
    previous = backend.observe_restored(control=lower, topology_state=registry.initial_state, damage_state=state)
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2, 8)).run_localized_step(
        lower_control=lower, upper_control=upper, previous_accepted=previous,
        damage_state=state, topology_state=registry.initial_state,
        localization_budget=LocalizationBudget(9, 12, 0, 0.002, 0.002), domain_certificate=_certificate(registry),
    )
    assert result.localization.status is LocalizationStatus.LOCALIZED
    event = result.cascade_result.transitions[0].material_event
    assert 0.1 <= event.load_coordinate <= 0.102
    accounting = result.energy_accounting[0]
    energies = accounting.phase_energies_pN_nm
    assert energies["U_after_control_before_relax"] == pytest.approx(energies["U_pre_event_relaxed"], rel=0.0, abs=1.0e-8)
    assert energies["U_post_delete_unrelaxed"] == pytest.approx(0.5 * energies["U_pre_event_relaxed"], rel=0.0, abs=1.0e-8)
    assert energies["U_post_event_relaxed"] == pytest.approx(0.0, abs=1.0e-8)
    assert accounting.held_control_boundary_work_pN_nm == 0.0
    expected_alive = tuple(
        bond_id for bond_id in ("b12", "b23")
        if bond_id != event.physical_bond_id
    )
    assert result.cascade_result.final_snapshot.topology.alive_bond_ids == expected_alive
    assert result.cascade_result.final_snapshot.topology.alive_angle_ids == ()
    assert result.final_damage_state.rupture_mask[event.physical_bond_id]
    assert backend.closed and backend.temporary_groups_live == ()
    write_restart_count = sum(
        command.startswith("write_restart ") for command in backend.command_trace
    )
    read_restart_count = sum(
        command.startswith("read_restart ") for command in backend.command_trace
    )
    assert write_restart_count >= 2
    assert read_restart_count >= 2
    topology_audit = backend.last_topology_audit
    assert topology_audit["counts"] == {"atoms": 3, "bonds": 1, "angles": 0}
    record_property(
        "p0204_evidence_json",
        json.dumps(
            {
                "fixed_reference_criteria": dict(backend.fixed_reference_criterion_values),
                "fixed_reference_convergence": backend.fixed_reference_convergence.as_record(),
                "initial_lower": {
                    "lambda_load": lower.lambda_load,
                    "path_progress": lower.path_progress,
                },
                "final_bracket": {
                    "lower_lambda": result.localization.lower_bracket_control.lambda_load,
                    "lower_progress": result.localization.lower_bracket_control.path_progress,
                    "upper_lambda": result.localization.upper_bracket_control.lambda_load,
                    "upper_progress": result.localization.upper_bracket_control.path_progress,
                },
                "event": {
                    "bond_id": event.physical_bond_id,
                    "lambda_load": event.load_coordinate,
                    "path_progress": event.path_progress,
                },
                "final_topology": {
                    "alive_bond_ids": list(result.final_topology_state.alive_bond_ids),
                    "alive_angle_ids": list(result.final_topology_state.alive_angle_ids),
                    "components": [list(row) for row in result.final_topology_state.components],
                },
                "phase_energies_pN_nm": dict(energies),
                "equations_pN_nm": {
                    "control_input": accounting.fixed_topology_conservative_loading_work_pN_nm,
                    "equilibrium_stored_change": accounting.equilibrium_stored_energy_change_pN_nm,
                    "pre_event_relaxation_loss": accounting.pre_event_relaxation_loss_pN_nm,
                    "control_partition_residual": (
                        accounting.fixed_topology_conservative_loading_work_pN_nm
                        - accounting.equilibrium_stored_energy_change_pN_nm
                        - accounting.pre_event_relaxation_loss_pN_nm
                    ),
                    "signed_deletion_change": accounting.same_coordinate_deletion_energy_change_pN_nm,
                    "held_control_boundary_work": accounting.held_control_boundary_work_pN_nm,
                    "post_delete_relaxation_loss": accounting.post_delete_relaxation_loss_pN_nm,
                },
                "transaction": {
                    "write_restart_count": write_restart_count,
                    "read_restart_count": read_restart_count,
                    "last_topology_counts": dict(topology_audit["counts"]),
                    "temporary_groups_live": list(backend.temporary_groups_live),
                    "backend_closed": backend.closed,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
