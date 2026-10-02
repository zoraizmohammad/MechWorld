from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
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
    ExcludedEventRecord,
    apply_excluded_event,
    initialize_damage_state,
    materialize_thresholds,
)
from pgworld.simulation.controls import AxisFrame, QuasiStaticControlStep
from pgworld.simulation.fracture import (
    BackendObservation,
    CascadeBudget,
    CascadeDiagnostic,
    CascadeResult,
    CascadeStatus,
    CascadeTransitionEnvelope,
    ConvergenceDiagnostics,
    FractureExecutionError,
    LammpsFractureBackend,
    QuasiStaticFractureCascade,
)
from pgworld.simulation.topology import (
    AngleTopology,
    BondTopology,
    Cell2D,
    NodeTopology,
    TopologyRegistry,
)


PROFILE = load_physics_profile("reviewed_physics_provisional_v0")
REFERENCE_ID = "fixture-fixed-reference"


def _registry() -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 5))
    positions = {"n1": (1.0, 2.0), "n2": (2.0, 2.0), "n3": (3.0, 2.0), "n4": (9.0, 8.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (0, 0), (1.0, 0.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.0, 0.0)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _periodic_crossing_registry() -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    positions = {"n1": (11.00, 2.0), "n2": (0.03, 2.0), "n3": (1.06, 2.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (1, 0), (1.03, 0.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.03, 0.0)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _angled_crossing_registry() -> TopologyRegistry:
    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 4))
    positions = {"n1": (11.00, 2.0), "n2": (0.03, 2.0), "n3": (1.06, 3.0)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (1, 0), (1.03, 0.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (1.03, 1.0)),
    )
    angles = (AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),)
    return TopologyRegistry(cell, nodes, positions, bonds, angles)


def _damage(registry: TopologyRegistry):
    law = DamageLaw(
        law_id="fixture-extension-v1",
        law_kind="deterministic_threshold",
        criterion="bond_extension_ratio",
        criterion_unit="dimensionless",
        base_threshold=1.1,
        distribution=None,
        predictor_visibility="hidden_from_predictor",
        physics_profile_id=PROFILE.profile_id,
        physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID,
    )
    field = materialize_thresholds(law, [bond.stable_bond_id for bond in registry.bonds])
    state = initialize_damage_state(
        law,
        field,
        [CriterionObservation(bond.stable_bond_id, law.criterion, law.criterion_unit, 1.0) for bond in registry.bonds],
    )
    return law, field, state


def _control() -> QuasiStaticControlStep:
    return QuasiStaticControlStep(
        control_id="axial:000001",
        step_index=1,
        control_kind="deformation_gradient",
        loading_mode="axial",
        axes=AxisFrame(),
        reference_state_id=REFERENCE_ID,
        lambda_load=0.2,
        load_coordinate_unit="dimensionless",
        progress_unit="dimensionless",
        path_progress=0.2,
        progress_increment=0.2,
        absolute_deformation_gradient=((1.2, 0.0), (0.0, 1.0)),
        incremental_deformation_gradient=((1.2, 0.0), (0.0, 1.0)),
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
    )


class FakeBackend:
    def __init__(self, registry: TopologyRegistry, values: list[dict[str, float]], *, fail_post=False, fail_at: str | None = None):
        self.registry = registry
        self.values = iter(values)
        self.fail_post = fail_post
        self.fail_at = fail_at
        self.commands: list[tuple[Any, ...]] = []
        self.closed = False
        self.deleted_bonds: set[str] = set()
        self.deleted_angles: set[str] = set()
        self.restore_count = 0
        self._last_values = {"b12": 1.0, "b23": 1.0}
        self._positions = np.vstack([
            registry.source_wrapped_positions_nm[node.stable_node_id]
            for node in sorted(registry.nodes, key=lambda item: item.solver_atom_id)
        ])

    def _observation(self, *, phase, control, topology_state, damage_state, converged):
        node_row = {node.stable_node_id: index for index, node in enumerate(sorted(self.registry.nodes, key=lambda item: item.solver_atom_id))}
        if phase != "post_delete_unrelaxed":
            if "b12" in topology_state.alive_bond_ids:
                self._positions[node_row["n2"]] = self._positions[node_row["n1"]] + (self._last_values["b12"], 0.0)
            if "b23" in topology_state.alive_bond_ids:
                self._positions[node_row["n3"]] = self._positions[node_row["n2"]] + (self._last_values["b23"], 0.0)
        criteria = {}
        for bond_id in topology_state.alive_bond_ids:
            bond = self.registry.bond(bond_id)
            displacement = self._positions[node_row[bond.node_j]] - self._positions[node_row[bond.node_i]]
            criteria[bond_id] = float(np.linalg.norm(displacement)) / float(np.linalg.norm(bond.source_displacement_nm))
        absolute = np.asarray(control.absolute_deformation_gradient, dtype=float)
        controlled_cell = Cell2D(absolute @ self.registry.cell.matrix_nm, self.registry.cell.origin_nm, self.registry.cell.periodic)
        return BackendObservation.from_solver_rows(
            phase=phase, registry=self.registry, topology_state=topology_state,
            solver_atom_ids=tuple(node.solver_atom_id for node in sorted(self.registry.nodes, key=lambda item: item.solver_atom_id)),
            positions_nm=self._positions, forces_pN=np.zeros_like(self._positions), criterion_values=criteria,
            criterion_unit="dimensionless", cell=controlled_cell,
            total_tension_pN_per_nm=np.zeros((2, 2)), reference_total_tension_pN_per_nm=np.zeros((2, 2)),
            raw_energies_pN_nm={"pe": 0.0, "ebond": 0.0, "eangle": 0.0},
            convergence=ConvergenceDiagnostics.successful(0.0, 1, 100) if converged else ConvergenceDiagnostics.rejected("phase_not_relaxed", 1.0, 0, 100),
            control=control, profile_id=PROFILE.profile_id, profile_hash=PROFILE.canonical_hash,
            reference_state_id=REFERENCE_ID, damage_state=damage_state,
        )

    def apply_control(self, control):
        if self.fail_at == "apply": raise FractureExecutionError("injected apply failure")
        self.commands.append(("control", control.control_id))

    def relax_and_observe(self, *, phase, control, topology_state, damage_state):
        self.commands.append(("relax", phase))
        if self.fail_at == f"relax:{phase}": raise FractureExecutionError("injected relax failure")
        if phase == "post_event_relaxed" and self.fail_post:
            raise FractureExecutionError("injected post-relax failure")
        try:
            self._last_values = next(self.values)
        except StopIteration:
            pass
        return self._observation(phase=phase, control=control, topology_state=topology_state, damage_state=damage_state, converged=True)

    def observe_unrelaxed(self, *, control, topology_state, damage_state):
        if self.fail_at == "observe": raise FractureExecutionError("injected observation failure")
        self.commands.append(("observe", "post_delete_unrelaxed"))
        return self._observation(phase="post_delete_unrelaxed", control=control, topology_state=topology_state, damage_state=damage_state, converged=False)

    def delete_angle(self, angle):
        self.commands.append(("delete_angle", angle.stable_angle_id))
        self.deleted_angles.add(angle.stable_angle_id)
        if self.fail_at == "delete_angle": raise FractureExecutionError("injected angle failure")

    def delete_bond(self, bond):
        if self.fail_at == "delete_bond": raise FractureExecutionError("injected bond failure")
        self.commands.append(("delete_bond", bond.stable_bond_id))
        self.deleted_bonds.add(bond.stable_bond_id)

    def audit_topology(self, topology_state):
        if self.fail_at == "audit": raise FractureExecutionError("injected audit failure")
        if self.fail_at == "audit_post" and topology_state != self.registry.initial_state:
            raise FractureExecutionError("injected post-mutation audit failure")
        self.commands.append(("audit", topology_state.topology_state_id))
        assert self.deleted_bonds == set(self.registry.initial_state.alive_bond_ids) - set(topology_state.alive_bond_ids)
        assert self.deleted_angles == set(self.registry.initial_state.alive_angle_ids) - set(topology_state.alive_angle_ids)

    def checkpoint(self):
        if self.fail_at == "checkpoint": raise FractureExecutionError("injected checkpoint failure")
        return (set(self.deleted_bonds), set(self.deleted_angles))

    def restore(self, checkpoint):
        self.restore_count += 1
        self.deleted_bonds, self.deleted_angles = map(set, checkpoint)
        self.commands.append(("restore",))
        if self.fail_at == "restore": raise FractureExecutionError("injected restore failure")

    def observe_restored(self, *, control, topology_state, damage_state):
        observation = self._observation(phase="pre_delete_relaxed", control=control, topology_state=topology_state, damage_state=damage_state, converged=True)
        if self.fail_at == "restore_corrupt_mechanics":
            body = observation._constructor_body(); body["positions_nm"] = np.array(observation.positions_nm, copy=True)
            body["positions_nm"][0, 0] += 0.25
            return BackendObservation._create(**body)
        return observation

    def close(self):
        if self.fail_at == "close": raise FractureExecutionError("injected close failure")
        self.closed = True


def test_transactional_cascade_deletes_exact_dependencies_reassesses_and_retains_fragments() -> None:
    registry = _registry()
    law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.30, "b23": 1.25}, {"b23": 1.25}, {}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(4)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )

    assert result.status is CascadeStatus.STABLE
    assert [event.material_event.physical_bond_id for event in result.transitions] == ["b12", "b23"]
    assert [row[:2] for row in backend.commands if row[0].startswith("delete")] == [
        ("delete_angle", "a123"), ("delete_bond", "b12"), ("delete_bond", "b23")
    ]
    assert result.final_snapshot.topology.components == (("n1",), ("n2",), ("n3",), ("n4",))
    assert result.transitions[0].pre_delete_raw.phase == "pre_delete_relaxed"
    assert result.transitions[0].post_delete_unrelaxed.phase == "post_delete_unrelaxed"
    assert result.transitions[0].post_event_relaxed.phase == "post_event_relaxed"
    assert result.transitions[0].as_observable_record().get("threshold_realization_id") is None
    assert "privileged_reference_metadata" not in result.transitions[0].as_observable_record()
    assert backend.closed is True


def test_post_relax_failure_rolls_back_without_committing_event() -> None:
    registry = _registry()
    law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.30, "b23": 1.0}], fail_post=True)
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.ROLLED_BACK
    assert result.transitions == ()
    assert result.damage_state == damage
    assert result.topology_state == registry.initial_state
    assert result.diagnostic is not None and result.diagnostic.counts_as_physical_failure is False
    assert backend.restore_count == 1 and backend.closed is True


def test_budget_exhaustion_is_explicit_and_does_not_accept_a_stale_candidate() -> None:
    registry = _registry()
    law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.30, "b23": 1.25}, {"b23": 1.25}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(1)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.EVENT_BUDGET_EXHAUSTED
    assert len(result.transitions) == 1
    assert result.transitions[0].material_event.physical_bond_id == "b12"
    assert result.diagnostic is not None and result.diagnostic.counts_as_physical_failure is False


def test_pressure_and_general_deformation_fail_before_backend_command() -> None:
    registry = _registry()
    law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [])
    pressure = replace(
        _control(),
        control_kind="membrane_tension_target",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=np.eye(2),
        incremental_tension_target_pN_per_nm=np.eye(2),
        pressure_derivation={"fixture": True},
    )
    with pytest.raises(FractureExecutionError, match="unsupported"):
        QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(1)).run_step(
            control=pressure, damage_state=damage, topology_state=registry.initial_state
        )
    assert backend.commands == []
    assert backend.closed is True

    general = replace(
        _control(),
        absolute_deformation_gradient=((1.0, 0.2), (0.1, 1.0)),
        incremental_deformation_gradient=((1.0, 0.2), (0.1, 1.0)),
    )
    backend = FakeBackend(registry, [])
    with pytest.raises(FractureExecutionError, match="restricted diagonal"):
        QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(1)).run_step(
            control=general, damage_state=damage, topology_state=registry.initial_state
        )
    assert backend.commands == []
    assert backend.closed is True


def test_real_serial_lammps_removes_only_dependent_angle_and_exact_bond(tmp_path: Path) -> None:
    registry = _registry()
    backend = LammpsFractureBackend.tiny_harmonic_fixture(
        registry=registry,
        profile=PROFILE,
        work_directory=tmp_path,
    )
    try:
        before = backend.topology_counts()
        backend.delete_angle(registry.angle("a123"))
        backend.delete_bond(registry.bond("b12"))
        after = backend.topology_counts()
        assert before == {"atoms": 4, "bonds": 2, "angles": 1}
        assert after == {"atoms": 4, "bonds": 1, "angles": 0}
        assert backend.alive_solver_bonds() == ((1, 2, 3),)
    finally:
        backend.close()
    assert backend.closed is True


@pytest.mark.parametrize(
    "failure_point",
    ["apply", "checkpoint", "delete_angle", "delete_bond", "observe", "audit_post", "relax:post_event_relaxed"],
)
def test_backend_phase_failures_close_and_partial_mutation_rolls_back(failure_point: str) -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}], fail_at=failure_point)
    if failure_point in {"apply", "checkpoint"}:
        with pytest.raises(FractureExecutionError):
            QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
                control=_control(), damage_state=damage, topology_state=registry.initial_state
            )
    else:
        result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=damage, topology_state=registry.initial_state
        )
        assert result.status is CascadeStatus.ROLLED_BACK
        assert result.transitions == ()
        assert result.damage_state == damage
        assert result.topology_state == registry.initial_state
        assert backend.restore_count == 1
    assert backend.closed is True


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_walk_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value), set())
    return set()


def _plain_boundary(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_boundary(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_boundary(item) for item in value]
    return value


def test_observable_pre_event_record_recursively_excludes_privileged_and_future_information() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    observed = result.transitions[0].as_observable_record()
    forbidden = {
        "threshold_realization_id", "material_disorder_seed", "thresholds",
        "privileged_reference_metadata", "event_id", "candidate_id", "assessment_id",
        "post_delete_unrelaxed", "post_event_relaxed", "future_state", "material_event",
    }
    assert not (_walk_keys(observed) & forbidden)
    assert set(observed) == {"schema_version", "pre_event_observable_state"}
    serialized = json.dumps(observed, sort_keys=True)
    transition = result.transitions[0]
    for forbidden_value in (
        field.realization_id,
        transition.material_event.event_id,
        transition.material_event.candidate_id,
        transition.material_event.assessment_id,
    ):
        assert forbidden_value not in serialized
    assert set(observed["pre_event_observable_state"]) == {
        "phase", "control", "profile", "topology", "damage_masks", "mechanics",
        "physical_time", "physical_time_valid",
    }


def test_backend_observation_copies_and_remaps_solver_rows_by_atom_tag() -> None:
    registry = _registry(); control = _control(); _, _, damage = _damage(registry)
    positions = np.array([[3.0, 2.0], [1.0, 2.0], [9.0, 8.0], [2.0, 2.0]])
    forces = np.array([[30.0, 0.0], [10.0, 0.0], [40.0, 0.0], [20.0, 0.0]])
    observation = BackendObservation.from_solver_rows(
        phase="pre_delete_relaxed", registry=registry, topology_state=registry.initial_state,
        solver_atom_ids=(3, 1, 4, 2), positions_nm=positions, forces_pN=forces,
        criterion_values={"b12": 1.0, "b23": 1.0}, criterion_unit="dimensionless",
        cell=registry.cell, total_tension_pN_per_nm=((1.0, 0.0), (0.0, 2.0)),
        reference_total_tension_pN_per_nm=((0.5, 0.0), (0.0, 1.0)),
        raw_energies_pN_nm={"pe": 2.0, "ebond": 2.0, "eangle": 0.0},
        convergence=ConvergenceDiagnostics.successful(1e-9, 10, 100), control=control,
        profile_id=PROFILE.profile_id, profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID, damage_state=damage,
    )
    positions[0, 0] = 999.0; forces[0, 0] = 999.0
    assert observation.solver_atom_ids == (1, 2, 3, 4)
    assert observation.positions_nm[:, 0].tolist() == [1.0, 2.0, 3.0, 9.0]
    assert observation.forces_pN[:, 0].tolist() == [10.0, 20.0, 30.0, 40.0]
    with pytest.raises(ValueError): observation.positions_nm[0, 0] = 0.0
    assert BackendObservation.from_record(observation.as_record()) == observation


def test_observation_constructor_rejects_missing_damage_and_explicit_empty_offset_or_boundary_mappings() -> None:
    registry = _registry(); control = _control(); _, _, damage = _damage(registry)
    common = dict(
        phase="pre_delete_relaxed", registry=registry, topology_state=registry.initial_state,
        solver_atom_ids=(1, 2, 3, 4),
        positions_nm=np.vstack([registry.source_wrapped_positions_nm[f"n{index}"] for index in range(1, 5)]),
        forces_pN=np.zeros((4, 2)), criterion_values={"b12": 1.0, "b23": 1.0}, criterion_unit="dimensionless",
        cell=Cell2D(((14.4, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True)),
        total_tension_pN_per_nm=np.zeros((2, 2)), reference_total_tension_pN_per_nm=np.zeros((2, 2)),
        raw_energies_pN_nm={"pe": 0.0, "ebond": 0.0, "eangle": 0.0},
        convergence=ConvergenceDiagnostics.successful(0.0, 1, 100), control=control,
        profile_id=PROFILE.profile_id, profile_hash=PROFILE.canonical_hash, reference_state_id=REFERENCE_ID,
    )
    with pytest.raises(FractureExecutionError, match="DamageState"):
        BackendObservation.from_solver_rows(**common)
    with pytest.raises(FractureExecutionError, match="offset"):
        BackendObservation.from_solver_rows(**common, damage_state=damage, current_edge_image_offsets_n_ij={})
    with pytest.raises(FractureExecutionError, match="boundary"):
        BackendObservation.from_solver_rows(**common, damage_state=damage, boundary_conditions={})


def test_nonconverged_normal_return_is_diagnostic_not_rupture_or_instability() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}])
    original = backend.relax_and_observe
    def nonconverged(**kwargs):
        observation = original(**kwargs)
        body = observation._constructor_body()
        body["convergence"] = ConvergenceDiagnostics.rejected("max_iterations", 1e-2, 100, 100)
        return BackendObservation._create(**body)
    backend.relax_and_observe = nonconverged
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.REJECTED_NONCONVERGENCE
    assert result.transitions == ()
    assert result.diagnostic.counts_as_physical_failure is False
    assert result.diagnostic.counts_as_mechanical_instability is False


def test_initial_violation_no_candidate_and_prescribed_removal_do_not_become_material_events() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    invalid = initialize_damage_state(
        law, field,
        [CriterionObservation("b12", law.criterion, law.criterion_unit, 1.2), CriterionObservation("b23", law.criterion, law.criterion_unit, 1.0)],
    )
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=invalid, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.INVALID_REFERENCE and result.transitions == ()
    assert backend.commands == [] and backend.closed is True

    excluded = ExcludedEventRecord.create(
        source="prescribed_intervention", event_kind="prescribed_removal",
        physics_profile_id=PROFILE.profile_id, physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID, accepted=True, physical_bond_id="b12", old_alive=True, new_alive=False,
    )
    prescribed_damage = apply_excluded_event(damage, excluded)
    prescribed_topology = registry.apply_plan(registry.initial_state, registry.plan_bond_removal(registry.initial_state, "b12"))
    backend = FakeBackend(registry, [{"b23": 1.0}])
    backend.deleted_bonds.add("b12"); backend.deleted_angles.add("a123")
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=prescribed_damage, topology_state=prescribed_topology
    )
    assert result.status is CascadeStatus.STABLE and result.transitions == ()


def test_zero_budget_terminates_without_mutation_or_zero_progress_repeat() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(0)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.EVENT_BUDGET_EXHAUSTED
    assert result.transitions == () and result.damage_state == damage


def test_public_record_replay_rejects_tampering_and_cross_object_forgery() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert CascadeResult.from_record(result.as_record()).as_record() == result.as_record()
    transition = result.transitions[0]
    assert CascadeTransitionEnvelope.from_record(transition.as_record()).as_record() == transition.as_record()
    forged = transition.as_record()
    forged["post_event_relaxed"]["control_id"] = "foreign"
    with pytest.raises(FractureExecutionError):
        CascadeTransitionEnvelope.from_record(forged)
    diagnostic = CascadeDiagnostic.create("solver_error", "fixture", counts_as_physical_failure=False)
    assert CascadeDiagnostic.from_record(diagnostic.as_record()) == diagnostic

    empty_history_record = result.as_record()
    empty_history_record["transitions"] = []
    _rehash_record_body(empty_history_record, "result_id")
    with pytest.raises(FractureExecutionError, match="sequence|transition"):
        replace(
            result,
            result_id=empty_history_record["result_id"],
            transitions=(item for item in result.transitions),
        )


def _rehash_record_body(record: dict[str, object], identity_field: str) -> None:
    body = {key: value for key, value in record.items() if key != identity_field}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    record[identity_field] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def _observed_bond_length(observation: BackendObservation, registry: TopologyRegistry, bond_id: str) -> float:
    bond = registry.bond(bond_id)
    positions = {stable_id: observation.positions_nm[index] for index, stable_id in enumerate(observation.stable_node_ids)}
    displacement = (
        positions[bond.node_j] - positions[bond.node_i]
        + observation.cell.matrix_nm @ np.asarray(observation.current_edge_image_offsets_n_ij[bond_id], dtype=float)
    )
    return float(np.linalg.norm(displacement))


def test_transition_replay_rejects_rehashed_privileged_visibility_and_law_forgery() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    record["privileged_reference_metadata"]["predictor_visibility"] = "visible_to_predictor"
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="privileged"):
        CascadeTransitionEnvelope.from_record(record)


def test_transition_replay_rejects_rehashed_observation_profile_forgery() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    for name in ("pre_delete_raw", "post_delete_unrelaxed", "post_event_relaxed"):
        record[name]["physics_profile_id"] = "forged-profile"
        _rehash_record_body(record[name], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="privileged|profile|provenance"):
        CascadeTransitionEnvelope.from_record(record)


def test_transition_replay_rejects_coherent_cell_not_matching_full_control_record() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    for name in ("pre_delete_raw", "post_delete_unrelaxed", "post_event_relaxed"):
        record[name]["cell"]["matrix_nm"] = [[15.6, 0.0], [0.0, 10.0]]
        _rehash_record_body(record[name], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="privileged|control|deformation|cell"):
        CascadeTransitionEnvelope.from_record(record)


def test_observation_replay_rejects_duplicate_foreign_nodes_and_envelope_binds_registry_geometry() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    transition = result.transitions[0]
    for node_ids in (["n1", "n1", "n3", "n4"], ["foreign", "n2", "n3", "n4"]):
        observation = transition.pre_delete_raw.as_record()
        observation["stable_node_ids"] = node_ids
        _rehash_record_body(observation, "observation_id")
        with pytest.raises(FractureExecutionError, match="node|registry|mapping"):
            BackendObservation.from_record(observation)

    record = transition.as_record()
    pre = record["pre_delete_raw"]
    pre["stable_node_ids"] = ["n2", "n1", "n3", "n4"]
    _rehash_record_body(pre, "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="privileged|registry|mapping|geometry"):
        CascadeTransitionEnvelope.from_record(record)

    record = transition.as_record()
    pre = record["pre_delete_raw"]
    pre["criterion_values"]["b12"] = 99.0
    _rehash_record_body(pre, "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="privileged|criterion|geometry|event"):
        CascadeTransitionEnvelope.from_record(record)


def test_transition_replay_binds_event_coordinate_units_progress_and_criterion() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    for name in ("pre_delete_raw", "post_delete_unrelaxed", "post_event_relaxed"):
        record[name]["load_coordinate"] = 0.25
        record[name]["path_progress"] = 0.25
        _rehash_record_body(record[name], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="control|event|coordinate|progress"):
        CascadeTransitionEnvelope.from_record(record)

    observation = result.transitions[0].pre_delete_raw.as_record()
    observation["load_coordinate_unit"] = "invented-unit"
    observation["progress_unit"] = "invented-unit"
    _rehash_record_body(observation, "observation_id")
    with pytest.raises(FractureExecutionError, match="control|unit"):
        BackendObservation.from_record(observation)


def test_transition_replay_binds_boundary_condition_pairs_and_phase_invariance() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    record["post_event_relaxed"]["boundary_conditions"] = {
        "kind": "fixture_only_fixed_endpoints_after_affine_cell_remap",
        "anchored_stable_node_ids": ["n1", "n3"],
        "anchored_solver_atom_ids": [1, 3],
        "constrained_components": ["x", "y"],
        "equilibrium_scope": "free_degrees_of_freedom_only",
        "reaction_forces_recorded": False,
        "node_force_scope": "post_constraint_reactions_excluded",
        "convergence_residual_scope": "free_degrees_of_freedom_post_constraint",
    }
    _rehash_record_body(record["post_event_relaxed"], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="boundary"):
        CascadeTransitionEnvelope.from_record(record)

    observation = result.transitions[0].pre_delete_raw.as_record()
    observation["boundary_conditions"]["anchored_stable_node_ids"] = ["n2"]
    observation["boundary_conditions"]["anchored_solver_atom_ids"] = [1]
    observation["boundary_conditions"]["kind"] = "fixture_only_fixed_endpoints_after_affine_cell_remap"
    observation["boundary_conditions"]["constrained_components"] = ["x", "y"]
    observation["boundary_conditions"]["equilibrium_scope"] = "free_degrees_of_freedom_only"
    observation["boundary_conditions"]["reaction_forces_recorded"] = False
    observation["boundary_conditions"]["node_force_scope"] = "post_constraint_reactions_excluded"
    observation["boundary_conditions"]["convergence_residual_scope"] = "free_degrees_of_freedom_post_constraint"
    _rehash_record_body(observation, "observation_id")
    with pytest.raises(FractureExecutionError, match="boundary|mapping"):
        BackendObservation.from_record(observation)


def test_transition_replay_preserves_one_fixed_reference_tension_across_phases() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.transitions[0].as_record()
    record["post_event_relaxed"]["incremental_tension_pN_per_nm"] = [[7.0, 0.0], [0.0, 0.0]]
    _rehash_record_body(record["post_event_relaxed"], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="reference.*tension|incremental.*total"):
        CascadeTransitionEnvelope.from_record(record)

    record = result.transitions[0].as_record()
    record["post_event_relaxed"]["reference_total_tension_pN_per_nm"] = [[-7.0, 0.0], [0.0, 0.0]]
    record["post_event_relaxed"]["incremental_tension_pN_per_nm"] = [[7.0, 0.0], [0.0, 0.0]]
    _rehash_record_body(record["post_event_relaxed"], "observation_id")
    _rehash_record_body(record, "envelope_id")
    with pytest.raises(FractureExecutionError, match="reference.*tension"):
        CascadeTransitionEnvelope.from_record(record)


def test_result_replay_binds_provenance_snapshot_and_close_status_semantics() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}, {"b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    record = result.as_record()
    record["control_id"] = "foreign-control"
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="control|provenance"):
        CascadeResult.from_record(record)

    record = result.as_record()
    record["status"] = CascadeStatus.BACKEND_CLOSE_FAILED.value
    record["diagnostic"] = CascadeDiagnostic.create("backend_close_failed", "fixture").as_record()
    record["backend_closed"] = True
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="close|status"):
        CascadeResult.from_record(record)


def test_zero_event_result_replay_binds_damage_masks_topology_snapshot_and_convergence() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.0, "b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.STABLE and result.transitions == ()
    assert CascadeResult.from_record(result.as_record()).as_record() == result.as_record()
    observable = json.dumps(result.as_observable_record(), sort_keys=True)
    assert field.realization_id not in observable and "threshold_field" not in observable
    excluded = ExcludedEventRecord.create(
        source="prescribed_intervention", event_kind="prescribed_removal",
        physics_profile_id=PROFILE.profile_id, physics_profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID, accepted=True, physical_bond_id="b12", old_alive=True, new_alive=False,
    )
    prescribed = apply_excluded_event(damage, excluded)
    record = result.as_record()
    record["damage_state"] = prescribed.as_record()
    record["final_snapshot"]["damage_state_id"] = prescribed.state_id
    _rehash_record_body(record["final_snapshot"], "observation_id")
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="mask|topology|snapshot|damage"):
        CascadeResult.from_record(record)

    record = result.as_record()
    record["final_snapshot"]["convergence"] = ConvergenceDiagnostics.rejected("forged_nonconvergence", 1.0, 100, 100).as_record()
    _rehash_record_body(record["final_snapshot"], "observation_id")
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="stable|convergence"):
        CascadeResult.from_record(record)


def test_invalid_reference_result_replay_still_binds_reference_and_supported_control() -> None:
    registry = _registry(); law, field, _ = _damage(registry)
    invalid = initialize_damage_state(
        law, field,
        [CriterionObservation("b12", law.criterion, law.criterion_unit, 1.2), CriterionObservation("b23", law.criterion, law.criterion_unit, 1.0)],
    )
    result = QuasiStaticFractureCascade(FakeBackend(registry, []), registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=invalid, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.INVALID_REFERENCE and result.final_snapshot is None
    record = result.as_record()
    record["control"]["reference_state_id"] = "forged-reference"
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="reference|control"):
        CascadeResult.from_record(record)

    pressure = replace(
        _control(), control_kind="membrane_tension_target", loading_mode="pressure_derived_tension",
        lambda_load=1.0, load_coordinate_unit="pN/nm^2", progress_unit="pN/nm^2",
        path_progress=1.0, progress_increment=1.0,
        absolute_deformation_gradient=None, incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=np.eye(2), incremental_tension_target_pN_per_nm=np.eye(2),
        pressure_derivation={"fixture": True},
    )
    record = result.as_record(); record["control"] = pressure.as_record()
    _rehash_record_body(record, "result_id")
    with pytest.raises(FractureExecutionError, match="unsupported|deformation"):
        CascadeResult.from_record(record)


def test_rollback_comparison_includes_pbc_incremental_tension_and_source_offsets() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    base = BackendObservation.fixture(
        phase="pre_delete_relaxed", registry=registry, topology_state=registry.initial_state,
        criterion_values={"b12": 1.0, "b23": 1.0}, criterion_unit="dimensionless", converged=True,
        control=_control(), profile_id=PROFILE.profile_id, profile_hash=PROFILE.canonical_hash,
        reference_state_id=REFERENCE_ID, damage_state=damage,
    )
    for changes in (
        {"cell": Cell2D(base.cell.matrix_nm, base.cell.origin_nm, (True, False))},
        {
            "reference_total_tension_pN_per_nm": ((-1.0, 0.0), (0.0, 0.0)),
            "incremental_tension_pN_per_nm": ((1.0, 0.0), (0.0, 0.0)),
        },
        {"source_edge_image_offsets_n_ij": {"b12": (1, 0), "b23": (0, 0)}},
    ):
        body = base._constructor_body(); body.update(changes)
        changed = BackendObservation._create(**body)
        assert not QuasiStaticFractureCascade._same_mechanical_state(base, changed)


def test_failed_temporary_group_cleanup_remains_tracked_for_close_retry() -> None:
    backend = object.__new__(LammpsFractureBackend)
    backend._group_counter = 0
    backend._live_groups = set()
    calls: list[str] = []
    fail_cleanup = True
    def command(value: str) -> None:
        nonlocal fail_cleanup
        calls.append(value)
        if value.endswith(" delete") and fail_cleanup:
            fail_cleanup = False
            raise FractureExecutionError("injected cleanup failure")
    backend._command = command
    with pytest.raises(FractureExecutionError, match="cleanup"):
        backend._with_group((1, 2), "delete_bonds {group} bond 1 remove special")
    assert backend.temporary_groups_live == ("p0203g00000001",)
    backend._command("group p0203g00000001 delete")
    backend._live_groups.discard("p0203g00000001")
    assert backend.temporary_groups_live == ()


def test_tiny_lammps_fixture_rejects_periodicity_and_angle_selector_collisions_before_commands(tmp_path: Path) -> None:
    class VersionOnlySolver:
        @staticmethod
        def version() -> int:
            return 20260902

    base = _registry()
    nonperiodic = TopologyRegistry(
        Cell2D(base.cell.matrix_nm, base.cell.origin_nm, (True, False)),
        base.nodes, base.source_wrapped_positions_nm, base.bonds, base.angles,
    )
    backend = LammpsFractureBackend(
        solver=VersionOnlySolver(), solver_factory=lambda: VersionOnlySolver(), registry=nonperiodic,
        profile=PROFILE, work_directory=tmp_path / "nonperiodic", reference_total_tension_pN_per_nm=np.zeros((2, 2)),
    )
    with pytest.raises(FractureExecutionError, match="periodic"):
        backend._configure_fixture()
    assert backend.command_trace == ()

    cell = Cell2D(((12.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    nodes = tuple(NodeTopology(f"n{index}", index) for index in range(1, 6))
    positions = {"n1": (2.0, 2.0), "n2": (3.0, 2.0), "n3": (2.5, 3.0), "n4": (1.0, 2.0), "n5": (3.5, 3.8)}
    bonds = (
        BondTopology("b12", "n1", "n2", 1, "glycan", (0, 0), (1.0, 0.0)),
        BondTopology("b13", "n1", "n3", 1, "glycan", (0, 0), (0.5, 1.0)),
        BondTopology("b23", "n2", "n3", 1, "glycan", (0, 0), (-0.5, 1.0)),
        BondTopology("b14", "n1", "n4", 1, "glycan", (0, 0), (-1.0, 0.0)),
        BondTopology("b35", "n3", "n5", 1, "glycan", (0, 0), (1.0, 0.8)),
    )
    angles = (
        AngleTopology("a123", ("n1", "n2", "n3"), 1, ("b12", "b23")),
        AngleTopology("a213", ("n2", "n1", "n3"), 1, ("b12", "b13")),
    )
    collision = TopologyRegistry(cell, nodes, positions, bonds, angles)
    backend = LammpsFractureBackend(
        solver=VersionOnlySolver(), solver_factory=lambda: VersionOnlySolver(), registry=collision,
        profile=PROFILE, work_directory=tmp_path / "collision", reference_total_tension_pN_per_nm=np.zeros((2, 2)),
    )
    with pytest.raises(FractureExecutionError, match="selector is ambiguous"):
        backend._configure_fixture()
    assert backend.command_trace == ()


def test_observation_phase_law_and_masks_are_bound_to_requested_state() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.0, "b23": 1.0}])
    original = backend.relax_and_observe
    def forged(**kwargs):
        observation = original(**kwargs); body = observation._constructor_body()
        body["law_id"] = "foreign-law"
        return BackendObservation._create(**body)
    backend.relax_and_observe = forged
    with pytest.raises(FractureExecutionError, match="law"):
        QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=damage, topology_state=registry.initial_state
        )


def test_observation_cell_must_realize_scheduled_absolute_deformation() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.0, "b23": 1.0}])
    original = backend.relax_and_observe
    def unchanged_cell(**kwargs):
        observation = original(**kwargs)
        body = observation._constructor_body(); body["cell"] = registry.cell
        return BackendObservation._create(**body)
    backend.relax_and_observe = unchanged_cell
    with pytest.raises(FractureExecutionError, match="cell|deformation"):
        QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=damage, topology_state=registry.initial_state
        )
    assert backend.closed is True


def test_hidden_heterogeneous_field_is_sampled_once_replayable_and_never_observable() -> None:
    registry = _registry(); base_law, _, _ = _damage(registry)
    law = replace(
        base_law,
        law_id="fixture-hidden-heterogeneous-extension-v1",
        law_kind="quenched_heterogeneous_threshold",
        distribution={"kind": "uniform_relative", "relative_half_width": 0.05},
        predictor_visibility="hidden_from_predictor",
    )
    field = materialize_thresholds(law, ["b23", "b12"], material_disorder_seed=1729)
    reordered = materialize_thresholds(law, ["b12", "b23"], material_disorder_seed=1729)
    assert reordered.as_record() == field.as_record()
    damage = initialize_damage_state(
        law, field,
        [CriterionObservation(bond_id, law.criterion, law.criterion_unit, 1.0) for bond_id in ("b12", "b23")],
    )
    backend = FakeBackend(registry, [{"b12": 2.0, "b23": 2.0}, {"b12": 2.0, "b23": 2.0}, {}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(3)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.STABLE
    assert len(result.transitions) == 2
    for transition in result.transitions:
        assert transition.material_event.threshold_value == field.thresholds[transition.material_event.physical_bond_id]
        replayed = CascadeTransitionEnvelope.from_record(transition.as_record())
        assert replayed.envelope_id == transition.envelope_id
        observable = json.dumps(transition.as_observable_record(), sort_keys=True)
        assert field.realization_id not in observable
        assert "1729" not in observable
        assert "threshold_field" not in observable
    result_observable = result.as_observable_record()
    serialized_result = json.dumps(result_observable, sort_keys=True)
    assert field.realization_id not in serialized_result
    assert "1729" not in serialized_result
    assert "threshold_field" not in serialized_result
    assert result_observable["control"] == _control().as_record()


def test_unimplemented_damage_criteria_fail_before_any_backend_command() -> None:
    registry = _registry(); base_law, _, _ = _damage(registry)
    law = replace(
        base_law,
        law_id="fixture-tension-v1",
        criterion="bond_tension",
        criterion_unit="pN",
        base_threshold=10.0,
    )
    field = materialize_thresholds(law, ("b12", "b23"))
    damage = initialize_damage_state(
        law, field,
        [CriterionObservation(bond_id, "bond_tension", "pN", 1.0) for bond_id in ("b12", "b23")],
    )
    backend = FakeBackend(registry, [])
    with pytest.raises(FractureExecutionError, match="bond_extension_ratio"):
        QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=damage, topology_state=registry.initial_state
        )
    assert backend.commands == [] and backend.closed is True


def test_cross_law_threshold_field_fails_before_any_backend_command() -> None:
    registry = _registry(); law, _, damage = _damage(registry)
    foreign_law = replace(law, law_id="foreign-extension-law-v1", base_threshold=1.2)
    foreign_field = materialize_thresholds(foreign_law, ("b12", "b23"))
    forged_damage = replace(damage, threshold_realization_id=foreign_field.realization_id)
    backend = FakeBackend(registry, [{"b12": 1.0, "b23": 1.0}])
    with pytest.raises(FractureExecutionError, match="field|law|provenance"):
        QuasiStaticFractureCascade(backend, registry, law, foreign_field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=forged_damage, topology_state=registry.initial_state
        )
    assert backend.commands == [] and backend.closed is True


def test_corrupted_restore_or_restore_exception_is_not_reported_as_successful_rollback() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    for failure in ("restore_corrupt_mechanics", "restore"):
        backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}], fail_at=failure)
        backend.fail_post = True
        result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
            control=_control(), damage_state=damage, topology_state=registry.initial_state
        )
        assert result.status is CascadeStatus.ROLLBACK_FAILED
        assert result.diagnostic.kind == "rollback_failed"


def test_relaxation_budget_is_enforced_separately_from_event_budget() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.3, "b23": 1.0}])
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(4, max_relaxations=1)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.RELAXATION_BUDGET_EXHAUSTED
    assert result.transitions == ()


def test_close_failure_is_explicit_incomplete_result() -> None:
    registry = _registry(); law, field, damage = _damage(registry)
    backend = FakeBackend(registry, [{"b12": 1.0, "b23": 1.0}], fail_at="close")
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.BACKEND_CLOSE_FAILED
    assert result.backend_closed is False


def test_real_lammps_engine_runs_end_to_end_and_preserves_cell_atoms_offsets_and_group_cleanup(tmp_path: Path) -> None:
    registry = _periodic_crossing_registry(); law, _, _ = _damage(registry)
    backend = LammpsFractureBackend.tiny_harmonic_fixture(registry=registry, profile=PROFILE, work_directory=tmp_path)
    reference_values = dict(backend.fixed_reference_criterion_values)
    assert backend.fixed_reference_convergence.accepted is True
    np.testing.assert_allclose(backend.fixed_reference_cell.matrix_nm, registry.cell.matrix_nm, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose([reference_values["b12"], reference_values["b23"]], (1.0, 1.0), rtol=0.0, atol=1e-10)
    assert max(reference_values.values()) < law.base_threshold
    field = materialize_thresholds(law, ["b12", "b23"])
    damage = initialize_damage_state(
        law, field,
        [CriterionObservation(bond_id, law.criterion, law.criterion_unit, value) for bond_id, value in reference_values.items()],
    )
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(4)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.STABLE
    assert len(result.transitions) == 1
    assert result.transitions[0].material_event.physical_bond_id == "b12"
    assert result.final_snapshot.solver_atom_ids == (1, 2, 3)
    assert result.topology_state.alive_bond_ids == ("b23",)
    assert result.topology_state.alive_angle_ids == ()
    assert result.topology_state.components == (("n1",), ("n2", "n3"))
    for transition in result.transitions:
        np.testing.assert_allclose(transition.pre_delete_raw.cell.matrix_nm, transition.post_delete_unrelaxed.cell.matrix_nm)
        np.testing.assert_allclose(transition.post_delete_unrelaxed.cell.matrix_nm, transition.post_event_relaxed.cell.matrix_nm)
        np.testing.assert_allclose(transition.pre_delete_raw.cell.matrix_nm, ((14.4, 0.0), (0.0, 10.0)), rtol=0.0, atol=1e-10)
        assert np.isfinite(list(transition.pre_delete_raw.raw_energies_pN_nm.values())).all()
        assert np.isfinite(transition.pre_delete_raw.total_tension_pN_per_nm).all()
        assert transition.pre_delete_raw.convergence.accepted is True
        assert transition.post_event_relaxed.convergence.accepted is True
        np.testing.assert_allclose(
            [transition.pre_delete_raw.criterion_values["b12"], transition.pre_delete_raw.criterion_values["b23"]],
            (1.2, 1.2), rtol=0.0, atol=1e-9,
        )
        assert transition.pre_delete_raw.current_edge_image_offsets_n_ij["b12"] == (1, 0)
        assert transition.pre_delete_raw.source_edge_image_offsets_n_ij["b12"] == (1, 0)
        boundary = transition.pre_delete_raw.boundary_conditions
        assert boundary["kind"] == "fixture_only_fixed_endpoints_after_affine_cell_remap"
        assert tuple(boundary["anchored_stable_node_ids"]) == ("n1", "n3")
        assert tuple(boundary["anchored_solver_atom_ids"]) == (1, 3)
        assert tuple(boundary["constrained_components"]) == ("x", "y")
        assert boundary["reaction_forces_recorded"] is False
        assert boundary["node_force_scope"] == "post_constraint_reactions_excluded"
        assert boundary["convergence_residual_scope"] == "free_degrees_of_freedom_post_constraint"
        assert _plain_boundary(transition.post_delete_unrelaxed.boundary_conditions) == _plain_boundary(boundary)
        assert _plain_boundary(transition.post_event_relaxed.boundary_conditions) == _plain_boundary(boundary)
        assert np.array_equal(transition.pre_delete_raw.positions_nm, transition.post_delete_unrelaxed.positions_nm)
        assert _observed_bond_length(transition.pre_delete_raw, registry, "b12") == pytest.approx(1.236, abs=1e-10)
        assert _observed_bond_length(transition.pre_delete_raw, registry, "b23") == pytest.approx(1.236, abs=1e-10)
        pre_energy = transition.pre_delete_raw.raw_energies_pN_nm
        unrelaxed_energy = transition.post_delete_unrelaxed.raw_energies_pN_nm
        relaxed_energy = transition.post_event_relaxed.raw_energies_pN_nm
        assert pre_energy["ebond"] == pytest.approx(472.73704, rel=1e-10, abs=1e-8)
        assert pre_energy["pe"] == pytest.approx(pre_energy["ebond"], abs=1e-8)
        assert unrelaxed_energy["ebond"] == pytest.approx(pre_energy["ebond"] / 2.0, rel=1e-10, abs=1e-8)
        assert unrelaxed_energy["eangle"] == pytest.approx(0.0, abs=1e-12)
        assert unrelaxed_energy["pe"] == pytest.approx(unrelaxed_energy["ebond"], abs=1e-8)
        assert relaxed_energy["ebond"] == pytest.approx(0.0, abs=1e-8)
        assert relaxed_energy["pe"] == pytest.approx(0.0, abs=1e-8)
        internal_row = transition.post_event_relaxed.stable_node_ids.index("n2")
        moved = np.linalg.norm(
            transition.post_event_relaxed.positions_nm[internal_row]
            - transition.post_delete_unrelaxed.positions_nm[internal_row]
        )
        assert moved > 0.15
        assert _observed_bond_length(transition.post_event_relaxed, registry, "b23") == pytest.approx(1.03, abs=1e-8)
        assert transition.post_event_relaxed.criterion_values["b23"] == pytest.approx(1.0, abs=1e-8)
    np.testing.assert_allclose(registry.bond_displacement_nm("b12"), (1.03, 0.0))
    assert backend.last_topology_audit["counts"] == {"atoms": 3, "bonds": 1, "angles": 0}
    assert backend.last_topology_audit["bonds"] == ((1, 2, 3),)
    assert backend.last_topology_audit["angles"] == ()
    assert backend.temporary_groups_live == ()
    assert all("bond/break" not in command for command in backend.command_trace)
    assert "fix p0203_anchor_lock p0203_anchor setforce 0.0 0.0 0.0" in backend.command_trace
    assert backend.closed is True


def test_real_lammps_normal_max_iteration_return_is_rejected_without_physical_failure_claim(tmp_path: Path) -> None:
    registry = _angled_crossing_registry(); base_law, _, _ = _damage(registry)
    law = replace(base_law, law_id="fixture-high-threshold-extension-v1", base_threshold=10.0)
    backend = LammpsFractureBackend.tiny_harmonic_fixture(registry=registry, profile=PROFILE, work_directory=tmp_path)
    field = materialize_thresholds(law, ("b12", "b23"))
    damage = initialize_damage_state(
        law, field,
        [
            CriterionObservation(bond_id, law.criterion, law.criterion_unit, value)
            for bond_id, value in backend.fixed_reference_criterion_values.items()
        ],
    )
    backend.maximum_iterations = 1
    backend.force_tolerance_pN = 1e-30
    result = QuasiStaticFractureCascade(backend, registry, law, field, CascadeBudget(2)).run_step(
        control=_control(), damage_state=damage, topology_state=registry.initial_state
    )
    assert result.status is CascadeStatus.REJECTED_NONCONVERGENCE
    assert result.transitions == ()
    assert result.final_snapshot.convergence.accepted is False
    assert result.final_snapshot.convergence.maximum_iterations == 1
    assert result.final_snapshot.convergence.iterations == 1
    assert result.diagnostic.kind == "nonconvergence"
    assert result.diagnostic.counts_as_physical_failure is False
    assert result.diagnostic.counts_as_mechanical_instability is False
    assert backend.closed is True
