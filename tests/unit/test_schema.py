from __future__ import annotations

from dataclasses import replace
import math
from types import MappingProxyType
from typing import Any, Mapping

import pytest
import pgworld.data.schema as schema_module

from pgworld.data.schema import (
    ACCESS_SCHEMA_VERSION,
    TRAJECTORY_SCHEMA_VERSION,
    AccessProjection,
    AngleReference,
    AngleState,
    BoundaryConditionRecord,
    CapabilityFlags,
    Cell2D,
    CensoringRecord,
    ControlRecord,
    ConvergenceRecord,
    DiagnosticTrial,
    EdgeParameterChange,
    EdgeReference,
    EdgeState,
    EndpointObservation,
    EventRecord,
    NamedScalars,
    NodeReference,
    NodeState,
    NormalizerRecord,
    PressureDerivation,
    PrivilegedRecord,
    ProvenanceRecord,
    ReferenceStateRecord,
    SchemaValidationError,
    StateRecord,
    StaticGraph,
    TrajectoryFailureEndpoints,
    TrajectoryRecord,
    canonicalize_p02_phase,
)


def _hash(character: str) -> str:
    return f"sha256:{character * 64}"


def _reference_cell() -> Cell2D:
    return Cell2D(
        origin_nm=(-1.0, 2.0),
        cell_matrix_nm=((4.0, -0.5), (0.0, 3.0)),
        periodic_axes=(True, True),
        axis_meanings=("axial", "hoop"),
    )


def _cell() -> Cell2D:
    return Cell2D(
        origin_nm=(-1.0, 2.0),
        cell_matrix_nm=((4.4, -0.55), (0.0, 3.0)),
        periodic_axes=(True, True),
        axis_meanings=("axial", "hoop"),
    )


def _parameters(k: float = 5570.0) -> NamedScalars:
    return NamedScalars(
        values={"K": k, "r0": 1.03},
        units={"K": "pN/nm", "r0": "nm"},
    )


def _graph() -> StaticGraph:
    nodes = (
        NodeReference("node:001", "molecule:glycan-A", "glycan", NamedScalars({}, {})),
        NodeReference("node:002", "molecule:glycan-A", "glycan", NamedScalars({}, {})),
        NodeReference("node:003", "molecule:glycan-A", "glycan", NamedScalars({}, {})),
    )
    edges = (
        EdgeReference(
            "edge:001",
            ("node:001", "node:002"),
            1,
            "glycan",
            1.03,
            _parameters(),
            (0, 0),
        ),
        EdgeReference(
            "edge:002",
            ("node:002", "node:003"),
            1,
            "glycan",
            1.03,
            _parameters(),
            (-1, 0),
        ),
    )
    angles = (
        AngleReference(
            "angle:001",
            ("node:001", "node:002", "node:003"),
            ("edge:001", "edge:002"),
            "glycan_bend",
            NamedScalars(
                {"K": 10.0, "theta0": math.pi},
                {"K": "pN nm/rad^2", "theta0": "rad"},
            ),
        ),
    )
    return StaticGraph.create(
        graph_id="graph:opaque-001",
        reference_state_id="reference:fixed-cell-001",
        reference_cell=_reference_cell(),
        nodes=nodes,
        edges=edges,
        angles=angles,
    )


def _control(
    control_id: str = "control:load-001",
    load_step_id: str = "load-step:001",
    load_coordinate: float = 0.1,
    path_progress: float = 0.1,
) -> ControlRecord:
    return ControlRecord(
        control_id=control_id,
        load_step_id=load_step_id,
        control_family="deformation",
        step_index=0,
        control_kind="deformation_gradient",
        loading_mode="axial",
        axis_basis_columns_in_current_coordinates=((1.0, 0.0), (0.0, 1.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=load_coordinate,
        load_coordinate_unit="dimensionless",
        path_progress=path_progress,
        progress_increment=path_progress,
        progress_unit="dimensionless",
        absolute_deformation_gradient=((1.1, 0.0), (0.0, 1.0)),
        incremental_deformation_gradient=((1.1, 0.0), (0.0, 1.0)),
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
        pressure_derivation=None,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=(),
    )


def _node_states(*, relaxed_shift: float = 0.0) -> tuple[NodeState, ...]:
    return (
        NodeState("node:001", (0.0, 0.1), (0.0, 0.0)),
        NodeState("node:002", (1.0 + relaxed_shift, 0.1), (0.0, 0.0)),
        NodeState("node:003", (2.0, 0.1), (0.0, 0.0)),
    )


def _edge_states(
    *, ruptured: bool = False, relaxed_shift: float = 0.0
) -> tuple[EdgeState, ...]:
    first = EdgeState(
        edge_id="edge:001",
        alive=not ruptured,
        image_offset_n_ij=None if ruptured else (0, 0),
        effective_parameters=_parameters(),
        damage_value=1.0 if ruptured else 0.0,
        damage_unit="dimensionless",
        length_nm=None if ruptured else 1.0 + relaxed_shift,
        tension_pN=None if ruptured else 2.0,
        energy_pN_nm=None if ruptured else 0.2,
    )
    second = EdgeState(
        edge_id="edge:002",
        alive=True,
        image_offset_n_ij=(-1, 0),
        effective_parameters=_parameters(),
        damage_value=0.0,
        damage_unit="dimensionless",
        length_nm=3.4 + relaxed_shift,
        tension_pN=3.0,
        energy_pN_nm=0.3,
    )
    return (first, second)


def _state(
    sequence_index: int,
    frame_id: str,
    phase: str,
    subevent_index: int,
    *,
    ruptured: bool = False,
    source_phase: str | None = None,
    relaxed_shift: float = 0.0,
) -> StateRecord:
    return StateRecord(
        sequence_index=sequence_index,
        frame_id=frame_id,
        load_step_id="load-step:001",
        control_id="control:load-001",
        subevent_index=subevent_index,
        phase=phase,
        source_phase=source_phase,
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
        progress_unit="dimensionless",
        physical_time_ns=None,
        physical_time_valid=False,
        cell=_cell(),
        nodes=_node_states(relaxed_shift=relaxed_shift),
        edges=_edge_states(ruptured=ruptured, relaxed_shift=relaxed_shift),
        angles=(AngleState("angle:001", not ruptured),),
        component_ids=(
            {
                "node:001": "component:001",
                "node:002": "component:002",
                "node:003": "component:002",
            }
            if ruptured
            else {
                "node:001": "component:001",
                "node:002": "component:001",
                "node:003": "component:001",
            }
        ),
        total_tension_pN_per_nm=((2.0, 0.0), (0.0, 1.0)),
        incremental_tension_pN_per_nm=((0.2, 0.0), (0.0, 0.1)),
        energy_terms=NamedScalars(
            {"pe": 0.6, "ebond": 0.5, "eangle": 0.1},
            {"pe": "pN nm", "ebond": "pN nm", "eangle": "pN nm"},
        ),
        convergence=ConvergenceRecord(
            converged=phase != "post_topology_change",
            accepted=phase != "post_topology_change",
            iterations=12 if phase != "post_topology_change" else 0,
            max_iterations=100,
            residual_force_pN=1e-10 if phase != "post_topology_change" else 2.0,
            force_tolerance_pN=1.0e-8,
            reason="converged" if phase != "post_topology_change" else "phase_not_relaxed",
        ),
    )


def _event() -> EventRecord:
    return EventRecord(
        event_id=_hash("9"),
        sequence_index=0,
        event_source="material_rupture",
        edge_id="edge:001",
        triggering_control_id="control:load-001",
        load_step_id="load-step:001",
        subevent_index=2,
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
        progress_unit="dimensionless",
        pre_state_id="frame:pre",
        post_topology_state_id="frame:post-topology",
        post_equilibrium_state_id="frame:post-equilibrium",
        old_alive=True,
        new_alive=False,
        removed_angle_ids=("angle:001",),
        cascade_parent_event_id=None,
        criterion_name="bond_extension_ratio",
        criterion_value=1.2,
        criterion_unit="dimensionless",
        damage_law_id="law:quenched-001",
        damage_law_hash=_hash("d"),
        threshold_realization_id=_hash("8"),
        physics_profile_id="reviewed_physics_provisional_v0",
        physics_profile_hash=_hash("b"),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate_semantics="instantaneous_event_control_coordinate",
        progress_semantics="cumulative_absolute_lambda_increment",
    )


def _reference_state() -> ReferenceStateRecord:
    graph = _graph()
    return ReferenceStateRecord.create(
        reference_state_id="reference:fixed-cell-001",
        physics_profile_id="reviewed_physics_provisional_v0",
        physics_profile_hash=_hash("b"),
        static_graph_hash=graph.graph_hash,
        cell=_reference_cell(),
        node_positions_nm={
            "node:001": (0.0, 0.0),
            "node:002": (1.0, 0.0),
            "node:003": (2.0, 0.0),
        },
        total_tension_pN_per_nm=((1.8, 0.0), (0.0, 0.9)),
        minimization=ConvergenceRecord(
            converged=True,
            accepted=True,
            iterations=12,
            max_iterations=100,
            residual_force_pN=1.0e-10,
            force_tolerance_pN=1.0e-8,
            reason="converged",
        ),
    )


def _boundary_condition() -> BoundaryConditionRecord:
    return BoundaryConditionRecord.create(
        boundary_condition_id="boundary:periodic-cell",
        anchor_solver_atom_ids={},
        constrained_dofs={},
        affine_remap_behavior="all_nodes_affine_then_relax",
        reaction_forces_available=False,
        node_force_scope="all_nodes_net_force",
        residual_force_scope="all_mobile_dofs",
    )


def _provenance(
    reference: ReferenceStateRecord | None = None,
    boundary: BoundaryConditionRecord | None = None,
) -> ProvenanceRecord:
    reference = _reference_state() if reference is None else reference
    boundary = _boundary_condition() if boundary is None else boundary
    return ProvenanceRecord(
        run_id="run:001",
        parent_network_id="network:001",
        branch_id="branch:root",
        parent_run_id=None,
        branch_frame_id=None,
        source_kind="test_fixture",
        source_commit="0222b6d6fdee180e2e2daa86ccfebb276c91f1f6",
        source_tree_hash=_hash("a"),
        source_dirty=False,
        physics_profile_id="reviewed_physics_provisional_v0",
        physics_profile_hash=_hash("b"),
        reference_state_id="reference:fixed-cell-001",
        reference_state_hash=reference.reference_state_hash,
        rupture_law_id="law:quenched-001",
        rupture_law_hash=_hash("d"),
        config_hash=_hash("e"),
        raw_artifact_hashes={"solver-log": _hash("f")},
        simulator_version="LAMMPS 20260902",
        build_features=("SERIAL",),
        split_id=None,
        split_assignment_hash=None,
        manifest_hash=None,
        observation_model_id="observation:native-solver-state",
        observation_model_hash=_hash("1"),
        boundary_condition_id="boundary:periodic-cell",
        boundary_condition_hash=boundary.boundary_condition_hash,
    )


def _capabilities() -> CapabilityFlags:
    return CapabilityFlags(
        velocities=False,
        node_virial=False,
        edge_damage=True,
        physical_time=False,
        local_stress=False,
        event_history=True,
        angle_mechanics=True,
        rejected_trials=True,
    )


def _privileged() -> PrivilegedRecord:
    return PrivilegedRecord(
        threshold_values=NamedScalars(
            {"edge:001": 1.1, "edge:002": 1.3},
            {"edge:001": "dimensionless", "edge:002": "dimensionless"},
        ),
        threshold_predictor_visibility="hidden_from_predictor",
        threshold_realization_id=_hash("8"),
        threshold_criterion="bond_extension_ratio",
        threshold_criterion_unit="dimensionless",
        seeds={"material_disorder": 17, "events": 23},
        realization_proxies={"quenched_field_id": "private-realization-7"},
        rejected_trials=(
            DiagnosticTrial(
                trial_id="trial:001",
                control_id="control:load-001",
                load_coordinate=0.11,
                path_progress=0.11,
                reason="crossed_nonlinear_pole",
                details={"future_reference_state": {"edge:001": False}},
            ),
        ),
        normalizers=(
            NormalizerRecord(
                normalizer_id="normalizer:diagnostic-only",
                fit_partition="test",
                statistics={"position_mean": 0.5},
            ),
        ),
        access_policy={"classification": "private", "custodian": "not-public"},
        hidden_metadata={"event_rng_state": [1, 2, 3]},
    )


def _endpoint_observations() -> CensoringRecord:
    identity = {
        "physics_profile_id": "reviewed_physics_provisional_v0",
        "physics_profile_hash": _hash("b"),
        "reference_state_id": "reference:fixed-cell-001",
    }
    damage = EndpointObservation(
        endpoint_name="damage_initiation",
        status="observed",
        evidence_kind="accepted_material_rupture",
        evidence_id=_hash("9"),
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        load_coordinate_semantics="instantaneous_event_control_coordinate",
        path_progress=0.1,
        progress_unit="dimensionless",
        progress_semantics="cumulative_absolute_lambda_increment",
        **identity,
    )
    not_evaluated = {}
    for endpoint in (
        "load_bearing_connectivity_loss",
        "load_or_stiffness_degradation",
        "mechanical_instability",
    ):
        not_evaluated[endpoint] = EndpointObservation(
            endpoint_name=endpoint,
            status="not_evaluated",
            evidence_kind="not_evaluated",
            evidence_id=None,
            load_coordinate=None,
            load_coordinate_unit=None,
            load_coordinate_semantics=None,
            path_progress=None,
            progress_unit=None,
            progress_semantics=None,
            **identity,
        )
    return TrajectoryFailureEndpoints(
        law_id="law:quenched-001",
        law_fingerprint=_hash("d"),
        threshold_realization_id=_hash("8"),
        damage_initiation=damage,
        load_bearing_connectivity_loss=not_evaluated["load_bearing_connectivity_loss"],
        load_or_stiffness_degradation=not_evaluated["load_or_stiffness_degradation"],
        mechanical_instability=not_evaluated["mechanical_instability"],
    )


def _right_censored() -> CensoringRecord:
    endpoints = _endpoint_observations()
    damage = replace(
        endpoints.damage_initiation,
        status="right_censored",
        evidence_kind="no_damage_initiation_observed_over_executed_schedule",
        evidence_id=None,
        load_coordinate_semantics="terminal_control_coordinate_not_path_exposure_bound",
    )
    return replace(endpoints, damage_initiation=damage)


def _trajectory() -> TrajectoryRecord:
    graph = _graph()
    reference = _reference_state()
    boundary = _boundary_condition()
    states = (
        _state(0, "frame:accepted", "accepted_equilibrium", 0),
        _state(
            1,
            "frame:pre",
            "pre_rupture",
            1,
            source_phase="pre_delete_relaxed",
            relaxed_shift=0.236,
        ),
        _state(
            2,
            "frame:post-topology",
            "post_topology_change",
            2,
            ruptured=True,
            source_phase="post_delete_unrelaxed",
            relaxed_shift=0.236,
        ),
        _state(
            3,
            "frame:post-equilibrium",
            "post_event_equilibrium",
            3,
            ruptured=True,
            source_phase="post_event_relaxed",
            relaxed_shift=0.256,
        ),
    )
    return TrajectoryRecord.create(
        provenance=_provenance(reference, boundary),
        capabilities=_capabilities(),
        static_graph=graph,
        reference_state=reference,
        boundary_condition=boundary,
        controls=(_control(),),
        states=states,
        events=(_event(),),
        privileged=_privileged(),
        quality_status="accepted",
        termination_reason="completed_schedule",
        censoring=_endpoint_observations(),
    )


def _two_event_trajectory() -> TrajectoryRecord:
    trajectory = _trajectory()
    pre2 = replace(
        trajectory.states[-1],
        sequence_index=4,
        frame_id="frame:pre-2",
        subevent_index=4,
        phase="pre_rupture",
        source_phase=None,
    )
    both_dead = (
        pre2.edges[0],
        replace(
            pre2.edges[1],
            alive=False,
            image_offset_n_ij=None,
            damage_value=1.0,
            length_nm=None,
            tension_pN=None,
            energy_pN_nm=None,
        ),
    )
    post2 = replace(
        pre2,
        sequence_index=5,
        frame_id="frame:post-topology-2",
        subevent_index=5,
        phase="post_topology_change",
        edges=both_dead,
        component_ids={
            "node:001": "component:001",
            "node:002": "component:002",
            "node:003": "component:003",
        },
        convergence=ConvergenceRecord(
            converged=False,
            accepted=False,
            iterations=0,
            max_iterations=100,
            residual_force_pN=2.0,
            force_tolerance_pN=1.0e-8,
            reason="phase_not_relaxed",
        ),
    )
    final2 = replace(
        post2,
        sequence_index=6,
        frame_id="frame:post-equilibrium-2",
        subevent_index=6,
        phase="post_event_equilibrium",
        convergence=ConvergenceRecord(
            converged=True,
            accepted=True,
            iterations=12,
            max_iterations=100,
            residual_force_pN=1.0e-10,
            force_tolerance_pN=1.0e-8,
            reason="converged",
        ),
    )
    event2 = replace(
        trajectory.events[0],
        event_id=_hash("7"),
        sequence_index=1,
        edge_id="edge:002",
        subevent_index=5,
        pre_state_id=pre2.frame_id,
        post_topology_state_id=post2.frame_id,
        post_equilibrium_state_id=final2.frame_id,
        removed_angle_ids=(),
        cascade_parent_event_id=trajectory.events[0].event_id,
        criterion_value=(
            pre2.edges[1].length_nm
            / trajectory.static_graph.edges[1].reference_rest_length_nm
        ),
    )
    return TrajectoryRecord.create(
        **{
            **trajectory.constructor_fields(),
            "states": (*trajectory.states, pre2, post2, final2),
            "events": (*trajectory.events, event2),
        }
    )


def _walk_keys(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        keys: list[str] = []
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
        return keys
    if isinstance(value, (list, tuple)):
        return [key for child in value for key in _walk_keys(child)]
    return []


def test_opaque_string_ids_preserve_numeric_spelling_and_reject_integers() -> None:
    node = NodeReference("001", "0007", "glycan", NamedScalars({}, {}))
    replayed = NodeReference.from_record(node.as_record())
    assert replayed.node_id == "001"
    assert replayed.molecule_id == "0007"
    with pytest.raises(SchemaValidationError, match="opaque string"):
        NodeReference.from_record({**node.as_record(), "node_id": 1})


def test_cell_uses_column_vectors_origin_periodic_axes_and_signed_n_ij() -> None:
    cell = _reference_cell()
    assert cell.vector_convention == "column"
    assert cell.axis_meanings == ("axial", "hoop")
    assert cell.periodic_axes == (True, True)
    assert cell.displacement((0.1, 0.2), (3.8, 0.2), (-1, 1)) == pytest.approx(
        (-0.8, 3.0)
    )
    edge = _graph().edges[1]
    assert edge.reference_image_offset_n_ij == (-1, 0)
    assert Cell2D.from_record(cell.as_record()) == cell


@pytest.mark.parametrize(
    "bad_matrix",
    [
        ((4.0, 0.0), (0.1, 3.0)),
        ((4.0, 0.0), (0.0, -3.0)),
        ((4.0, float("nan")), (0.0, 3.0)),
    ],
)
def test_cell_fails_closed_outside_supported_restricted_finite_domain(
    bad_matrix: tuple[tuple[float, float], tuple[float, float]],
) -> None:
    with pytest.raises(SchemaValidationError):
        replace(_cell(), cell_matrix_nm=bad_matrix)


def test_static_graph_validates_endpoint_angle_dependency_and_identity_universes() -> None:
    graph = _graph()
    assert graph.node_ids == ("node:001", "node:002", "node:003")
    assert graph.edge_ids == ("edge:001", "edge:002")
    assert graph.angle_ids == ("angle:001",)
    broken_edge = replace(graph.edges[0], endpoints=("node:001", "node:missing"))
    with pytest.raises(SchemaValidationError, match="endpoint"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=(broken_edge, graph.edges[1]),
            angles=graph.angles,
        )
    broken_angle = replace(graph.angles[0], dependent_edge_ids=("edge:001", "edge:x"))
    with pytest.raises(SchemaValidationError, match="dependent"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=graph.edges,
            angles=(broken_angle,),
        )


def test_records_are_deeply_immutable() -> None:
    trajectory = _trajectory()
    assert isinstance(trajectory.privileged.seeds, MappingProxyType)
    assert isinstance(trajectory.states[0].component_ids, MappingProxyType)
    with pytest.raises(TypeError):
        trajectory.privileged.seeds["events"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        trajectory.states[0].energy_terms.values["bond"] = 2.0  # type: ignore[index]


def test_trajectory_round_trip_is_exact_and_content_hash_bound() -> None:
    trajectory = _trajectory()
    replayed = TrajectoryRecord.from_record(trajectory.as_record())
    assert replayed == trajectory
    assert replayed.record_hash == trajectory.record_hash
    tampered = trajectory.as_record()
    tampered["states"][0]["nodes"][0]["position_nm"][0] = 9.0  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="record_hash|length"):
        TrajectoryRecord.from_record(tampered)


def test_unknown_fields_and_mixed_or_old_schema_versions_fail_closed() -> None:
    record = _trajectory().as_record()
    record["unexpected"] = "ignored-by-a-loose-loader"
    with pytest.raises(SchemaValidationError, match="unexpected"):
        TrajectoryRecord.from_record(record)

    mixed = _trajectory().as_record()
    mixed["static_graph"]["schema_version"] = "pgworld.trajectory.v0"  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="schema_version|record_hash"):
        TrajectoryRecord.from_record(mixed)

    old = _trajectory().as_record()
    old["schema_version"] = "pgworld.trajectory.v0"
    with pytest.raises(SchemaValidationError, match="explicit migration"):
        TrajectoryRecord.from_record(old)


def test_no_int64_id_coercion_occurs_during_nested_replay() -> None:
    record = _trajectory().as_record()
    record["static_graph"]["edges"][0]["edge_id"] = 1  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="opaque string"):
        TrajectoryRecord.from_record(record)


def test_canonical_phase_adapter_is_exact_and_source_phase_is_provenance_only() -> None:
    assert canonicalize_p02_phase("pre_delete_relaxed") == "pre_rupture"
    assert canonicalize_p02_phase("post_delete_unrelaxed") == "post_topology_change"
    assert canonicalize_p02_phase("post_event_relaxed") == "post_event_equilibrium"
    for alias in ("pre-rupture", "PRE_DELETE_RELAXED", "post_delete_relaxed", "pre_rupture"):
        with pytest.raises(SchemaValidationError, match="P02 source phase"):
            canonicalize_p02_phase(alias)
    state = _trajectory().states[1]
    assert state.phase == "pre_rupture"
    assert state.source_phase == "pre_delete_relaxed"
    with pytest.raises(SchemaValidationError, match="source phase"):
        replace(state, source_phase="post_event_relaxed")


def test_same_load_subevents_are_preserved_and_ordered_not_deduplicated() -> None:
    trajectory = _trajectory()
    assert [state.load_coordinate for state in trajectory.states] == [0.1] * 4
    assert [state.subevent_index for state in trajectory.states] == [0, 1, 2, 3]
    assert [state.phase for state in trajectory.states] == [
        "accepted_equilibrium",
        "pre_rupture",
        "post_topology_change",
        "post_event_equilibrium",
    ]
    with pytest.raises(SchemaValidationError, match="subevent"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (
                    trajectory.states[0],
                    replace(trajectory.states[1], subevent_index=0),
                    *trajectory.states[2:],
                ),
            }
        )


def test_replay_rejects_healing_repeat_events_and_angle_resurrection() -> None:
    trajectory = _trajectory()
    healed = replace(
        trajectory.states[-1],
        edges=_edge_states(ruptured=False, relaxed_shift=0.256),
        angles=(AngleState("angle:001", True),),
        component_ids={
            "node:001": "component:001",
            "node:002": "component:001",
            "node:003": "component:001",
        },
    )
    with pytest.raises(SchemaValidationError, match="irreversible|resurrect"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "states": (*trajectory.states[:-1], healed)}
        )

    repeat = replace(
        trajectory.events[0],
        event_id=_hash("6"),
        sequence_index=1,
    )
    with pytest.raises(SchemaValidationError, match="repeat|duplicate"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "events": (*trajectory.events, repeat)}
        )

    invalid_angle = replace(
        trajectory.states[2], angles=(AngleState("angle:001", True),)
    )
    with pytest.raises(SchemaValidationError, match="angle"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (
                    *trajectory.states[:2],
                    invalid_angle,
                    trajectory.states[3],
                ),
            }
        )


def test_event_requires_exact_dependent_angle_removal_and_linked_phases() -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="dependent angle"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "events": (replace(trajectory.events[0], removed_angle_ids=()),),
            }
        )
    with pytest.raises(SchemaValidationError, match="pre_rupture"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (
                    trajectory.states[0],
                    replace(trajectory.states[1], phase="accepted_equilibrium", source_phase=None),
                    *trajectory.states[2:],
                ),
            }
        )


def test_current_effective_parameters_and_damage_are_reconstructible_per_edge() -> None:
    trajectory = _trajectory()
    state = trajectory.states[0]
    assert state.edge_by_id("edge:001").effective_parameters.values["K"] == 5570.0
    assert state.edge_by_id("edge:001").damage_value == 0.0
    weakened = replace(
        state.edge_by_id("edge:002"), effective_parameters=_parameters(2785.0)
    )
    rebuilt = replace(state, edges=(state.edges[0], weakened))
    assert rebuilt.edge_by_id("edge:002").effective_parameters.values["K"] == 2785.0
    mismatched_units = replace(
        weakened,
        effective_parameters=NamedScalars(
            {"K": 2785.0, "r0": 1.03},
            {"K": "pN", "r0": "nm"},
        ),
    )
    with pytest.raises(SchemaValidationError, match="parameter.*unit"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (replace(state, edges=(state.edges[0], mismatched_units)),),
                "events": (),
                "termination_reason": "completed_schedule",
                "censoring": _right_censored(),
            }
        )


def test_capability_flags_fail_closed_when_payload_presence_disagrees() -> None:
    trajectory = _trajectory()
    velocity_state = replace(
        trajectory.states[0],
        nodes=(
            replace(trajectory.states[0].nodes[0], velocity_nm_per_ns=(0.0, 0.0)),
            *trajectory.states[0].nodes[1:],
        ),
    )
    with pytest.raises(SchemaValidationError, match="velocit"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (velocity_state,),
                "events": (),
                "termination_reason": "completed_schedule",
                "censoring": _right_censored(),
            }
        )
    with pytest.raises(SchemaValidationError, match="rejected_trials"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "capabilities": replace(trajectory.capabilities, rejected_trials=False),
            }
        )


def test_status_termination_and_right_censoring_are_explicit_and_consistent() -> None:
    trajectory = _trajectory()
    censored = TrajectoryRecord.create(
        **{
            **trajectory.constructor_fields(),
            "states": (trajectory.states[0],),
            "events": (),
            "termination_reason": "completed_schedule",
            "censoring": _right_censored(),
        }
    )
    assert censored.censoring.damage_initiation.status == "right_censored"
    with pytest.raises(SchemaValidationError, match="termination"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (trajectory.states[0],),
                "events": (),
                "termination_reason": "damage_initiation",
                "censoring": _right_censored(),
            }
        )


def test_provenance_requires_source_profile_reference_law_and_config_hashes() -> None:
    provenance = _provenance()
    for field in (
        "source_tree_hash",
        "physics_profile_hash",
        "reference_state_hash",
        "rupture_law_hash",
        "config_hash",
    ):
        with pytest.raises(SchemaValidationError, match="sha256"):
            replace(provenance, **{field: "not-a-hash"})


def test_observed_projection_recursively_excludes_privileged_and_future_information() -> None:
    projection = _trajectory().observed_projection("frame:pre")
    record = projection.as_record()
    assert projection.access_kind == "observed"
    assert record["schema_version"] == ACCESS_SCHEMA_VERSION
    payload = record["payload"]
    assert [state["frame_id"] for state in payload["states"]] == [  # type: ignore[index]
        "frame:accepted",
        "frame:pre",
    ]
    assert payload["event_history"] == []  # type: ignore[index]
    lowered = " ".join(_walk_keys(payload)).lower()
    for forbidden in (
        "threshold",
        "seed",
        "realization",
        "rejected",
        "normalizer",
        "access_policy",
        "private",
        "future",
        "rng",
    ):
        assert forbidden not in lowered
    assert "frame:post-topology" not in repr(payload)
    assert _hash("9") not in repr(payload)


@pytest.mark.parametrize(
    "alias",
    [
        "rupture_cutoff",
        "event_rng_state",
        "disorder_draw_id",
        "futureGraph",
        "oracle_event",
        "rejected-attempts",
        "testScaler",
        "privacyPolicy",
    ],
)
def test_observed_projection_replay_rejects_recursive_hidden_aliases(alias: str) -> None:
    record = _trajectory().observed_projection("frame:pre").as_record()
    record["payload"]["states"][0]["nested"] = {"innocent": [{alias: 7}]}  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="forbidden predictor-visible"):
        AccessProjection.from_record(record)


def test_target_projection_contains_only_post_anchor_targets_not_privileged_data() -> None:
    projection = _trajectory().target_projection("frame:pre")
    payload = projection.as_record()["payload"]
    assert projection.access_kind == "target_only"
    assert [state["frame_id"] for state in payload["states"]] == [  # type: ignore[index]
        "frame:post-topology",
        "frame:post-equilibrium",
    ]
    assert [event["event_id"] for event in payload["events"]] == [  # type: ignore[index]
        _hash("9")
    ]
    assert "threshold_values" not in repr(payload)
    assert "material_disorder" not in repr(payload)
    assert "access_policy" not in repr(payload)


def test_privileged_projection_is_explicit_and_not_predictor_visible() -> None:
    projection = _trajectory().privileged_projection()
    payload = projection.as_record()["payload"]
    assert projection.access_kind == "privileged"
    privileged = payload["privileged"]  # type: ignore[index]
    assert privileged["threshold_values"]["values"]["edge:001"] == 1.1
    assert privileged["seeds"]["events"] == 23
    assert privileged["rejected_trials"][0]["trial_id"] == "trial:001"
    assert privileged["normalizers"][0]["fit_partition"] == "test"
    assert privileged["access_policy"]["classification"] == "private"


def test_access_projection_is_immutable_hash_bound_and_schema_strict() -> None:
    projection = _trajectory().observed_projection("frame:pre")
    assert isinstance(projection.payload, MappingProxyType)
    with pytest.raises(TypeError):
        projection.payload["leak"] = 1  # type: ignore[index]
    tampered = projection.as_record()
    tampered["payload"]["anchor_frame_id"] = "frame:post-equilibrium"  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="projection_hash"):
        AccessProjection.from_record(tampered)
    mixed = projection.as_record()
    mixed["trajectory_schema_version"] = "pgworld.trajectory.v0"
    with pytest.raises(SchemaValidationError, match="trajectory_schema_version"):
        AccessProjection.from_record(mixed)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sequence_index", "not-an-integer"),
        ("criterion_value", "not-a-number"),
    ],
)
def test_observed_replay_rejects_rehashed_untyped_event_history(
    field: str, value: object
) -> None:
    record = _trajectory().observed_projection("frame:post-equilibrium").as_record()
    record["payload"]["event_history"][0][field] = value  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError):
        AccessProjection.from_record(record)


def test_observed_replay_rejects_rehashed_noncontiguous_state_sequence() -> None:
    record = _trajectory().observed_projection("frame:pre").as_record()
    record["payload"]["states"][0]["sequence_index"] = 77  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="sequence"):
        AccessProjection.from_record(record)


def test_target_replay_rejects_rehashed_forged_event_pre_state() -> None:
    record = _trajectory().target_projection("frame:pre").as_record()
    record["payload"]["events"][0]["pre_state_id"] = "frame:forged"  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="pre_state"):
        AccessProjection.from_record(record)


def test_target_replay_rejects_rehashed_inconsistent_censor_coordinate() -> None:
    record = _trajectory().target_projection("frame:pre").as_record()
    record["payload"]["censoring"]["damage_initiation"]["load_coordinate"] = 99.0  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="censor"):
        AccessProjection.from_record(record)


def test_reference_state_is_typed_hash_bound_and_keeps_fixed_box_prestress() -> None:
    assert hasattr(schema_module, "ReferenceStateRecord")
    reference_type = schema_module.ReferenceStateRecord
    reference = reference_type.create(
        reference_state_id="reference:fixed-cell-001",
        physics_profile_id="reviewed_physics_provisional_v0",
        physics_profile_hash=_hash("b"),
        static_graph_hash=_graph().graph_hash,
        cell=_reference_cell(),
        node_positions_nm={
            "node:001": (0.0, 0.0),
            "node:002": (1.0, 0.0),
            "node:003": (2.0, 0.0),
        },
        total_tension_pN_per_nm=((1.8, 0.0), (0.0, 0.9)),
        minimization=ConvergenceRecord(
            converged=True,
            accepted=True,
            iterations=12,
            max_iterations=100,
            residual_force_pN=1.0e-10,
            force_tolerance_pN=1.0e-8,
            reason="converged",
        ),
    )
    assert reference.reference_kind == "fixed_cell_equilibrated_not_zero_tension"
    assert reference_type.from_record(reference.as_record()) == reference
    tampered = reference.as_record()
    tampered["node_positions_nm"]["node:002"][0] = 1.2
    with pytest.raises(SchemaValidationError, match="reference_state_hash"):
        reference_type.from_record(tampered)


def test_convergence_preserves_budget_and_force_acceptance_contract() -> None:
    convergence = ConvergenceRecord(
        converged=True,
        accepted=True,
        iterations=12,
        max_iterations=100,
        residual_force_pN=1.0e-10,
        force_tolerance_pN=1.0e-8,
        reason="converged",
    )
    assert convergence.max_iterations == 100
    assert convergence.force_tolerance_pN == 1.0e-8
    with pytest.raises(SchemaValidationError, match="tolerance"):
        replace(convergence, residual_force_pN=1.0, reason="converged")


def test_static_graph_allows_only_selector_unambiguous_parallel_edges() -> None:
    graph = _graph()
    assert hasattr(graph.edges[0], "solver_bond_type")
    parallel = replace(graph.edges[0], edge_id="edge:parallel", solver_bond_type=2)
    accepted = StaticGraph.create(
        graph_id=graph.graph_id,
        reference_state_id=graph.reference_state_id,
        reference_cell=graph.reference_cell,
        nodes=graph.nodes,
        edges=(*graph.edges, parallel),
        angles=graph.angles,
    )
    assert accepted.edge_by_id("edge:parallel").endpoints == graph.edges[0].endpoints
    ambiguous = replace(parallel, edge_id="edge:ambiguous", solver_bond_type=1)
    with pytest.raises(SchemaValidationError, match="parallel"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=(*graph.edges, ambiguous),
            angles=graph.angles,
        )


def test_dead_edge_does_not_claim_current_periodic_image_geometry() -> None:
    dead = replace(_edge_states(ruptured=True)[0], image_offset_n_ij=None)
    assert dead.image_offset_n_ij is None
    with pytest.raises(SchemaValidationError, match="inactive"):
        replace(dead, image_offset_n_ij=(0, 0))


def test_projection_hash_is_not_parent_derivation_proof() -> None:
    trajectory = _trajectory()
    record = trajectory.observed_projection("frame:pre").as_record()
    record["payload"]["states"][0]["nodes"][0]["force_pN"][0] = 7.0  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    replayed = AccessProjection.from_record(record)
    with pytest.raises(SchemaValidationError, match="not derived"):
        replayed.validate_against(trajectory)
    trajectory.observed_projection("frame:pre").validate_against(trajectory)


def test_incremental_tension_is_bound_to_fixed_reference_prestress() -> None:
    trajectory = _trajectory()
    altered = replace(
        trajectory.states[0],
        incremental_tension_pN_per_nm=((0.0, 0.0), (0.0, 0.0)),
    )
    with pytest.raises(SchemaValidationError, match="incremental tension"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "states": (altered, *trajectory.states[1:])}
        )


def test_parallel_edges_cannot_hide_ambiguity_in_chemical_label() -> None:
    graph = _graph()
    ambiguous = replace(
        graph.edges[0],
        edge_id="edge:ambiguous-label",
        chemical_type="different-label",
    )
    with pytest.raises(SchemaValidationError, match="parallel"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=(*graph.edges, ambiguous),
            angles=graph.angles,
        )


def test_p02_topology_adapter_preserves_opaque_ids_type_and_signed_image() -> None:
    edge = EdgeReference.from_p02_topology(
        {
            "stable_bond_id": "bond:0007",
            "node_i": "node:0001",
            "node_j": "node:0002",
            "solver_bond_type": 3,
            "chemical_type": "glycan",
            "image_offset_n_ij": [-1, 2],
            "source_displacement_nm": [1.0, 0.0],
        },
        reference_rest_length_nm=1.03,
        reference_parameters=_parameters(),
    )
    assert edge.edge_id == "bond:0007"
    assert edge.solver_bond_type == 3
    assert edge.reference_image_offset_n_ij == (-1, 2)


def test_effective_coefficients_require_ordered_declared_weakening() -> None:
    trajectory = _trajectory()
    parent_control = replace(
        trajectory.controls[0],
        control_id="control:parent-load",
        load_step_id="load-step:parent-load",
    )
    state = trajectory.states[0]
    weakened_edge = replace(
        state.edge_by_id("edge:002"), effective_parameters=_parameters(2785.0)
    )
    weakened_state = replace(state, edges=(state.edges[0], weakened_edge))
    with pytest.raises(SchemaValidationError, match="reconstruct"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (weakened_state,),
                "events": (),
                "censoring": _right_censored(),
            }
        )
    intervention = replace(
        trajectory.controls[0],
        control_family="prescribed_intervention",
        control_kind="prescribed_intervention",
        loading_mode="declared_local_weakening",
        step_index=1,
        progress_increment=0.0,
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        local_weakening=(EdgeParameterChange("edge:002", ("K",), 0.5),),
    )
    accepted = TrajectoryRecord.create(
        **{
            **trajectory.constructor_fields(),
            "controls": (parent_control, intervention),
            "states": (weakened_state,),
            "events": (),
            "censoring": _right_censored(),
        }
    )
    assert accepted.states[0].edge_by_id("edge:002").effective_parameters.values["K"] == 2785.0


def test_threshold_visibility_is_explicit_without_seed_or_realization_leakage() -> None:
    trajectory = _trajectory()
    hidden = trajectory.observed_projection("frame:pre").as_record()["payload"]
    assert "material_limits" not in hidden
    visible_privileged = replace(
        trajectory.privileged,
        threshold_predictor_visibility="visible_to_predictor",
    )
    visible_trajectory = TrajectoryRecord.create(
        **{**trajectory.constructor_fields(), "privileged": visible_privileged}
    )
    visible = visible_trajectory.observed_projection("frame:pre").as_record()["payload"]
    assert visible["material_limits"]["values"]["values"]["edge:001"] == 1.1  # type: ignore[index]
    assert "seed" not in repr(visible).lower()
    assert "realization" not in repr(visible).lower()


def test_units_energy_time_and_boundary_semantics_fail_closed() -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="dimensionless"):
        replace(
            trajectory.controls[0],
            load_coordinate_unit="seconds",
            progress_unit="seconds",
        )
    with pytest.raises(SchemaValidationError, match="physical time"):
        replace(trajectory.states[0], physical_time_ns=1.0, physical_time_valid=True)
    with pytest.raises(SchemaValidationError, match="pe/ebond/eangle"):
        replace(
            trajectory.states[0],
            energy_terms=NamedScalars({"pe": 0.6}, {"pe": "pN nm"}),
        )
    changed_boundary = BoundaryConditionRecord.create(
        boundary_condition_id="boundary:periodic-cell",
        anchor_solver_atom_ids={"node:001": 1},
        constrained_dofs={"node:001": (True, True)},
        affine_remap_behavior="anchors_only",
        reaction_forces_available=False,
        node_force_scope="all_nodes_net_force",
        residual_force_scope="all_mobile_dofs",
    )
    with pytest.raises(SchemaValidationError, match="boundary"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "boundary_condition": changed_boundary}
        )


def test_event_source_and_standalone_angle_death_are_control_bound() -> None:
    trajectory = _trajectory()
    parent_control = replace(
        trajectory.controls[0],
        control_id="control:parent-load",
        load_step_id="load-step:parent-load",
    )
    declared = replace(
        trajectory.controls[0],
        control_family="prescribed_intervention",
        control_kind="prescribed_intervention",
        loading_mode="declared_edge_removal",
        step_index=1,
        progress_increment=0.0,
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        prescribed_removal_edge_ids=("edge:001",),
    )
    with pytest.raises(SchemaValidationError, match="material rupture"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "controls": (parent_control, declared)}
        )
    angle_only = replace(
        trajectory.states[1], angles=(AngleState("angle:001", False),)
    )
    with pytest.raises(SchemaValidationError, match="angle death"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (trajectory.states[0], angle_only),
                "events": (),
                "censoring": _right_censored(),
            }
        )


@pytest.mark.parametrize(
    "termination",
    ["solver_failure", "invalid_reference", "event_budget_exhausted"],
)
def test_accepted_quality_rejects_failure_or_budget_termination(termination: str) -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="quality_status/termination"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "termination_reason": termination}
        )


def test_damage_initiation_is_endpoint_not_trajectory_termination_and_cascade_continues() -> None:
    trajectory = _trajectory()
    pre2 = replace(
        trajectory.states[-1],
        sequence_index=4,
        frame_id="frame:pre-2",
        subevent_index=4,
        phase="pre_rupture",
        source_phase=None,
    )
    both_dead = (
        pre2.edges[0],
        replace(
            pre2.edges[1],
            alive=False,
            image_offset_n_ij=None,
            damage_value=1.0,
            length_nm=None,
            tension_pN=None,
            energy_pN_nm=None,
        ),
    )
    post2 = replace(
        pre2,
        sequence_index=5,
        frame_id="frame:post-topology-2",
        subevent_index=5,
        phase="post_topology_change",
        edges=both_dead,
        component_ids={
            "node:001": "component:001",
            "node:002": "component:002",
            "node:003": "component:003",
        },
        convergence=ConvergenceRecord(
            converged=False,
            accepted=False,
            iterations=0,
            max_iterations=100,
            residual_force_pN=2.0,
            force_tolerance_pN=1.0e-8,
            reason="phase_not_relaxed",
        ),
    )
    final2 = replace(
        post2,
        sequence_index=6,
        frame_id="frame:post-equilibrium-2",
        subevent_index=6,
        phase="post_event_equilibrium",
        convergence=ConvergenceRecord(
            converged=True,
            accepted=True,
            iterations=12,
            max_iterations=100,
            residual_force_pN=1.0e-10,
            force_tolerance_pN=1.0e-8,
            reason="converged",
        ),
    )
    event2 = replace(
        trajectory.events[0],
        event_id=_hash("7"),
        sequence_index=1,
        edge_id="edge:002",
        subevent_index=5,
        pre_state_id=pre2.frame_id,
        post_topology_state_id=post2.frame_id,
        post_equilibrium_state_id=final2.frame_id,
        removed_angle_ids=(),
        cascade_parent_event_id=trajectory.events[0].event_id,
        criterion_value=(
            pre2.edges[1].length_nm
            / trajectory.static_graph.edges[1].reference_rest_length_nm
        ),
    )
    continued = TrajectoryRecord.create(
        **{
            **trajectory.constructor_fields(),
            "states": (*trajectory.states, pre2, post2, final2),
            "events": (*trajectory.events, event2),
        }
    )
    assert len(continued.events) == 2
    assert continued.termination_reason == "completed_schedule"


def test_failure_endpoints_are_exact_p02_isomorphic_records() -> None:
    endpoints = _endpoint_observations()

    class P02Record:
        def as_record(self) -> dict[str, object]:
            return endpoints.as_record()

    replayed = TrajectoryFailureEndpoints.from_p02(P02Record())
    assert replayed.as_record() == endpoints.as_record()


def test_p02_unrelaxed_and_relaxed_convergence_semantics_are_exact() -> None:
    trajectory = _trajectory()
    unrelaxed = trajectory.states[2].convergence
    assert (unrelaxed.converged, unrelaxed.accepted, unrelaxed.reason) == (
        False,
        False,
        "phase_not_relaxed",
    )
    assert ConvergenceRecord.from_record(unrelaxed.as_record()) == unrelaxed
    with pytest.raises(SchemaValidationError, match="cannot be accepted"):
        replace(unrelaxed, accepted=True)
    relaxed = trajectory.states[1].convergence
    with pytest.raises(SchemaValidationError, match="tolerance"):
        replace(relaxed, iterations=relaxed.max_iterations)


@pytest.mark.parametrize(
    ("criterion", "unit"),
    [
        ("bond_extension_ratio", "pN"),
        ("bond_tension", "dimensionless"),
        ("bond_energy", "pN"),
    ],
)
def test_material_event_criterion_units_are_exact(criterion: str, unit: str) -> None:
    with pytest.raises(SchemaValidationError, match="criterion"):
        replace(_event(), criterion_name=criterion, criterion_unit=unit)


@pytest.mark.parametrize(
    "frame_id",
    ["frame:accepted", "frame:pre", "frame:post-topology", "frame:post-equilibrium"],
)
def test_access_projections_replay_and_parent_bind_at_every_anchor(frame_id: str) -> None:
    trajectory = _trajectory()
    observed = AccessProjection.from_record(
        trajectory.observed_projection(frame_id).as_record()
    )
    target = AccessProjection.from_record(trajectory.target_projection(frame_id).as_record())
    observed.validate_against(trajectory)
    target.validate_against(trajectory)


def test_component_partition_must_equal_alive_edge_connectivity() -> None:
    trajectory = _trajectory()
    wrong = replace(
        trajectory.states[2],
        component_ids={
            "node:001": "component:all",
            "node:002": "component:all",
            "node:003": "component:all",
        },
    )
    with pytest.raises(SchemaValidationError, match="component"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (*trajectory.states[:2], wrong, trajectory.states[3]),
            }
        )


def test_image_offsets_must_be_zero_on_nonperiodic_axes() -> None:
    graph = _graph()
    nonperiodic_y = replace(graph.reference_cell, periodic_axes=(True, False))
    invalid_edge = replace(
        graph.edges[0], reference_image_offset_n_ij=(0, 1)
    )
    with pytest.raises(SchemaValidationError, match="nonperiodic"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=nonperiodic_y,
            nodes=graph.nodes,
            edges=(invalid_edge, graph.edges[1]),
            angles=graph.angles,
        )


def test_alive_edge_length_is_recomputed_from_nodes_cell_and_signed_image() -> None:
    trajectory = _trajectory()
    state = trajectory.states[0]
    wrong_edge = replace(state.edges[0], length_nm=9.0)
    wrong_state = replace(state, edges=(wrong_edge, state.edges[1]))
    with pytest.raises(SchemaValidationError, match="length"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (wrong_state, *trajectory.states[1:]),
            }
        )


@pytest.mark.parametrize("failure", ["negative", "wrong_unit"])
def test_threshold_values_obey_p02_domain_and_declared_criterion_unit(
    failure: str,
) -> None:
    trajectory = _trajectory()
    values = {"edge:001": -1.0, "edge:002": 1.3} if failure == "negative" else {
        "edge:001": 1.1,
        "edge:002": 1.3,
    }
    units = {
        "edge:001": "pN" if failure == "wrong_unit" else "dimensionless",
        "edge:002": "dimensionless",
    }
    with pytest.raises(SchemaValidationError, match="threshold"):
        privileged = replace(
            trajectory.privileged,
            threshold_values=NamedScalars(values, units),
        )
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "privileged": privileged}
        )


@pytest.mark.parametrize("criterion_value", [999.0, 0.1])
def test_material_event_criterion_is_bound_to_pre_state_and_threshold(
    criterion_value: float,
) -> None:
    trajectory = _trajectory()
    forged = replace(trajectory.events[0], criterion_value=criterion_value)
    with pytest.raises(SchemaValidationError, match="criterion|threshold"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "events": (forged,)}
        )


def test_material_event_cannot_rupture_below_immutable_threshold() -> None:
    trajectory = _trajectory()
    privileged = replace(
        trajectory.privileged,
        threshold_values=NamedScalars(
            {"edge:001": 2.0, "edge:002": 1.3},
            {"edge:001": "dimensionless", "edge:002": "dimensionless"},
        ),
    )
    with pytest.raises(SchemaValidationError, match="threshold"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "privileged": privileged}
        )


def test_angle_dependencies_are_exact_adjacent_segments_with_chemical_semantics() -> None:
    graph = _graph()
    with pytest.raises(SchemaValidationError, match="exactly two"):
        replace(graph.angles[0], dependent_edge_ids=("edge:001",))
    diagonal = replace(
        graph.edges[0],
        edge_id="edge:diagonal",
        endpoints=("node:001", "node:003"),
        solver_bond_type=4,
    )
    wrong_segments = replace(
        graph.angles[0], dependent_edge_ids=("edge:001", "edge:diagonal")
    )
    with pytest.raises(SchemaValidationError, match="adjacent"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=(*graph.edges, diagonal),
            angles=(wrong_segments,),
        )
    peptide_edge = replace(graph.edges[1], chemical_type="peptide")
    with pytest.raises(SchemaValidationError, match="glycan"):
        StaticGraph.create(
            graph_id=graph.graph_id,
            reference_state_id=graph.reference_state_id,
            reference_cell=graph.reference_cell,
            nodes=graph.nodes,
            edges=(graph.edges[0], peptide_edge),
            angles=graph.angles,
        )


def test_progress_increment_is_absolute_control_change_not_free_path_delta() -> None:
    trajectory = _trajectory()
    second = replace(
        _control(
            control_id="control:load-002",
            load_step_id="load-step:002",
            load_coordinate=0.15,
            path_progress=0.2,
        ),
        step_index=1,
        progress_increment=0.1,
        absolute_deformation_gradient=((1.2, 0.0), (0.0, 1.0)),
        incremental_deformation_gradient=((1.2 / 1.1, 0.0), (0.0, 1.0)),
    )
    with pytest.raises(SchemaValidationError, match="absolute.*load|progress_increment"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "controls": (*trajectory.controls, second)}
        )


def test_trajectory_rejects_mixed_continuous_control_families_and_units() -> None:
    trajectory = _trajectory()
    derivation = PressureDerivation(
        pressure_pN_per_nm2=0.2,
        cylinder_radius_nm=500.0,
        shell_assumption="closed_thin_cylinder_away_from_end_effects",
        axial_relation="N_axial=pR/2",
        hoop_relation="N_hoop=pR",
        flat_patch_meaning="membrane_tension_target_not_normal_inflation",
    )
    pressure = ControlRecord(
        control_id="control:pressure-002",
        load_step_id="load-step:002",
        control_family="pressure_derived_tension",
        step_index=1,
        control_kind="membrane_tension_target",
        loading_mode="closed_cylinder_pressure_balance",
        axis_basis_columns_in_current_coordinates=((1.0, 0.0), (0.0, 1.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=0.2,
        load_coordinate_unit="pN/nm^2",
        path_progress=0.2,
        progress_increment=0.1,
        progress_unit="pN/nm^2",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=((50.0, 0.0), (0.0, 100.0)),
        incremental_tension_target_pN_per_nm=((50.0, 0.0), (0.0, 100.0)),
        pressure_derivation=derivation,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=(),
    )
    with pytest.raises(SchemaValidationError, match="family|unit"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "controls": (*trajectory.controls, pressure)}
        )


def test_pressure_path_intervention_inherits_pressure_coordinate_unit() -> None:
    derivation = PressureDerivation(
        pressure_pN_per_nm2=0.01,
        cylinder_radius_nm=500.0,
        shell_assumption="closed_thin_cylinder_away_from_end_effects",
        axial_relation="N_axial=pR/2",
        hoop_relation="N_hoop=pR",
        flat_patch_meaning="membrane_tension_target_not_normal_inflation",
    )
    pressure = ControlRecord(
        control_id="control:pressure-parent",
        load_step_id="load-step:pressure-parent",
        control_family="pressure_derived_tension",
        step_index=0,
        control_kind="membrane_tension_target",
        loading_mode="closed_cylinder_pressure_balance",
        axis_basis_columns_in_current_coordinates=((1.0, 0.0), (0.0, 1.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=0.01,
        load_coordinate_unit="pN/nm^2",
        path_progress=0.01,
        progress_increment=0.01,
        progress_unit="pN/nm^2",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=((2.5, 0.0), (0.0, 5.0)),
        incremental_tension_target_pN_per_nm=((2.5, 0.0), (0.0, 5.0)),
        pressure_derivation=derivation,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=(),
    )
    intervention = ControlRecord(
        control_id="control:pressure-cut",
        load_step_id="load-step:pressure-cut",
        control_family="prescribed_intervention",
        step_index=1,
        control_kind="prescribed_intervention",
        loading_mode="declared_edge_removal",
        axis_basis_columns_in_current_coordinates=((1.0, 0.0), (0.0, 1.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=0.01,
        load_coordinate_unit="pN/nm^2",
        path_progress=0.01,
        progress_increment=0.0,
        progress_unit="pN/nm^2",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=None,
        incremental_tension_target_pN_per_nm=None,
        pressure_derivation=None,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=("edge:001",),
    )
    assert intervention.load_coordinate_unit == pressure.load_coordinate_unit


def test_pressure_target_rotates_principal_axial_hoop_tensions() -> None:
    derivation = PressureDerivation(
        pressure_pN_per_nm2=0.01,
        cylinder_radius_nm=500.0,
        shell_assumption="closed_thin_cylinder_away_from_end_effects",
        axial_relation="N_axial=pR/2",
        hoop_relation="N_hoop=pR",
        flat_patch_meaning="membrane_tension_target_not_normal_inflation",
    )
    rotated = ControlRecord(
        control_id="control:pressure-rotated",
        load_step_id="load-step:pressure-rotated",
        control_family="pressure_derived_tension",
        step_index=0,
        control_kind="membrane_tension_target",
        loading_mode="closed_cylinder_pressure_balance",
        axis_basis_columns_in_current_coordinates=((0.0, -1.0), (1.0, 0.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=0.01,
        load_coordinate_unit="pN/nm^2",
        path_progress=0.01,
        progress_increment=0.01,
        progress_unit="pN/nm^2",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=((5.0, 0.0), (0.0, 2.5)),
        incremental_tension_target_pN_per_nm=((5.0, 0.0), (0.0, 2.5)),
        pressure_derivation=derivation,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=(),
    )
    assert rotated.absolute_tension_target_pN_per_nm == ((5.0, 0.0), (0.0, 2.5))


def test_observed_projection_exposes_only_controls_reached_by_anchor() -> None:
    trajectory = _trajectory()
    future_control = _control(
        control_id="control:future",
        load_step_id="load-step:future",
        load_coordinate=0.2,
        path_progress=0.2,
    )
    future_control = replace(
        future_control,
        step_index=1,
        progress_increment=0.1,
        absolute_deformation_gradient=((1.2, 0.0), (0.0, 1.0)),
        incremental_deformation_gradient=((1.2 / 1.1, 0.0), (0.0, 1.0)),
    )
    extended = TrajectoryRecord.create(
        **{**trajectory.constructor_fields(), "controls": (*trajectory.controls, future_control)}
    )
    payload = extended.observed_projection("frame:pre").as_record()["payload"]
    assert [row["control_id"] for row in payload["controls"]] == [  # type: ignore[index]
        "control:load-001"
    ]
    assert "control:future" not in repr(payload)


def test_nonfinite_nested_numeric_values_are_rejected() -> None:
    with pytest.raises(SchemaValidationError, match="finite"):
        NamedScalars({"bad": float("inf")}, {"bad": "dimensionless"})
    with pytest.raises(SchemaValidationError, match="finite"):
        DiagnosticTrial(
            "trial:bad",
            "control:load-001",
            0.1,
            0.1,
            "diagnostic",
            {"nested": [1.0, float("nan")]},
        )


def test_local_weakening_uses_stable_edge_ids_and_named_effective_parameters() -> None:
    change = EdgeParameterChange(
        edge_id="edge:002", parameter_names=("K",), factor=0.5
    )
    control = replace(
        _control(),
        control_family="prescribed_intervention",
        control_kind="prescribed_intervention",
        loading_mode="local_weakening",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        local_weakening=(change,),
    )
    assert control.local_weakening[0].edge_id == "edge:002"
    with pytest.raises(SchemaValidationError, match="opaque string"):
        replace(change, edge_id=2)  # type: ignore[arg-type]


def test_control_preserves_absolute_incremental_axis_and_constrained_dof_semantics() -> None:
    control = replace(
        _control(),
        constrained_dofs={"node:001": (True, False)},
    )
    assert control.step_index == 0
    assert control.control_kind == "deformation_gradient"
    assert control.loading_mode == "axial"
    assert control.axis_basis_columns_in_current_coordinates == (
        (1.0, 0.0),
        (0.0, 1.0),
    )
    assert control.absolute_deformation_gradient == ((1.1, 0.0), (0.0, 1.0))
    assert control.incremental_deformation_gradient == ((1.1, 0.0), (0.0, 1.0))
    assert control.constrained_dofs["node:001"] == (True, False)
    replayed = ControlRecord.from_record(control.as_record())
    assert replayed == control
    with pytest.raises(SchemaValidationError, match="orthonormal"):
        replace(control, axis_basis_columns_in_current_coordinates=((1.0, 0.2), (0.0, 1.0)))


def test_deformation_control_binds_state_cell_to_absolute_F_and_reference_H() -> None:
    trajectory = _trajectory()
    assert trajectory.states[0].cell.cell_matrix_nm == ((4.4, -0.55), (0.0, 3.0))
    wrong_cell = replace(trajectory.states[0], cell=_reference_cell())
    with pytest.raises(SchemaValidationError, match="absolute deformation gradient"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (wrong_cell,),
                "events": (),
                "termination_reason": "completed_schedule",
                "censoring": _right_censored(),
            }
        )


def test_ordered_controls_validate_step_progress_and_incremental_composition() -> None:
    trajectory = _trajectory()
    second = replace(
        _control(
            control_id="control:load-002",
            load_step_id="load-step:002",
            load_coordinate=0.2,
            path_progress=0.2,
        ),
        step_index=1,
        progress_increment=0.1,
        absolute_deformation_gradient=((1.2, 0.0), (0.0, 1.0)),
        incremental_deformation_gradient=((1.2 / 1.1, 0.0), (0.0, 1.0)),
    )
    extended = TrajectoryRecord.create(
        **{**trajectory.constructor_fields(), "controls": (*trajectory.controls, second)}
    )
    assert extended.controls[1].progress_increment == pytest.approx(0.1)
    with pytest.raises(SchemaValidationError, match="progress_increment"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "controls": (*trajectory.controls, replace(second, progress_increment=0.2)),
            }
        )
    with pytest.raises(SchemaValidationError, match="incremental deformation"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "controls": (
                    *trajectory.controls,
                    replace(second, incremental_deformation_gradient=((1.0, 0.0), (0.0, 1.0))),
                ),
            }
        )


def test_pressure_control_preserves_closed_cylinder_shell_meaning() -> None:
    derivation = PressureDerivation(
        pressure_pN_per_nm2=0.01,
        cylinder_radius_nm=500.0,
        shell_assumption="closed_thin_cylinder_away_from_end_effects",
        axial_relation="N_axial=pR/2",
        hoop_relation="N_hoop=pR",
        flat_patch_meaning="membrane_tension_target_not_normal_inflation",
    )
    control = ControlRecord(
        control_id="control:pressure-001",
        load_step_id="load-step:pressure-001",
        control_family="pressure_derived_tension",
        step_index=0,
        control_kind="membrane_tension_target",
        loading_mode="closed_cylinder_pressure_balance",
        axis_basis_columns_in_current_coordinates=((1.0, 0.0), (0.0, 1.0)),
        reference_state_id="reference:fixed-cell-001",
        load_coordinate=0.01,
        load_coordinate_unit="pN/nm^2",
        path_progress=0.01,
        progress_increment=0.01,
        progress_unit="pN/nm^2",
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        absolute_tension_target_pN_per_nm=((2.5, 0.0), (0.0, 5.0)),
        incremental_tension_target_pN_per_nm=((2.5, 0.0), (0.0, 5.0)),
        pressure_derivation=derivation,
        boundary_displacements_nm={},
        prescribed_forces_pN={},
        constrained_dofs={},
        local_weakening=(),
        prescribed_removal_edge_ids=(),
    )
    assert ControlRecord.from_record(control.as_record()) == control
    with pytest.raises(SchemaValidationError, match="shell_assumption"):
        replace(derivation, shell_assumption="isotropic_box_strain_called_turgor")


def test_provenance_represents_branch_split_observation_and_boundary_contracts() -> None:
    branch = replace(
        _provenance(),
        parent_run_id="run:parent",
        branch_frame_id="frame:branch-point",
        split_id="split:test",
        split_assignment_hash=_hash("3"),
        manifest_hash=_hash("4"),
    )
    assert ProvenanceRecord.from_record(branch.as_record()) == branch
    with pytest.raises(SchemaValidationError, match="both be present"):
        replace(branch, branch_frame_id=None)

    trajectory = TrajectoryRecord.create(
        **{**_trajectory().constructor_fields(), "provenance": branch}
    )
    observed = trajectory.observed_projection("frame:pre").as_record()["payload"]
    rendered = repr(observed)
    for hidden in (
        "split:test",
        "split_assignment_hash",
        "manifest_hash",
        "raw_artifact_hashes",
        "material_disorder",
        "normalizer:diagnostic-only",
        "classification",
    ):
        assert hidden not in rendered
    privileged = trajectory.privileged_projection().as_record()["payload"]
    assert privileged["trajectory"]["provenance"]["split_id"] == "split:test"  # type: ignore[index]
    assert privileged["trajectory"]["provenance"]["observation_model_id"] == "observation:native-solver-state"  # type: ignore[index]
    assert privileged["trajectory"]["provenance"]["boundary_condition_id"] == "boundary:periodic-cell"  # type: ignore[index]


def test_observed_projection_rejects_innocent_unknown_nested_fields_after_rehash() -> None:
    record = _trajectory().observed_projection("frame:pre").as_record()
    record["payload"]["states"][0]["comment"] = "not part of the schema"  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="unexpected"):
        AccessProjection.from_record(record)


def test_disconnected_component_labels_retain_every_node_after_rupture() -> None:
    trajectory = _trajectory()
    split_components = {
        "node:001": "component:left",
        "node:002": "component:right",
        "node:003": "component:right",
    }
    states = (
        *trajectory.states[:2],
        replace(trajectory.states[2], component_ids=split_components),
        replace(trajectory.states[3], component_ids=split_components),
    )
    replay = TrajectoryRecord.create(
        **{**trajectory.constructor_fields(), "states": states}
    )
    assert set(replay.states[-1].component_ids) == set(replay.static_graph.node_ids)


def test_prescribed_intervention_uses_distinct_phase_and_never_damage_initiation() -> None:
    trajectory = _trajectory()
    parent_control = replace(
        trajectory.controls[0],
        control_id="control:parent-load",
        load_step_id="load-step:parent-load",
    )
    intervention = replace(
        trajectory.controls[0],
        control_family="prescribed_intervention",
        control_kind="prescribed_intervention",
        loading_mode="declared_edge_removal",
        step_index=1,
        progress_increment=0.0,
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        prescribed_removal_edge_ids=("edge:001",),
    )
    pre = replace(
        trajectory.states[1],
        phase="pre_intervention",
        source_phase=None,
    )
    event = replace(
        trajectory.events[0],
        event_id="event:prescribed-001",
        event_source="prescribed_intervention",
        criterion_name=None,
        criterion_value=None,
        criterion_unit=None,
    )
    replay = TrajectoryRecord.create(
        **{
            **trajectory.constructor_fields(),
            "controls": (parent_control, intervention),
            "states": (trajectory.states[0], pre, *trajectory.states[2:]),
            "events": (event,),
            "termination_reason": "completed_schedule",
            "censoring": _right_censored(),
        }
    )
    assert replay.events[0].event_source == "prescribed_intervention"
    assert replay.censoring.damage_initiation.status == "right_censored"


def test_schema_v1_rejects_unrepresented_local_stress_capability() -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="local_stress"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "capabilities": replace(trajectory.capabilities, local_stress=True),
            }
        )


def test_nonempty_graph_requires_one_immutable_threshold_per_edge() -> None:
    trajectory = _trajectory()
    privileged = replace(
        trajectory.privileged,
        threshold_values=NamedScalars({}, {}),
    )
    with pytest.raises(SchemaValidationError, match="threshold_values"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (trajectory.states[0],),
                "events": (),
                "privileged": privileged,
                "censoring": _right_censored(),
            }
        )


def test_invalid_reference_cannot_retain_accepted_material_event() -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="invalid_reference"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "quality_status": "invalid",
                "termination_reason": "invalid_reference",
            }
        )


def test_observed_material_event_id_must_remain_sha256_after_rehash() -> None:
    record = _trajectory().observed_projection("frame:post-equilibrium").as_record()
    record["payload"]["event_history"][0]["event_id"] = "event:not-a-hash"  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="event_id|SHA-256"):
        AccessProjection.from_record(record)


def test_component_labels_cannot_rename_without_topology_change() -> None:
    trajectory = _trajectory()
    renamed = replace(
        trajectory.states[1],
        component_ids={node_id: "component:renamed" for node_id in trajectory.static_graph.node_ids},
    )
    with pytest.raises(SchemaValidationError, match="component.*rename|stable component"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (trajectory.states[0], renamed, *trajectory.states[2:]),
            }
        )


def test_surviving_edge_image_cannot_rebranch_during_same_position_deletion() -> None:
    trajectory = _trajectory()
    rebranched_edge = replace(
        trajectory.states[2].edges[1],
        image_offset_n_ij=(0, 0),
        length_nm=0.764,
    )
    rebranched = replace(
        trajectory.states[2],
        edges=(trajectory.states[2].edges[0], rebranched_edge),
    )
    with pytest.raises(SchemaValidationError, match="image.*surviving|rebranch"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (*trajectory.states[:2], rebranched, trajectory.states[3]),
            }
        )


def test_reference_factory_hashes_normalized_integer_reals() -> None:
    graph = _graph()
    reference = ReferenceStateRecord.create(
        reference_state_id="reference:fixed-cell-001",
        physics_profile_id="reviewed_physics_provisional_v0",
        physics_profile_hash=_hash("b"),
        static_graph_hash=graph.graph_hash,
        cell=_reference_cell(),
        node_positions_nm={
            "node:001": (0, 0),
            "node:002": (1, 0),
            "node:003": (2, 0),
        },
        total_tension_pN_per_nm=((0, 0), (0, 0)),
        minimization=ConvergenceRecord(
            converged=True,
            accepted=True,
            iterations=1,
            max_iterations=2,
            residual_force_pN=0,
            force_tolerance_pN=1,
            reason="converged",
        ),
    )
    assert ReferenceStateRecord.from_record(reference.as_record()) == reference


def test_intervention_cannot_advance_load_without_mechanical_target_or_keep_stale_cell() -> None:
    trajectory = _trajectory()
    parent = replace(
        trajectory.controls[0],
        control_id="control:parent",
        load_step_id="load-step:parent",
    )
    intervention = replace(
        trajectory.controls[0],
        control_id="control:intervention",
        load_step_id="load-step:intervention",
        control_family="prescribed_intervention",
        control_kind="prescribed_intervention",
        loading_mode="local_weakening",
        step_index=1,
        load_coordinate=0.2,
        path_progress=0.2,
        progress_increment=0.1,
        absolute_deformation_gradient=None,
        incremental_deformation_gradient=None,
        local_weakening=(EdgeParameterChange("edge:002", ("K",), 0.5),),
    )
    weakened_edges = (
        trajectory.states[0].edges[0],
        replace(trajectory.states[0].edges[1], effective_parameters=_parameters(2785.0)),
    )
    stale = replace(
        trajectory.states[0],
        load_step_id=intervention.load_step_id,
        control_id=intervention.control_id,
        load_coordinate=0.2,
        path_progress=0.2,
        edges=weakened_edges,
    )
    censoring = replace(
        _right_censored(),
        damage_initiation=replace(
            _right_censored().damage_initiation,
            load_coordinate=0.2,
            path_progress=0.2,
        ),
    )
    with pytest.raises(SchemaValidationError, match="intervention.*load|mechanical target"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "controls": (parent, intervention),
                "states": (stale,),
                "events": (),
                "censoring": censoring,
            }
        )
    same_load_intervention = replace(
        intervention,
        load_coordinate=0.1,
        path_progress=0.1,
        progress_increment=0.0,
    )
    wrong_cell = replace(
        stale,
        load_coordinate=0.1,
        path_progress=0.1,
        cell=_reference_cell(),
    )
    with pytest.raises(SchemaValidationError, match="absolute deformation gradient"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "controls": (parent, same_load_intervention),
                "states": (wrong_cell,),
                "events": (),
                "censoring": _right_censored(),
            }
        )


def test_event_sequence_order_cannot_reverse_linked_state_chronology() -> None:
    trajectory = _two_event_trajectory()
    first, second = trajectory.events
    reversed_events = (
        replace(second, sequence_index=0, cascade_parent_event_id=None),
        replace(first, sequence_index=1),
    )
    censoring = replace(
        trajectory.censoring,
        damage_initiation=replace(
            trajectory.censoring.damage_initiation,
            evidence_id=second.event_id,
        ),
    )
    with pytest.raises(SchemaValidationError, match="event sequence.*chronolog"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "events": reversed_events,
                "censoring": censoring,
            }
        )


def test_target_projection_after_first_event_preserves_historical_damage_endpoint() -> None:
    trajectory = _two_event_trajectory()
    projection = trajectory.target_projection("frame:post-equilibrium")
    assert AccessProjection.from_record(projection.as_record()) == projection
    projection.validate_against(trajectory)


def test_target_damage_context_rejects_unknown_edge_after_rehash() -> None:
    record = _two_event_trajectory().target_projection(
        "frame:post-equilibrium"
    ).as_record()
    record["payload"]["damage_initiation_event"]["edge_id"] = "edge:foreign"  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="damage context.*edge|unknown edge"):
        AccessProjection.from_record(record)


def test_future_damage_context_must_equal_first_future_material_event() -> None:
    record = _trajectory().target_projection("frame:accepted").as_record()
    forged_id = _hash("6")
    record["payload"]["damage_initiation_event"]["event_id"] = forged_id  # type: ignore[index]
    record["payload"]["censoring"]["damage_initiation"]["evidence_id"] = forged_id  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="first future material event"):
        AccessProjection.from_record(record)


def test_target_future_event_must_match_exact_topology_and_angle_delta() -> None:
    record = _trajectory().target_projection("frame:accepted").as_record()
    derived_edge_two_ratio = 3.636 / 1.03
    for event in (
        record["payload"]["events"][0],  # type: ignore[index]
        record["payload"]["damage_initiation_event"],  # type: ignore[index]
    ):
        event["edge_id"] = "edge:002"
        event["removed_angle_ids"] = []
        event["criterion_value"] = derived_edge_two_ratio
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="edge delta|angle delta"):
        AccessProjection.from_record(record)


def test_target_future_event_identity_must_match_endpoint_provenance() -> None:
    record = _trajectory().target_projection("frame:accepted").as_record()
    event = record["payload"]["events"][0]  # type: ignore[index]
    event["damage_law_id"] = "law:foreign"
    event["damage_law_hash"] = _hash("4")
    event["threshold_realization_id"] = _hash("5")
    event["physics_profile_id"] = "profile:foreign"
    event["physics_profile_hash"] = _hash("6")
    event["reference_state_id"] = "reference:foreign"
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="law|profile|reference|realization"):
        AccessProjection.from_record(record)


def test_observed_event_history_must_match_exact_topology_and_angle_delta() -> None:
    record = _trajectory().observed_projection("frame:post-equilibrium").as_record()
    event = record["payload"]["event_history"][0]  # type: ignore[index]
    event["edge_id"] = "edge:002"
    event["removed_angle_ids"] = []
    event["criterion_value"] = 3.636 / 1.03
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="edge delta|angle delta"):
        AccessProjection.from_record(record)


def test_observed_material_criterion_must_match_linked_pre_state_mechanics() -> None:
    record = _trajectory().observed_projection("frame:post-equilibrium").as_record()
    record["payload"]["event_history"][0]["criterion_value"] = 999.0  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="criterion.*pre-state"):
        AccessProjection.from_record(record)


def test_target_material_criterion_must_match_linked_pre_state_mechanics() -> None:
    record = _trajectory().target_projection("frame:accepted").as_record()
    record["payload"]["events"][0]["criterion_value"] = 999.0  # type: ignore[index]
    record["payload"]["damage_initiation_event"]["criterion_value"] = 999.0  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="criterion.*pre-state"):
        AccessProjection.from_record(record)


def test_observed_state_load_and_progress_must_match_referenced_control() -> None:
    record = _trajectory().observed_projection("frame:post-equilibrium").as_record()
    record["payload"]["states"][0]["load_coordinate"] = 0.05  # type: ignore[index]
    record["payload"]["states"][0]["path_progress"] = 0.05  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="state.*control|load coordinate"):
        AccessProjection.from_record(record)


def test_target_anchor_load_and_progress_must_match_referenced_control() -> None:
    record = _trajectory().target_projection("frame:accepted").as_record()
    record["payload"]["anchor_state"]["load_coordinate"] = 0.05  # type: ignore[index]
    record["payload"]["anchor_state"]["path_progress"] = 0.05  # type: ignore[index]
    record["projection_hash"] = AccessProjection.compute_hash(
        record["access_kind"], record["anchor_frame_id"], record["payload"]
    )
    with pytest.raises(SchemaValidationError, match="state.*control|load coordinate"):
        AccessProjection.from_record(record)


def test_public_constructor_and_nested_replay_cannot_bypass_hash_or_order_binding() -> None:
    trajectory = _trajectory()
    with pytest.raises(SchemaValidationError, match="record_hash"):
        TrajectoryRecord(
            **trajectory.constructor_fields(),
            record_hash=_hash("0"),
        )

    reordered = trajectory.as_record()
    reordered["static_graph"]["nodes"].reverse()  # type: ignore[index,union-attr]
    with pytest.raises(SchemaValidationError, match="canonical opaque-ID order"):
        TrajectoryRecord.from_record(reordered)

    duplicate = trajectory.as_record()
    duplicate["states"][0]["edges"][1] = duplicate["states"][0]["edges"][0]  # type: ignore[index]
    with pytest.raises(SchemaValidationError, match="unique canonical opaque IDs"):
        TrajectoryRecord.from_record(duplicate)


def test_source_phase_forgery_fails_in_direct_construction_and_replay() -> None:
    state = _trajectory().states[1]
    with pytest.raises(SchemaValidationError, match="source phase"):
        replace(state, source_phase="post_event_relaxed")
    record = state.as_record()
    record["source_phase"] = "post_event_relaxed"
    with pytest.raises(SchemaValidationError, match="source phase"):
        StateRecord.from_record(record)


@pytest.mark.parametrize(
    "constraints",
    [
        {"node:001": (False, False)},
        {"node:001": (1, False)},
        {"node:001": (True,)},
    ],
)
def test_constraint_dofs_reject_ambiguous_or_empty_masks(
    constraints: Mapping[str, tuple[object, ...]],
) -> None:
    with pytest.raises(SchemaValidationError, match="constrained_dofs"):
        replace(_control(), constrained_dofs=constraints)
    with pytest.raises(SchemaValidationError, match="unknown nodes"):
        trajectory = _trajectory()
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "controls": (replace(_control(), constrained_dofs={"node:missing": (True, False)}),),
            }
        )
