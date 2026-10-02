from __future__ import annotations

from dataclasses import replace
import math
from types import MappingProxyType
from typing import Any, Mapping

import pytest

from pgworld.data.schema import (
    ACCESS_SCHEMA_VERSION,
    TRAJECTORY_SCHEMA_VERSION,
    AccessProjection,
    AngleReference,
    AngleState,
    CapabilityFlags,
    Cell2D,
    CensoringRecord,
    ControlRecord,
    ConvergenceRecord,
    DiagnosticTrial,
    EdgeParameterChange,
    EdgeReference,
    EdgeState,
    EventRecord,
    NamedScalars,
    NodeReference,
    NodeState,
    NormalizerRecord,
    PressureDerivation,
    PrivilegedRecord,
    ProvenanceRecord,
    SchemaValidationError,
    StateRecord,
    StaticGraph,
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
            "glycan",
            1.03,
            _parameters(),
            (0, 0),
        ),
        EdgeReference(
            "edge:002",
            ("node:002", "node:003"),
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


def _edge_states(*, ruptured: bool = False) -> tuple[EdgeState, ...]:
    first = EdgeState(
        edge_id="edge:001",
        alive=not ruptured,
        image_offset_n_ij=(0, 0),
        effective_parameters=_parameters(),
        damage_value=1.0 if ruptured else 0.0,
        damage_unit="dimensionless",
        length_nm=None if ruptured else 1.0,
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
        length_nm=3.0,
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
        edges=_edge_states(ruptured=ruptured),
        angles=(AngleState("angle:001", not ruptured),),
        component_ids={
            "node:001": "component:001",
            "node:002": "component:001",
            "node:003": "component:001",
        },
        total_tension_pN_per_nm=((2.0, 0.0), (0.0, 1.0)),
        incremental_tension_pN_per_nm=((0.2, 0.0), (0.0, 0.1)),
        energy_terms=NamedScalars(
            {"bond": 0.5, "angle": 0.1},
            {"bond": "pN nm", "angle": "pN nm"},
        ),
        convergence=ConvergenceRecord(
            converged=phase != "post_topology_change",
            accepted=True,
            iterations=12 if phase != "post_topology_change" else 0,
            residual_force_pN=1e-10 if phase != "post_topology_change" else 2.0,
            reason="converged" if phase != "post_topology_change" else "not_relaxed_by_phase",
        ),
    )


def _event() -> EventRecord:
    return EventRecord(
        event_id="event:material-001",
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
        damage_law_hash=_hash("d"),
    )


def _provenance() -> ProvenanceRecord:
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
        reference_state_hash=_hash("c"),
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
        boundary_condition_hash=_hash("2"),
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


def _trajectory() -> TrajectoryRecord:
    states = (
        _state(0, "frame:accepted", "accepted_equilibrium", 0),
        _state(
            1,
            "frame:pre",
            "pre_rupture",
            1,
            source_phase="pre_delete_relaxed",
        ),
        _state(
            2,
            "frame:post-topology",
            "post_topology_change",
            2,
            ruptured=True,
            source_phase="post_delete_unrelaxed",
        ),
        _state(
            3,
            "frame:post-equilibrium",
            "post_event_equilibrium",
            3,
            ruptured=True,
            source_phase="post_event_relaxed",
            relaxed_shift=0.02,
        ),
    )
    return TrajectoryRecord.create(
        provenance=_provenance(),
        capabilities=_capabilities(),
        static_graph=_graph(),
        controls=(_control(),),
        states=states,
        events=(_event(),),
        privileged=_privileged(),
        quality_status="accepted",
        termination_reason="damage_initiation",
        censoring=CensoringRecord(
            status="observed",
            endpoint="damage_initiation",
            load_coordinate=0.1,
            load_coordinate_unit="dimensionless",
            path_progress=0.1,
            progress_unit="dimensionless",
            evidence_event_id="event:material-001",
        ),
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
    with pytest.raises(SchemaValidationError, match="record_hash"):
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
        edges=_edge_states(ruptured=False),
        angles=(AngleState("angle:001", True),),
    )
    with pytest.raises(SchemaValidationError, match="irreversible|resurrect"):
        TrajectoryRecord.create(
            **{**trajectory.constructor_fields(), "states": (*trajectory.states[:-1], healed)}
        )

    repeat = replace(
        trajectory.events[0],
        event_id="event:material-002",
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
                "censoring": CensoringRecord.right_censored(
                    "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
                ),
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
                "censoring": CensoringRecord.right_censored(
                    "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
                ),
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
            "censoring": CensoringRecord.right_censored(
                "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
            ),
        }
    )
    assert censored.censoring.status == "right_censored"
    with pytest.raises(SchemaValidationError, match="censor"):
        TrajectoryRecord.create(
            **{
                **trajectory.constructor_fields(),
                "states": (trajectory.states[0],),
                "events": (),
                "termination_reason": "damage_initiation",
                "censoring": CensoringRecord.right_censored(
                    "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
                ),
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
    assert "event:material-001" not in repr(payload)


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
        "event:material-001"
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
                "censoring": CensoringRecord.right_censored(
                    "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
                ),
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
            "states": (trajectory.states[0], pre, *trajectory.states[2:]),
            "events": (event,),
            "termination_reason": "completed_schedule",
            "censoring": CensoringRecord.right_censored(
                "damage_initiation", 0.1, "dimensionless", 0.1, "dimensionless"
            ),
        }
    )
    assert replay.events[0].event_source == "prescribed_intervention"
    assert replay.censoring.status == "right_censored"


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
