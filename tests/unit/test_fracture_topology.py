from __future__ import annotations

import numpy as np
import pytest

from pgworld.simulation.topology import (
    AngleTopology,
    BondTopology,
    Cell2D,
    NodeTopology,
    TopologyRegistry,
    TopologyMutationPlan,
    TopologyState,
    TopologyValidationError,
    infer_fixture_image_offset,
)


def _cell() -> Cell2D:
    return Cell2D(
        matrix_nm=((10.0, 2.0), (0.0, 8.0)),
        origin_nm=(-1.0, -2.0),
        periodic=(True, True),
    )


def _nodes() -> tuple[NodeTopology, ...]:
    return tuple(NodeTopology(f"node-{index}", index) for index in range(1, 5))


def test_explicit_non_nearest_signed_image_offset_is_authoritative_and_roundtrips() -> None:
    cell = _cell()
    positions = {
        "node-1": (0.0, 0.0),
        "node-2": (1.0, 0.0),
        "node-3": (2.0, 0.0),
        "node-4": (3.0, 0.0),
    }
    expected = np.array((23.0, 8.0))
    registry = TopologyRegistry(
        cell=cell,
        nodes=_nodes(),
        source_wrapped_positions_nm=positions,
        bonds=(
            BondTopology(
                stable_bond_id="bond-long",
                node_i="node-1",
                node_j="node-2",
                solver_bond_type=7,
                chemical_type="glycan",
                image_offset_n_ij=(2, 1),
                source_displacement_nm=tuple(expected),
            ),
        ),
        angles=(),
    )

    assert registry.bond("bond-long").image_offset_n_ij == (2, 1)
    np.testing.assert_allclose(
        registry.bond_displacement_nm("bond-long"), expected, rtol=0.0, atol=1e-12
    )
    replayed = TopologyRegistry.from_record(registry.as_record())
    assert replayed.as_record() == registry.as_record()
    assert replayed.bond("bond-long").image_offset_n_ij == (2, 1)


def test_registry_rejects_ambiguous_duplicate_endpoint_type_and_bad_displacement() -> None:
    cell = _cell()
    positions = {node.stable_node_id: (float(index), 0.0) for index, node in enumerate(_nodes())}
    first = BondTopology("bond-a", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0))
    duplicate = BondTopology("bond-b", "node-2", "node-1", 1, "glycan", (0, 0), (-1.0, 0.0))
    with pytest.raises(TopologyValidationError, match="ambiguous duplicate"):
        TopologyRegistry(cell, _nodes(), positions, (first, duplicate), ())

    forged = BondTopology("bond-a", "node-1", "node-2", 1, "glycan", (0, 0), (3.0, 0.0))
    with pytest.raises(TopologyValidationError, match="source displacement"):
        TopologyRegistry(cell, _nodes(), positions, (forged,), ())


def test_fixture_inference_rejects_half_cell_tie_and_long_edge_ambiguity() -> None:
    orthogonal = Cell2D(((10.0, 0.0), (0.0, 8.0)), (0.0, 0.0), (True, True))
    with pytest.raises(TopologyValidationError, match="half-cell"):
        infer_fixture_image_offset(orthogonal, (0.0, 0.0), (5.0, 0.0))
    with pytest.raises(TopologyValidationError, match="long-edge"):
        infer_fixture_image_offset(
            orthogonal, (0.0, 0.0), (4.7, 0.0), maximum_fractional_span=0.45
        )


def test_exact_dependent_angles_are_removed_and_disconnected_nodes_are_retained() -> None:
    cell = Cell2D(((10.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    positions = {
        "node-1": (0.0, 0.0),
        "node-2": (1.0, 0.0),
        "node-3": (2.0, 0.0),
        "node-4": (5.0, 5.0),
    }
    bonds = (
        BondTopology("bond-12", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),
        BondTopology("bond-23", "node-2", "node-3", 1, "glycan", (0, 0), (1.0, 0.0)),
    )
    angles = (
        AngleTopology(
            "angle-123", ("node-1", "node-2", "node-3"), 2, ("bond-12", "bond-23")
        ),
    )
    registry = TopologyRegistry(cell, _nodes(), positions, bonds, angles)
    state = TopologyState.initial(registry)
    plan = registry.plan_bond_removal(state, "bond-12")

    assert plan.removed_angle_ids == ("angle-123",)
    assert plan.removed_bond_id == "bond-12"
    next_state = registry.apply_plan(state, plan)
    assert next_state.alive_bond_ids == ("bond-23",)
    assert next_state.alive_angle_ids == ()
    assert next_state.components == (("node-1",), ("node-2", "node-3"), ("node-4",))
    assert next_state.node_ids == ("node-1", "node-2", "node-3", "node-4")


def test_angle_dependencies_must_be_exact_glycan_segments_and_angle_key_is_unambiguous() -> None:
    cell = Cell2D(((10.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    positions = {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)}
    nodes = _nodes()
    bonds = (
        BondTopology("b12", "node-2", "node-1", 1, "glycan", (0, 0), (-1.0, 0.0)),
        BondTopology("b23", "node-2", "node-3", 1, "glycan", (0, 0), (1.0, 0.0)),
        BondTopology("b34", "node-3", "node-4", 1, "glycan", (0, 0), (1.0, 0.0)),
        BondTopology("peptide", "node-1", "node-4", 2, "peptide", (0, 0), (3.0, 0.0)),
        BondTopology("peptide-12", "node-1", "node-2", 2, "peptide", (0, 0), (1.0, 0.0)),
    )
    valid = AngleTopology("a123", ("node-1", "node-2", "node-3"), 1, ("b12", "b23"))
    TopologyRegistry(cell, nodes, positions, bonds, (valid,))

    for invalid in (
        AngleTopology("wrong-edge", ("node-1", "node-2", "node-3"), 1, ("b12", "b34")),
        AngleTopology("wrong-middle", ("node-2", "node-1", "node-3"), 1, ("b12", "b23")),
        AngleTopology("nonglycan", ("node-1", "node-2", "node-3"), 1, ("peptide-12", "b23")),
    ):
        with pytest.raises(TopologyValidationError, match="depend|glycan"):
            TopologyRegistry(cell, nodes, positions, bonds, (invalid,))

    reverse = AngleTopology("a321", ("node-3", "node-2", "node-1"), 1, ("b23", "b12"))
    with pytest.raises(TopologyValidationError, match="ambiguous duplicate angle"):
        TopologyRegistry(cell, nodes, positions, bonds, (valid, reverse))


def test_registry_is_deterministic_under_row_reorder_and_nested_inputs_are_copied() -> None:
    cell = Cell2D(((10.0, -2.0), (0.0, 8.0)), (-4.5, -2.0), (True, True))
    raw_positions = {"node-1": [4.0, 3.0], "node-2": [-4.0, 3.0], "node-3": [-3.0, 3.0], "node-4": [0.0, -1.0]}
    bonds = (
        BondTopology("b12", "node-1", "node-2", 1, "glycan", (1, 0), (2.0, 0.0)),
        BondTopology("b23", "node-2", "node-3", 1, "glycan", (0, 0), (1.0, 0.0)),
    )
    angle = AngleTopology("a123", ("node-1", "node-2", "node-3"), 1, ("b12", "b23"))
    first = TopologyRegistry(cell, _nodes(), raw_positions, bonds, (angle,))
    second = TopologyRegistry(cell, tuple(reversed(_nodes())), dict(reversed(tuple(raw_positions.items()))), tuple(reversed(bonds)), (angle,))
    assert first.as_record() == second.as_record()
    assert first.initial_state == second.initial_state
    raw_positions["node-1"][0] = 999.0
    assert first.source_wrapped_positions_nm["node-1"].tolist() == [4.0, 3.0]
    with pytest.raises(ValueError):
        first.source_wrapped_positions_nm["node-1"][0] = 1.0


def test_production_registry_allows_explicit_half_cell_branch_and_never_infers_it() -> None:
    cell = Cell2D(((10.0, 0.0), (0.0, 8.0)), (0.0, 0.0), (True, True))
    positions = {"node-1": (0.0, 0.0), "node-2": (5.0, 0.0), "node-3": (1.0, 1.0), "node-4": (2.0, 1.0)}
    registry = TopologyRegistry(
        cell,
        _nodes(),
        positions,
        (BondTopology("half", "node-1", "node-2", 1, "glycan", (-1, 0), (-5.0, 0.0)),),
        (),
    )
    assert registry.bond("half").image_offset_n_ij == (-1, 0)
    np.testing.assert_allclose(registry.bond_displacement_nm("half"), (-5.0, 0.0))


def test_registry_replay_rejects_unknown_fields_and_hash_tampering() -> None:
    registry = TopologyRegistry(
        _cell(), _nodes(),
        {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)},
        (BondTopology("b", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),), (),
    )
    record = registry.as_record()
    record["unexpected"] = True
    with pytest.raises(TopologyValidationError):
        TopologyRegistry.from_record(record)
    record = registry.as_record()
    record["registry_id"] = "sha256:" + "0" * 64
    with pytest.raises(TopologyValidationError, match="registry_id"):
        TopologyRegistry.from_record(record)


def test_registry_and_nested_record_are_immutable_after_identity_hashing() -> None:
    registry = TopologyRegistry(
        _cell(), _nodes(),
        {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)},
        (BondTopology("b", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),), (),
    )
    identity = registry.registry_id
    with pytest.raises((AttributeError, TypeError)):
        registry.registry_id = "sha256:" + "0" * 64
    with pytest.raises((AttributeError, TypeError)):
        registry._record["schema_version"] = "forged"
    assert registry.registry_id == identity


def test_state_rejects_alive_angle_with_dead_dependency_and_noncanonical_components() -> None:
    cell = Cell2D(((10.0, 0.0), (0.0, 10.0)), (0.0, 0.0), (True, True))
    registry = TopologyRegistry(
        cell, _nodes(),
        {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)},
        (
            BondTopology("b12", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),
            BondTopology("b23", "node-2", "node-3", 1, "glycan", (0, 0), (1.0, 0.0)),
        ),
        (AngleTopology("a123", ("node-1", "node-2", "node-3"), 1, ("b12", "b23")),),
    )
    forged = TopologyState(
        registry.registry_id,
        registry.initial_state.node_ids,
        ("b23",),
        ("a123",),
        (("node-1",), ("node-2", "node-3"), ("node-4",)),
    )
    with pytest.raises(TopologyValidationError, match="depend"):
        registry.validate_state(forged)
    with pytest.raises(TopologyValidationError, match="canonical"):
        TopologyState(
            registry.registry_id,
            registry.initial_state.node_ids,
            registry.initial_state.alive_bond_ids,
            registry.initial_state.alive_angle_ids,
            (("node-3", "node-2", "node-1"), ("node-4",)),
        )


def test_registry_replay_rejects_duplicate_nested_rows_without_collapsing() -> None:
    registry = TopologyRegistry(
        _cell(), _nodes(),
        {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)},
        (BondTopology("b", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),), (),
    )
    record = registry.as_record()
    record["source_wrapped_positions_nm"].append(dict(record["source_wrapped_positions_nm"][0]))
    with pytest.raises(TopologyValidationError, match="duplicate"):
        TopologyRegistry.from_record(record)


def test_state_and_mutation_plan_have_strict_hash_bound_replay() -> None:
    registry = TopologyRegistry(
        _cell(), _nodes(),
        {"node-1": (0.0, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)},
        (BondTopology("b", "node-1", "node-2", 1, "glycan", (0, 0), (1.0, 0.0)),), (),
    )
    state = TopologyState.from_record(registry.initial_state.as_record())
    assert state == registry.initial_state
    state_record = state.as_record(); state_record["topology_state_id"] = "sha256:" + "0" * 64
    with pytest.raises(TopologyValidationError, match="topology_state_id"):
        TopologyState.from_record(state_record)
    state_record = state.as_record(); state_record["unexpected"] = True
    with pytest.raises(TopologyValidationError):
        TopologyState.from_record(state_record)
    plan = registry.plan_bond_removal(state, "b")
    assert TopologyMutationPlan.from_record(plan.as_record()) == plan
    forged = plan.as_record(); forged["removed_bond_id"] = "foreign"
    with pytest.raises(TopologyValidationError):
        TopologyMutationPlan.from_record(forged)


def test_fixture_inference_validates_tolerance_and_rejects_skew_cell() -> None:
    with pytest.raises(TopologyValidationError, match="ambiguity_tolerance"):
        infer_fixture_image_offset(_cell(), (0.0, 0.0), (1.0, 0.0), ambiguity_tolerance=float("nan"))
    with pytest.raises(TopologyValidationError, match="orthogonal"):
        infer_fixture_image_offset(_cell(), (0.0, 0.0), (1.0, 0.0))


def test_wrapped_domain_does_not_shrink_near_upper_face_but_rejects_exact_upper() -> None:
    cell = Cell2D(((10.0, 0.0), (0.0, 8.0)), (0.0, 0.0), (True, True))
    near = 10.0 * 0.999999999995
    nodes = _nodes()
    valid_positions = {"node-1": (near, 0.0), "node-2": (1.0, 0.0), "node-3": (2.0, 0.0), "node-4": (3.0, 0.0)}
    TopologyRegistry(cell, nodes, valid_positions, (), ())
    invalid_positions = dict(valid_positions); invalid_positions["node-1"] = (10.0, 0.0)
    with pytest.raises(TopologyValidationError, match="outside"):
        TopologyRegistry(cell, nodes, invalid_positions, (), ())


def test_mutation_plan_create_rejects_string_angle_collection() -> None:
    with pytest.raises(TopologyValidationError, match="sequence"):
        TopologyMutationPlan.create("sha256:" + "0" * 64, "bond", "angle")


@pytest.mark.parametrize(
    "bad_id",
    ["", "  ", "node\n1"],
)
def test_opaque_ids_fail_closed(bad_id: str) -> None:
    with pytest.raises(TopologyValidationError):
        NodeTopology(bad_id, 1)
