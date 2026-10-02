"""Persistent physical topology for quasi-static fracture execution.

The registry consumes authoritative source image offsets.  Nearest-image
inference is deliberately restricted to a separately named fixture helper.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Integral, Real
from types import MappingProxyType
from typing import Mapping, Sequence

import numpy as np


TOPOLOGY_SCHEMA_VERSION = "pgworld.fracture_topology.v1"
_TOL = 1.0e-10
_HASH_RE = __import__("re").compile(r"^sha256:[0-9a-f]{64}$")


class TopologyValidationError(ValueError):
    """Raised when a physical topology identity is ambiguous or inconsistent."""


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise TopologyValidationError(f"{field} must be a nonempty trimmed string")
    if any(ord(char) < 32 for char in value):
        raise TopologyValidationError(f"{field} cannot contain control characters")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise TopologyValidationError(f"{field} must be a positive integer")
    return int(value)


def _finite_vector(value: object, size: int, field: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise TopologyValidationError(f"{field} must be a finite numeric vector") from error
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise TopologyValidationError(f"{field} must be a finite length-{size} vector")
    result = np.array(result, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _int_pair(value: object, field: str) -> tuple[int, int]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence) or len(value) != 2:
        raise TopologyValidationError(f"{field} must be two signed integers")
    if any(isinstance(item, bool) or not isinstance(item, Integral) for item in value):
        raise TopologyValidationError(f"{field} must be two signed integers")
    return (int(value[0]), int(value[1]))


def _stable_sequence(value: object, field: str, size: int | None = None) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise TopologyValidationError(f"{field} must be a stable-ID sequence")
    result = tuple(_string(item, field) for item in value)
    if size is not None and len(result) != size:
        raise TopologyValidationError(f"{field} must contain exactly {size} IDs")
    if len(set(result)) != len(result):
        raise TopologyValidationError(f"{field} contains duplicate IDs")
    return result


def _canonical_hash(record: object) -> str:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _row(value: object, expected: set[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise TopologyValidationError(f"{field} must be an object with string keys")
    missing = expected - set(value); extra = set(value) - expected
    if missing or extra:
        raise TopologyValidationError(f"{field} fields mismatch; missing={sorted(missing)}, unexpected={sorted(extra)}")
    return value


@dataclass(frozen=True, init=False)
class Cell2D:
    matrix_nm: np.ndarray
    origin_nm: np.ndarray
    periodic: tuple[bool, bool]

    def __init__(self, matrix_nm: object, origin_nm: object, periodic: object):
        try:
            matrix = np.asarray(matrix_nm, dtype=float)
        except (TypeError, ValueError) as error:
            raise TopologyValidationError("matrix_nm must be a finite 2x2 matrix") from error
        if matrix.shape != (2, 2) or not np.all(np.isfinite(matrix)):
            raise TopologyValidationError("matrix_nm must be a finite 2x2 matrix")
        if float(np.linalg.det(matrix)) <= _TOL:
            raise TopologyValidationError("matrix_nm must have positive area")
        matrix = np.array(matrix, copy=True)
        matrix.setflags(write=False)
        if isinstance(periodic, (str, bytes, Mapping)) or not isinstance(periodic, Sequence) or len(periodic) != 2 or any(type(item) is not bool for item in periodic):
            raise TopologyValidationError("periodic must be two booleans")
        object.__setattr__(self, "matrix_nm", matrix)
        object.__setattr__(self, "origin_nm", _finite_vector(origin_nm, 2, "origin_nm"))
        object.__setattr__(self, "periodic", (periodic[0], periodic[1]))

    def as_record(self) -> dict[str, object]:
        return {"matrix_nm": self.matrix_nm.tolist(), "origin_nm": self.origin_nm.tolist(), "periodic": list(self.periodic)}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "Cell2D":
        if not isinstance(value, Mapping) or set(value) != {"matrix_nm", "origin_nm", "periodic"}:
            raise TopologyValidationError("cell record fields are invalid")
        return cls(value["matrix_nm"], value["origin_nm"], value["periodic"])


@dataclass(frozen=True)
class NodeTopology:
    stable_node_id: str
    solver_atom_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "stable_node_id", _string(self.stable_node_id, "stable_node_id"))
        object.__setattr__(self, "solver_atom_id", _positive_int(self.solver_atom_id, "solver_atom_id"))

    def as_record(self) -> dict[str, object]:
        return {"stable_node_id": self.stable_node_id, "solver_atom_id": self.solver_atom_id}


@dataclass(frozen=True)
class BondTopology:
    stable_bond_id: str
    node_i: str
    node_j: str
    solver_bond_type: int
    chemical_type: str
    image_offset_n_ij: tuple[int, int]
    source_displacement_nm: tuple[float, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stable_bond_id", _string(self.stable_bond_id, "stable_bond_id"))
        object.__setattr__(self, "node_i", _string(self.node_i, "node_i"))
        object.__setattr__(self, "node_j", _string(self.node_j, "node_j"))
        if self.node_i == self.node_j:
            raise TopologyValidationError("bond endpoints must differ")
        object.__setattr__(self, "solver_bond_type", _positive_int(self.solver_bond_type, "solver_bond_type"))
        object.__setattr__(self, "chemical_type", _string(self.chemical_type, "chemical_type"))
        object.__setattr__(self, "image_offset_n_ij", _int_pair(self.image_offset_n_ij, "image_offset_n_ij"))
        displacement = _finite_vector(self.source_displacement_nm, 2, "source_displacement_nm")
        if float(np.linalg.norm(displacement)) <= _TOL:
            raise TopologyValidationError("source displacement cannot have zero length")
        object.__setattr__(self, "source_displacement_nm", tuple(float(v) for v in displacement))

    def as_record(self) -> dict[str, object]:
        return {
            "stable_bond_id": self.stable_bond_id,
            "node_i": self.node_i,
            "node_j": self.node_j,
            "solver_bond_type": self.solver_bond_type,
            "chemical_type": self.chemical_type,
            "image_offset_n_ij": list(self.image_offset_n_ij),
            "source_displacement_nm": list(self.source_displacement_nm),
        }


@dataclass(frozen=True)
class AngleTopology:
    stable_angle_id: str
    node_ids: tuple[str, str, str]
    solver_angle_type: int
    dependent_bond_ids: tuple[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stable_angle_id", _string(self.stable_angle_id, "stable_angle_id"))
        object.__setattr__(self, "node_ids", _stable_sequence(self.node_ids, "angle node_ids", 3))
        object.__setattr__(self, "solver_angle_type", _positive_int(self.solver_angle_type, "solver_angle_type"))
        object.__setattr__(self, "dependent_bond_ids", _stable_sequence(self.dependent_bond_ids, "dependent_bond_ids", 2))

    def as_record(self) -> dict[str, object]:
        return {"stable_angle_id": self.stable_angle_id, "node_ids": list(self.node_ids), "solver_angle_type": self.solver_angle_type, "dependent_bond_ids": list(self.dependent_bond_ids)}


@dataclass(frozen=True)
class TopologyMutationPlan:
    plan_id: str
    pre_topology_state_id: str
    removed_bond_id: str
    removed_angle_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if _HASH_RE.fullmatch(self.pre_topology_state_id) is None:
            raise TopologyValidationError("pre_topology_state_id must be a sha256 digest")
        object.__setattr__(self, "removed_bond_id", _string(self.removed_bond_id, "removed_bond_id"))
        removed = _stable_sequence(self.removed_angle_ids, "removed_angle_ids")
        if removed != tuple(sorted(removed)):
            raise TopologyValidationError("removed_angle_ids must be canonical sorted IDs")
        object.__setattr__(self, "removed_angle_ids", removed)
        if self.plan_id != _canonical_hash(self._body()):
            raise TopologyValidationError("plan_id does not match mutation plan")

    def _body(self) -> dict[str, object]:
        return {"pre_topology_state_id": self.pre_topology_state_id, "removed_bond_id": self.removed_bond_id, "removed_angle_ids": list(self.removed_angle_ids)}

    def as_record(self) -> dict[str, object]:
        return {"plan_id": self.plan_id, **self._body()}

    @classmethod
    def create(cls, pre_topology_state_id: str, removed_bond_id: str, removed_angle_ids: Sequence[str]) -> "TopologyMutationPlan":
        validated = tuple(sorted(_stable_sequence(removed_angle_ids, "removed_angle_ids")))
        body = {"pre_topology_state_id": pre_topology_state_id, "removed_bond_id": removed_bond_id, "removed_angle_ids": list(validated)}
        return cls(_canonical_hash(body), pre_topology_state_id, removed_bond_id, validated)

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "TopologyMutationPlan":
        row = _row(value, {"plan_id", "pre_topology_state_id", "removed_bond_id", "removed_angle_ids"}, "mutation plan")
        return cls(row["plan_id"], row["pre_topology_state_id"], row["removed_bond_id"], tuple(_stable_sequence(row["removed_angle_ids"], "removed_angle_ids")))  # type: ignore[arg-type]


@dataclass(frozen=True)
class TopologyState:
    registry_id: str
    node_ids: tuple[str, ...]
    alive_bond_ids: tuple[str, ...]
    alive_angle_ids: tuple[str, ...]
    components: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.registry_id, str) or _HASH_RE.fullmatch(self.registry_id) is None:
            raise TopologyValidationError("registry_id must be a sha256 identity")
        node_ids = _stable_sequence(self.node_ids, "node_ids")
        alive_bonds = _stable_sequence(self.alive_bond_ids, "alive_bond_ids")
        alive_angles = _stable_sequence(self.alive_angle_ids, "alive_angle_ids")
        if node_ids != tuple(sorted(node_ids)) or alive_bonds != tuple(sorted(alive_bonds)) or alive_angles != tuple(sorted(alive_angles)):
            raise TopologyValidationError("topology state IDs must be canonical sorted")
        object.__setattr__(self, "node_ids", node_ids)
        object.__setattr__(self, "alive_bond_ids", alive_bonds)
        object.__setattr__(self, "alive_angle_ids", alive_angles)
        components = tuple(tuple(component) for component in self.components)
        canonical_components = tuple(sorted(tuple(sorted(component)) for component in components))
        if components != canonical_components:
            raise TopologyValidationError("components must be canonical sorted")
        if tuple(sorted(node for component in components for node in component)) != tuple(sorted(self.node_ids)):
            raise TopologyValidationError("components must retain every node exactly once")
        object.__setattr__(self, "components", components)

    @property
    def topology_state_id(self) -> str:
        return _canonical_hash(self._body())

    def _body(self) -> dict[str, object]:
        return {"registry_id": self.registry_id, "node_ids": list(self.node_ids), "alive_bond_ids": list(self.alive_bond_ids), "alive_angle_ids": list(self.alive_angle_ids), "components": [list(component) for component in self.components]}

    def as_record(self) -> dict[str, object]:
        return {"topology_state_id": self.topology_state_id, **self._body()}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "TopologyState":
        row = _row(value, {"topology_state_id", "registry_id", "node_ids", "alive_bond_ids", "alive_angle_ids", "components"}, "topology state")
        node_ids = _stable_sequence(row["node_ids"], "node_ids")
        alive_bonds = _stable_sequence(row["alive_bond_ids"], "alive_bond_ids")
        alive_angles = _stable_sequence(row["alive_angle_ids"], "alive_angle_ids")
        raw_components = row["components"]
        if isinstance(raw_components, (str, bytes, Mapping)) or not isinstance(raw_components, Sequence):
            raise TopologyValidationError("components must be an array")
        components = tuple(_stable_sequence(component, "component") for component in raw_components)
        state = cls(row["registry_id"], node_ids, alive_bonds, alive_angles, components)  # type: ignore[arg-type]
        if row["topology_state_id"] != state.topology_state_id:
            raise TopologyValidationError("topology_state_id does not match state record")
        return state

    @classmethod
    def initial(cls, registry: "TopologyRegistry") -> "TopologyState":
        return registry._state(tuple(b.stable_bond_id for b in registry.bonds), tuple(a.stable_angle_id for a in registry.angles))


class TopologyRegistry:
    """Immutable ID registry and dependency graph for physical topology."""

    __slots__ = ("cell", "nodes", "bonds", "angles", "source_wrapped_positions_nm", "_node", "_bond", "_angle", "_record", "registry_id", "initial_state", "_sealed")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("TopologyRegistry is immutable")
        object.__setattr__(self, name, value)

    def __init__(
        self,
        cell: Cell2D,
        nodes: Sequence[NodeTopology],
        source_wrapped_positions_nm: Mapping[str, object],
        bonds: Sequence[BondTopology],
        angles: Sequence[AngleTopology],
    ) -> None:
        if not isinstance(cell, Cell2D):
            raise TopologyValidationError("cell must be Cell2D")
        if isinstance(nodes, (str, bytes, Mapping)) or isinstance(bonds, (str, bytes, Mapping)) or isinstance(angles, (str, bytes, Mapping)):
            raise TopologyValidationError("topology rows must be sequences")
        nodes = tuple(nodes); bonds = tuple(bonds); angles = tuple(angles)
        if not nodes or any(not isinstance(row, NodeTopology) for row in nodes):
            raise TopologyValidationError("nodes must contain NodeTopology rows")
        if any(not isinstance(row, BondTopology) for row in bonds) or any(not isinstance(row, AngleTopology) for row in angles):
            raise TopologyValidationError("bond/angle rows have invalid types")
        node_ids = [node.stable_node_id for node in nodes]
        atom_ids = [node.solver_atom_id for node in nodes]
        if len(set(node_ids)) != len(node_ids) or len(set(atom_ids)) != len(atom_ids):
            raise TopologyValidationError("duplicate node or solver atom ID")
        positions_raw = source_wrapped_positions_nm
        if not isinstance(positions_raw, Mapping) or any(not isinstance(key, str) for key in positions_raw) or set(positions_raw) != set(node_ids):
            raise TopologyValidationError("source positions must cover exact node universe")
        positions = {node_id: _finite_vector(positions_raw[node_id], 2, f"position[{node_id}]") for node_id in node_ids}
        for node_id, position in positions.items():
            fractional = np.linalg.solve(cell.matrix_nm, position - cell.origin_nm)
            for axis, is_periodic in enumerate(cell.periodic):
                if is_periodic and (fractional[axis] < -_TOL or fractional[axis] >= 1.0):
                    raise TopologyValidationError(f"source_wrapped_positions_nm[{node_id!r}] is outside the periodic primary cell")
        bond_ids = [bond.stable_bond_id for bond in bonds]
        if len(set(bond_ids)) != len(bond_ids):
            raise TopologyValidationError("duplicate stable bond ID")
        ambiguous_bonds: set[tuple[frozenset[str], int]] = set()
        for bond in bonds:
            if bond.node_i not in positions or bond.node_j not in positions:
                raise TopologyValidationError("bond references unknown node")
            key = (frozenset((bond.node_i, bond.node_j)), bond.solver_bond_type)
            if key in ambiguous_bonds:
                raise TopologyValidationError("ambiguous duplicate bond endpoint/type topology")
            ambiguous_bonds.add(key)
            reconstructed = positions[bond.node_j] - positions[bond.node_i] + cell.matrix_nm @ np.asarray(bond.image_offset_n_ij, dtype=float)
            if not np.allclose(reconstructed, bond.source_displacement_nm, rtol=0.0, atol=_TOL):
                raise TopologyValidationError("bond source displacement disagrees with x_j-x_i+H@n_ij")
        by_bond = {bond.stable_bond_id: bond for bond in bonds}
        angle_ids = [angle.stable_angle_id for angle in angles]
        if len(set(angle_ids)) != len(angle_ids):
            raise TopologyValidationError("duplicate stable angle ID")
        ambiguous_angles: set[tuple[str, str, str, int]] = set()
        for angle in angles:
            if any(node not in positions for node in angle.node_ids):
                raise TopologyValidationError("angle references unknown node")
            if any(bond_id not in by_bond for bond_id in angle.dependent_bond_ids):
                raise TopologyValidationError("angle references unknown dependent bond")
            a, center, c = angle.node_ids
            key = (min(a, c), center, max(a, c), angle.solver_angle_type)
            if key in ambiguous_angles:
                raise TopologyValidationError("ambiguous duplicate angle endpoint/type topology")
            ambiguous_angles.add(key)
            expected_segments = {frozenset((a, center)), frozenset((center, c))}
            actual_segments = {frozenset((by_bond[b].node_i, by_bond[b].node_j)) for b in angle.dependent_bond_ids}
            if actual_segments != expected_segments:
                raise TopologyValidationError("angle dependencies do not match its two physical segments")
            if any(by_bond[b].chemical_type != "glycan" for b in angle.dependent_bond_ids):
                raise TopologyValidationError("glycan bending angles require glycan bond dependencies")
        self.cell = cell
        self.nodes = tuple(sorted(nodes, key=lambda row: row.stable_node_id))
        self.bonds = tuple(sorted(bonds, key=lambda row: row.stable_bond_id))
        self.angles = tuple(sorted(angles, key=lambda row: row.stable_angle_id))
        self.source_wrapped_positions_nm = MappingProxyType({key: positions[key] for key in sorted(positions)})
        self._node = MappingProxyType({row.stable_node_id: row for row in self.nodes})
        self._bond = MappingProxyType({row.stable_bond_id: row for row in self.bonds})
        self._angle = MappingProxyType({row.stable_angle_id: row for row in self.angles})
        self._record = _deep_freeze(self._build_record())
        self.registry_id = _canonical_hash(_plain(self._record))
        self.initial_state = TopologyState.initial(self)
        self._sealed = True

    def _build_record(self) -> dict[str, object]:
        return {"schema_version": TOPOLOGY_SCHEMA_VERSION, "cell": self.cell.as_record(), "nodes": [row.as_record() for row in self.nodes], "source_wrapped_positions_nm": [{"stable_node_id": key, "position_nm": self.source_wrapped_positions_nm[key].tolist()} for key in self.source_wrapped_positions_nm], "bonds": [row.as_record() for row in self.bonds], "angles": [row.as_record() for row in self.angles]}

    def as_record(self) -> dict[str, object]:
        return {"registry_id": self.registry_id, **_plain(self._record)}  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "TopologyRegistry":
        row = _row(value, {"registry_id", "schema_version", "cell", "nodes", "source_wrapped_positions_nm", "bonds", "angles"}, "topology registry")
        if row["schema_version"] != TOPOLOGY_SCHEMA_VERSION:
            raise TopologyValidationError("unsupported topology schema")
        def rows(field: str) -> tuple[object, ...]:
            raw = row[field]
            if isinstance(raw, (str, bytes, Mapping)) or not isinstance(raw, Sequence):
                raise TopologyValidationError(f"{field} must be an array")
            return tuple(raw)
        node_rows = rows("nodes")
        nodes = tuple(NodeTopology(**dict(_row(item, {"stable_node_id", "solver_atom_id"}, f"nodes[{index}]"))) for index, item in enumerate(node_rows))
        position_rows = rows("source_wrapped_positions_nm")
        positions: dict[str, object] = {}
        for index, item in enumerate(position_rows):
            parsed = _row(item, {"stable_node_id", "position_nm"}, f"source positions[{index}]")
            stable_id = _string(parsed["stable_node_id"], "stable_node_id")
            if stable_id in positions:
                raise TopologyValidationError("duplicate source position stable_node_id")
            positions[stable_id] = parsed["position_nm"]
        bonds = tuple(BondTopology(**dict(_row(item, {"stable_bond_id", "node_i", "node_j", "solver_bond_type", "chemical_type", "image_offset_n_ij", "source_displacement_nm"}, f"bonds[{index}]"))) for index, item in enumerate(rows("bonds")))
        angles = tuple(AngleTopology(**dict(_row(item, {"stable_angle_id", "node_ids", "solver_angle_type", "dependent_bond_ids"}, f"angles[{index}]"))) for index, item in enumerate(rows("angles")))
        registry = cls(Cell2D.from_record(row["cell"]), nodes, positions, bonds, angles)  # type: ignore[arg-type]
        if registry.registry_id != row["registry_id"]:
            raise TopologyValidationError("registry_id does not match record")
        return registry

    def node(self, stable_id: str) -> NodeTopology:
        try: return self._node[_string(stable_id, "stable_node_id")]
        except KeyError as error: raise TopologyValidationError("unknown stable node ID") from error

    def bond(self, stable_id: str) -> BondTopology:
        try: return self._bond[_string(stable_id, "stable_bond_id")]
        except KeyError as error: raise TopologyValidationError("unknown stable bond ID") from error

    def angle(self, stable_id: str) -> AngleTopology:
        try: return self._angle[_string(stable_id, "stable_angle_id")]
        except KeyError as error: raise TopologyValidationError("unknown stable angle ID") from error

    def bond_displacement_nm(self, stable_id: str) -> np.ndarray:
        bond = self.bond(stable_id)
        result = self.source_wrapped_positions_nm[bond.node_j] - self.source_wrapped_positions_nm[bond.node_i] + self.cell.matrix_nm @ np.asarray(bond.image_offset_n_ij, dtype=float)
        result.setflags(write=False)
        return result

    def plan_bond_removal(self, state: TopologyState, stable_bond_id: str) -> TopologyMutationPlan:
        self.validate_state(state)
        bond = self.bond(stable_bond_id)
        if bond.stable_bond_id not in state.alive_bond_ids:
            raise TopologyValidationError("cannot remove an inactive physical bond")
        dependent = tuple(sorted(angle.stable_angle_id for angle in self.angles if angle.stable_angle_id in state.alive_angle_ids and stable_bond_id in angle.dependent_bond_ids))
        return TopologyMutationPlan.create(state.topology_state_id, stable_bond_id, dependent)

    def apply_plan(self, state: TopologyState, plan: TopologyMutationPlan) -> TopologyState:
        self.validate_state(state)
        if plan.pre_topology_state_id != state.topology_state_id:
            raise TopologyValidationError("stale topology mutation plan")
        expected = self.plan_bond_removal(state, plan.removed_bond_id)
        if plan != expected:
            raise TopologyValidationError("mutation plan does not contain exact dependent angles")
        return self._state(tuple(item for item in state.alive_bond_ids if item != plan.removed_bond_id), tuple(item for item in state.alive_angle_ids if item not in plan.removed_angle_ids))

    def validate_state(self, state: TopologyState) -> None:
        if not isinstance(state, TopologyState) or state.registry_id != self.registry_id or state.node_ids != tuple(node.stable_node_id for node in self.nodes):
            raise TopologyValidationError("topology state belongs to another registry")
        if not set(state.alive_bond_ids) <= set(self._bond) or not set(state.alive_angle_ids) <= set(self._angle):
            raise TopologyValidationError("topology state contains unknown interactions")
        for angle_id in state.alive_angle_ids:
            if not set(self._angle[angle_id].dependent_bond_ids) <= set(state.alive_bond_ids):
                raise TopologyValidationError("alive angle has an inactive dependency")
        if state != self._state(state.alive_bond_ids, state.alive_angle_ids):
            raise TopologyValidationError("topology state components are inconsistent")

    def _state(self, alive_bonds: Sequence[str], alive_angles: Sequence[str]) -> TopologyState:
        alive_bonds = tuple(sorted(alive_bonds)); alive_angles = tuple(sorted(alive_angles))
        adjacency = {node.stable_node_id: set() for node in self.nodes}
        for bond_id in alive_bonds:
            bond = self._bond[bond_id]
            adjacency[bond.node_i].add(bond.node_j); adjacency[bond.node_j].add(bond.node_i)
        components: list[tuple[str, ...]] = []
        unseen = set(adjacency)
        while unseen:
            seed = min(unseen); stack = [seed]; component: set[str] = set()
            while stack:
                node = stack.pop()
                if node in component: continue
                component.add(node); unseen.discard(node); stack.extend(sorted(adjacency[node] - component, reverse=True))
            components.append(tuple(sorted(component)))
        return TopologyState(self.registry_id, tuple(node.stable_node_id for node in self.nodes), alive_bonds, alive_angles, tuple(sorted(components)))


def infer_fixture_image_offset(
    cell: Cell2D,
    position_i_nm: object,
    position_j_nm: object,
    *,
    maximum_fractional_span: float = 0.49,
    ambiguity_tolerance: float = 1.0e-10,
) -> tuple[int, int]:
    """Infer a componentwise fractional image for orthogonal bounded fixtures."""
    if not isinstance(cell, Cell2D):
        raise TopologyValidationError("cell must be Cell2D")
    if isinstance(maximum_fractional_span, bool) or not isinstance(maximum_fractional_span, Real) or not 0.0 < float(maximum_fractional_span) < 0.5:
        raise TopologyValidationError("maximum_fractional_span must lie in (0, 0.5)")
    if isinstance(ambiguity_tolerance, bool) or not isinstance(ambiguity_tolerance, Real) or not math.isfinite(float(ambiguity_tolerance)) or not 0.0 <= float(ambiguity_tolerance) < 0.5:
        raise TopologyValidationError("ambiguity_tolerance must be finite and lie in [0, 0.5)")
    if abs(float(cell.matrix_nm[0, 1])) > _TOL or abs(float(cell.matrix_nm[1, 0])) > _TOL:
        raise TopologyValidationError("fixture image inference supports orthogonal cells only")
    direct = _finite_vector(position_j_nm, 2, "position_j_nm") - _finite_vector(position_i_nm, 2, "position_i_nm")
    fractional = np.linalg.solve(cell.matrix_nm, direct)
    offsets: list[int] = []
    for axis, coordinate in enumerate(fractional):
        if not cell.periodic[axis]:
            offsets.append(0); continue
        nearest = math.floor(float(coordinate) + 0.5)
        local = float(coordinate) - nearest
        if abs(abs(local) - 0.5) <= ambiguity_tolerance:
            raise TopologyValidationError("fixture image inference has a half-cell ambiguity")
        if abs(local) > float(maximum_fractional_span) + ambiguity_tolerance:
            raise TopologyValidationError("fixture image inference has long-edge ambiguity")
        offsets.append(-nearest)
    return (offsets[0], offsets[1])


__all__ = [
    "TOPOLOGY_SCHEMA_VERSION", "AngleTopology", "BondTopology", "Cell2D",
    "NodeTopology", "TopologyMutationPlan", "TopologyRegistry", "TopologyState",
    "TopologyValidationError", "infer_fixture_image_offset",
]
