"""Versioned immutable graph-trajectory records and access projections.

This module defines the in-memory/replay contract for P03-01.  It deliberately
does not implement HDF5, dataset export, or solver adapters.  Records use
opaque string identities, exact schema versions, content hashes, and explicit
observed/target/privileged projections so later model code cannot obtain
privileged fields by traversing a convenient catch-all manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Integral, Real
import re
from types import MappingProxyType
from typing import Mapping, Sequence


TRAJECTORY_SCHEMA_VERSION = "pgworld.trajectory.v1"
ACCESS_SCHEMA_VERSION = "pgworld.trajectory_access.v1"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CANONICAL_PHASES = {
    "accepted_equilibrium",
    "pre_intervention",
    "pre_rupture",
    "post_topology_change",
    "post_event_equilibrium",
}
_P02_PHASE_MAP = {
    "pre_delete_relaxed": "pre_rupture",
    "post_delete_unrelaxed": "post_topology_change",
    "post_event_relaxed": "post_event_equilibrium",
}
_QUALITY_STATUSES = {"accepted", "rejected", "incomplete", "invalid"}
_TERMINATION_REASONS = {
    "completed_schedule",
    "damage_initiation",
    "event_budget_exhausted",
    "relaxation_budget_exhausted",
    "solver_failure",
    "invalid_reference",
    "user_stopped",
    "incomplete",
}
_SOURCE_KINDS = {
    "lammps_reference",
    "model_prediction",
    "experimental",
    "test_fixture",
}
_EVENT_SOURCES = {"material_rupture", "prescribed_intervention"}
_CONTROL_FAMILIES = {
    "deformation",
    "pressure_derived_tension",
    "prescribed_intervention",
}


class SchemaValidationError(ValueError):
    """Raised when a record violates the frozen trajectory contract."""


def _opaque(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise SchemaValidationError(f"{field} must be an opaque string ID")
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise SchemaValidationError(f"{field} must be a nonempty trimmed opaque string ID")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SchemaValidationError(f"{field} must be a nonempty trimmed string")
    if any(ord(char) < 32 for char in value):
        raise SchemaValidationError(f"{field} cannot contain control characters")
    return value


def _optional_id(value: object, field: str) -> str | None:
    return None if value is None else _opaque(value, field)


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SchemaValidationError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise SchemaValidationError(f"{field} must be finite")
    return result


def _nonnegative_float(value: object, field: str) -> float:
    result = _finite(value, field)
    if result < 0.0:
        raise SchemaValidationError(f"{field} must be nonnegative")
    return result


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise SchemaValidationError(f"{field} must be a nonnegative integer")
    return int(value)


def _exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise SchemaValidationError(f"{field} must be a boolean")
    return value


def _sha256(value: object, field: str) -> str:
    value = _text(value, field)
    if _HASH_RE.fullmatch(value) is None:
        raise SchemaValidationError(f"{field} must be a lowercase sha256: digest")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{field} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise SchemaValidationError(f"{field} keys must be strings")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], field: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        raise SchemaValidationError(
            f"{field} keys mismatch; missing={missing}, unexpected={extra}"
        )


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{field} must be an array")
    return value


def _ids(value: object, field: str, *, unique: bool = True) -> tuple[str, ...]:
    result = tuple(_opaque(item, f"{field}[{index}]") for index, item in enumerate(_sequence(value, field)))
    if unique and len(set(result)) != len(result):
        raise SchemaValidationError(f"{field} contains duplicate opaque IDs")
    return result


def _vector2(value: object, field: str) -> tuple[float, float]:
    values = _sequence(value, field)
    if len(values) != 2:
        raise SchemaValidationError(f"{field} must contain exactly two values")
    return (_finite(values[0], f"{field}[0]"), _finite(values[1], f"{field}[1]"))


def _int_vector2(value: object, field: str) -> tuple[int, int]:
    values = _sequence(value, field)
    if len(values) != 2:
        raise SchemaValidationError(f"{field} must contain exactly two signed integers")
    result: list[int] = []
    for index, item in enumerate(values):
        if isinstance(item, bool) or not isinstance(item, Integral):
            raise SchemaValidationError(f"{field}[{index}] must be a signed integer")
        result.append(int(item))
    return (result[0], result[1])


def _matrix2(value: object, field: str) -> tuple[tuple[float, float], tuple[float, float]]:
    rows = _sequence(value, field)
    if len(rows) != 2:
        raise SchemaValidationError(f"{field} must be a 2x2 matrix")
    return (_vector2(rows[0], f"{field}[0]"), _vector2(rows[1], f"{field}[1]"))


def _optional_vector2(value: object, field: str) -> tuple[float, float] | None:
    return None if value is None else _vector2(value, field)


def _freeze_json(value: object, field: str = "value") -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real) and not isinstance(value, bool):
        return _finite(value, field)
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, child in value.items():
            key = _text(key, f"{field} key")
            frozen[key] = _freeze_json(child, f"{field}.{key}")
        return MappingProxyType(dict(sorted(frozen.items())))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze_json(child, f"{field}[{index}]") for index, child in enumerate(value))
    raise SchemaValidationError(f"{field} contains unsupported non-JSON value {type(value).__name__}")


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_plain(child) for child in value]
    return value


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        _plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _record_sequence(value: object, field: str) -> tuple[Mapping[str, object], ...]:
    rows = _sequence(value, field)
    return tuple(_mapping(row, f"{field}[{index}]") for index, row in enumerate(rows))


def canonicalize_p02_phase(source_phase: str) -> str:
    """Map one exact P02 execution phase into the canonical storage vocabulary."""

    source_phase = _text(source_phase, "P02 source phase")
    try:
        return _P02_PHASE_MAP[source_phase]
    except KeyError as error:
        raise SchemaValidationError(
            f"unsupported P02 source phase {source_phase!r}; no alias or case coercion is permitted"
        ) from error


@dataclass(frozen=True)
class NamedScalars:
    """Finite named values with one explicit unit per value."""

    values: Mapping[str, float]
    units: Mapping[str, str]

    def __post_init__(self) -> None:
        values = _mapping(self.values, "named scalar values")
        units = _mapping(self.units, "named scalar units")
        if set(values) != set(units):
            raise SchemaValidationError("named scalar values and units must have identical keys")
        normalized_values: dict[str, float] = {}
        normalized_units: dict[str, str] = {}
        for name in sorted(values):
            name = _text(name, "named scalar name")
            normalized_values[name] = _finite(values[name], f"named scalar {name}")
            normalized_units[name] = _text(units[name], f"unit for {name}")
        object.__setattr__(self, "values", MappingProxyType(normalized_values))
        object.__setattr__(self, "units", MappingProxyType(normalized_units))

    def as_record(self) -> dict[str, object]:
        return {"values": dict(self.values), "units": dict(self.units)}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "NamedScalars":
        value = _mapping(value, "named scalars")
        _exact_keys(value, {"values", "units"}, "named scalars")
        return cls(
            values=_mapping(value["values"], "named scalar values"),  # type: ignore[arg-type]
            units=_mapping(value["units"], "named scalar units"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class Cell2D:
    """Supported two-dimensional restricted triclinic cell using column vectors."""

    origin_nm: tuple[float, float]
    cell_matrix_nm: tuple[tuple[float, float], tuple[float, float]]
    periodic_axes: tuple[bool, bool]
    axis_meanings: tuple[str, str]
    dimension: int = 2
    vector_convention: str = "column"
    coordinate_representation: str = "cartesian_nm"
    image_offset_convention: str = "r_ij=x_j-x_i+H@n_ij"

    def __post_init__(self) -> None:
        origin = _vector2(self.origin_nm, "origin_nm")
        matrix = _matrix2(self.cell_matrix_nm, "cell_matrix_nm")
        axes = _sequence(self.periodic_axes, "periodic_axes")
        if len(axes) != 2:
            raise SchemaValidationError("periodic_axes must contain two booleans")
        periodic = tuple(_exact_bool(item, f"periodic_axes[{index}]") for index, item in enumerate(axes))
        meanings = _ids(self.axis_meanings, "axis_meanings")
        if meanings != ("axial", "hoop"):
            raise SchemaValidationError("axis_meanings must equal ('axial', 'hoop')")
        if self.dimension != 2 or self.vector_convention != "column":
            raise SchemaValidationError("Cell2D requires dimension=2 and column vectors")
        if self.coordinate_representation != "cartesian_nm":
            raise SchemaValidationError("coordinate_representation must be cartesian_nm")
        if self.image_offset_convention != "r_ij=x_j-x_i+H@n_ij":
            raise SchemaValidationError("image-offset sign convention changed")
        if matrix[1][0] != 0.0:
            raise SchemaValidationError(
                "only the supported restricted 2D triclinic form H=[[Lx,xy],[0,Ly]] is accepted"
            )
        if matrix[0][0] <= 0.0 or matrix[1][1] <= 0.0:
            raise SchemaValidationError("cell lattice lengths must be positive")
        object.__setattr__(self, "origin_nm", origin)
        object.__setattr__(self, "cell_matrix_nm", matrix)
        object.__setattr__(self, "periodic_axes", periodic)
        object.__setattr__(self, "axis_meanings", meanings)

    def displacement(
        self,
        x_i_nm: Sequence[float],
        x_j_nm: Sequence[float],
        n_ij: Sequence[int],
    ) -> tuple[float, float]:
        left = _vector2(x_i_nm, "x_i_nm")
        right = _vector2(x_j_nm, "x_j_nm")
        image = _int_vector2(n_ij, "n_ij")
        h = self.cell_matrix_nm
        return (
            right[0] - left[0] + h[0][0] * image[0] + h[0][1] * image[1],
            right[1] - left[1] + h[1][0] * image[0] + h[1][1] * image[1],
        )

    def as_record(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "origin_nm": list(self.origin_nm),
            "cell_matrix_nm": [list(row) for row in self.cell_matrix_nm],
            "periodic_axes": list(self.periodic_axes),
            "axis_meanings": list(self.axis_meanings),
            "vector_convention": self.vector_convention,
            "coordinate_representation": self.coordinate_representation,
            "image_offset_convention": self.image_offset_convention,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "Cell2D":
        value = _mapping(value, "cell")
        _exact_keys(
            value,
            {
                "dimension",
                "origin_nm",
                "cell_matrix_nm",
                "periodic_axes",
                "axis_meanings",
                "vector_convention",
                "coordinate_representation",
                "image_offset_convention",
            },
            "cell",
        )
        return cls(
            origin_nm=value["origin_nm"],  # type: ignore[arg-type]
            cell_matrix_nm=value["cell_matrix_nm"],  # type: ignore[arg-type]
            periodic_axes=value["periodic_axes"],  # type: ignore[arg-type]
            axis_meanings=value["axis_meanings"],  # type: ignore[arg-type]
            dimension=value["dimension"],  # type: ignore[arg-type]
            vector_convention=value["vector_convention"],  # type: ignore[arg-type]
            coordinate_representation=value["coordinate_representation"],  # type: ignore[arg-type]
            image_offset_convention=value["image_offset_convention"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class NodeReference:
    node_id: str
    molecule_id: str
    node_type: str
    material_features: NamedScalars

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _opaque(self.node_id, "node_id"))
        object.__setattr__(self, "molecule_id", _opaque(self.molecule_id, "molecule_id"))
        object.__setattr__(self, "node_type", _text(self.node_type, "node_type"))
        if not isinstance(self.material_features, NamedScalars):
            raise SchemaValidationError("material_features must be NamedScalars")

    def as_record(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "molecule_id": self.molecule_id,
            "node_type": self.node_type,
            "material_features": self.material_features.as_record(),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "NodeReference":
        value = _mapping(value, "node reference")
        _exact_keys(value, {"node_id", "molecule_id", "node_type", "material_features"}, "node reference")
        return cls(
            value["node_id"],  # type: ignore[arg-type]
            value["molecule_id"],  # type: ignore[arg-type]
            value["node_type"],  # type: ignore[arg-type]
            NamedScalars.from_record(value["material_features"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class EdgeReference:
    edge_id: str
    endpoints: tuple[str, str]
    chemical_type: str
    reference_rest_length_nm: float
    reference_parameters: NamedScalars
    reference_image_offset_n_ij: tuple[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _opaque(self.edge_id, "edge_id"))
        endpoints = _ids(self.endpoints, "edge endpoints")
        if len(endpoints) != 2 or endpoints[0] == endpoints[1]:
            raise SchemaValidationError("edge endpoints must contain two distinct node IDs")
        object.__setattr__(self, "endpoints", endpoints)
        object.__setattr__(self, "chemical_type", _text(self.chemical_type, "chemical_type"))
        rest = _finite(self.reference_rest_length_nm, "reference_rest_length_nm")
        if rest <= 0.0:
            raise SchemaValidationError("reference_rest_length_nm must be positive")
        object.__setattr__(self, "reference_rest_length_nm", rest)
        if not isinstance(self.reference_parameters, NamedScalars):
            raise SchemaValidationError("reference_parameters must be NamedScalars")
        object.__setattr__(
            self,
            "reference_image_offset_n_ij",
            _int_vector2(self.reference_image_offset_n_ij, "reference_image_offset_n_ij"),
        )

    def as_record(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "endpoints": list(self.endpoints),
            "chemical_type": self.chemical_type,
            "reference_rest_length_nm": self.reference_rest_length_nm,
            "reference_parameters": self.reference_parameters.as_record(),
            "reference_image_offset_n_ij": list(self.reference_image_offset_n_ij),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EdgeReference":
        value = _mapping(value, "edge reference")
        _exact_keys(
            value,
            {
                "edge_id",
                "endpoints",
                "chemical_type",
                "reference_rest_length_nm",
                "reference_parameters",
                "reference_image_offset_n_ij",
            },
            "edge reference",
        )
        return cls(
            value["edge_id"],  # type: ignore[arg-type]
            value["endpoints"],  # type: ignore[arg-type]
            value["chemical_type"],  # type: ignore[arg-type]
            value["reference_rest_length_nm"],  # type: ignore[arg-type]
            NamedScalars.from_record(value["reference_parameters"]),  # type: ignore[arg-type]
            value["reference_image_offset_n_ij"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class AngleReference:
    angle_id: str
    node_ids: tuple[str, str, str]
    dependent_edge_ids: tuple[str, ...]
    chemical_type: str
    reference_parameters: NamedScalars

    def __post_init__(self) -> None:
        object.__setattr__(self, "angle_id", _opaque(self.angle_id, "angle_id"))
        nodes = _ids(self.node_ids, "angle node_ids")
        if len(nodes) != 3:
            raise SchemaValidationError("angle node_ids must contain three IDs")
        dependencies = _ids(self.dependent_edge_ids, "angle dependent edge IDs")
        if not dependencies:
            raise SchemaValidationError("angle must depend on at least one physical edge")
        object.__setattr__(self, "node_ids", nodes)
        object.__setattr__(self, "dependent_edge_ids", tuple(sorted(dependencies)))
        object.__setattr__(self, "chemical_type", _text(self.chemical_type, "chemical_type"))
        if not isinstance(self.reference_parameters, NamedScalars):
            raise SchemaValidationError("reference_parameters must be NamedScalars")

    def as_record(self) -> dict[str, object]:
        return {
            "angle_id": self.angle_id,
            "node_ids": list(self.node_ids),
            "dependent_edge_ids": list(self.dependent_edge_ids),
            "chemical_type": self.chemical_type,
            "reference_parameters": self.reference_parameters.as_record(),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "AngleReference":
        value = _mapping(value, "angle reference")
        _exact_keys(
            value,
            {"angle_id", "node_ids", "dependent_edge_ids", "chemical_type", "reference_parameters"},
            "angle reference",
        )
        return cls(
            value["angle_id"],  # type: ignore[arg-type]
            value["node_ids"],  # type: ignore[arg-type]
            value["dependent_edge_ids"],  # type: ignore[arg-type]
            value["chemical_type"],  # type: ignore[arg-type]
            NamedScalars.from_record(value["reference_parameters"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class StaticGraph:
    graph_id: str
    reference_state_id: str
    reference_cell: Cell2D
    nodes: tuple[NodeReference, ...]
    edges: tuple[EdgeReference, ...]
    angles: tuple[AngleReference, ...]
    graph_hash: str
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("static graph schema_version requires explicit migration")
        object.__setattr__(self, "graph_id", _opaque(self.graph_id, "graph_id"))
        object.__setattr__(self, "reference_state_id", _opaque(self.reference_state_id, "reference_state_id"))
        if not isinstance(self.reference_cell, Cell2D):
            raise SchemaValidationError("reference_cell must be Cell2D")
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        angles = tuple(self.angles)
        if any(not isinstance(item, NodeReference) for item in nodes):
            raise SchemaValidationError("nodes must contain NodeReference records")
        if any(not isinstance(item, EdgeReference) for item in edges):
            raise SchemaValidationError("edges must contain EdgeReference records")
        if any(not isinstance(item, AngleReference) for item in angles):
            raise SchemaValidationError("angles must contain AngleReference records")
        if nodes != tuple(sorted(nodes, key=lambda row: row.node_id)):
            raise SchemaValidationError("nodes must be in canonical opaque-ID order")
        if edges != tuple(sorted(edges, key=lambda row: row.edge_id)):
            raise SchemaValidationError("edges must be in canonical opaque-ID order")
        if angles != tuple(sorted(angles, key=lambda row: row.angle_id)):
            raise SchemaValidationError("angles must be in canonical opaque-ID order")
        for label, identifiers in (
            ("node", tuple(row.node_id for row in nodes)),
            ("edge", tuple(row.edge_id for row in edges)),
            ("angle", tuple(row.angle_id for row in angles)),
        ):
            if len(set(identifiers)) != len(identifiers):
                raise SchemaValidationError(f"duplicate {label} opaque IDs")
        node_ids = {row.node_id for row in nodes}
        edge_ids = {row.edge_id for row in edges}
        endpoint_keys: set[tuple[str, str]] = set()
        for edge in edges:
            if not set(edge.endpoints) <= node_ids:
                raise SchemaValidationError(f"edge {edge.edge_id!r} has an unknown endpoint")
            key = tuple(sorted(edge.endpoints))
            if key in endpoint_keys:
                raise SchemaValidationError("duplicate physical edge endpoints are not permitted in schema v1")
            endpoint_keys.add(key)
        for angle in angles:
            if not set(angle.node_ids) <= node_ids:
                raise SchemaValidationError(f"angle {angle.angle_id!r} references an unknown node")
            if not set(angle.dependent_edge_ids) <= edge_ids:
                raise SchemaValidationError(f"angle {angle.angle_id!r} references an unknown dependent edge")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "angles", angles)
        _sha256(self.graph_hash, "graph_hash")
        if self.graph_hash != _fingerprint(self._body()):
            raise SchemaValidationError("graph_hash does not match static graph content")

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(row.node_id for row in self.nodes)

    @property
    def edge_ids(self) -> tuple[str, ...]:
        return tuple(row.edge_id for row in self.edges)

    @property
    def angle_ids(self) -> tuple[str, ...]:
        return tuple(row.angle_id for row in self.angles)

    def edge_by_id(self, edge_id: str) -> EdgeReference:
        edge_id = _opaque(edge_id, "edge_id")
        try:
            return next(row for row in self.edges if row.edge_id == edge_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown edge_id {edge_id!r}") from error

    def angle_by_id(self, angle_id: str) -> AngleReference:
        angle_id = _opaque(angle_id, "angle_id")
        try:
            return next(row for row in self.angles if row.angle_id == angle_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown angle_id {angle_id!r}") from error

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "graph_id": self.graph_id,
            "reference_state_id": self.reference_state_id,
            "reference_cell": self.reference_cell.as_record(),
            "nodes": [row.as_record() for row in self.nodes],
            "edges": [row.as_record() for row in self.edges],
            "angles": [row.as_record() for row in self.angles],
        }

    def as_record(self) -> dict[str, object]:
        return {"graph_hash": self.graph_hash, **self._body()}

    def observed_record(self) -> dict[str, object]:
        """Return physical static content without realization/lineage shortcuts."""

        return {
            "schema_version": self.schema_version,
            "reference_cell": self.reference_cell.as_record(),
            "nodes": [row.as_record() for row in self.nodes],
            "edges": [row.as_record() for row in self.edges],
            "angles": [row.as_record() for row in self.angles],
        }

    @classmethod
    def create(
        cls,
        *,
        graph_id: str,
        reference_state_id: str,
        reference_cell: Cell2D,
        nodes: Sequence[NodeReference],
        edges: Sequence[EdgeReference],
        angles: Sequence[AngleReference],
    ) -> "StaticGraph":
        ordered_nodes = tuple(sorted(nodes, key=lambda row: row.node_id))
        ordered_edges = tuple(sorted(edges, key=lambda row: row.edge_id))
        ordered_angles = tuple(sorted(angles, key=lambda row: row.angle_id))
        body = {
            "schema_version": TRAJECTORY_SCHEMA_VERSION,
            "graph_id": graph_id,
            "reference_state_id": reference_state_id,
            "reference_cell": reference_cell.as_record(),
            "nodes": [row.as_record() for row in ordered_nodes],
            "edges": [row.as_record() for row in ordered_edges],
            "angles": [row.as_record() for row in ordered_angles],
        }
        return cls(
            graph_id,
            reference_state_id,
            reference_cell,
            ordered_nodes,
            ordered_edges,
            ordered_angles,
            _fingerprint(body),
        )

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "StaticGraph":
        value = _mapping(value, "static graph")
        if value.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("static graph schema_version requires explicit migration")
        _exact_keys(
            value,
            {"graph_hash", "schema_version", "graph_id", "reference_state_id", "reference_cell", "nodes", "edges", "angles"},
            "static graph",
        )
        return cls(
            graph_id=value["graph_id"],  # type: ignore[arg-type]
            reference_state_id=value["reference_state_id"],  # type: ignore[arg-type]
            reference_cell=Cell2D.from_record(value["reference_cell"]),  # type: ignore[arg-type]
            nodes=tuple(NodeReference.from_record(row) for row in _record_sequence(value["nodes"], "nodes")),
            edges=tuple(EdgeReference.from_record(row) for row in _record_sequence(value["edges"], "edges")),
            angles=tuple(AngleReference.from_record(row) for row in _record_sequence(value["angles"], "angles")),
            graph_hash=value["graph_hash"],  # type: ignore[arg-type]
            schema_version=value["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class EdgeParameterChange:
    edge_id: str
    parameter_names: tuple[str, ...]
    factor: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _opaque(self.edge_id, "edge_id"))
        names = _ids(self.parameter_names, "parameter_names")
        if not names or names != tuple(sorted(names)):
            raise SchemaValidationError("parameter_names must be nonempty canonical names")
        factor = _finite(self.factor, "weakening factor")
        if not 0.0 < factor < 1.0:
            raise SchemaValidationError("weakening factor must satisfy 0 < factor < 1")
        object.__setattr__(self, "parameter_names", names)
        object.__setattr__(self, "factor", factor)

    def as_record(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "parameter_names": list(self.parameter_names),
            "factor": self.factor,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EdgeParameterChange":
        value = _mapping(value, "edge parameter change")
        _exact_keys(value, {"edge_id", "parameter_names", "factor"}, "edge parameter change")
        return cls(
            value["edge_id"],  # type: ignore[arg-type]
            value["parameter_names"],  # type: ignore[arg-type]
            value["factor"],  # type: ignore[arg-type]
        )


def _vector_mapping(
    value: object, field: str
) -> Mapping[str, tuple[float, float]]:
    value = _mapping(value, field)
    result: dict[str, tuple[float, float]] = {}
    for identifier in sorted(value):
        stable_id = _opaque(identifier, f"{field} ID")
        result[stable_id] = _vector2(value[identifier], f"{field}[{identifier!r}]")
    return MappingProxyType(result)


@dataclass(frozen=True)
class PressureDerivation:
    """Declared thin-shell mapping from pressure label to 2D tension targets."""

    pressure_pN_per_nm2: float
    cylinder_radius_nm: float
    shell_assumption: str
    axial_relation: str
    hoop_relation: str
    flat_patch_meaning: str

    def __post_init__(self) -> None:
        pressure = _finite(self.pressure_pN_per_nm2, "pressure_pN_per_nm2")
        radius = _finite(self.cylinder_radius_nm, "cylinder_radius_nm")
        if pressure < 0.0 or radius <= 0.0:
            raise SchemaValidationError("pressure must be nonnegative and cylinder radius positive")
        object.__setattr__(self, "pressure_pN_per_nm2", pressure)
        object.__setattr__(self, "cylinder_radius_nm", radius)
        if self.shell_assumption != "closed_thin_cylinder_away_from_end_effects":
            raise SchemaValidationError("shell_assumption must declare the closed thin-cylinder idealization")
        if self.axial_relation != "N_axial=pR/2" or self.hoop_relation != "N_hoop=pR":
            raise SchemaValidationError("pressure derivation must preserve the declared axial/hoop equilibrium relations")
        if self.flat_patch_meaning != "membrane_tension_target_not_normal_inflation":
            raise SchemaValidationError("flat_patch_meaning cannot relabel a tension target as normal inflation")

    def as_record(self) -> dict[str, object]:
        return {
            "pressure_pN_per_nm2": self.pressure_pN_per_nm2,
            "cylinder_radius_nm": self.cylinder_radius_nm,
            "shell_assumption": self.shell_assumption,
            "axial_relation": self.axial_relation,
            "hoop_relation": self.hoop_relation,
            "flat_patch_meaning": self.flat_patch_meaning,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "PressureDerivation":
        value = _mapping(value, "pressure derivation")
        _exact_keys(
            value,
            {"pressure_pN_per_nm2", "cylinder_radius_nm", "shell_assumption", "axial_relation", "hoop_relation", "flat_patch_meaning"},
            "pressure derivation",
        )
        return cls(**dict(value))  # type: ignore[arg-type]


def _dof_mapping(value: object) -> Mapping[str, tuple[bool, bool]]:
    value = _mapping(value, "constrained_dofs")
    result: dict[str, tuple[bool, bool]] = {}
    for node_id in sorted(value):
        stable_id = _opaque(node_id, "constrained_dofs node ID")
        row = _sequence(value[node_id], f"constrained_dofs[{node_id!r}]")
        if len(row) != 2:
            raise SchemaValidationError("each constrained_dofs row must contain x/y booleans")
        flags = (
            _exact_bool(row[0], f"constrained_dofs[{node_id!r}][0]"),
            _exact_bool(row[1], f"constrained_dofs[{node_id!r}][1]"),
        )
        if not any(flags):
            raise SchemaValidationError("constrained_dofs entries must constrain at least one DOF")
        result[stable_id] = flags
    return MappingProxyType(result)


def _matrix_determinant(value: tuple[tuple[float, float], tuple[float, float]]) -> float:
    return value[0][0] * value[1][1] - value[0][1] * value[1][0]


def _matrix_multiply(
    left: tuple[tuple[float, float], tuple[float, float]],
    right: tuple[tuple[float, float], tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (
            left[0][0] * right[0][0] + left[0][1] * right[1][0],
            left[0][0] * right[0][1] + left[0][1] * right[1][1],
        ),
        (
            left[1][0] * right[0][0] + left[1][1] * right[1][0],
            left[1][0] * right[0][1] + left[1][1] * right[1][1],
        ),
    )


def _matrix_add(
    left: tuple[tuple[float, float], tuple[float, float]],
    right: tuple[tuple[float, float], tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    return tuple(
        tuple(left[i][j] + right[i][j] for j in range(2)) for i in range(2)
    )  # type: ignore[return-value]


def _matrix_close(
    left: tuple[tuple[float, float], tuple[float, float]],
    right: tuple[tuple[float, float], tuple[float, float]],
    tolerance: float = 1.0e-12,
) -> bool:
    return all(
        math.isclose(left[i][j], right[i][j], rel_tol=0.0, abs_tol=tolerance)
        for i in range(2)
        for j in range(2)
    )


@dataclass(frozen=True)
class ControlRecord:
    """One explicit quasi-static control/action at a load coordinate."""

    control_id: str
    load_step_id: str
    control_family: str
    step_index: int
    control_kind: str
    loading_mode: str
    axis_basis_columns_in_current_coordinates: tuple[tuple[float, float], tuple[float, float]]
    reference_state_id: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_increment: float
    progress_unit: str
    absolute_deformation_gradient: tuple[tuple[float, float], tuple[float, float]] | None
    incremental_deformation_gradient: tuple[tuple[float, float], tuple[float, float]] | None
    absolute_tension_target_pN_per_nm: tuple[tuple[float, float], tuple[float, float]] | None
    incremental_tension_target_pN_per_nm: tuple[tuple[float, float], tuple[float, float]] | None
    pressure_derivation: PressureDerivation | None
    boundary_displacements_nm: Mapping[str, tuple[float, float]]
    prescribed_forces_pN: Mapping[str, tuple[float, float]]
    constrained_dofs: Mapping[str, tuple[bool, bool]]
    local_weakening: tuple[EdgeParameterChange, ...]
    prescribed_removal_edge_ids: tuple[str, ...]
    axis_meanings: tuple[str, str] = ("axial", "hoop")
    reference_reset_policy: str = "never"
    load_coordinate_kind: str = "quasi_static_not_physical_time"
    progress_semantics: str = "cumulative_absolute_lambda_increment"
    physical_time_ns: None = None
    physical_time_valid: bool = False
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("control schema_version requires explicit migration")
        object.__setattr__(self, "control_id", _opaque(self.control_id, "control_id"))
        object.__setattr__(self, "load_step_id", _opaque(self.load_step_id, "load_step_id"))
        object.__setattr__(self, "step_index", _nonnegative_int(self.step_index, "step_index"))
        if self.control_family not in _CONTROL_FAMILIES:
            raise SchemaValidationError("unsupported control_family")
        if self.control_kind not in {"deformation_gradient", "membrane_tension_target", "prescribed_intervention"}:
            raise SchemaValidationError("unsupported control_kind")
        object.__setattr__(self, "loading_mode", _text(self.loading_mode, "loading_mode"))
        basis = _matrix2(self.axis_basis_columns_in_current_coordinates, "axis_basis_columns_in_current_coordinates")
        gram = (
            (basis[0][0] ** 2 + basis[1][0] ** 2, basis[0][0] * basis[0][1] + basis[1][0] * basis[1][1]),
            (basis[0][1] * basis[0][0] + basis[1][1] * basis[1][0], basis[0][1] ** 2 + basis[1][1] ** 2),
        )
        if not _matrix_close(gram, ((1.0, 0.0), (0.0, 1.0))):
            raise SchemaValidationError("axis basis columns must be orthonormal")
        object.__setattr__(self, "axis_basis_columns_in_current_coordinates", basis)
        meanings = _ids(self.axis_meanings, "axis_meanings")
        if meanings != ("axial", "hoop"):
            raise SchemaValidationError("control axis meanings must be x=axial, y=hoop")
        object.__setattr__(self, "axis_meanings", meanings)
        object.__setattr__(self, "reference_state_id", _opaque(self.reference_state_id, "reference_state_id"))
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "load_coordinate"))
        object.__setattr__(self, "load_coordinate_unit", _text(self.load_coordinate_unit, "load_coordinate_unit"))
        object.__setattr__(self, "path_progress", _nonnegative_float(self.path_progress, "path_progress"))
        object.__setattr__(self, "progress_increment", _nonnegative_float(self.progress_increment, "progress_increment"))
        object.__setattr__(self, "progress_unit", _text(self.progress_unit, "progress_unit"))
        if self.progress_unit != self.load_coordinate_unit:
            raise SchemaValidationError("progress_unit must match load_coordinate_unit in schema v1")
        absolute_f = None if self.absolute_deformation_gradient is None else _matrix2(self.absolute_deformation_gradient, "absolute_deformation_gradient")
        incremental_f = None if self.incremental_deformation_gradient is None else _matrix2(self.incremental_deformation_gradient, "incremental_deformation_gradient")
        for name, gradient in (("absolute", absolute_f), ("incremental", incremental_f)):
            if gradient is not None and _matrix_determinant(gradient) <= 0.0:
                raise SchemaValidationError(f"{name} deformation gradient must preserve positive area")
        object.__setattr__(self, "absolute_deformation_gradient", absolute_f)
        object.__setattr__(self, "incremental_deformation_gradient", incremental_f)
        absolute_tension = None if self.absolute_tension_target_pN_per_nm is None else _matrix2(self.absolute_tension_target_pN_per_nm, "absolute_tension_target_pN_per_nm")
        incremental_tension = None if self.incremental_tension_target_pN_per_nm is None else _matrix2(self.incremental_tension_target_pN_per_nm, "incremental_tension_target_pN_per_nm")
        object.__setattr__(self, "absolute_tension_target_pN_per_nm", absolute_tension)
        object.__setattr__(self, "incremental_tension_target_pN_per_nm", incremental_tension)
        if self.pressure_derivation is not None and not isinstance(self.pressure_derivation, PressureDerivation):
            raise SchemaValidationError("pressure_derivation must be PressureDerivation")
        object.__setattr__(self, "boundary_displacements_nm", _vector_mapping(self.boundary_displacements_nm, "boundary_displacements_nm"))
        object.__setattr__(self, "prescribed_forces_pN", _vector_mapping(self.prescribed_forces_pN, "prescribed_forces_pN"))
        object.__setattr__(self, "constrained_dofs", _dof_mapping(self.constrained_dofs))
        changes = tuple(self.local_weakening)
        if any(not isinstance(change, EdgeParameterChange) for change in changes):
            raise SchemaValidationError("local_weakening must contain EdgeParameterChange records")
        if tuple(change.edge_id for change in changes) != tuple(sorted(change.edge_id for change in changes)):
            raise SchemaValidationError("local_weakening must be in canonical edge-ID order")
        if len({change.edge_id for change in changes}) != len(changes):
            raise SchemaValidationError("local_weakening contains duplicate edge IDs")
        object.__setattr__(self, "local_weakening", changes)
        removals = _ids(self.prescribed_removal_edge_ids, "prescribed_removal_edge_ids")
        if removals != tuple(sorted(removals)):
            raise SchemaValidationError("prescribed_removal_edge_ids must be canonical")
        object.__setattr__(self, "prescribed_removal_edge_ids", removals)
        if self.reference_reset_policy != "never":
            raise SchemaValidationError("reference_reset_policy must be never")
        if self.load_coordinate_kind != "quasi_static_not_physical_time":
            raise SchemaValidationError("load_coordinate_kind must remain quasi-static")
        if self.progress_semantics != "cumulative_absolute_lambda_increment":
            raise SchemaValidationError("progress semantics changed")
        if self.physical_time_ns is not None or self.physical_time_valid is not False:
            raise SchemaValidationError("quasi-static controls cannot carry physical time")
        if self.control_family == "deformation":
            if self.control_kind != "deformation_gradient" or absolute_f is None or incremental_f is None or absolute_tension is not None or incremental_tension is not None or self.pressure_derivation is not None or changes or removals:
                raise SchemaValidationError("deformation control has incompatible action fields")
        elif self.control_family == "pressure_derived_tension":
            if self.control_kind != "membrane_tension_target" or absolute_tension is None or incremental_tension is None or absolute_f is not None or incremental_f is not None or self.pressure_derivation is None or changes or removals:
                raise SchemaValidationError("pressure-derived control has incompatible action fields")
            derivation = self.pressure_derivation
            if not math.isclose(self.load_coordinate, derivation.pressure_pN_per_nm2, rel_tol=0.0, abs_tol=1.0e-12):
                raise SchemaValidationError("pressure load coordinate differs from pressure_derivation")
            p_r = derivation.pressure_pN_per_nm2 * derivation.cylinder_radius_nm
            expected = ((p_r / 2.0, 0.0), (0.0, p_r))
            if not _matrix_close(absolute_tension, expected):
                raise SchemaValidationError("absolute tension target violates declared closed-cylinder pressure balance")
        else:
            if self.control_kind != "prescribed_intervention" or absolute_f is not None or incremental_f is not None or absolute_tension is not None or incremental_tension is not None or self.pressure_derivation is not None or not (changes or removals):
                raise SchemaValidationError("prescribed intervention requires weakening or removal only")

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "control_id": self.control_id,
            "load_step_id": self.load_step_id,
            "control_family": self.control_family,
            "step_index": self.step_index,
            "control_kind": self.control_kind,
            "loading_mode": self.loading_mode,
            "axis_meanings": list(self.axis_meanings),
            "axis_basis_columns_in_current_coordinates": [list(row) for row in self.axis_basis_columns_in_current_coordinates],
            "reference_state_id": self.reference_state_id,
            "reference_reset_policy": self.reference_reset_policy,
            "load_coordinate_kind": self.load_coordinate_kind,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_increment": self.progress_increment,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
            "absolute_control_semantics": (
                "F_absolute_maps_fixed_reference_to_target"
                if self.control_kind == "deformation_gradient"
                else "N_absolute_is_total_membrane_tension_target"
                if self.control_kind == "membrane_tension_target"
                else "intervention_applies_to_current_physical_interactions"
            ),
            "increment_control_semantics": (
                "F_increment_maps_previous_accepted_state_to_target"
                if self.control_kind == "deformation_gradient"
                else "Delta_N_target_is_additive_from_previous_target"
                if self.control_kind == "membrane_tension_target"
                else "no_continuous_increment"
            ),
            "absolute_deformation_gradient": None if self.absolute_deformation_gradient is None else [list(row) for row in self.absolute_deformation_gradient],
            "incremental_deformation_gradient": None if self.incremental_deformation_gradient is None else [list(row) for row in self.incremental_deformation_gradient],
            "absolute_tension_target_pN_per_nm": None if self.absolute_tension_target_pN_per_nm is None else [list(row) for row in self.absolute_tension_target_pN_per_nm],
            "incremental_tension_target_pN_per_nm": None if self.incremental_tension_target_pN_per_nm is None else [list(row) for row in self.incremental_tension_target_pN_per_nm],
            "pressure_derivation": None if self.pressure_derivation is None else self.pressure_derivation.as_record(),
            "boundary_displacements_nm": {key: list(value) for key, value in self.boundary_displacements_nm.items()},
            "prescribed_forces_pN": {key: list(value) for key, value in self.prescribed_forces_pN.items()},
            "constrained_dofs": {key: list(value) for key, value in self.constrained_dofs.items()},
            "local_weakening": [change.as_record() for change in self.local_weakening],
            "prescribed_removal_edge_ids": list(self.prescribed_removal_edge_ids),
            "physical_time_ns": self.physical_time_ns,
            "physical_time_valid": self.physical_time_valid,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ControlRecord":
        value = _mapping(value, "control")
        if value.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("control schema_version requires explicit migration")
        _exact_keys(
            value,
            {
                "schema_version", "control_id", "load_step_id", "control_family", "step_index", "control_kind", "loading_mode",
                "axis_meanings", "axis_basis_columns_in_current_coordinates", "reference_state_id", "reference_reset_policy",
                "load_coordinate_kind", "load_coordinate", "load_coordinate_unit", "path_progress", "progress_increment", "progress_unit",
                "progress_semantics", "absolute_control_semantics", "increment_control_semantics", "absolute_deformation_gradient",
                "incremental_deformation_gradient", "absolute_tension_target_pN_per_nm", "incremental_tension_target_pN_per_nm",
                "pressure_derivation", "boundary_displacements_nm", "prescribed_forces_pN", "constrained_dofs", "local_weakening",
                "prescribed_removal_edge_ids", "physical_time_ns", "physical_time_valid",
            },
            "control",
        )
        kind = value["control_kind"]
        expected_absolute = (
            "F_absolute_maps_fixed_reference_to_target"
            if kind == "deformation_gradient"
            else "N_absolute_is_total_membrane_tension_target"
            if kind == "membrane_tension_target"
            else "intervention_applies_to_current_physical_interactions"
        )
        expected_increment = (
            "F_increment_maps_previous_accepted_state_to_target"
            if kind == "deformation_gradient"
            else "Delta_N_target_is_additive_from_previous_target"
            if kind == "membrane_tension_target"
            else "no_continuous_increment"
        )
        if value["absolute_control_semantics"] != expected_absolute or value["increment_control_semantics"] != expected_increment:
            raise SchemaValidationError("control absolute/increment semantics changed")
        return cls(
            control_id=value["control_id"],  # type: ignore[arg-type]
            load_step_id=value["load_step_id"],  # type: ignore[arg-type]
            control_family=value["control_family"],  # type: ignore[arg-type]
            step_index=value["step_index"],  # type: ignore[arg-type]
            control_kind=value["control_kind"],  # type: ignore[arg-type]
            loading_mode=value["loading_mode"],  # type: ignore[arg-type]
            axis_meanings=value["axis_meanings"],  # type: ignore[arg-type]
            axis_basis_columns_in_current_coordinates=value["axis_basis_columns_in_current_coordinates"],  # type: ignore[arg-type]
            reference_state_id=value["reference_state_id"],  # type: ignore[arg-type]
            reference_reset_policy=value["reference_reset_policy"],  # type: ignore[arg-type]
            load_coordinate_kind=value["load_coordinate_kind"],  # type: ignore[arg-type]
            load_coordinate=value["load_coordinate"],  # type: ignore[arg-type]
            load_coordinate_unit=value["load_coordinate_unit"],  # type: ignore[arg-type]
            path_progress=value["path_progress"],  # type: ignore[arg-type]
            progress_increment=value["progress_increment"],  # type: ignore[arg-type]
            progress_unit=value["progress_unit"],  # type: ignore[arg-type]
            progress_semantics=value["progress_semantics"],  # type: ignore[arg-type]
            absolute_deformation_gradient=value["absolute_deformation_gradient"],  # type: ignore[arg-type]
            incremental_deformation_gradient=value["incremental_deformation_gradient"],  # type: ignore[arg-type]
            absolute_tension_target_pN_per_nm=value["absolute_tension_target_pN_per_nm"],  # type: ignore[arg-type]
            incremental_tension_target_pN_per_nm=value["incremental_tension_target_pN_per_nm"],  # type: ignore[arg-type]
            pressure_derivation=None if value["pressure_derivation"] is None else PressureDerivation.from_record(value["pressure_derivation"]),  # type: ignore[arg-type]
            boundary_displacements_nm=value["boundary_displacements_nm"],  # type: ignore[arg-type]
            prescribed_forces_pN=value["prescribed_forces_pN"],  # type: ignore[arg-type]
            constrained_dofs=value["constrained_dofs"],  # type: ignore[arg-type]
            local_weakening=tuple(EdgeParameterChange.from_record(row) for row in _record_sequence(value["local_weakening"], "local_weakening")),
            prescribed_removal_edge_ids=value["prescribed_removal_edge_ids"],  # type: ignore[arg-type]
            physical_time_ns=value["physical_time_ns"],  # type: ignore[arg-type]
            physical_time_valid=value["physical_time_valid"],  # type: ignore[arg-type]
            schema_version=value["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ProvenanceRecord:
    run_id: str
    parent_network_id: str
    branch_id: str
    parent_run_id: str | None
    branch_frame_id: str | None
    source_kind: str
    source_commit: str
    source_tree_hash: str
    source_dirty: bool
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    reference_state_hash: str
    rupture_law_id: str
    rupture_law_hash: str
    config_hash: str
    raw_artifact_hashes: Mapping[str, str]
    simulator_version: str
    build_features: tuple[str, ...]
    split_id: str | None
    split_assignment_hash: str | None
    manifest_hash: str | None
    observation_model_id: str
    observation_model_hash: str
    boundary_condition_id: str
    boundary_condition_hash: str

    def __post_init__(self) -> None:
        for field in ("run_id", "parent_network_id", "branch_id"):
            object.__setattr__(self, field, _opaque(getattr(self, field), field))
        object.__setattr__(self, "parent_run_id", _optional_id(self.parent_run_id, "parent_run_id"))
        object.__setattr__(self, "branch_frame_id", _optional_id(self.branch_frame_id, "branch_frame_id"))
        if (self.parent_run_id is None) != (self.branch_frame_id is None):
            raise SchemaValidationError("parent_run_id and branch_frame_id must both be present or absent")
        if self.source_kind not in _SOURCE_KINDS:
            raise SchemaValidationError("unsupported source_kind")
        object.__setattr__(self, "source_commit", _text(self.source_commit, "source_commit"))
        for field in (
            "source_tree_hash", "physics_profile_hash", "reference_state_hash", "rupture_law_hash", "config_hash"
        ):
            object.__setattr__(self, field, _sha256(getattr(self, field), field))
        object.__setattr__(self, "source_dirty", _exact_bool(self.source_dirty, "source_dirty"))
        for field in ("physics_profile_id", "reference_state_id", "rupture_law_id"):
            object.__setattr__(self, field, _opaque(getattr(self, field), field))
        hashes = _mapping(self.raw_artifact_hashes, "raw_artifact_hashes")
        normalized_hashes: dict[str, str] = {}
        for name in sorted(hashes):
            normalized_hashes[_text(name, "raw artifact name")] = _sha256(hashes[name], f"raw_artifact_hashes[{name!r}]")
        object.__setattr__(self, "raw_artifact_hashes", MappingProxyType(normalized_hashes))
        object.__setattr__(self, "simulator_version", _text(self.simulator_version, "simulator_version"))
        features = _ids(self.build_features, "build_features")
        if features != tuple(sorted(features)):
            raise SchemaValidationError("build_features must be canonical")
        object.__setattr__(self, "build_features", features)
        object.__setattr__(self, "split_id", _optional_id(self.split_id, "split_id"))
        optional_hashes = (self.split_assignment_hash, self.manifest_hash)
        if self.split_id is None:
            if any(value is not None for value in optional_hashes):
                raise SchemaValidationError("split hashes require split_id")
        else:
            if any(value is None for value in optional_hashes):
                raise SchemaValidationError("split_id requires assignment and manifest hashes")
            object.__setattr__(self, "split_assignment_hash", _sha256(self.split_assignment_hash, "split_assignment_hash"))
            object.__setattr__(self, "manifest_hash", _sha256(self.manifest_hash, "manifest_hash"))
        for field in ("observation_model_id", "boundary_condition_id"):
            object.__setattr__(self, field, _opaque(getattr(self, field), field))
        for field in ("observation_model_hash", "boundary_condition_hash"):
            object.__setattr__(self, field, _sha256(getattr(self, field), field))

    def as_record(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "parent_network_id": self.parent_network_id,
            "branch_id": self.branch_id,
            "parent_run_id": self.parent_run_id,
            "branch_frame_id": self.branch_frame_id,
            "source_kind": self.source_kind,
            "source_commit": self.source_commit,
            "source_tree_hash": self.source_tree_hash,
            "source_dirty": self.source_dirty,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "reference_state_hash": self.reference_state_hash,
            "rupture_law_id": self.rupture_law_id,
            "rupture_law_hash": self.rupture_law_hash,
            "config_hash": self.config_hash,
            "raw_artifact_hashes": dict(self.raw_artifact_hashes),
            "simulator_version": self.simulator_version,
            "build_features": list(self.build_features),
            "split_id": self.split_id,
            "split_assignment_hash": self.split_assignment_hash,
            "manifest_hash": self.manifest_hash,
            "observation_model_id": self.observation_model_id,
            "observation_model_hash": self.observation_model_hash,
            "boundary_condition_id": self.boundary_condition_id,
            "boundary_condition_hash": self.boundary_condition_hash,
        }

    def observed_record(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "rupture_law_id": self.rupture_law_id,
            "rupture_law_hash": self.rupture_law_hash,
            "simulator_version": self.simulator_version,
            "build_features": list(self.build_features),
            "observation_model_id": self.observation_model_id,
            "observation_model_hash": self.observation_model_hash,
            "boundary_condition_id": self.boundary_condition_id,
            "boundary_condition_hash": self.boundary_condition_hash,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ProvenanceRecord":
        value = _mapping(value, "provenance")
        expected = {
            "run_id", "parent_network_id", "branch_id", "parent_run_id", "branch_frame_id", "source_kind",
            "source_commit", "source_tree_hash", "source_dirty", "physics_profile_id", "physics_profile_hash",
            "reference_state_id", "reference_state_hash", "rupture_law_id", "rupture_law_hash", "config_hash",
            "raw_artifact_hashes", "simulator_version", "build_features",
            "split_id", "split_assignment_hash", "manifest_hash", "observation_model_id", "observation_model_hash",
            "boundary_condition_id", "boundary_condition_hash",
        }
        _exact_keys(value, expected, "provenance")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class CapabilityFlags:
    velocities: bool
    node_virial: bool
    edge_damage: bool
    physical_time: bool
    local_stress: bool
    event_history: bool
    angle_mechanics: bool
    rejected_trials: bool

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            object.__setattr__(self, field, _exact_bool(getattr(self, field), field))

    def as_record(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CapabilityFlags":
        value = _mapping(value, "capability flags")
        expected = set(cls.__dataclass_fields__)
        _exact_keys(value, expected, "capability flags")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class ConvergenceRecord:
    converged: bool
    accepted: bool
    iterations: int
    residual_force_pN: float
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "converged", _exact_bool(self.converged, "converged"))
        object.__setattr__(self, "accepted", _exact_bool(self.accepted, "accepted"))
        object.__setattr__(self, "iterations", _nonnegative_int(self.iterations, "iterations"))
        object.__setattr__(self, "residual_force_pN", _nonnegative_float(self.residual_force_pN, "residual_force_pN"))
        object.__setattr__(self, "reason", _text(self.reason, "convergence reason"))
        if self.converged and not self.accepted:
            raise SchemaValidationError("a converged scientific state cannot be marked unaccepted")

    def as_record(self) -> dict[str, object]:
        return {
            "converged": self.converged,
            "accepted": self.accepted,
            "iterations": self.iterations,
            "residual_force_pN": self.residual_force_pN,
            "reason": self.reason,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ConvergenceRecord":
        value = _mapping(value, "convergence")
        _exact_keys(value, {"converged", "accepted", "iterations", "residual_force_pN", "reason"}, "convergence")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class NodeState:
    node_id: str
    position_nm: tuple[float, float]
    force_pN: tuple[float, float]
    velocity_nm_per_ns: tuple[float, float] | None = None
    virial_pN_nm: tuple[tuple[float, float], tuple[float, float]] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _opaque(self.node_id, "node_id"))
        object.__setattr__(self, "position_nm", _vector2(self.position_nm, "position_nm"))
        object.__setattr__(self, "force_pN", _vector2(self.force_pN, "force_pN"))
        object.__setattr__(self, "velocity_nm_per_ns", _optional_vector2(self.velocity_nm_per_ns, "velocity_nm_per_ns"))
        object.__setattr__(self, "virial_pN_nm", None if self.virial_pN_nm is None else _matrix2(self.virial_pN_nm, "virial_pN_nm"))

    def as_record(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "position_nm": list(self.position_nm),
            "force_pN": list(self.force_pN),
            "velocity_nm_per_ns": None if self.velocity_nm_per_ns is None else list(self.velocity_nm_per_ns),
            "virial_pN_nm": None if self.virial_pN_nm is None else [list(row) for row in self.virial_pN_nm],
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "NodeState":
        value = _mapping(value, "node state")
        _exact_keys(value, {"node_id", "position_nm", "force_pN", "velocity_nm_per_ns", "virial_pN_nm"}, "node state")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class EdgeState:
    edge_id: str
    alive: bool
    image_offset_n_ij: tuple[int, int]
    effective_parameters: NamedScalars
    damage_value: float | None
    damage_unit: str | None
    length_nm: float | None
    tension_pN: float | None
    energy_pN_nm: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _opaque(self.edge_id, "edge_id"))
        object.__setattr__(self, "alive", _exact_bool(self.alive, "edge alive"))
        object.__setattr__(self, "image_offset_n_ij", _int_vector2(self.image_offset_n_ij, "image_offset_n_ij"))
        if not isinstance(self.effective_parameters, NamedScalars):
            raise SchemaValidationError("effective_parameters must be NamedScalars")
        if self.damage_value is None:
            if self.damage_unit is not None:
                raise SchemaValidationError("damage_unit requires a valid damage_value")
        else:
            object.__setattr__(self, "damage_value", _finite(self.damage_value, "damage_value"))
            object.__setattr__(self, "damage_unit", _text(self.damage_unit, "damage_unit"))
        for field in ("length_nm", "tension_pN", "energy_pN_nm"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _finite(value, field))
        if not self.alive and any(getattr(self, field) is not None for field in ("length_nm", "tension_pN", "energy_pN_nm")):
            raise SchemaValidationError("inactive edges cannot carry physical length/tension/energy observations")

    def as_record(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "alive": self.alive,
            "image_offset_n_ij": list(self.image_offset_n_ij),
            "effective_parameters": self.effective_parameters.as_record(),
            "damage_value": self.damage_value,
            "damage_unit": self.damage_unit,
            "length_nm": self.length_nm,
            "tension_pN": self.tension_pN,
            "energy_pN_nm": self.energy_pN_nm,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EdgeState":
        value = _mapping(value, "edge state")
        _exact_keys(
            value,
            {"edge_id", "alive", "image_offset_n_ij", "effective_parameters", "damage_value", "damage_unit", "length_nm", "tension_pN", "energy_pN_nm"},
            "edge state",
        )
        return cls(
            edge_id=value["edge_id"],  # type: ignore[arg-type]
            alive=value["alive"],  # type: ignore[arg-type]
            image_offset_n_ij=value["image_offset_n_ij"],  # type: ignore[arg-type]
            effective_parameters=NamedScalars.from_record(value["effective_parameters"]),  # type: ignore[arg-type]
            damage_value=value["damage_value"],  # type: ignore[arg-type]
            damage_unit=value["damage_unit"],  # type: ignore[arg-type]
            length_nm=value["length_nm"],  # type: ignore[arg-type]
            tension_pN=value["tension_pN"],  # type: ignore[arg-type]
            energy_pN_nm=value["energy_pN_nm"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class AngleState:
    angle_id: str
    alive: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "angle_id", _opaque(self.angle_id, "angle_id"))
        object.__setattr__(self, "alive", _exact_bool(self.alive, "angle alive"))

    def as_record(self) -> dict[str, object]:
        return {"angle_id": self.angle_id, "alive": self.alive}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "AngleState":
        value = _mapping(value, "angle state")
        _exact_keys(value, {"angle_id", "alive"}, "angle state")
        return cls(value["angle_id"], value["alive"])  # type: ignore[arg-type]


def _component_mapping(value: object) -> Mapping[str, str]:
    value = _mapping(value, "component_ids")
    result: dict[str, str] = {}
    for node_id in sorted(value):
        result[_opaque(node_id, "component node ID")] = _opaque(value[node_id], f"component_ids[{node_id!r}]")
    return MappingProxyType(result)


@dataclass(frozen=True)
class StateRecord:
    """One accepted scientific state/event substep, separate from trial diagnostics."""

    sequence_index: int
    frame_id: str
    load_step_id: str
    control_id: str
    subevent_index: int
    phase: str
    source_phase: str | None
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    physical_time_ns: float | None
    physical_time_valid: bool
    cell: Cell2D
    nodes: tuple[NodeState, ...]
    edges: tuple[EdgeState, ...]
    angles: tuple[AngleState, ...]
    component_ids: Mapping[str, str]
    total_tension_pN_per_nm: tuple[tuple[float, float], tuple[float, float]]
    incremental_tension_pN_per_nm: tuple[tuple[float, float], tuple[float, float]]
    energy_terms: NamedScalars
    convergence: ConvergenceRecord
    state_status: str = "accepted"
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("state schema_version requires explicit migration")
        object.__setattr__(self, "sequence_index", _nonnegative_int(self.sequence_index, "sequence_index"))
        for field in ("frame_id", "load_step_id", "control_id"):
            object.__setattr__(self, field, _opaque(getattr(self, field), field))
        object.__setattr__(self, "subevent_index", _nonnegative_int(self.subevent_index, "subevent_index"))
        if self.phase not in _CANONICAL_PHASES:
            raise SchemaValidationError(f"unsupported canonical state phase {self.phase!r}")
        if self.source_phase is not None:
            source_phase = _text(self.source_phase, "source phase")
            if canonicalize_p02_phase(source_phase) != self.phase:
                raise SchemaValidationError("source phase does not map to the canonical phase")
            object.__setattr__(self, "source_phase", source_phase)
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "load_coordinate"))
        object.__setattr__(self, "load_coordinate_unit", _text(self.load_coordinate_unit, "load_coordinate_unit"))
        object.__setattr__(self, "path_progress", _nonnegative_float(self.path_progress, "path_progress"))
        object.__setattr__(self, "progress_unit", _text(self.progress_unit, "progress_unit"))
        if self.progress_unit != self.load_coordinate_unit:
            raise SchemaValidationError("state progress_unit must equal load_coordinate_unit")
        time_valid = _exact_bool(self.physical_time_valid, "physical_time_valid")
        if time_valid:
            if self.physical_time_ns is None:
                raise SchemaValidationError("physical_time_valid requires physical_time_ns")
            object.__setattr__(self, "physical_time_ns", _nonnegative_float(self.physical_time_ns, "physical_time_ns"))
        elif self.physical_time_ns is not None:
            raise SchemaValidationError("invalid physical time cannot carry a value")
        if not isinstance(self.cell, Cell2D):
            raise SchemaValidationError("state cell must be Cell2D")
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        angles = tuple(self.angles)
        for rows, expected, label, key in (
            (nodes, NodeState, "nodes", lambda row: row.node_id),
            (edges, EdgeState, "edges", lambda row: row.edge_id),
            (angles, AngleState, "angles", lambda row: row.angle_id),
        ):
            if any(not isinstance(row, expected) for row in rows):
                raise SchemaValidationError(f"{label} contain an invalid record type")
            identifiers = tuple(key(row) for row in rows)
            if identifiers != tuple(sorted(identifiers)) or len(set(identifiers)) != len(identifiers):
                raise SchemaValidationError(f"{label} must have unique canonical opaque IDs")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "angles", angles)
        object.__setattr__(self, "component_ids", _component_mapping(self.component_ids))
        object.__setattr__(self, "total_tension_pN_per_nm", _matrix2(self.total_tension_pN_per_nm, "total_tension_pN_per_nm"))
        object.__setattr__(self, "incremental_tension_pN_per_nm", _matrix2(self.incremental_tension_pN_per_nm, "incremental_tension_pN_per_nm"))
        if not isinstance(self.energy_terms, NamedScalars):
            raise SchemaValidationError("energy_terms must be NamedScalars")
        if any(unit != "pN nm" for unit in self.energy_terms.units.values()):
            raise SchemaValidationError("all energy_terms units must be pN nm")
        if not isinstance(self.convergence, ConvergenceRecord) or not self.convergence.accepted:
            raise SchemaValidationError("accepted scientific state requires accepted convergence diagnostics")
        if self.phase != "post_topology_change" and not self.convergence.converged:
            raise SchemaValidationError("all phases except post_topology_change must be converged")
        if self.phase == "post_topology_change" and self.convergence.converged:
            raise SchemaValidationError("post_topology_change must remain explicitly unrelaxed")
        if self.state_status != "accepted":
            raise SchemaValidationError("StateRecord stores accepted scientific states only")

    def edge_by_id(self, edge_id: str) -> EdgeState:
        edge_id = _opaque(edge_id, "edge_id")
        try:
            return next(row for row in self.edges if row.edge_id == edge_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown state edge_id {edge_id!r}") from error

    def angle_by_id(self, angle_id: str) -> AngleState:
        angle_id = _opaque(angle_id, "angle_id")
        try:
            return next(row for row in self.angles if row.angle_id == angle_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown state angle_id {angle_id!r}") from error

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sequence_index": self.sequence_index,
            "frame_id": self.frame_id,
            "load_step_id": self.load_step_id,
            "control_id": self.control_id,
            "subevent_index": self.subevent_index,
            "phase": self.phase,
            "source_phase": self.source_phase,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "physical_time_ns": self.physical_time_ns,
            "physical_time_valid": self.physical_time_valid,
            "cell": self.cell.as_record(),
            "nodes": [row.as_record() for row in self.nodes],
            "edges": [row.as_record() for row in self.edges],
            "angles": [row.as_record() for row in self.angles],
            "component_ids": dict(self.component_ids),
            "total_tension_pN_per_nm": [list(row) for row in self.total_tension_pN_per_nm],
            "incremental_tension_pN_per_nm": [list(row) for row in self.incremental_tension_pN_per_nm],
            "energy_terms": self.energy_terms.as_record(),
            "convergence": self.convergence.as_record(),
            "state_status": self.state_status,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "StateRecord":
        value = _mapping(value, "state")
        if value.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("state schema_version requires explicit migration")
        expected = {
            "schema_version", "sequence_index", "frame_id", "load_step_id", "control_id", "subevent_index",
            "phase", "source_phase", "load_coordinate", "load_coordinate_unit", "path_progress", "progress_unit",
            "physical_time_ns", "physical_time_valid", "cell", "nodes", "edges", "angles", "component_ids",
            "total_tension_pN_per_nm", "incremental_tension_pN_per_nm", "energy_terms", "convergence", "state_status",
        }
        _exact_keys(value, expected, "state")
        return cls(
            sequence_index=value["sequence_index"],  # type: ignore[arg-type]
            frame_id=value["frame_id"],  # type: ignore[arg-type]
            load_step_id=value["load_step_id"],  # type: ignore[arg-type]
            control_id=value["control_id"],  # type: ignore[arg-type]
            subevent_index=value["subevent_index"],  # type: ignore[arg-type]
            phase=value["phase"],  # type: ignore[arg-type]
            source_phase=value["source_phase"],  # type: ignore[arg-type]
            load_coordinate=value["load_coordinate"],  # type: ignore[arg-type]
            load_coordinate_unit=value["load_coordinate_unit"],  # type: ignore[arg-type]
            path_progress=value["path_progress"],  # type: ignore[arg-type]
            progress_unit=value["progress_unit"],  # type: ignore[arg-type]
            physical_time_ns=value["physical_time_ns"],  # type: ignore[arg-type]
            physical_time_valid=value["physical_time_valid"],  # type: ignore[arg-type]
            cell=Cell2D.from_record(value["cell"]),  # type: ignore[arg-type]
            nodes=tuple(NodeState.from_record(row) for row in _record_sequence(value["nodes"], "state nodes")),
            edges=tuple(EdgeState.from_record(row) for row in _record_sequence(value["edges"], "state edges")),
            angles=tuple(AngleState.from_record(row) for row in _record_sequence(value["angles"], "state angles")),
            component_ids=value["component_ids"],  # type: ignore[arg-type]
            total_tension_pN_per_nm=value["total_tension_pN_per_nm"],  # type: ignore[arg-type]
            incremental_tension_pN_per_nm=value["incremental_tension_pN_per_nm"],  # type: ignore[arg-type]
            energy_terms=NamedScalars.from_record(value["energy_terms"]),  # type: ignore[arg-type]
            convergence=ConvergenceRecord.from_record(value["convergence"]),  # type: ignore[arg-type]
            state_status=value["state_status"],  # type: ignore[arg-type]
            schema_version=value["schema_version"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class EventRecord:
    """One accepted irreversible physical-topology transition."""

    event_id: str
    sequence_index: int
    event_source: str
    edge_id: str
    triggering_control_id: str
    load_step_id: str
    subevent_index: int
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    pre_state_id: str
    post_topology_state_id: str
    post_equilibrium_state_id: str
    old_alive: bool
    new_alive: bool
    removed_angle_ids: tuple[str, ...]
    cascade_parent_event_id: str | None
    criterion_name: str | None
    criterion_value: float | None
    criterion_unit: str | None
    damage_law_hash: str
    accepted: bool = True
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("event schema_version requires explicit migration")
        object.__setattr__(self, "event_id", _opaque(self.event_id, "event_id"))
        object.__setattr__(self, "sequence_index", _nonnegative_int(self.sequence_index, "event sequence_index"))
        if self.event_source not in _EVENT_SOURCES:
            raise SchemaValidationError("unsupported event_source")
        for field in ("edge_id", "triggering_control_id", "load_step_id", "pre_state_id", "post_topology_state_id", "post_equilibrium_state_id"):
            object.__setattr__(self, field, _opaque(getattr(self, field), field))
        object.__setattr__(self, "subevent_index", _nonnegative_int(self.subevent_index, "subevent_index"))
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "event load_coordinate"))
        object.__setattr__(self, "load_coordinate_unit", _text(self.load_coordinate_unit, "event load_coordinate_unit"))
        object.__setattr__(self, "path_progress", _nonnegative_float(self.path_progress, "event path_progress"))
        object.__setattr__(self, "progress_unit", _text(self.progress_unit, "event progress_unit"))
        if self.progress_unit != self.load_coordinate_unit:
            raise SchemaValidationError("event progress_unit must equal load_coordinate_unit")
        if self.old_alive is not True or self.new_alive is not False or self.accepted is not True:
            raise SchemaValidationError("accepted event must be irreversible alive-to-dead")
        removed = _ids(self.removed_angle_ids, "removed_angle_ids")
        if removed != tuple(sorted(removed)):
            raise SchemaValidationError("removed_angle_ids must be canonical")
        object.__setattr__(self, "removed_angle_ids", removed)
        object.__setattr__(self, "cascade_parent_event_id", _optional_id(self.cascade_parent_event_id, "cascade_parent_event_id"))
        if self.event_source == "material_rupture":
            object.__setattr__(self, "criterion_name", _text(self.criterion_name, "criterion_name"))
            object.__setattr__(self, "criterion_value", _finite(self.criterion_value, "criterion_value"))
            object.__setattr__(self, "criterion_unit", _text(self.criterion_unit, "criterion_unit"))
        elif any(item is not None for item in (self.criterion_name, self.criterion_value, self.criterion_unit)):
            raise SchemaValidationError("prescribed interventions cannot carry rupture criterion fields")
        object.__setattr__(self, "damage_law_hash", _sha256(self.damage_law_hash, "damage_law_hash"))

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "sequence_index": self.sequence_index,
            "event_source": self.event_source,
            "edge_id": self.edge_id,
            "triggering_control_id": self.triggering_control_id,
            "load_step_id": self.load_step_id,
            "subevent_index": self.subevent_index,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "pre_state_id": self.pre_state_id,
            "post_topology_state_id": self.post_topology_state_id,
            "post_equilibrium_state_id": self.post_equilibrium_state_id,
            "old_alive": self.old_alive,
            "new_alive": self.new_alive,
            "removed_angle_ids": list(self.removed_angle_ids),
            "cascade_parent_event_id": self.cascade_parent_event_id,
            "criterion_name": self.criterion_name,
            "criterion_value": self.criterion_value,
            "criterion_unit": self.criterion_unit,
            "damage_law_hash": self.damage_law_hash,
            "accepted": self.accepted,
        }

    def observed_history_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "sequence_index": self.sequence_index,
            "event_source": self.event_source,
            "edge_id": self.edge_id,
            "triggering_control_id": self.triggering_control_id,
            "load_step_id": self.load_step_id,
            "subevent_index": self.subevent_index,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "post_equilibrium_state_id": self.post_equilibrium_state_id,
            "removed_angle_ids": list(self.removed_angle_ids),
            "criterion_name": self.criterion_name,
            "criterion_value": self.criterion_value,
            "criterion_unit": self.criterion_unit,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EventRecord":
        value = _mapping(value, "event")
        if value.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("event schema_version requires explicit migration")
        expected = {
            "schema_version", "event_id", "sequence_index", "event_source", "edge_id", "triggering_control_id",
            "load_step_id", "subevent_index", "load_coordinate", "load_coordinate_unit", "path_progress",
            "progress_unit", "pre_state_id", "post_topology_state_id", "post_equilibrium_state_id", "old_alive",
            "new_alive", "removed_angle_ids", "cascade_parent_event_id", "criterion_name", "criterion_value",
            "criterion_unit", "damage_law_hash", "accepted",
        }
        _exact_keys(value, expected, "event")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class DiagnosticTrial:
    """Rejected numerical trial stored outside accepted state/event sequences."""

    trial_id: str
    control_id: str
    load_coordinate: float
    path_progress: float
    reason: str
    details: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "trial_id", _opaque(self.trial_id, "trial_id"))
        object.__setattr__(self, "control_id", _opaque(self.control_id, "control_id"))
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "trial load_coordinate"))
        object.__setattr__(self, "path_progress", _nonnegative_float(self.path_progress, "trial path_progress"))
        object.__setattr__(self, "reason", _text(self.reason, "trial reason"))
        frozen = _freeze_json(self.details, "trial details")
        if not isinstance(frozen, Mapping):
            raise SchemaValidationError("trial details must be a mapping")
        object.__setattr__(self, "details", frozen)

    def as_record(self) -> dict[str, object]:
        return {
            "trial_id": self.trial_id,
            "control_id": self.control_id,
            "load_coordinate": self.load_coordinate,
            "path_progress": self.path_progress,
            "reason": self.reason,
            "details": _plain(self.details),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "DiagnosticTrial":
        value = _mapping(value, "diagnostic trial")
        _exact_keys(value, {"trial_id", "control_id", "load_coordinate", "path_progress", "reason", "details"}, "diagnostic trial")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class NormalizerRecord:
    normalizer_id: str
    fit_partition: str
    statistics: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "normalizer_id", _opaque(self.normalizer_id, "normalizer_id"))
        if self.fit_partition not in {"train", "validation", "test", "unknown"}:
            raise SchemaValidationError("unsupported normalizer fit_partition")
        frozen = _freeze_json(self.statistics, "normalizer statistics")
        if not isinstance(frozen, Mapping):
            raise SchemaValidationError("normalizer statistics must be a mapping")
        object.__setattr__(self, "statistics", frozen)

    def as_record(self) -> dict[str, object]:
        return {
            "normalizer_id": self.normalizer_id,
            "fit_partition": self.fit_partition,
            "statistics": _plain(self.statistics),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "NormalizerRecord":
        value = _mapping(value, "normalizer")
        _exact_keys(value, {"normalizer_id", "fit_partition", "statistics"}, "normalizer")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class PrivilegedRecord:
    """Reproducibility/private fields unavailable to predictor projections."""

    threshold_values: NamedScalars
    seeds: Mapping[str, int]
    realization_proxies: Mapping[str, object]
    rejected_trials: tuple[DiagnosticTrial, ...]
    normalizers: tuple[NormalizerRecord, ...]
    access_policy: Mapping[str, object]
    hidden_metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.threshold_values, NamedScalars):
            raise SchemaValidationError("threshold_values must be NamedScalars")
        seeds = _mapping(self.seeds, "seeds")
        normalized_seeds: dict[str, int] = {}
        for name in sorted(seeds):
            normalized_seeds[_text(name, "seed namespace")] = _nonnegative_int(seeds[name], f"seed {name}")
        object.__setattr__(self, "seeds", MappingProxyType(normalized_seeds))
        for field in ("realization_proxies", "access_policy", "hidden_metadata"):
            frozen = _freeze_json(getattr(self, field), field)
            if not isinstance(frozen, Mapping):
                raise SchemaValidationError(f"{field} must be a mapping")
            object.__setattr__(self, field, frozen)
        trials = tuple(self.rejected_trials)
        if any(not isinstance(row, DiagnosticTrial) for row in trials):
            raise SchemaValidationError("rejected_trials must contain DiagnosticTrial records")
        if tuple(row.trial_id for row in trials) != tuple(sorted(row.trial_id for row in trials)):
            raise SchemaValidationError("rejected_trials must be canonical")
        if len({row.trial_id for row in trials}) != len(trials):
            raise SchemaValidationError("rejected_trials contains duplicate trial IDs")
        object.__setattr__(self, "rejected_trials", trials)
        normalizers = tuple(self.normalizers)
        if any(not isinstance(row, NormalizerRecord) for row in normalizers):
            raise SchemaValidationError("normalizers must contain NormalizerRecord records")
        if tuple(row.normalizer_id for row in normalizers) != tuple(sorted(row.normalizer_id for row in normalizers)):
            raise SchemaValidationError("normalizers must be canonical")
        object.__setattr__(self, "normalizers", normalizers)

    def as_record(self) -> dict[str, object]:
        return {
            "threshold_values": self.threshold_values.as_record(),
            "seeds": dict(self.seeds),
            "realization_proxies": _plain(self.realization_proxies),
            "rejected_trials": [row.as_record() for row in self.rejected_trials],
            "normalizers": [row.as_record() for row in self.normalizers],
            "access_policy": _plain(self.access_policy),
            "hidden_metadata": _plain(self.hidden_metadata),
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "PrivilegedRecord":
        value = _mapping(value, "privileged record")
        _exact_keys(
            value,
            {"threshold_values", "seeds", "realization_proxies", "rejected_trials", "normalizers", "access_policy", "hidden_metadata"},
            "privileged record",
        )
        return cls(
            threshold_values=NamedScalars.from_record(value["threshold_values"]),  # type: ignore[arg-type]
            seeds=value["seeds"],  # type: ignore[arg-type]
            realization_proxies=value["realization_proxies"],  # type: ignore[arg-type]
            rejected_trials=tuple(DiagnosticTrial.from_record(row) for row in _record_sequence(value["rejected_trials"], "rejected_trials")),
            normalizers=tuple(NormalizerRecord.from_record(row) for row in _record_sequence(value["normalizers"], "normalizers")),
            access_policy=value["access_policy"],  # type: ignore[arg-type]
            hidden_metadata=value["hidden_metadata"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class CensoringRecord:
    status: str
    endpoint: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    evidence_event_id: str | None

    def __post_init__(self) -> None:
        if self.status not in {"observed", "right_censored"}:
            raise SchemaValidationError("censoring status must be observed or right_censored")
        object.__setattr__(self, "endpoint", _text(self.endpoint, "censoring endpoint"))
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "censoring load_coordinate"))
        object.__setattr__(self, "load_coordinate_unit", _text(self.load_coordinate_unit, "censoring load_coordinate_unit"))
        object.__setattr__(self, "path_progress", _nonnegative_float(self.path_progress, "censoring path_progress"))
        object.__setattr__(self, "progress_unit", _text(self.progress_unit, "censoring progress_unit"))
        if self.progress_unit != self.load_coordinate_unit:
            raise SchemaValidationError("censoring progress/load units must match")
        if self.status == "observed":
            object.__setattr__(self, "evidence_event_id", _opaque(self.evidence_event_id, "evidence_event_id"))
        elif self.evidence_event_id is not None:
            raise SchemaValidationError("right-censored endpoint cannot name an event")

    @classmethod
    def right_censored(
        cls,
        endpoint: str,
        load_coordinate: float,
        load_coordinate_unit: str,
        path_progress: float,
        progress_unit: str,
    ) -> "CensoringRecord":
        return cls("right_censored", endpoint, load_coordinate, load_coordinate_unit, path_progress, progress_unit, None)

    def as_record(self) -> dict[str, object]:
        return {
            "status": self.status,
            "endpoint": self.endpoint,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "evidence_event_id": self.evidence_event_id,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CensoringRecord":
        value = _mapping(value, "censoring")
        _exact_keys(value, {"status", "endpoint", "load_coordinate", "load_coordinate_unit", "path_progress", "progress_unit", "evidence_event_id"}, "censoring")
        return cls(**dict(value))  # type: ignore[arg-type]


def _same_float(left: float, right: float) -> bool:
    return left == right


@dataclass(frozen=True)
class TrajectoryRecord:
    """Content-hashed, replay-validated trajectory with separated record families."""

    provenance: ProvenanceRecord
    capabilities: CapabilityFlags
    static_graph: StaticGraph
    controls: tuple[ControlRecord, ...]
    states: tuple[StateRecord, ...]
    events: tuple[EventRecord, ...]
    privileged: PrivilegedRecord
    quality_status: str
    termination_reason: str
    censoring: CensoringRecord
    record_hash: str
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError(
                f"trajectory schema_version {self.schema_version!r} is unsupported; explicit migration is required"
            )
        if not isinstance(self.provenance, ProvenanceRecord):
            raise SchemaValidationError("provenance must be a ProvenanceRecord")
        if not isinstance(self.capabilities, CapabilityFlags):
            raise SchemaValidationError("capabilities must be CapabilityFlags")
        if not isinstance(self.static_graph, StaticGraph):
            raise SchemaValidationError("static_graph must be StaticGraph")
        if not isinstance(self.privileged, PrivilegedRecord):
            raise SchemaValidationError("privileged must be PrivilegedRecord")
        if not isinstance(self.censoring, CensoringRecord):
            raise SchemaValidationError("censoring must be CensoringRecord")
        controls = tuple(self.controls)
        states = tuple(self.states)
        events = tuple(self.events)
        if any(not isinstance(row, ControlRecord) for row in controls):
            raise SchemaValidationError("controls must contain ControlRecord records")
        if any(not isinstance(row, StateRecord) for row in states):
            raise SchemaValidationError("states must contain StateRecord records")
        if any(not isinstance(row, EventRecord) for row in events):
            raise SchemaValidationError("events must contain EventRecord records")
        if not states:
            raise SchemaValidationError("trajectory must contain at least one accepted state")
        object.__setattr__(self, "controls", controls)
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "events", events)
        if self.quality_status not in _QUALITY_STATUSES:
            raise SchemaValidationError("unsupported quality_status")
        if self.termination_reason not in _TERMINATION_REASONS:
            raise SchemaValidationError("unsupported termination_reason")
        self._validate_provenance_and_controls()
        self._validate_states()
        self._validate_events()
        self._validate_capabilities()
        self._validate_status()
        _sha256(self.record_hash, "record_hash")
        if self.record_hash != _fingerprint(self._body()):
            raise SchemaValidationError("record_hash does not match trajectory content")

    def _validate_provenance_and_controls(self) -> None:
        provenance = self.provenance
        graph = self.static_graph
        if provenance.reference_state_id != graph.reference_state_id:
            raise SchemaValidationError("provenance and static graph reference_state_id differ")
        control_ids = tuple(row.control_id for row in self.controls)
        load_ids = tuple(row.load_step_id for row in self.controls)
        if len(set(control_ids)) != len(control_ids):
            raise SchemaValidationError("duplicate control_id")
        if len(set(load_ids)) != len(load_ids):
            raise SchemaValidationError("duplicate load_step_id")
        if [row.step_index for row in self.controls] != list(range(len(self.controls))):
            raise SchemaValidationError("control step_index must be contiguous from zero")
        if any(right.path_progress < left.path_progress for left, right in zip(self.controls, self.controls[1:])):
            raise SchemaValidationError("controls must be ordered by nondecreasing path_progress")
        previous_progress = 0.0
        previous_absolute_f: tuple[tuple[float, float], tuple[float, float]] | None = None
        previous_absolute_tension: tuple[tuple[float, float], tuple[float, float]] | None = None
        for control in self.controls:
            if control.reference_state_id != graph.reference_state_id:
                raise SchemaValidationError("control mixes a different reference state")
            expected_progress_increment = control.path_progress - previous_progress
            if not math.isclose(control.progress_increment, expected_progress_increment, rel_tol=0.0, abs_tol=1.0e-12):
                raise SchemaValidationError("control progress_increment differs from ordered cumulative path_progress")
            previous_progress = control.path_progress
            if control.control_kind == "deformation_gradient":
                assert control.absolute_deformation_gradient is not None
                assert control.incremental_deformation_gradient is not None
                expected_absolute = (
                    control.incremental_deformation_gradient
                    if previous_absolute_f is None
                    else _matrix_multiply(control.incremental_deformation_gradient, previous_absolute_f)
                )
                if not _matrix_close(control.absolute_deformation_gradient, expected_absolute):
                    raise SchemaValidationError("incremental deformation gradient does not compose to the absolute target")
                previous_absolute_f = control.absolute_deformation_gradient
            elif control.control_kind == "membrane_tension_target":
                assert control.absolute_tension_target_pN_per_nm is not None
                assert control.incremental_tension_target_pN_per_nm is not None
                expected_absolute_tension = (
                    control.incremental_tension_target_pN_per_nm
                    if previous_absolute_tension is None
                    else _matrix_add(previous_absolute_tension, control.incremental_tension_target_pN_per_nm)
                )
                if not _matrix_close(control.absolute_tension_target_pN_per_nm, expected_absolute_tension):
                    raise SchemaValidationError("incremental tension target does not add to the absolute target")
                previous_absolute_tension = control.absolute_tension_target_pN_per_nm
            unknown_nodes = (
                set(control.boundary_displacements_nm)
                | set(control.prescribed_forces_pN)
                | set(control.constrained_dofs)
            ) - set(graph.node_ids)
            if unknown_nodes:
                raise SchemaValidationError(f"control references unknown nodes: {sorted(unknown_nodes)}")
            unknown_edges = (
                {change.edge_id for change in control.local_weakening}
                | set(control.prescribed_removal_edge_ids)
            ) - set(graph.edge_ids)
            if unknown_edges:
                raise SchemaValidationError(f"control references unknown edges: {sorted(unknown_edges)}")
            for change in control.local_weakening:
                reference = graph.edge_by_id(change.edge_id)
                if not set(change.parameter_names) <= set(reference.reference_parameters.values):
                    raise SchemaValidationError("local weakening names unknown reference parameters")

    def _validate_states(self) -> None:
        graph = self.static_graph
        controls = {row.control_id: row for row in self.controls}
        if [row.sequence_index for row in self.states] != list(range(len(self.states))):
            raise SchemaValidationError("state sequence_index must be contiguous from zero")
        frame_ids = [row.frame_id for row in self.states]
        if len(set(frame_ids)) != len(frame_ids):
            raise SchemaValidationError("duplicate frame_id")
        prior: StateRecord | None = None
        for state in self.states:
            try:
                control = controls[state.control_id]
            except KeyError as error:
                raise SchemaValidationError(f"state references unknown control_id {state.control_id!r}") from error
            if control.load_step_id != state.load_step_id:
                raise SchemaValidationError("state load_step_id differs from its control")
            if not _same_float(control.load_coordinate, state.load_coordinate) or control.load_coordinate_unit != state.load_coordinate_unit:
                raise SchemaValidationError("state load coordinate differs from its control")
            if not _same_float(control.path_progress, state.path_progress) or control.progress_unit != state.progress_unit:
                raise SchemaValidationError("state path progress differs from its control")
            if control.control_kind == "deformation_gradient":
                assert control.absolute_deformation_gradient is not None
                expected_cell = _matrix_multiply(
                    control.absolute_deformation_gradient,
                    graph.reference_cell.cell_matrix_nm,
                )
                if not _matrix_close(state.cell.cell_matrix_nm, expected_cell):
                    raise SchemaValidationError("state cell H is inconsistent with the absolute deformation gradient and reference H")
            if tuple(row.node_id for row in state.nodes) != graph.node_ids:
                raise SchemaValidationError("state node universe/order differs from static graph")
            if tuple(row.edge_id for row in state.edges) != graph.edge_ids:
                raise SchemaValidationError("state edge universe/order differs from static graph")
            if tuple(row.angle_id for row in state.angles) != graph.angle_ids:
                raise SchemaValidationError("state angle universe/order differs from static graph")
            if set(state.component_ids) != set(graph.node_ids):
                raise SchemaValidationError("component_ids must cover the exact node universe")
            for edge_ref, edge_state in zip(graph.edges, state.edges, strict=True):
                if set(edge_state.effective_parameters.values) != set(edge_ref.reference_parameters.values):
                    raise SchemaValidationError("effective parameter names differ from immutable reference parameters")
                if edge_state.effective_parameters.units != edge_ref.reference_parameters.units:
                    raise SchemaValidationError("effective parameter units differ from immutable reference parameter units")
            alive_edges = {row.edge_id for row in state.edges if row.alive}
            for angle_ref, angle_state in zip(graph.angles, state.angles, strict=True):
                dependencies_alive = set(angle_ref.dependent_edge_ids) <= alive_edges
                if angle_state.alive and not dependencies_alive:
                    raise SchemaValidationError("angle remains alive after a dependent physical edge was removed")
            if prior is None:
                if state.subevent_index != 0:
                    raise SchemaValidationError("first state of a load step must have subevent_index zero")
            else:
                if state.path_progress < prior.path_progress:
                    raise SchemaValidationError("path_progress must be nondecreasing")
                for before, after in zip(prior.edges, state.edges, strict=True):
                    if not before.alive and after.alive:
                        raise SchemaValidationError(f"edge {after.edge_id!r} resurrected; irreversible topology forbids healing")
                for before, after in zip(prior.angles, state.angles, strict=True):
                    if not before.alive and after.alive:
                        raise SchemaValidationError(f"angle {after.angle_id!r} resurrected")
                if state.load_step_id == prior.load_step_id:
                    if state.control_id != prior.control_id:
                        raise SchemaValidationError("same load step cannot switch controls")
                    if state.subevent_index <= prior.subevent_index:
                        raise SchemaValidationError("same-load subevent_index must strictly increase")
                elif state.subevent_index != 0:
                    raise SchemaValidationError("new load step must reset subevent_index to zero")
            prior = state

    def _validate_events(self) -> None:
        if [row.sequence_index for row in self.events] != list(range(len(self.events))):
            raise SchemaValidationError("event sequence_index must be contiguous from zero")
        event_ids = [row.event_id for row in self.events]
        edge_ids = [row.edge_id for row in self.events]
        if len(set(event_ids)) != len(event_ids):
            raise SchemaValidationError("duplicate event_id")
        if len(set(edge_ids)) != len(edge_ids):
            raise SchemaValidationError("repeat event for an already removed edge is forbidden")
        frames = {row.frame_id: row for row in self.states}
        controls = {row.control_id: row for row in self.controls}
        prior_event_ids: set[str] = set()
        graph = self.static_graph
        for event in self.events:
            if event.edge_id not in graph.edge_ids:
                raise SchemaValidationError("event references unknown edge")
            if event.damage_law_hash != self.provenance.rupture_law_hash:
                raise SchemaValidationError("event mixes a different rupture law hash")
            if event.triggering_control_id not in controls:
                raise SchemaValidationError("event references unknown control")
            if event.cascade_parent_event_id is not None and event.cascade_parent_event_id not in prior_event_ids:
                raise SchemaValidationError("cascade parent must be an earlier event")
            prior_event_ids.add(event.event_id)
            try:
                pre = frames[event.pre_state_id]
                post_topology = frames[event.post_topology_state_id]
                post_equilibrium = frames[event.post_equilibrium_state_id]
            except KeyError as error:
                raise SchemaValidationError("event references an unknown state") from error
            expected_pre_phase = (
                "pre_rupture"
                if event.event_source == "material_rupture"
                else "pre_intervention"
            )
            if pre.phase != expected_pre_phase:
                raise SchemaValidationError(
                    f"event pre_state must use canonical {expected_pre_phase} phase"
                )
            if post_topology.phase != "post_topology_change":
                raise SchemaValidationError("event topology state must use canonical post_topology_change phase")
            if post_equilibrium.phase != "post_event_equilibrium":
                raise SchemaValidationError("event final state must use canonical post_event_equilibrium phase")
            linked = (pre, post_topology, post_equilibrium)
            if any(row.control_id != event.triggering_control_id or row.load_step_id != event.load_step_id for row in linked):
                raise SchemaValidationError("event-linked states differ in control/load step")
            if any(
                row.load_coordinate != event.load_coordinate
                or row.load_coordinate_unit != event.load_coordinate_unit
                or row.path_progress != event.path_progress
                or row.progress_unit != event.progress_unit
                for row in linked
            ):
                raise SchemaValidationError("event-linked states differ in load coordinate/progress")
            if post_topology.subevent_index != event.subevent_index:
                raise SchemaValidationError("event subevent_index must identify post_topology_change")
            if not pre.edge_by_id(event.edge_id).alive:
                raise SchemaValidationError("event pre-state edge is already inactive")
            if post_topology.edge_by_id(event.edge_id).alive or post_equilibrium.edge_by_id(event.edge_id).alive:
                raise SchemaValidationError("event edge was not irreversibly removed")
            expected_angles = tuple(
                angle.angle_id
                for angle in graph.angles
                if event.edge_id in angle.dependent_edge_ids and pre.angle_by_id(angle.angle_id).alive
            )
            if event.removed_angle_ids != expected_angles:
                raise SchemaValidationError("event must remove every and only dependent angle")
            if any(post_topology.angle_by_id(angle_id).alive for angle_id in expected_angles):
                raise SchemaValidationError("dependent angle was not removed")
            for before, after in zip(pre.edges, post_topology.edges, strict=True):
                if before.edge_id != event.edge_id and before.alive != after.alive:
                    raise SchemaValidationError("one event changed an unrelated edge")
            for before, after in zip(pre.angles, post_topology.angles, strict=True):
                if before.angle_id not in expected_angles and before.alive != after.alive:
                    raise SchemaValidationError("one event changed an unrelated angle")
            if tuple(row.position_nm for row in pre.nodes) != tuple(row.position_nm for row in post_topology.nodes):
                raise SchemaValidationError("post_topology_change must preserve pre-relaxation positions")
        event_post_frames = {row.post_topology_state_id for row in self.events}
        for before, after in zip(self.states, self.states[1:]):
            changed = any(left.alive != right.alive for left, right in zip(before.edges, after.edges, strict=True))
            if changed and after.frame_id not in event_post_frames:
                raise SchemaValidationError("topology changed without a linked accepted event")

    def _validate_capabilities(self) -> None:
        capabilities = self.capabilities
        all_nodes = tuple(node for state in self.states for node in state.nodes)
        all_edges = tuple(edge for state in self.states for edge in state.edges)
        if any(node.velocity_nm_per_ns is not None for node in all_nodes) != capabilities.velocities:
            raise SchemaValidationError("velocities capability disagrees with payload presence")
        if any(node.virial_pN_nm is not None for node in all_nodes) != capabilities.node_virial:
            raise SchemaValidationError("node_virial capability disagrees with payload presence")
        if any(edge.damage_value is not None for edge in all_edges) != capabilities.edge_damage:
            raise SchemaValidationError("edge_damage capability disagrees with payload presence")
        if any(state.physical_time_valid for state in self.states) != capabilities.physical_time:
            raise SchemaValidationError("physical_time capability disagrees with payload presence")
        if bool(self.events) and not capabilities.event_history:
            raise SchemaValidationError("event_history capability is false despite stored events")
        if bool(self.static_graph.angles) != capabilities.angle_mechanics:
            raise SchemaValidationError("angle_mechanics capability disagrees with static graph")
        if bool(self.privileged.rejected_trials) != capabilities.rejected_trials:
            raise SchemaValidationError("rejected_trials capability disagrees with privileged diagnostics")
        threshold_ids = set(self.privileged.threshold_values.values)
        if threshold_ids and threshold_ids != set(self.static_graph.edge_ids):
            raise SchemaValidationError("threshold_values must cover the exact stable edge universe")

    def _validate_status(self) -> None:
        event_ids = {row.event_id for row in self.events}
        if self.censoring.status == "observed":
            if self.censoring.evidence_event_id not in event_ids:
                raise SchemaValidationError("observed censoring endpoint lacks its evidence event")
        elif self.censoring.evidence_event_id is not None:
            raise SchemaValidationError("right-censored endpoint cannot carry event evidence")
        if self.termination_reason == "damage_initiation":
            if self.censoring.status != "observed" or not any(row.event_source == "material_rupture" for row in self.events):
                raise SchemaValidationError("damage_initiation termination requires an observed material event, not censoring")
        if self.censoring.status == "right_censored" and any(row.event_source == "material_rupture" for row in self.events):
            raise SchemaValidationError("damage initiation cannot be right-censored after a material rupture")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provenance": self.provenance.as_record(),
            "capabilities": self.capabilities.as_record(),
            "static_graph": self.static_graph.as_record(),
            "controls": [row.as_record() for row in self.controls],
            "states": [row.as_record() for row in self.states],
            "events": [row.as_record() for row in self.events],
            "privileged": self.privileged.as_record(),
            "quality_status": self.quality_status,
            "termination_reason": self.termination_reason,
            "censoring": self.censoring.as_record(),
        }

    def as_record(self) -> dict[str, object]:
        return {"record_hash": self.record_hash, **self._body()}

    def constructor_fields(self) -> dict[str, object]:
        """Return validated constructor inputs, excluding the derived content hash."""

        return {
            "provenance": self.provenance,
            "capabilities": self.capabilities,
            "static_graph": self.static_graph,
            "controls": self.controls,
            "states": self.states,
            "events": self.events,
            "privileged": self.privileged,
            "quality_status": self.quality_status,
            "termination_reason": self.termination_reason,
            "censoring": self.censoring,
        }

    @classmethod
    def create(
        cls,
        *,
        provenance: ProvenanceRecord,
        capabilities: CapabilityFlags,
        static_graph: StaticGraph,
        controls: Sequence[ControlRecord],
        states: Sequence[StateRecord],
        events: Sequence[EventRecord],
        privileged: PrivilegedRecord,
        quality_status: str,
        termination_reason: str,
        censoring: CensoringRecord,
    ) -> "TrajectoryRecord":
        controls_tuple = tuple(controls)
        states_tuple = tuple(states)
        events_tuple = tuple(events)
        body = {
            "schema_version": TRAJECTORY_SCHEMA_VERSION,
            "provenance": provenance.as_record(),
            "capabilities": capabilities.as_record(),
            "static_graph": static_graph.as_record(),
            "controls": [row.as_record() for row in controls_tuple],
            "states": [row.as_record() for row in states_tuple],
            "events": [row.as_record() for row in events_tuple],
            "privileged": privileged.as_record(),
            "quality_status": quality_status,
            "termination_reason": termination_reason,
            "censoring": censoring.as_record(),
        }
        return cls(
            provenance=provenance,
            capabilities=capabilities,
            static_graph=static_graph,
            controls=controls_tuple,
            states=states_tuple,
            events=events_tuple,
            privileged=privileged,
            quality_status=quality_status,
            termination_reason=termination_reason,
            censoring=censoring,
            record_hash=_fingerprint(body),
        )

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "TrajectoryRecord":
        value = _mapping(value, "trajectory")
        if value.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError(
                f"trajectory schema_version {value.get('schema_version')!r} is unsupported; explicit migration is required"
            )
        expected = {
            "record_hash", "schema_version", "provenance", "capabilities", "static_graph", "controls", "states",
            "events", "privileged", "quality_status", "termination_reason", "censoring",
        }
        _exact_keys(value, expected, "trajectory")
        return cls(
            provenance=ProvenanceRecord.from_record(value["provenance"]),  # type: ignore[arg-type]
            capabilities=CapabilityFlags.from_record(value["capabilities"]),  # type: ignore[arg-type]
            static_graph=StaticGraph.from_record(value["static_graph"]),  # type: ignore[arg-type]
            controls=tuple(ControlRecord.from_record(row) for row in _record_sequence(value["controls"], "controls")),
            states=tuple(StateRecord.from_record(row) for row in _record_sequence(value["states"], "states")),
            events=tuple(EventRecord.from_record(row) for row in _record_sequence(value["events"], "events")),
            privileged=PrivilegedRecord.from_record(value["privileged"]),  # type: ignore[arg-type]
            quality_status=value["quality_status"],  # type: ignore[arg-type]
            termination_reason=value["termination_reason"],  # type: ignore[arg-type]
            censoring=CensoringRecord.from_record(value["censoring"]),  # type: ignore[arg-type]
            record_hash=value["record_hash"],  # type: ignore[arg-type]
            schema_version=value["schema_version"],  # type: ignore[arg-type]
        )

    def observed_projection(self, frame_id: str) -> "AccessProjection":
        frame_id = _opaque(frame_id, "frame_id")
        try:
            anchor = next(row for row in self.states if row.frame_id == frame_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown observation anchor {frame_id!r}") from error
        states = tuple(row for row in self.states if row.sequence_index <= anchor.sequence_index)
        used_controls = {row.control_id for row in states}
        controls = tuple(row for row in self.controls if row.control_id in used_controls)
        included_frames = {row.frame_id for row in states}
        history = tuple(row for row in self.events if row.post_equilibrium_state_id in included_frames)
        visible_capabilities = self.capabilities.as_record()
        visible_capabilities.pop("rejected_trials")
        payload = {
            "projection_contract": "predictor_input_only",
            "provenance": self.provenance.observed_record(),
            "capabilities": visible_capabilities,
            "static_graph": self.static_graph.observed_record(),
            "controls": [row.as_record() for row in controls],
            "states": [row.as_record() for row in states],
            "event_history": [row.observed_history_record() for row in history],
        }
        return AccessProjection.create("observed", frame_id, payload)

    def target_projection(self, frame_id: str) -> "AccessProjection":
        frame_id = _opaque(frame_id, "frame_id")
        try:
            anchor = next(row for row in self.states if row.frame_id == frame_id)
        except StopIteration as error:
            raise SchemaValidationError(f"unknown target anchor {frame_id!r}") from error
        future_states = tuple(row for row in self.states if row.sequence_index > anchor.sequence_index)
        future_frames = {row.frame_id for row in future_states}
        events = tuple(
            row for row in self.events
            if row.post_topology_state_id in future_frames or row.post_equilibrium_state_id in future_frames
        )
        payload = {
            "projection_contract": "supervised_targets_only",
            "trajectory_record_hash": self.record_hash,
            "anchor_frame_id": frame_id,
            "states": [row.as_record() for row in future_states],
            "events": [row.as_record() for row in events],
            "quality_status": self.quality_status,
            "termination_reason": self.termination_reason,
            "censoring": self.censoring.as_record(),
        }
        return AccessProjection.create("target_only", frame_id, payload)

    def privileged_projection(self) -> "AccessProjection":
        payload = {
            "projection_contract": "privileged_reproducibility_only",
            "trajectory": self.as_record(),
            "privileged": self.privileged.as_record(),
        }
        return AccessProjection.create("privileged", None, payload)


_FORBIDDEN_OBSERVED_KEY_PARTS = {
    "threshold",
    "cutoff",
    "breakinglimit",
    "rupturelimit",
    "seed",
    "rng",
    "randomstate",
    "entropy",
    "realization",
    "disorderdraw",
    "quenchedfield",
    "replicakey",
    "future",
    "oracle",
    "rejected",
    "normalizer",
    "scaler",
    "privacy",
    "private",
    "accesspolicy",
    "custodian",
}


def _normalized_key(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def _validate_observed_payload(value: object, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError(f"{path} has a non-string key")
            normalized = _normalized_key(key)
            if any(part in normalized for part in _FORBIDDEN_OBSERVED_KEY_PARTS):
                raise SchemaValidationError(f"forbidden predictor-visible field {path}.{key}")
            _validate_observed_payload(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _validate_observed_payload(child, f"{path}[{index}]")


def _validate_projection_shape(
    access_kind: str, anchor_frame_id: str | None, payload: Mapping[str, object]
) -> None:
    if access_kind == "observed":
        _exact_keys(
            payload,
            {
                "projection_contract",
                "provenance",
                "capabilities",
                "static_graph",
                "controls",
                "states",
                "event_history",
            },
            "observed projection payload",
        )
        if payload["projection_contract"] != "predictor_input_only":
            raise SchemaValidationError("observed projection contract label changed")
        provenance = _mapping(payload["provenance"], "observed provenance")
        expected_provenance = {
            "source_kind",
            "physics_profile_id",
            "physics_profile_hash",
            "rupture_law_id",
            "rupture_law_hash",
            "simulator_version",
            "build_features",
            "observation_model_id",
            "observation_model_hash",
            "boundary_condition_id",
            "boundary_condition_hash",
        }
        _exact_keys(provenance, expected_provenance, "observed provenance")
        capabilities = _mapping(payload["capabilities"], "observed capabilities")
        _exact_keys(
            capabilities,
            set(CapabilityFlags.__dataclass_fields__) - {"rejected_trials"},
            "observed capabilities",
        )
        for key, value in capabilities.items():
            _exact_bool(value, f"observed capabilities.{key}")
        observed_graph = _mapping(payload["static_graph"], "observed static graph")
        _exact_keys(
            observed_graph,
            {"schema_version", "reference_cell", "nodes", "edges", "angles"},
            "observed static graph",
        )
        if observed_graph["schema_version"] != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("observed static graph schema requires explicit migration")
        cell = Cell2D.from_record(observed_graph["reference_cell"])  # type: ignore[arg-type]
        nodes = tuple(NodeReference.from_record(row) for row in _record_sequence(observed_graph["nodes"], "observed nodes"))
        edges = tuple(EdgeReference.from_record(row) for row in _record_sequence(observed_graph["edges"], "observed edges"))
        angles = tuple(AngleReference.from_record(row) for row in _record_sequence(observed_graph["angles"], "observed angles"))
        StaticGraph.create(
            graph_id="access-validation-graph",
            reference_state_id="access-validation-reference",
            reference_cell=cell,
            nodes=nodes,
            edges=edges,
            angles=angles,
        )
        controls = tuple(
            ControlRecord.from_record(row)
            for row in _record_sequence(payload["controls"], "observed controls")
        )
        states = tuple(
            StateRecord.from_record(row)
            for row in _record_sequence(payload["states"], "observed states")
        )
        if not states or states[-1].frame_id != anchor_frame_id:
            raise SchemaValidationError("observed states must end exactly at the anchor frame")
        control_ids = {row.control_id for row in controls}
        if {row.control_id for row in states} != control_ids:
            raise SchemaValidationError("observed controls must be exactly those reached by the state history")
        history_rows = _record_sequence(payload["event_history"], "event_history")
        history_keys = {
            "event_id",
            "sequence_index",
            "event_source",
            "edge_id",
            "triggering_control_id",
            "load_step_id",
            "subevent_index",
            "load_coordinate",
            "load_coordinate_unit",
            "path_progress",
            "progress_unit",
            "post_equilibrium_state_id",
            "removed_angle_ids",
            "criterion_name",
            "criterion_value",
            "criterion_unit",
        }
        included_frames = {row.frame_id for row in states}
        for index, row in enumerate(history_rows):
            _exact_keys(row, history_keys, f"event_history[{index}]")
            if row["post_equilibrium_state_id"] not in included_frames:
                raise SchemaValidationError("observed event history contains a future event")
    elif access_kind == "target_only":
        _exact_keys(
            payload,
            {
                "projection_contract",
                "trajectory_record_hash",
                "anchor_frame_id",
                "states",
                "events",
                "quality_status",
                "termination_reason",
                "censoring",
            },
            "target projection payload",
        )
        if payload["projection_contract"] != "supervised_targets_only" or payload["anchor_frame_id"] != anchor_frame_id:
            raise SchemaValidationError("target projection contract/anchor mismatch")
        _sha256(payload["trajectory_record_hash"], "trajectory_record_hash")
        tuple(StateRecord.from_record(row) for row in _record_sequence(payload["states"], "target states"))
        tuple(EventRecord.from_record(row) for row in _record_sequence(payload["events"], "target events"))
        CensoringRecord.from_record(payload["censoring"])  # type: ignore[arg-type]
        if payload["quality_status"] not in _QUALITY_STATUSES or payload["termination_reason"] not in _TERMINATION_REASONS:
            raise SchemaValidationError("target status/termination is invalid")
    else:
        _exact_keys(
            payload,
            {"projection_contract", "trajectory", "privileged"},
            "privileged projection payload",
        )
        if payload["projection_contract"] != "privileged_reproducibility_only":
            raise SchemaValidationError("privileged projection contract label changed")
        trajectory = TrajectoryRecord.from_record(payload["trajectory"])  # type: ignore[arg-type]
        privileged = PrivilegedRecord.from_record(payload["privileged"])  # type: ignore[arg-type]
        if privileged != trajectory.privileged:
            raise SchemaValidationError("privileged projection duplicates inconsistent metadata")


@dataclass(frozen=True)
class AccessProjection:
    schema_version: str
    trajectory_schema_version: str
    access_kind: str
    anchor_frame_id: str | None
    payload: Mapping[str, object]
    projection_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != ACCESS_SCHEMA_VERSION:
            raise SchemaValidationError("access projection schema_version requires explicit migration")
        if self.trajectory_schema_version != TRAJECTORY_SCHEMA_VERSION:
            raise SchemaValidationError("trajectory_schema_version mismatch in access projection")
        if self.access_kind not in {"observed", "target_only", "privileged"}:
            raise SchemaValidationError("unsupported access_kind")
        anchor = _optional_id(self.anchor_frame_id, "anchor_frame_id")
        if self.access_kind == "privileged" and anchor is not None:
            raise SchemaValidationError("privileged projection cannot have an anchor")
        if self.access_kind != "privileged" and anchor is None:
            raise SchemaValidationError("observed/target projection requires an anchor")
        object.__setattr__(self, "anchor_frame_id", anchor)
        payload = _freeze_json(self.payload, "projection payload")
        if not isinstance(payload, Mapping):
            raise SchemaValidationError("projection payload must be a mapping")
        object.__setattr__(self, "payload", payload)
        if self.access_kind == "observed":
            _validate_observed_payload(payload)
        _sha256(self.projection_hash, "projection_hash")
        expected = self.compute_hash(self.access_kind, self.anchor_frame_id, payload)
        if self.projection_hash != expected:
            raise SchemaValidationError("projection_hash does not match access projection content")
        _validate_projection_shape(self.access_kind, self.anchor_frame_id, payload)

    @staticmethod
    def compute_hash(
        access_kind: object, anchor_frame_id: object, payload: object
    ) -> str:
        return _fingerprint(
            {
                "schema_version": ACCESS_SCHEMA_VERSION,
                "trajectory_schema_version": TRAJECTORY_SCHEMA_VERSION,
                "access_kind": access_kind,
                "anchor_frame_id": anchor_frame_id,
                "payload": payload,
            }
        )

    @classmethod
    def create(
        cls, access_kind: str, anchor_frame_id: str | None, payload: Mapping[str, object]
    ) -> "AccessProjection":
        projection_hash = cls.compute_hash(access_kind, anchor_frame_id, payload)
        return cls(
            ACCESS_SCHEMA_VERSION,
            TRAJECTORY_SCHEMA_VERSION,
            access_kind,
            anchor_frame_id,
            payload,
            projection_hash,
        )

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "trajectory_schema_version": self.trajectory_schema_version,
            "access_kind": self.access_kind,
            "anchor_frame_id": self.anchor_frame_id,
            "payload": _plain(self.payload),
            "projection_hash": self.projection_hash,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "AccessProjection":
        value = _mapping(value, "access projection")
        _exact_keys(
            value,
            {"schema_version", "trajectory_schema_version", "access_kind", "anchor_frame_id", "payload", "projection_hash"},
            "access projection",
        )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            trajectory_schema_version=value["trajectory_schema_version"],  # type: ignore[arg-type]
            access_kind=value["access_kind"],  # type: ignore[arg-type]
            anchor_frame_id=value["anchor_frame_id"],  # type: ignore[arg-type]
            payload=value["payload"],  # type: ignore[arg-type]
            projection_hash=value["projection_hash"],  # type: ignore[arg-type]
        )


__all__ = [
    "ACCESS_SCHEMA_VERSION",
    "TRAJECTORY_SCHEMA_VERSION",
    "AccessProjection",
    "AngleReference",
    "AngleState",
    "CapabilityFlags",
    "Cell2D",
    "CensoringRecord",
    "ControlRecord",
    "ConvergenceRecord",
    "DiagnosticTrial",
    "EdgeParameterChange",
    "EdgeReference",
    "EdgeState",
    "EventRecord",
    "NamedScalars",
    "NodeReference",
    "NodeState",
    "NormalizerRecord",
    "PressureDerivation",
    "PrivilegedRecord",
    "ProvenanceRecord",
    "SchemaValidationError",
    "StateRecord",
    "StaticGraph",
    "TrajectoryRecord",
    "canonicalize_p02_phase",
]
