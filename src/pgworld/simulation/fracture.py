"""Transactional quasi-static rupture/relaxation execution.

This module executes the P02-02 logical event contract against an injected
mechanics backend.  It records raw named phase mechanics but intentionally
does not localize events or derive deletion/work/relaxation energy balances.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

import numpy as np

from pgworld.physics.damage import (
    CriterionObservation,
    DamageAssessment,
    DamageLaw,
    DamageState,
    DamageTransition,
    MaterialRuptureEvent,
    ThresholdField,
    accept_next_material_rupture,
    assess_material_rupture,
    validate_irreversible_transition,
)
from pgworld.simulation.controls import AxisFrame, QuasiStaticControlStep
from pgworld.simulation.topology import (
    AngleTopology,
    BondTopology,
    Cell2D,
    TopologyMutationPlan,
    TopologyRegistry,
    TopologyState,
)


FRACTURE_SCHEMA_VERSION = "pgworld.fracture_execution.v1"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PHASES = {"pre_delete_relaxed", "post_delete_unrelaxed", "post_event_relaxed"}
_RELAXED_PHASES = {"pre_delete_relaxed", "post_event_relaxed"}
_LOAD_UNITS = {"dimensionless", "pN/nm^2"}


class FractureExecutionError(RuntimeError):
    """Fail-closed fracture execution or replay error."""


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise FractureExecutionError(f"{field} must be a nonempty trimmed string")
    if any(ord(char) < 32 for char in value):
        raise FractureExecutionError(f"{field} cannot contain control characters")
    return value


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise FractureExecutionError(f"{field} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise FractureExecutionError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise FractureExecutionError(f"{field} must be finite")
    return result


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise FractureExecutionError(f"{field} must be an integer >= {minimum}")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise FractureExecutionError(f"{field} must be an object with string keys")
    return value


def _keys(value: Mapping[str, object], expected: set[str], field: str) -> None:
    missing = expected - set(value); extra = set(value) - expected
    if missing or extra:
        raise FractureExecutionError(f"{field} fields mismatch; missing={sorted(missing)}, unexpected={sorted(extra)}")


def _sequence(value: object, field: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise FractureExecutionError(f"{field} must be an array")
    return tuple(value)


def _hash(body: object) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _array(value: object, shape: tuple[int, ...], field: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise FractureExecutionError(f"{field} must be a finite array") from error
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise FractureExecutionError(f"{field} must be finite with shape {shape}")
    result = np.array(result, copy=True)
    result.setflags(write=False)
    return result


def _float_mapping(value: object, field: str) -> Mapping[str, float]:
    source = _mapping(value, field)
    result: dict[str, float] = {}
    for key, item in source.items():
        key = _string(key, f"{field} key")
        result[key] = _finite(item, f"{field}.{key}")
    return MappingProxyType(dict(sorted(result.items())))


def _deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _control_from_record(value: object) -> QuasiStaticControlStep:
    record = _mapping(value, "control")
    expected = {
        "control_id", "step_index", "control_kind", "loading_mode", "axes", "reference_state_id",
        "reference_reset_policy", "lambda_load", "load_coordinate_kind", "load_coordinate_unit",
        "path_progress", "progress_increment", "progress_unit", "progress_semantics",
        "absolute_control_semantics", "increment_control_semantics", "absolute_deformation_gradient",
        "incremental_deformation_gradient", "absolute_tension_target_pN_per_nm",
        "incremental_tension_target_pN_per_nm", "pressure_derivation", "physical_time", "physical_time_valid",
    }
    _keys(record, expected, "control")
    axes_record = _mapping(record["axes"], "control.axes")
    _keys(axes_record, {"axis_meanings", "basis_columns_in_current_coordinates"}, "control.axes")
    meanings = _mapping(axes_record["axis_meanings"], "control.axes.axis_meanings")
    _keys(meanings, {"x", "y"}, "control.axes.axis_meanings")
    try:
        control = QuasiStaticControlStep(
            control_id=record["control_id"], step_index=record["step_index"], control_kind=record["control_kind"],
            loading_mode=record["loading_mode"],
            axes=AxisFrame(meanings["x"], meanings["y"], axes_record["basis_columns_in_current_coordinates"]),
            reference_state_id=record["reference_state_id"], lambda_load=record["lambda_load"],
            load_coordinate_unit=record["load_coordinate_unit"], progress_unit=record["progress_unit"],
            path_progress=record["path_progress"], progress_increment=record["progress_increment"],
            absolute_deformation_gradient=record["absolute_deformation_gradient"],
            incremental_deformation_gradient=record["incremental_deformation_gradient"],
            absolute_tension_target_pN_per_nm=record["absolute_tension_target_pN_per_nm"],
            incremental_tension_target_pN_per_nm=record["incremental_tension_target_pN_per_nm"],
            pressure_derivation=record["pressure_derivation"], physical_time=record["physical_time"],
            physical_time_valid=record["physical_time_valid"],
        )
    except Exception as error:
        raise FractureExecutionError("control record is invalid") from error
    if _plain(control.as_record()) != _plain(record):
        raise FractureExecutionError("control record is noncanonical or has invalid semantics")
    return control


def _bool_mapping(value: object, ids: tuple[str, ...], field: str) -> Mapping[str, bool]:
    source = _mapping(value, field)
    if set(source) != set(ids):
        raise FractureExecutionError(f"{field} must cover exact physical-bond IDs")
    result: dict[str, bool] = {}
    for stable_id in ids:
        if type(source[stable_id]) is not bool:
            raise FractureExecutionError(f"{field}.{stable_id} must be boolean")
        result[stable_id] = source[stable_id]  # type: ignore[assignment]
    return MappingProxyType(result)


@dataclass(frozen=True)
class ConvergenceDiagnostics:
    is_accepted: bool
    termination_reason: str
    max_force_residual_pN: float
    iterations: int
    maximum_iterations: int
    residual_tolerance_pN: float

    def __post_init__(self) -> None:
        if type(self.is_accepted) is not bool:
            raise FractureExecutionError("convergence accepted must be boolean")
        _string(self.termination_reason, "termination_reason")
        residual = _finite(self.max_force_residual_pN, "max_force_residual_pN")
        tolerance = _finite(self.residual_tolerance_pN, "residual_tolerance_pN")
        if residual < 0.0 or tolerance <= 0.0:
            raise FractureExecutionError("residual/tolerance must be nonnegative/positive")
        object.__setattr__(self, "max_force_residual_pN", residual)
        object.__setattr__(self, "residual_tolerance_pN", tolerance)
        _integer(self.iterations, "iterations")
        _integer(self.maximum_iterations, "maximum_iterations", minimum=1)
        expected = residual <= tolerance and self.iterations < self.maximum_iterations
        if self.is_accepted != expected:
            raise FractureExecutionError("convergence acceptance differs from residual/iteration policy")

    @property
    def accepted(self) -> bool:
        return self.is_accepted

    @classmethod
    def successful(cls, residual: float, iterations: int, maximum_iterations: int, tolerance: float = 1e-8) -> "ConvergenceDiagnostics":
        return cls(True, "residual_force_below_tolerance", residual, iterations, maximum_iterations, tolerance)

    @classmethod
    def rejected(cls, reason: str, residual: float, iterations: int, maximum_iterations: int, tolerance: float = 1e-8) -> "ConvergenceDiagnostics":
        return cls(False, reason, residual, iterations, maximum_iterations, tolerance)

    def as_record(self) -> dict[str, object]:
        return {"accepted": self.is_accepted, "termination_reason": self.termination_reason, "max_force_residual_pN": self.max_force_residual_pN, "iterations": self.iterations, "maximum_iterations": self.maximum_iterations, "residual_tolerance_pN": self.residual_tolerance_pN}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ConvergenceDiagnostics":
        value = _mapping(value, "convergence")
        _keys(value, {"accepted", "termination_reason", "max_force_residual_pN", "iterations", "maximum_iterations", "residual_tolerance_pN"}, "convergence")
        kwargs = dict(value); kwargs["is_accepted"] = kwargs.pop("accepted")
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True, eq=False)
class BackendObservation:
    observation_id: str
    phase: str
    registry_id: str
    topology: TopologyState
    damage_state_id: str
    physical_bond_ids: tuple[str, ...]
    alive_mask: Mapping[str, bool]
    rupture_mask: Mapping[str, bool]
    prescribed_removal_mask: Mapping[str, bool]
    law_id: str
    control: QuasiStaticControlStep
    control_id: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    cell: Cell2D
    solver_atom_ids: tuple[int, ...]
    stable_node_ids: tuple[str, ...]
    positions_nm: np.ndarray
    forces_pN: np.ndarray
    source_edge_image_offsets_n_ij: Mapping[str, tuple[int, int]]
    current_edge_image_offsets_n_ij: Mapping[str, tuple[int, int]]
    criterion_values: Mapping[str, float]
    criterion_unit: str
    total_tension_pN_per_nm: np.ndarray
    reference_total_tension_pN_per_nm: np.ndarray
    incremental_tension_pN_per_nm: np.ndarray
    raw_energies_pN_nm: Mapping[str, float]
    convergence: ConvergenceDiagnostics
    boundary_conditions: Mapping[str, object]
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = FRACTURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != FRACTURE_SCHEMA_VERSION or self.phase not in _PHASES:
            raise FractureExecutionError("invalid observation schema or phase")
        if _HASH_RE.fullmatch(self.registry_id) is None or _HASH_RE.fullmatch(self.damage_state_id) is None:
            raise FractureExecutionError("observation identities must be sha256 digests")
        if not isinstance(self.topology, TopologyState) or self.topology.registry_id != self.registry_id:
            raise FractureExecutionError("observation topology/registry mismatch")
        ids = tuple(_string(item, "physical_bond_id") for item in self.physical_bond_ids)
        if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
            raise FractureExecutionError("physical_bond_ids must be canonical unique IDs")
        object.__setattr__(self, "physical_bond_ids", ids)
        alive = _bool_mapping(self.alive_mask, ids, "alive_mask")
        ruptured = _bool_mapping(self.rupture_mask, ids, "rupture_mask")
        prescribed = _bool_mapping(self.prescribed_removal_mask, ids, "prescribed_removal_mask")
        for stable_id in ids:
            if ruptured[stable_id] and prescribed[stable_id]:
                raise FractureExecutionError("a physical bond cannot be ruptured and prescribed-removed")
            if alive[stable_id] != (not ruptured[stable_id] and not prescribed[stable_id]):
                raise FractureExecutionError("observation alive mask must complement terminal damage masks")
        if tuple(stable_id for stable_id in ids if alive[stable_id]) != self.topology.alive_bond_ids:
            raise FractureExecutionError("observation damage alive mask differs from physical topology")
        object.__setattr__(self, "alive_mask", alive); object.__setattr__(self, "rupture_mask", ruptured); object.__setattr__(self, "prescribed_removal_mask", prescribed)
        _string(self.law_id, "law_id")
        if not isinstance(self.control, QuasiStaticControlStep):
            raise FractureExecutionError("control must be a validated QuasiStaticControlStep")
        _string(self.control_id, "control_id")
        if (
            self.control_id != self.control.control_id
            or self.load_coordinate != self.control.lambda_load
            or self.load_coordinate_unit != self.control.load_coordinate_unit
            or self.path_progress != self.control.path_progress
            or self.progress_unit != self.control.progress_unit
            or self.reference_state_id != self.control.reference_state_id
        ):
            raise FractureExecutionError("observation scalar control fields differ from full control record")
        object.__setattr__(self, "load_coordinate", _finite(self.load_coordinate, "load_coordinate"))
        object.__setattr__(self, "path_progress", _finite(self.path_progress, "path_progress"))
        if self.load_coordinate_unit not in _LOAD_UNITS or self.path_progress < 0 or self.progress_unit != self.load_coordinate_unit:
            raise FractureExecutionError("invalid path progress/unit")
        _string(self.physics_profile_id, "physics_profile_id")
        if _HASH_RE.fullmatch(self.physics_profile_hash) is None:
            raise FractureExecutionError("physics_profile_hash must be sha256")
        _string(self.reference_state_id, "reference_state_id")
        if not isinstance(self.cell, Cell2D):
            raise FractureExecutionError("cell must be Cell2D")
        atom_ids = tuple(_integer(item, "solver_atom_id", minimum=1) for item in self.solver_atom_ids)
        node_ids = tuple(_string(item, "stable_node_id") for item in self.stable_node_ids)
        if (
            atom_ids != tuple(sorted(atom_ids))
            or len(set(atom_ids)) != len(atom_ids)
            or len(atom_ids) != len(node_ids)
            or len(set(node_ids)) != len(node_ids)
            or set(node_ids) != set(self.topology.node_ids)
        ):
            raise FractureExecutionError("atom/stable-node rows must be unique and solver-tag ordered")
        object.__setattr__(self, "solver_atom_ids", atom_ids); object.__setattr__(self, "stable_node_ids", node_ids)
        object.__setattr__(self, "positions_nm", _array(self.positions_nm, (len(atom_ids), 2), "positions_nm"))
        object.__setattr__(self, "forces_pN", _array(self.forces_pN, (len(atom_ids), 2), "forces_pN"))
        expected_offsets = set(ids)
        source = self._offsets(self.source_edge_image_offsets_n_ij, expected_offsets, "source_edge_image_offsets_n_ij")
        current = self._offsets(self.current_edge_image_offsets_n_ij, set(self.topology.alive_bond_ids), "current_edge_image_offsets_n_ij")
        object.__setattr__(self, "source_edge_image_offsets_n_ij", source); object.__setattr__(self, "current_edge_image_offsets_n_ij", current)
        criteria = _float_mapping(self.criterion_values, "criterion_values")
        if set(criteria) != set(self.topology.alive_bond_ids):
            raise FractureExecutionError("criterion values must cover exact alive bonds")
        object.__setattr__(self, "criterion_values", criteria)
        _string(self.criterion_unit, "criterion_unit")
        total_tension = _array(self.total_tension_pN_per_nm, (2, 2), "total_tension")
        reference_tension = _array(self.reference_total_tension_pN_per_nm, (2, 2), "reference_total_tension")
        incremental_tension = _array(self.incremental_tension_pN_per_nm, (2, 2), "incremental_tension")
        if not np.allclose(incremental_tension, total_tension - reference_tension, rtol=0.0, atol=1e-12):
            raise FractureExecutionError("incremental tension must equal total minus fixed reference tension within 1e-12 pN/nm")
        object.__setattr__(self, "total_tension_pN_per_nm", total_tension)
        object.__setattr__(self, "reference_total_tension_pN_per_nm", reference_tension)
        object.__setattr__(self, "incremental_tension_pN_per_nm", incremental_tension)
        energies = _float_mapping(self.raw_energies_pN_nm, "raw_energies_pN_nm")
        if not {"pe", "ebond", "eangle"} <= set(energies):
            raise FractureExecutionError("raw energy record requires pe, ebond, and eangle")
        object.__setattr__(self, "raw_energies_pN_nm", energies)
        if not isinstance(self.convergence, ConvergenceDiagnostics):
            raise FractureExecutionError("convergence must be validated")
        boundary = _mapping(self.boundary_conditions, "boundary_conditions")
        _keys(boundary, {"kind", "anchored_stable_node_ids", "anchored_solver_atom_ids", "constrained_components", "equilibrium_scope", "reaction_forces_recorded", "node_force_scope", "convergence_residual_scope"}, "boundary_conditions")
        kind = boundary["kind"]
        anchored_nodes = tuple(_string(item, "anchored_stable_node_id") for item in _sequence(boundary["anchored_stable_node_ids"], "anchored_stable_node_ids"))
        anchored_atoms = tuple(_integer(item, "anchored_solver_atom_id", minimum=1) for item in _sequence(boundary["anchored_solver_atom_ids"], "anchored_solver_atom_ids"))
        if len(anchored_nodes) != len(anchored_atoms) or len(set(anchored_nodes)) != len(anchored_nodes) or len(set(anchored_atoms)) != len(anchored_atoms):
            raise FractureExecutionError("anchored boundary-condition rows must be unique pairs")
        row_map = dict(zip(self.solver_atom_ids, self.stable_node_ids))
        if any(row_map.get(atom_id) != node_id for atom_id, node_id in zip(anchored_atoms, anchored_nodes)):
            raise FractureExecutionError("anchored boundary-condition rows differ from atom/node mapping")
        if type(boundary["reaction_forces_recorded"]) is not bool:
            raise FractureExecutionError("reaction_forces_recorded must be boolean")
        constrained_components = tuple(_string(item, "constrained_component") for item in _sequence(boundary["constrained_components"], "constrained_components"))
        if kind == "all_nodes_free":
            if (
                anchored_nodes or constrained_components
                or boundary["equilibrium_scope"] != "all_degrees_of_freedom"
                or boundary["reaction_forces_recorded"] is not True
                or boundary["node_force_scope"] != "all_computed_forces"
                or boundary["convergence_residual_scope"] != "all_degrees_of_freedom"
            ):
                raise FractureExecutionError("all-free boundary-condition semantics are inconsistent")
        elif kind == "fixture_only_fixed_endpoints_after_affine_cell_remap":
            if (
                not anchored_nodes or constrained_components != ("x", "y")
                or boundary["equilibrium_scope"] != "free_degrees_of_freedom_only"
                or boundary["reaction_forces_recorded"] is not False
                or boundary["node_force_scope"] != "post_constraint_reactions_excluded"
                or boundary["convergence_residual_scope"] != "free_degrees_of_freedom_post_constraint"
            ):
                raise FractureExecutionError("fixed-endpoint boundary-condition semantics are inconsistent")
        else:
            raise FractureExecutionError("unsupported boundary-condition kind")
        object.__setattr__(self, "boundary_conditions", _deep_freeze(boundary))
        if self.phase in _RELAXED_PHASES and not self.convergence.accepted:
            pass
        if self.phase == "post_delete_unrelaxed" and self.convergence.accepted:
            raise FractureExecutionError("unrelaxed observation cannot claim accepted convergence")
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise FractureExecutionError("quasi-static observation cannot carry physical time")
        if self.observation_id != _hash(self._body()):
            raise FractureExecutionError("observation_id does not match observation record")

    @staticmethod
    def _offsets(value: object, expected: set[str], field: str) -> Mapping[str, tuple[int, int]]:
        source = _mapping(value, field)
        if set(source) != expected:
            raise FractureExecutionError(f"{field} must cover its exact bond set")
        result: dict[str, tuple[int, int]] = {}
        for key in sorted(source):
            raw = _sequence(source[key], f"{field}.{key}")
            if len(raw) != 2 or any(isinstance(item, bool) or not isinstance(item, int) for item in raw):
                raise FractureExecutionError(f"{field}.{key} must be signed integer pair")
            result[key] = (raw[0], raw[1])  # type: ignore[assignment]
        return MappingProxyType(result)

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version, "phase": self.phase, "registry_id": self.registry_id,
            "topology": self.topology.as_record(), "damage_state_id": self.damage_state_id,
            "physical_bond_ids": list(self.physical_bond_ids), "alive_mask": dict(self.alive_mask),
            "rupture_mask": dict(self.rupture_mask), "prescribed_removal_mask": dict(self.prescribed_removal_mask),
            "law_id": self.law_id, "control": self.control.as_record(), "control_id": self.control_id, "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit, "path_progress": self.path_progress, "progress_unit": self.progress_unit,
            "physics_profile_id": self.physics_profile_id, "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id, "cell": self.cell.as_record(),
            "solver_atom_ids": list(self.solver_atom_ids), "stable_node_ids": list(self.stable_node_ids),
            "positions_nm": self.positions_nm.tolist(), "forces_pN": self.forces_pN.tolist(),
            "source_edge_image_offsets_n_ij": {key: list(value) for key, value in self.source_edge_image_offsets_n_ij.items()},
            "current_edge_image_offsets_n_ij": {key: list(value) for key, value in self.current_edge_image_offsets_n_ij.items()},
            "criterion_values": dict(self.criterion_values), "criterion_unit": self.criterion_unit,
            "total_tension_pN_per_nm": self.total_tension_pN_per_nm.tolist(),
            "reference_total_tension_pN_per_nm": self.reference_total_tension_pN_per_nm.tolist(),
            "incremental_tension_pN_per_nm": self.incremental_tension_pN_per_nm.tolist(),
            "raw_energies_pN_nm": dict(self.raw_energies_pN_nm), "convergence": self.convergence.as_record(),
            "boundary_conditions": _plain(self.boundary_conditions),
            "physical_time": None, "physical_time_valid": False,
        }

    def as_record(self) -> dict[str, object]:
        return {"observation_id": self.observation_id, **self._body()}

    def as_predictor_record(self) -> dict[str, object]:
        """Explicit predictor allowlist; excludes all content-hash/event provenance."""
        return {
            "phase": self.phase,
            "control": self.control.as_record(),
            "profile": {"physics_profile_id": self.physics_profile_id, "physics_profile_hash": self.physics_profile_hash, "reference_state_id": self.reference_state_id},
            "topology": {"node_ids": list(self.topology.node_ids), "alive_bond_ids": list(self.topology.alive_bond_ids), "alive_angle_ids": list(self.topology.alive_angle_ids), "components": [list(item) for item in self.topology.components], "source_edge_image_offsets_n_ij": {key: list(value) for key, value in self.source_edge_image_offsets_n_ij.items()}, "current_edge_image_offsets_n_ij": {key: list(value) for key, value in self.current_edge_image_offsets_n_ij.items()}},
            "damage_masks": {"alive_mask": dict(self.alive_mask), "rupture_mask": dict(self.rupture_mask), "prescribed_removal_mask": dict(self.prescribed_removal_mask)},
            "mechanics": {"cell": self.cell.as_record(), "solver_atom_ids": list(self.solver_atom_ids), "stable_node_ids": list(self.stable_node_ids), "positions_nm": self.positions_nm.tolist(), "forces_pN": self.forces_pN.tolist(), "criterion_values": dict(self.criterion_values), "criterion_unit": self.criterion_unit, "total_tension_pN_per_nm": self.total_tension_pN_per_nm.tolist(), "reference_total_tension_pN_per_nm": self.reference_total_tension_pN_per_nm.tolist(), "incremental_tension_pN_per_nm": self.incremental_tension_pN_per_nm.tolist(), "raw_energies_pN_nm": dict(self.raw_energies_pN_nm), "convergence": self.convergence.as_record(), "boundary_conditions": _plain(self.boundary_conditions)},
            "physical_time": None, "physical_time_valid": False,
        }

    @classmethod
    def _create(cls, **body: object) -> "BackendObservation":
        serial = cls._body_from_kwargs(body)
        return cls(observation_id=_hash(serial), **body)  # type: ignore[arg-type]

    @staticmethod
    def _body_from_kwargs(body: Mapping[str, object]) -> dict[str, object]:
        temporary = dict(body)
        temporary.setdefault("schema_version", FRACTURE_SCHEMA_VERSION)
        temporary.setdefault("physical_time", None); temporary.setdefault("physical_time_valid", False)
        return {
            "schema_version": temporary["schema_version"], "phase": temporary["phase"], "registry_id": temporary["registry_id"],
            "topology": temporary["topology"].as_record(), "damage_state_id": temporary["damage_state_id"],  # type: ignore[union-attr]
            "physical_bond_ids": list(temporary["physical_bond_ids"]), "alive_mask": dict(temporary["alive_mask"]), "rupture_mask": dict(temporary["rupture_mask"]), "prescribed_removal_mask": dict(temporary["prescribed_removal_mask"]),
            "law_id": temporary["law_id"], "control": temporary["control"].as_record(), "control_id": temporary["control_id"], "load_coordinate": temporary["load_coordinate"], "load_coordinate_unit": temporary["load_coordinate_unit"], "path_progress": temporary["path_progress"], "progress_unit": temporary["progress_unit"],  # type: ignore[union-attr]
            "physics_profile_id": temporary["physics_profile_id"], "physics_profile_hash": temporary["physics_profile_hash"], "reference_state_id": temporary["reference_state_id"], "cell": temporary["cell"].as_record(),  # type: ignore[union-attr]
            "solver_atom_ids": list(temporary["solver_atom_ids"]), "stable_node_ids": list(temporary["stable_node_ids"]),
            "positions_nm": np.asarray(temporary["positions_nm"]).tolist(), "forces_pN": np.asarray(temporary["forces_pN"]).tolist(),
            "source_edge_image_offsets_n_ij": {key: list(value) for key, value in temporary["source_edge_image_offsets_n_ij"].items()},  # type: ignore[union-attr]
            "current_edge_image_offsets_n_ij": {key: list(value) for key, value in temporary["current_edge_image_offsets_n_ij"].items()},  # type: ignore[union-attr]
            "criterion_values": dict(temporary["criterion_values"]), "criterion_unit": temporary["criterion_unit"],  # type: ignore[arg-type]
            "total_tension_pN_per_nm": np.asarray(temporary["total_tension_pN_per_nm"]).tolist(), "reference_total_tension_pN_per_nm": np.asarray(temporary["reference_total_tension_pN_per_nm"]).tolist(), "incremental_tension_pN_per_nm": np.asarray(temporary["incremental_tension_pN_per_nm"]).tolist(),
            "raw_energies_pN_nm": dict(temporary["raw_energies_pN_nm"]), "convergence": temporary["convergence"].as_record(),  # type: ignore[arg-type,union-attr]
            "boundary_conditions": _plain(temporary["boundary_conditions"]),
            "physical_time": None, "physical_time_valid": False,
        }

    @classmethod
    def from_solver_rows(
        cls, *, phase: str, registry: TopologyRegistry, topology_state: TopologyState,
        solver_atom_ids: Sequence[int], positions_nm: object, forces_pN: object,
        criterion_values: Mapping[str, float], criterion_unit: str, cell: Cell2D,
        total_tension_pN_per_nm: object, reference_total_tension_pN_per_nm: object,
        raw_energies_pN_nm: Mapping[str, float], convergence: ConvergenceDiagnostics,
        control: QuasiStaticControlStep, profile_id: str, profile_hash: str, reference_state_id: str,
        damage_state: DamageState | None = None, current_edge_image_offsets_n_ij: Mapping[str, tuple[int, int]] | None = None,
        boundary_conditions: Mapping[str, object] | None = None,
    ) -> "BackendObservation":
        tags = tuple(int(item) for item in solver_atom_ids)
        if len(set(tags)) != len(tags):
            raise FractureExecutionError("duplicate solver atom IDs")
        positions = _array(positions_nm, (len(tags), 2), "positions_nm")
        forces = _array(forces_pN, (len(tags), 2), "forces_pN")
        order = np.argsort(np.asarray(tags)); ordered_tags = tuple(tags[int(index)] for index in order)
        by_atom = {node.solver_atom_id: node.stable_node_id for node in registry.nodes}
        if set(ordered_tags) != set(by_atom):
            raise FractureExecutionError("solver rows do not preserve exact persistent atom IDs")
        if not isinstance(damage_state, DamageState):
            raise FractureExecutionError("from_solver_rows requires a validated DamageState")
        alive = damage_state.alive_mask; rupture = damage_state.rupture_mask; prescribed = damage_state.prescribed_removal_mask
        damage_state_id = damage_state.state_id; law_id = damage_state.law_id
        total = _array(total_tension_pN_per_nm, (2, 2), "total_tension")
        reference = _array(reference_total_tension_pN_per_nm, (2, 2), "reference_total_tension")
        source_offsets = {bond.stable_bond_id: bond.image_offset_n_ij for bond in registry.bonds}
        current_offsets = ({bond_id: source_offsets[bond_id] for bond_id in topology_state.alive_bond_ids}
                           if current_edge_image_offsets_n_ij is None else current_edge_image_offsets_n_ij)
        body = {
            "phase": phase, "registry_id": registry.registry_id, "topology": topology_state,
            "damage_state_id": damage_state_id, "physical_bond_ids": tuple(sorted(alive)),
            "alive_mask": alive, "rupture_mask": rupture, "prescribed_removal_mask": prescribed,
            "law_id": law_id, "control": control, "control_id": control.control_id, "load_coordinate": control.lambda_load,
            "load_coordinate_unit": control.load_coordinate_unit, "path_progress": control.path_progress, "progress_unit": control.progress_unit,
            "physics_profile_id": profile_id, "physics_profile_hash": profile_hash, "reference_state_id": reference_state_id,
            "cell": cell, "solver_atom_ids": ordered_tags, "stable_node_ids": tuple(by_atom[tag] for tag in ordered_tags),
            "positions_nm": positions[order], "forces_pN": forces[order], "source_edge_image_offsets_n_ij": source_offsets,
            "current_edge_image_offsets_n_ij": current_offsets, "criterion_values": criterion_values, "criterion_unit": criterion_unit,
            "total_tension_pN_per_nm": total, "reference_total_tension_pN_per_nm": reference, "incremental_tension_pN_per_nm": total - reference,
            "raw_energies_pN_nm": raw_energies_pN_nm, "convergence": convergence,
            "boundary_conditions": ({"kind": "all_nodes_free", "anchored_stable_node_ids": [], "anchored_solver_atom_ids": [], "constrained_components": [], "equilibrium_scope": "all_degrees_of_freedom", "reaction_forces_recorded": True, "node_force_scope": "all_computed_forces", "convergence_residual_scope": "all_degrees_of_freedom"} if boundary_conditions is None else boundary_conditions),
        }
        return cls._create(**body)

    @classmethod
    def fixture(cls, *, phase: str, registry: TopologyRegistry, topology_state: TopologyState,
                criterion_values: Mapping[str, float], criterion_unit: str, converged: bool,
                control: QuasiStaticControlStep, profile_id: str, profile_hash: str,
                reference_state_id: str, damage_state: DamageState) -> "BackendObservation":
        convergence = ConvergenceDiagnostics.successful(0.0, 1, 100) if converged else ConvergenceDiagnostics.rejected("phase_not_relaxed", 1.0, 0, 100)
        positions = np.vstack([registry.source_wrapped_positions_nm[node.stable_node_id] for node in sorted(registry.nodes, key=lambda item: item.solver_atom_id)])
        alive_criteria = {key: value for key, value in criterion_values.items() if key in topology_state.alive_bond_ids}
        return cls.from_solver_rows(
            phase=phase, registry=registry, topology_state=topology_state,
            solver_atom_ids=tuple(node.solver_atom_id for node in sorted(registry.nodes, key=lambda item: item.solver_atom_id)),
            positions_nm=positions, forces_pN=np.zeros_like(positions), criterion_values=alive_criteria,
            criterion_unit=criterion_unit, cell=registry.cell, total_tension_pN_per_nm=np.zeros((2, 2)),
            reference_total_tension_pN_per_nm=np.zeros((2, 2)), raw_energies_pN_nm={"pe": 0.0, "ebond": 0.0, "eangle": 0.0},
            convergence=convergence, control=control, profile_id=profile_id, profile_hash=profile_hash,
            reference_state_id=reference_state_id, damage_state=damage_state,
        )

    def rephase(self, phase: str) -> "BackendObservation":
        body = self._constructor_body(); body["phase"] = phase
        return BackendObservation._create(**body)

    def _constructor_body(self) -> dict[str, object]:
        return {
            "phase": self.phase, "registry_id": self.registry_id, "topology": self.topology, "damage_state_id": self.damage_state_id,
            "physical_bond_ids": self.physical_bond_ids, "alive_mask": self.alive_mask, "rupture_mask": self.rupture_mask,
            "prescribed_removal_mask": self.prescribed_removal_mask, "law_id": self.law_id, "control": self.control, "control_id": self.control_id,
            "load_coordinate": self.load_coordinate, "load_coordinate_unit": self.load_coordinate_unit, "path_progress": self.path_progress,
            "progress_unit": self.progress_unit, "physics_profile_id": self.physics_profile_id, "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id, "cell": self.cell, "solver_atom_ids": self.solver_atom_ids,
            "stable_node_ids": self.stable_node_ids, "positions_nm": self.positions_nm, "forces_pN": self.forces_pN,
            "source_edge_image_offsets_n_ij": self.source_edge_image_offsets_n_ij,
            "current_edge_image_offsets_n_ij": self.current_edge_image_offsets_n_ij,
            "criterion_values": self.criterion_values, "criterion_unit": self.criterion_unit,
            "total_tension_pN_per_nm": self.total_tension_pN_per_nm, "reference_total_tension_pN_per_nm": self.reference_total_tension_pN_per_nm, "incremental_tension_pN_per_nm": self.incremental_tension_pN_per_nm,
            "raw_energies_pN_nm": self.raw_energies_pN_nm, "convergence": self.convergence,
            "boundary_conditions": self.boundary_conditions,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "BackendObservation":
        value = _mapping(value, "backend observation")
        expected = set(cls._create_record_keys())
        _keys(value, expected, "backend observation")
        topology = TopologyState.from_record(value["topology"])  # type: ignore[arg-type]
        body = dict(value); observation_id = body.pop("observation_id")
        body["topology"] = topology; body["cell"] = Cell2D.from_record(body["cell"])  # type: ignore[arg-type]
        body["convergence"] = ConvergenceDiagnostics.from_record(body["convergence"])  # type: ignore[arg-type]
        body["control"] = _control_from_record(body["control"])
        body["physical_bond_ids"] = tuple(_sequence(body["physical_bond_ids"], "physical_bond_ids"))
        body["solver_atom_ids"] = tuple(_sequence(body["solver_atom_ids"], "solver_atom_ids")); body["stable_node_ids"] = tuple(_sequence(body["stable_node_ids"], "stable_node_ids"))
        return cls(observation_id=observation_id, **body)  # type: ignore[arg-type]

    @staticmethod
    def _create_record_keys() -> tuple[str, ...]:
        return ("observation_id", "schema_version", "phase", "registry_id", "topology", "damage_state_id", "physical_bond_ids", "alive_mask", "rupture_mask", "prescribed_removal_mask", "law_id", "control", "control_id", "load_coordinate", "load_coordinate_unit", "path_progress", "progress_unit", "physics_profile_id", "physics_profile_hash", "reference_state_id", "cell", "solver_atom_ids", "stable_node_ids", "positions_nm", "forces_pN", "source_edge_image_offsets_n_ij", "current_edge_image_offsets_n_ij", "criterion_values", "criterion_unit", "total_tension_pN_per_nm", "reference_total_tension_pN_per_nm", "incremental_tension_pN_per_nm", "raw_energies_pN_nm", "convergence", "boundary_conditions", "physical_time", "physical_time_valid")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, BackendObservation) and self.as_record() == other.as_record()


@dataclass(frozen=True)
class CascadeBudget:
    max_events: int
    max_relaxations: int = 64

    def __post_init__(self) -> None:
        _integer(self.max_events, "max_events")
        _integer(self.max_relaxations, "max_relaxations", minimum=1)


class CascadeStatus(str, Enum):
    STABLE = "stable"
    EVENT_BUDGET_EXHAUSTED = "event_budget_exhausted"
    REJECTED_NONCONVERGENCE = "rejected_nonconvergence"
    INVALID_REFERENCE = "invalid_reference"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"
    BACKEND_CLOSE_FAILED = "backend_close_failed"
    RELAXATION_BUDGET_EXHAUSTED = "relaxation_budget_exhausted"


@dataclass(frozen=True)
class CascadeDiagnostic:
    diagnostic_id: str
    kind: str
    detail: str
    counts_as_physical_failure: bool
    counts_as_mechanical_instability: bool = False
    schema_version: str = FRACTURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != FRACTURE_SCHEMA_VERSION:
            raise FractureExecutionError("invalid diagnostic schema")
        _string(self.kind, "diagnostic kind"); _string(self.detail, "diagnostic detail")
        if type(self.counts_as_physical_failure) is not bool or type(self.counts_as_mechanical_instability) is not bool:
            raise FractureExecutionError("diagnostic claim flags must be boolean")
        if self.counts_as_physical_failure or self.counts_as_mechanical_instability:
            raise FractureExecutionError("execution diagnostics cannot claim physical failure or instability")
        if self.diagnostic_id != _hash(self._body()):
            raise FractureExecutionError("diagnostic_id does not match record")

    def _body(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "kind": self.kind, "detail": self.detail, "counts_as_physical_failure": self.counts_as_physical_failure, "counts_as_mechanical_instability": self.counts_as_mechanical_instability}

    def as_record(self) -> dict[str, object]: return {"diagnostic_id": self.diagnostic_id, **self._body()}

    @classmethod
    def create(cls, kind: str, detail: str, *, counts_as_physical_failure: bool = False) -> "CascadeDiagnostic":
        body = {"schema_version": FRACTURE_SCHEMA_VERSION, "kind": kind, "detail": detail, "counts_as_physical_failure": counts_as_physical_failure, "counts_as_mechanical_instability": False}
        return cls(_hash(body), **body)

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CascadeDiagnostic":
        value = _mapping(value, "diagnostic"); _keys(value, {"diagnostic_id", "schema_version", "kind", "detail", "counts_as_physical_failure", "counts_as_mechanical_instability"}, "diagnostic")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class CascadeTransitionEnvelope:
    envelope_id: str
    previous_damage_state: DamageState
    damage_state: DamageState
    material_event: MaterialRuptureEvent
    mutation_plan: TopologyMutationPlan
    pre_delete_raw: BackendObservation
    post_delete_unrelaxed: BackendObservation
    post_event_relaxed: BackendObservation
    privileged_reference_metadata: Mapping[str, object]
    schema_version: str = FRACTURE_SCHEMA_VERSION

    @staticmethod
    def _validate_observation_against_registry(
        observation: BackendObservation, registry: TopologyRegistry, law: DamageLaw
    ) -> None:
        if law.criterion != "bond_extension_ratio" or observation.criterion_unit != "dimensionless":
            raise FractureExecutionError("P02-03 geometry replay supports bond_extension_ratio only")
        if (
            observation.law_id != law.law_id
            or observation.physics_profile_id != law.physics_profile_id
            or observation.physics_profile_hash != law.physics_profile_hash
            or observation.reference_state_id != law.reference_state_id
            or observation.control.reference_state_id != law.reference_state_id
        ):
            raise FractureExecutionError("observation law/profile/reference provenance differs from replayed law")
        if observation.control.control_kind != "deformation_gradient" or observation.control.absolute_deformation_gradient is None:
            raise FractureExecutionError("P02-03 observation requires full deformation control provenance")
        expected_cell = observation.control.absolute_deformation_gradient @ registry.cell.matrix_nm
        if not np.allclose(observation.cell.matrix_nm, expected_cell, rtol=1e-12, atol=1e-12):
            raise FractureExecutionError("observation cell differs from full absolute deformation control")
        expected_rows = tuple(
            (node.solver_atom_id, node.stable_node_id)
            for node in sorted(registry.nodes, key=lambda item: item.solver_atom_id)
        )
        actual_rows = tuple(zip(observation.solver_atom_ids, observation.stable_node_ids))
        if actual_rows != expected_rows:
            raise FractureExecutionError("observation solver-tag/stable-node mapping differs from registry")
        source_offsets = {bond.stable_bond_id: bond.image_offset_n_ij for bond in registry.bonds}
        if dict(observation.source_edge_image_offsets_n_ij) != source_offsets:
            raise FractureExecutionError("observation authoritative source offsets differ from registry")
        if observation.registry_id != registry.registry_id or observation.cell.periodic != registry.cell.periodic:
            raise FractureExecutionError("observation registry/periodicity differs from registry")
        boundary = observation.boundary_conditions
        if boundary["kind"] == "fixture_only_fixed_endpoints_after_affine_cell_remap":
            degree = {node.stable_node_id: 0 for node in registry.nodes}
            for bond in registry.bonds:
                degree[bond.node_i] += 1; degree[bond.node_j] += 1
            expected_nodes = tuple(sorted(node_id for node_id, value in degree.items() if value == 1))
            expected_atoms = tuple(registry.node(node_id).solver_atom_id for node_id in expected_nodes)
            if tuple(boundary["anchored_stable_node_ids"]) != expected_nodes or tuple(boundary["anchored_solver_atom_ids"]) != expected_atoms:
                raise FractureExecutionError("fixture anchors differ from exact degree-one registry endpoints")
        positions = {
            stable_id: observation.positions_nm[index]
            for index, stable_id in enumerate(observation.stable_node_ids)
        }
        for bond_id in observation.topology.alive_bond_ids:
            bond = registry.bond(bond_id)
            displacement = (
                positions[bond.node_j]
                - positions[bond.node_i]
                + observation.cell.matrix_nm
                @ np.asarray(observation.current_edge_image_offsets_n_ij[bond_id], dtype=float)
            )
            reference_length = float(np.linalg.norm(bond.source_displacement_nm))
            expected_criterion = float(np.linalg.norm(displacement)) / reference_length
            if not math.isclose(
                observation.criterion_values[bond_id], expected_criterion, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise FractureExecutionError("observation criterion differs from positions/cell/registry geometry")

    def __post_init__(self) -> None:
        if self.schema_version != FRACTURE_SCHEMA_VERSION:
            raise FractureExecutionError("invalid transition schema")
        try: validate_irreversible_transition(self.previous_damage_state, self.damage_state)
        except Exception as error: raise FractureExecutionError("invalid damage transition") from error
        if self.material_event.pre_state_id != self.previous_damage_state.state_id or self.damage_state.accepted_material_event_ids[-1] != self.material_event.event_id:
            raise FractureExecutionError("material event does not bind envelope damage states")
        if (
            self.pre_delete_raw.damage_state_id != self.previous_damage_state.state_id
            or self.pre_delete_raw.law_id != self.previous_damage_state.law_id
            or dict(self.pre_delete_raw.alive_mask) != dict(self.previous_damage_state.alive_mask)
            or dict(self.pre_delete_raw.rupture_mask) != dict(self.previous_damage_state.rupture_mask)
            or dict(self.pre_delete_raw.prescribed_removal_mask) != dict(self.previous_damage_state.prescribed_removal_mask)
        ):
            raise FractureExecutionError("pre-delete observation does not bind previous DamageState")
        if self.mutation_plan.pre_topology_state_id != self.pre_delete_raw.topology.topology_state_id or self.mutation_plan.removed_bond_id != self.material_event.physical_bond_id:
            raise FractureExecutionError("mutation plan does not bind event/pre-topology")
        if self.post_delete_unrelaxed.topology != self.post_event_relaxed.topology or self.post_delete_unrelaxed.topology.topology_state_id == self.pre_delete_raw.topology.topology_state_id:
            raise FractureExecutionError("post-event topology binding is invalid")
        expected_common = (
            self.pre_delete_raw.control_id,
            self.pre_delete_raw.load_coordinate,
            self.pre_delete_raw.load_coordinate_unit,
            self.pre_delete_raw.path_progress,
            self.pre_delete_raw.progress_unit,
            self.pre_delete_raw.physics_profile_id,
            self.pre_delete_raw.physics_profile_hash,
            self.pre_delete_raw.reference_state_id,
        )
        for observation in (self.post_delete_unrelaxed, self.post_event_relaxed):
            if (
                observation.control_id,
                observation.load_coordinate,
                observation.load_coordinate_unit,
                observation.path_progress,
                observation.progress_unit,
                observation.physics_profile_id,
                observation.physics_profile_hash,
                observation.reference_state_id,
            ) != expected_common:
                raise FractureExecutionError("transition phases changed control/profile/reference")
            if _plain(observation.boundary_conditions) != _plain(self.pre_delete_raw.boundary_conditions):
                raise FractureExecutionError("transition phases changed boundary-condition provenance")
            if observation.control.as_record() != self.pre_delete_raw.control.as_record():
                raise FractureExecutionError("transition phases changed full control provenance")
            if (
                observation.law_id != self.damage_state.law_id
                or dict(observation.alive_mask) != dict(self.damage_state.alive_mask)
                or dict(observation.rupture_mask) != dict(self.damage_state.rupture_mask)
                or dict(observation.prescribed_removal_mask) != dict(self.damage_state.prescribed_removal_mask)
            ):
                raise FractureExecutionError("post-event observation does not bind staged DamageState")
            if not np.array_equal(observation.cell.matrix_nm, self.pre_delete_raw.cell.matrix_nm) or not np.array_equal(observation.cell.origin_nm, self.pre_delete_raw.cell.origin_nm):
                raise FractureExecutionError("event cascade changed the accepted control cell")
            if not np.allclose(observation.reference_total_tension_pN_per_nm, self.pre_delete_raw.reference_total_tension_pN_per_nm, rtol=0.0, atol=1e-12):
                raise FractureExecutionError("event phases changed the fixed reference tension tensor")
        if self.pre_delete_raw.phase != "pre_delete_relaxed" or self.post_delete_unrelaxed.phase != "post_delete_unrelaxed" or self.post_event_relaxed.phase != "post_event_relaxed":
            raise FractureExecutionError("transition phases are mislabeled")
        if not self.pre_delete_raw.convergence.accepted:
            raise FractureExecutionError("pre-delete state must be an accepted equilibrium")
        if self.post_delete_unrelaxed.damage_state_id != self.damage_state.state_id or self.post_event_relaxed.damage_state_id != self.damage_state.state_id:
            raise FractureExecutionError("post phases do not bind staged damage state")
        if not self.post_event_relaxed.convergence.accepted:
            raise FractureExecutionError("unconverged post-event state cannot be committed")
        if not np.array_equal(self.pre_delete_raw.positions_nm, self.post_delete_unrelaxed.positions_nm):
            raise FractureExecutionError("unrelaxed deletion phase changed positions")
        metadata = _mapping(self.privileged_reference_metadata, "privileged_reference_metadata")
        required = {"access", "law_id", "law_fingerprint", "threshold_realization_id", "predictor_visibility", "physics_profile_id", "physics_profile_hash", "reference_state_id", "damage_law", "threshold_field", "topology_registry"}
        _keys(metadata, required, "privileged_reference_metadata")
        try:
            replayed_law = DamageLaw.from_record(metadata["damage_law"])  # type: ignore[arg-type]
            replayed_field = ThresholdField.from_record(metadata["threshold_field"])  # type: ignore[arg-type]
            replayed_registry = TopologyRegistry.from_record(metadata["topology_registry"])  # type: ignore[arg-type]
            expected_post = replayed_registry.apply_plan(self.pre_delete_raw.topology, self.mutation_plan)
            for observation in (self.pre_delete_raw, self.post_delete_unrelaxed, self.post_event_relaxed):
                self._validate_observation_against_registry(observation, replayed_registry, replayed_law)
        except Exception as error:
            raise FractureExecutionError("privileged replay contract is invalid") from error
        if (
            metadata["access"] != "reference_only_never_predictor_input"
            or metadata["threshold_realization_id"] != self.damage_state.threshold_realization_id
            or metadata["threshold_realization_id"] != replayed_field.realization_id
            or metadata["law_id"] != replayed_law.law_id
            or metadata["law_fingerprint"] != replayed_law.fingerprint
            or metadata["law_fingerprint"] != self.damage_state.law_fingerprint
            or metadata["predictor_visibility"] != replayed_law.predictor_visibility
            or metadata["physics_profile_id"] != replayed_law.physics_profile_id
            or metadata["physics_profile_hash"] != replayed_law.physics_profile_hash
            or metadata["reference_state_id"] != replayed_law.reference_state_id
            or replayed_field.law_id != replayed_law.law_id
            or replayed_field.law_fingerprint != replayed_law.fingerprint
            or replayed_field.physics_profile_id != replayed_law.physics_profile_id
            or replayed_field.physics_profile_hash != replayed_law.physics_profile_hash
            or replayed_field.reference_state_id != replayed_law.reference_state_id
            or replayed_field.criterion != replayed_law.criterion
            or replayed_field.criterion_unit != replayed_law.criterion_unit
            or replayed_field.predictor_visibility != replayed_law.predictor_visibility
            or set(replayed_field.thresholds) != set(self.damage_state.physical_bond_ids)
            or replayed_registry.registry_id != self.pre_delete_raw.registry_id
            or expected_post != self.post_event_relaxed.topology
        ):
            raise FractureExecutionError("privileged damage provenance is inconsistent")
        if (
            self.material_event.law_id != replayed_law.law_id
            or self.material_event.law_fingerprint != replayed_law.fingerprint
            or self.material_event.physics_profile_id != replayed_law.physics_profile_id
            or self.material_event.physics_profile_hash != replayed_law.physics_profile_hash
            or self.material_event.reference_state_id != replayed_law.reference_state_id
            or self.material_event.control_id != self.pre_delete_raw.control_id
            or self.material_event.load_coordinate != self.pre_delete_raw.load_coordinate
            or self.material_event.load_coordinate_unit != self.pre_delete_raw.load_coordinate_unit
            or self.material_event.path_progress != self.pre_delete_raw.path_progress
            or self.material_event.progress_unit != self.pre_delete_raw.progress_unit
            or self.material_event.criterion != replayed_law.criterion
            or self.material_event.criterion_unit != self.pre_delete_raw.criterion_unit
            or self.material_event.criterion_value
            != self.pre_delete_raw.criterion_values[self.material_event.physical_bond_id]
            or self.material_event.threshold_value
            != replayed_field.thresholds[self.material_event.physical_bond_id]
        ):
            raise FractureExecutionError("material event differs from law/control provenance")
        object.__setattr__(self, "privileged_reference_metadata", _deep_freeze(metadata))
        if self.envelope_id != _hash(self._body()):
            raise FractureExecutionError("envelope_id does not match transition")

    def _body(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "previous_damage_state": self.previous_damage_state.as_record(), "damage_state": self.damage_state.as_record(), "material_event": self.material_event.as_record(), "mutation_plan": self.mutation_plan.as_record(), "pre_delete_raw": self.pre_delete_raw.as_record(), "post_delete_unrelaxed": self.post_delete_unrelaxed.as_record(), "post_event_relaxed": self.post_event_relaxed.as_record(), "privileged_reference_metadata": _plain(self.privileged_reference_metadata)}

    def as_record(self) -> dict[str, object]: return {"envelope_id": self.envelope_id, **self._body()}

    def as_observable_record(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "pre_event_observable_state": self.pre_delete_raw.as_predictor_record()}

    @classmethod
    def create(cls, *, previous_damage_state: DamageState, damage_state: DamageState, material_event: MaterialRuptureEvent, mutation_plan: TopologyMutationPlan, pre_delete_raw: BackendObservation, post_delete_unrelaxed: BackendObservation, post_event_relaxed: BackendObservation, law: DamageLaw, field: ThresholdField, registry: TopologyRegistry) -> "CascadeTransitionEnvelope":
        privileged = {"access": "reference_only_never_predictor_input", "law_id": law.law_id, "law_fingerprint": law.fingerprint, "threshold_realization_id": field.realization_id, "predictor_visibility": law.predictor_visibility, "physics_profile_id": law.physics_profile_id, "physics_profile_hash": law.physics_profile_hash, "reference_state_id": law.reference_state_id, "damage_law": law.as_record(), "threshold_field": field.as_record(), "topology_registry": registry.as_record()}
        body = {"schema_version": FRACTURE_SCHEMA_VERSION, "previous_damage_state": previous_damage_state.as_record(), "damage_state": damage_state.as_record(), "material_event": material_event.as_record(), "mutation_plan": mutation_plan.as_record(), "pre_delete_raw": pre_delete_raw.as_record(), "post_delete_unrelaxed": post_delete_unrelaxed.as_record(), "post_event_relaxed": post_event_relaxed.as_record(), "privileged_reference_metadata": privileged}
        return cls(_hash(body), previous_damage_state, damage_state, material_event, mutation_plan, pre_delete_raw, post_delete_unrelaxed, post_event_relaxed, privileged)

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CascadeTransitionEnvelope":
        value = _mapping(value, "transition envelope")
        _keys(value, {"envelope_id", "schema_version", "previous_damage_state", "damage_state", "material_event", "mutation_plan", "pre_delete_raw", "post_delete_unrelaxed", "post_event_relaxed", "privileged_reference_metadata"}, "transition envelope")
        return cls(
            envelope_id=value["envelope_id"], schema_version=value["schema_version"],  # type: ignore[arg-type]
            previous_damage_state=DamageState.from_record(value["previous_damage_state"]),  # type: ignore[arg-type]
            damage_state=DamageState.from_record(value["damage_state"]), material_event=MaterialRuptureEvent.from_record(value["material_event"]),  # type: ignore[arg-type]
            mutation_plan=TopologyMutationPlan.from_record(value["mutation_plan"]), pre_delete_raw=BackendObservation.from_record(value["pre_delete_raw"]),  # type: ignore[arg-type]
            post_delete_unrelaxed=BackendObservation.from_record(value["post_delete_unrelaxed"]), post_event_relaxed=BackendObservation.from_record(value["post_event_relaxed"]),  # type: ignore[arg-type]
            privileged_reference_metadata=value["privileged_reference_metadata"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class CascadeResult:
    result_id: str
    status: CascadeStatus
    transitions: tuple[CascadeTransitionEnvelope, ...]
    damage_state: DamageState
    topology_state: TopologyState
    final_snapshot: BackendObservation | None
    diagnostic: CascadeDiagnostic | None
    control: QuasiStaticControlStep
    control_id: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    backend_closed: bool
    privileged_reference_metadata: Mapping[str, object]
    schema_version: str = FRACTURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != FRACTURE_SCHEMA_VERSION or not isinstance(self.status, CascadeStatus):
            raise FractureExecutionError("invalid cascade result schema/status")
        if isinstance(self.transitions, (str, bytes, Mapping)) or not isinstance(self.transitions, Sequence):
            raise FractureExecutionError("transitions must be a concrete sequence of envelopes")
        transitions = tuple(self.transitions)
        if any(not isinstance(item, CascadeTransitionEnvelope) for item in transitions):
            raise FractureExecutionError("transitions must be envelopes")
        object.__setattr__(self, "transitions", transitions)
        if not isinstance(self.control, QuasiStaticControlStep) or self.control_id != self.control.control_id:
            raise FractureExecutionError("result requires its exact validated full control record")
        result_provenance = (
            self.control_id,
            self.physics_profile_id,
            self.physics_profile_hash,
            self.reference_state_id,
        )
        if self.transitions:
            if self.transitions[-1].damage_state != self.damage_state or self.transitions[-1].post_event_relaxed.topology != self.topology_state:
                raise FractureExecutionError("result final states differ from transition history")
            for index, transition in enumerate(self.transitions):
                if transition.material_event.sequence_index + 1 != len(transition.damage_state.accepted_material_event_ids):
                    raise FractureExecutionError("transition event sequence/history mismatch")
                if index and transition.previous_damage_state != self.transitions[index - 1].damage_state:
                    raise FractureExecutionError("transition chain is discontinuous")
                transition_provenance = (
                    transition.pre_delete_raw.control_id,
                    transition.pre_delete_raw.physics_profile_id,
                    transition.pre_delete_raw.physics_profile_hash,
                    transition.pre_delete_raw.reference_state_id,
                )
                if transition_provenance != result_provenance:
                    raise FractureExecutionError("result provenance differs from transition history")
                if transition.pre_delete_raw.control.as_record() != self.control.as_record():
                    raise FractureExecutionError("result full control differs from transition history")
                if index and not np.allclose(
                    transition.pre_delete_raw.reference_total_tension_pN_per_nm,
                    self.transitions[0].pre_delete_raw.reference_total_tension_pN_per_nm,
                    rtol=0.0,
                    atol=1e-12,
                ):
                    raise FractureExecutionError("transition chain changed the fixed reference tension tensor")
        if self.final_snapshot is not None:
            if self.final_snapshot.topology != self.topology_state or self.final_snapshot.damage_state_id != self.damage_state.state_id:
                raise FractureExecutionError("final snapshot differs from logical final state")
            if (
                self.final_snapshot.control_id,
                self.final_snapshot.physics_profile_id,
                self.final_snapshot.physics_profile_hash,
                self.final_snapshot.reference_state_id,
            ) != result_provenance:
                raise FractureExecutionError("result provenance differs from final snapshot")
            if self.final_snapshot.control.as_record() != self.control.as_record():
                raise FractureExecutionError("result full control differs from final snapshot")
            if self.transitions and not np.allclose(
                self.final_snapshot.reference_total_tension_pN_per_nm,
                self.transitions[0].pre_delete_raw.reference_total_tension_pN_per_nm,
                rtol=0.0,
                atol=1e-12,
            ):
                raise FractureExecutionError("final snapshot changed the fixed reference tension tensor")
        _string(self.control_id, "control_id"); _string(self.physics_profile_id, "physics_profile_id")
        if _HASH_RE.fullmatch(self.physics_profile_hash) is None: raise FractureExecutionError("invalid profile hash")
        _string(self.reference_state_id, "reference_state_id")
        if (
            self.damage_state.physics_profile_id != self.physics_profile_id
            or self.damage_state.physics_profile_hash != self.physics_profile_hash
            or self.damage_state.reference_state_id != self.reference_state_id
        ):
            raise FractureExecutionError("result provenance differs from damage state")
        metadata = _mapping(self.privileged_reference_metadata, "privileged_reference_metadata")
        required = {"access", "law_id", "law_fingerprint", "threshold_realization_id", "predictor_visibility", "physics_profile_id", "physics_profile_hash", "reference_state_id", "damage_law", "threshold_field", "topology_registry"}
        _keys(metadata, required, "privileged_reference_metadata")
        try:
            replayed_law = DamageLaw.from_record(metadata["damage_law"])  # type: ignore[arg-type]
            replayed_field = ThresholdField.from_record(metadata["threshold_field"])  # type: ignore[arg-type]
            replayed_registry = TopologyRegistry.from_record(metadata["topology_registry"])  # type: ignore[arg-type]
            replayed_registry.validate_state(self.topology_state)
        except Exception as error:
            raise FractureExecutionError("result privileged replay contract is invalid") from error
        registry_bonds = tuple(sorted(bond.stable_bond_id for bond in replayed_registry.bonds))
        if (
            metadata["access"] != "reference_only_never_predictor_input"
            or metadata["law_id"] != replayed_law.law_id
            or metadata["law_fingerprint"] != replayed_law.fingerprint
            or metadata["threshold_realization_id"] != replayed_field.realization_id
            or metadata["predictor_visibility"] != replayed_law.predictor_visibility
            or metadata["physics_profile_id"] != replayed_law.physics_profile_id
            or metadata["physics_profile_hash"] != replayed_law.physics_profile_hash
            or metadata["reference_state_id"] != replayed_law.reference_state_id
            or replayed_field.law_id != replayed_law.law_id
            or replayed_field.law_fingerprint != replayed_law.fingerprint
            or replayed_field.physics_profile_id != replayed_law.physics_profile_id
            or replayed_field.physics_profile_hash != replayed_law.physics_profile_hash
            or replayed_field.reference_state_id != replayed_law.reference_state_id
            or replayed_field.criterion != replayed_law.criterion
            or replayed_field.criterion_unit != replayed_law.criterion_unit
            or replayed_field.predictor_visibility != replayed_law.predictor_visibility
            or tuple(sorted(replayed_field.thresholds)) != registry_bonds
            or self.damage_state.law_id != replayed_law.law_id
            or self.damage_state.law_fingerprint != replayed_law.fingerprint
            or self.damage_state.threshold_realization_id != replayed_field.realization_id
            or self.damage_state.physical_bond_ids != registry_bonds
            or self.topology_state.registry_id != replayed_registry.registry_id
            or tuple(bond_id for bond_id in registry_bonds if self.damage_state.alive_mask[bond_id]) != self.topology_state.alive_bond_ids
        ):
            raise FractureExecutionError("result law/field/registry/damage provenance is inconsistent")
        if self.control.reference_state_id != replayed_law.reference_state_id or self.reference_state_id != replayed_law.reference_state_id:
            raise FractureExecutionError("result full control reference differs from replayed law/result reference")
        if (
            self.control.control_kind != "deformation_gradient"
            or not np.allclose(self.control.axes.basis, np.eye(2), rtol=0.0, atol=1e-12)
            or self.control.absolute_deformation_gradient is None
            or self.control.incremental_deformation_gradient is None
            or abs(float(self.control.absolute_deformation_gradient[0, 1])) > 1e-12
            or abs(float(self.control.absolute_deformation_gradient[1, 0])) > 1e-12
            or abs(float(self.control.incremental_deformation_gradient[0, 1])) > 1e-12
            or abs(float(self.control.incremental_deformation_gradient[1, 0])) > 1e-12
        ):
            raise FractureExecutionError("result carries an unsupported non-diagonal deformation control")
        if self.final_snapshot is not None:
            if (
                self.final_snapshot.physical_bond_ids != self.damage_state.physical_bond_ids
                or dict(self.final_snapshot.alive_mask) != dict(self.damage_state.alive_mask)
                or dict(self.final_snapshot.rupture_mask) != dict(self.damage_state.rupture_mask)
                or dict(self.final_snapshot.prescribed_removal_mask) != dict(self.damage_state.prescribed_removal_mask)
                or self.final_snapshot.law_id != self.damage_state.law_id
            ):
                raise FractureExecutionError("result final snapshot masks/law differ from DamageState")
            CascadeTransitionEnvelope._validate_observation_against_registry(self.final_snapshot, replayed_registry, replayed_law)
        for transition in self.transitions:
            transition_metadata = _mapping(transition.privileged_reference_metadata, "transition privileged metadata")
            if (
                transition_metadata["law_fingerprint"] != replayed_law.fingerprint
                or transition_metadata["threshold_realization_id"] != replayed_field.realization_id
                or _plain(transition_metadata["topology_registry"]) != replayed_registry.as_record()
            ):
                raise FractureExecutionError("result privileged provenance differs from a transition")
        object.__setattr__(self, "privileged_reference_metadata", _deep_freeze(metadata))
        if type(self.backend_closed) is not bool: raise FractureExecutionError("backend_closed must be boolean")
        if self.status == CascadeStatus.BACKEND_CLOSE_FAILED:
            if self.backend_closed:
                raise FractureExecutionError("backend-close-failed result cannot claim the backend closed")
        elif not self.backend_closed:
            raise FractureExecutionError("completed result requires closed backend")
        if self.status == CascadeStatus.STABLE and self.diagnostic is not None:
            raise FractureExecutionError("stable result cannot carry diagnostic")
        if self.status != CascadeStatus.STABLE and self.diagnostic is None:
            raise FractureExecutionError("non-stable result requires diagnostic")
        diagnostic_kind = {
            CascadeStatus.INVALID_REFERENCE: "invalid_reference",
            CascadeStatus.REJECTED_NONCONVERGENCE: "nonconvergence",
            CascadeStatus.EVENT_BUDGET_EXHAUSTED: "event_budget_exhausted",
            CascadeStatus.RELAXATION_BUDGET_EXHAUSTED: "relaxation_budget_exhausted",
            CascadeStatus.ROLLED_BACK: "rolled_back",
            CascadeStatus.ROLLBACK_FAILED: "rollback_failed",
            CascadeStatus.BACKEND_CLOSE_FAILED: "backend_close_failed",
        }
        if self.diagnostic is not None and self.diagnostic.kind != diagnostic_kind.get(self.status):
            raise FractureExecutionError("result status and diagnostic kind differ")
        if self.status == CascadeStatus.STABLE and (self.final_snapshot is None or not self.final_snapshot.convergence.accepted):
            raise FractureExecutionError("stable result requires a converged final snapshot")
        if self.status == CascadeStatus.REJECTED_NONCONVERGENCE and (self.final_snapshot is None or self.final_snapshot.convergence.accepted):
            raise FractureExecutionError("nonconvergence result requires a rejected final snapshot")
        if self.status in {CascadeStatus.INVALID_REFERENCE, CascadeStatus.REJECTED_NONCONVERGENCE} and self.transitions:
            raise FractureExecutionError("invalid-reference/nonconvergence results cannot contain transitions")
        if self.status == CascadeStatus.INVALID_REFERENCE and self.final_snapshot is not None:
            raise FractureExecutionError("invalid reference must fail before producing a controlled snapshot")
        if self.status in {
            CascadeStatus.EVENT_BUDGET_EXHAUSTED,
            CascadeStatus.RELAXATION_BUDGET_EXHAUSTED,
            CascadeStatus.ROLLED_BACK,
            CascadeStatus.ROLLBACK_FAILED,
        } and (self.final_snapshot is None or not self.final_snapshot.convergence.accepted):
            raise FractureExecutionError("incomplete cascade status requires the last accepted converged snapshot")
        if self.result_id != _hash(self._body()): raise FractureExecutionError("result_id does not match result")

    def _body(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "status": self.status.value, "transitions": [item.as_record() for item in self.transitions], "damage_state": self.damage_state.as_record(), "topology_state": self.topology_state.as_record(), "final_snapshot": None if self.final_snapshot is None else self.final_snapshot.as_record(), "diagnostic": None if self.diagnostic is None else self.diagnostic.as_record(), "control": self.control.as_record(), "control_id": self.control_id, "physics_profile_id": self.physics_profile_id, "physics_profile_hash": self.physics_profile_hash, "reference_state_id": self.reference_state_id, "backend_closed": self.backend_closed, "privileged_reference_metadata": _plain(self.privileged_reference_metadata)}

    def as_record(self) -> dict[str, object]: return {"result_id": self.result_id, **self._body()}

    def as_observable_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "control": self.control.as_record(),
            "transitions": [transition.as_observable_record() for transition in self.transitions],
            "final_snapshot": None if self.final_snapshot is None else self.final_snapshot.as_predictor_record(),
        }

    @classmethod
    def create(cls, **kwargs: object) -> "CascadeResult":
        temporary = dict(kwargs); temporary.setdefault("schema_version", FRACTURE_SCHEMA_VERSION)
        status = temporary["status"]
        body = {"schema_version": temporary["schema_version"], "status": status.value, "transitions": [item.as_record() for item in temporary["transitions"]], "damage_state": temporary["damage_state"].as_record(), "topology_state": temporary["topology_state"].as_record(), "final_snapshot": None if temporary["final_snapshot"] is None else temporary["final_snapshot"].as_record(), "diagnostic": None if temporary["diagnostic"] is None else temporary["diagnostic"].as_record(), "control": temporary["control"].as_record(), "control_id": temporary["control_id"], "physics_profile_id": temporary["physics_profile_id"], "physics_profile_hash": temporary["physics_profile_hash"], "reference_state_id": temporary["reference_state_id"], "backend_closed": temporary["backend_closed"], "privileged_reference_metadata": _plain(temporary["privileged_reference_metadata"])}  # type: ignore[union-attr]
        return cls(result_id=_hash(body), **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CascadeResult":
        value = _mapping(value, "cascade result")
        _keys(value, {"result_id", "schema_version", "status", "transitions", "damage_state", "topology_state", "final_snapshot", "diagnostic", "control", "control_id", "physics_profile_id", "physics_profile_hash", "reference_state_id", "backend_closed", "privileged_reference_metadata"}, "cascade result")
        transitions = tuple(CascadeTransitionEnvelope.from_record(item) for item in _sequence(value["transitions"], "transitions"))
        final = None if value["final_snapshot"] is None else BackendObservation.from_record(value["final_snapshot"])  # type: ignore[arg-type]
        diagnostic = None if value["diagnostic"] is None else CascadeDiagnostic.from_record(value["diagnostic"])  # type: ignore[arg-type]
        return cls(
            result_id=value["result_id"], status=CascadeStatus(value["status"]), transitions=transitions,
            damage_state=DamageState.from_record(value["damage_state"]), topology_state=TopologyState.from_record(value["topology_state"]),
            final_snapshot=final, diagnostic=diagnostic, control=_control_from_record(value["control"]), control_id=value["control_id"],
            physics_profile_id=value["physics_profile_id"], physics_profile_hash=value["physics_profile_hash"], reference_state_id=value["reference_state_id"],
            backend_closed=value["backend_closed"], privileged_reference_metadata=value["privileged_reference_metadata"], schema_version=value["schema_version"],
        )  # type: ignore[arg-type]


class FractureBackend(Protocol):
    def apply_control(self, control: QuasiStaticControlStep) -> None: ...
    def relax_and_observe(self, *, phase: str, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def observe_unrelaxed(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def delete_angle(self, angle: AngleTopology) -> None: ...
    def delete_bond(self, bond: BondTopology) -> None: ...
    def audit_topology(self, topology_state: TopologyState) -> None: ...
    def checkpoint(self) -> object: ...
    def restore(self, checkpoint: object) -> None: ...
    def observe_restored(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def close(self) -> None: ...


class QuasiStaticFractureCascade:
    def __init__(self, backend: FractureBackend, registry: TopologyRegistry, law: DamageLaw, threshold_field: ThresholdField, budget: CascadeBudget):
        self.backend = backend; self.registry = registry; self.law = law; self.field = threshold_field; self.budget = budget

    def run_step(self, *, control: QuasiStaticControlStep, damage_state: DamageState, topology_state: TopologyState) -> CascadeResult:
        outcome: dict[str, object] | None = None; active_error: BaseException | None = None
        try:
            outcome = self._execute(control, damage_state, topology_state)
        except BaseException as error:
            active_error = error
        close_error: BaseException | None = None
        try:
            self.backend.close()
        except BaseException as error:
            close_error = error
        if active_error is not None:
            if close_error is not None:
                raise FractureExecutionError(f"execution failed ({active_error}); backend close also failed ({close_error})") from active_error
            raise active_error
        assert outcome is not None
        if close_error is not None:
            outcome["status"] = CascadeStatus.BACKEND_CLOSE_FAILED
            outcome["diagnostic"] = CascadeDiagnostic.create("backend_close_failed", str(close_error))
            outcome["backend_closed"] = False
        else:
            outcome["backend_closed"] = True
        return CascadeResult.create(**outcome)

    def _execute(self, control: QuasiStaticControlStep, damage_state: DamageState, topology_state: TopologyState) -> dict[str, object]:
        self._validate_before_commands(control, damage_state, topology_state)
        if damage_state.has_initial_threshold_violation:
            return self._outcome(CascadeStatus.INVALID_REFERENCE, (), damage_state, topology_state, None, CascadeDiagnostic.create("invalid_reference", "initial_threshold_violation"), control)
        try: self.backend.audit_topology(topology_state)
        except Exception as error: raise FractureExecutionError(f"pre-step backend topology audit failed: {error}") from error
        self.backend.apply_control(control)
        pre = self.backend.relax_and_observe(phase="pre_delete_relaxed", control=control, topology_state=topology_state, damage_state=damage_state)
        self._validate_observation(pre, control, damage_state, topology_state, expected_phase="pre_delete_relaxed")
        relaxation_count = 1
        if not pre.convergence.accepted:
            return self._outcome(CascadeStatus.REJECTED_NONCONVERGENCE, (), damage_state, topology_state, pre, CascadeDiagnostic.create("nonconvergence", pre.convergence.termination_reason), control)
        current_damage = damage_state; current_topology = topology_state; current_pre = pre; transitions: list[CascadeTransitionEnvelope] = []
        while True:
            assessment = self._assess(current_pre, current_damage, control)
            if current_damage.has_initial_threshold_violation:
                return self._outcome(CascadeStatus.INVALID_REFERENCE, tuple(transitions), current_damage, current_topology, current_pre, CascadeDiagnostic.create("invalid_reference", "initial_threshold_violation"), control)
            if not assessment.candidates:
                return self._outcome(CascadeStatus.STABLE, tuple(transitions), current_damage, current_topology, current_pre, None, control)
            if len(transitions) >= self.budget.max_events:
                return self._outcome(CascadeStatus.EVENT_BUDGET_EXHAUSTED, tuple(transitions), current_damage, current_topology, current_pre, CascadeDiagnostic.create("event_budget_exhausted", f"max_events={self.budget.max_events}"), control)
            if relaxation_count >= self.budget.max_relaxations:
                return self._outcome(CascadeStatus.RELAXATION_BUDGET_EXHAUSTED, tuple(transitions), current_damage, current_topology, current_pre, CascadeDiagnostic.create("relaxation_budget_exhausted", f"max_relaxations={self.budget.max_relaxations}"), control)
            checkpoint = self.backend.checkpoint()
            candidate = assessment.candidates[0]
            try:
                plan = self.registry.plan_bond_removal(current_topology, candidate.physical_bond_id)
                staged: DamageTransition = accept_next_material_rupture(current_damage, assessment)
                next_topology = self.registry.apply_plan(current_topology, plan)
                for angle_id in plan.removed_angle_ids: self.backend.delete_angle(self.registry.angle(angle_id))
                self.backend.delete_bond(self.registry.bond(plan.removed_bond_id))
                self.backend.audit_topology(next_topology)
                unrelaxed = self.backend.observe_unrelaxed(control=control, topology_state=next_topology, damage_state=staged.state)
                self._validate_observation(unrelaxed, control, staged.state, next_topology, expected_phase="post_delete_unrelaxed")
                if not np.array_equal(current_pre.positions_nm, unrelaxed.positions_nm):
                    raise FractureExecutionError("post-delete unrelaxed capture changed atom positions")
                post = self.backend.relax_and_observe(phase="post_event_relaxed", control=control, topology_state=next_topology, damage_state=staged.state)
                relaxation_count += 1
                self._validate_observation(post, control, staged.state, next_topology, expected_phase="post_event_relaxed")
                self.backend.audit_topology(next_topology)
                if not post.convergence.accepted:
                    raise FractureExecutionError("post-event relaxation did not satisfy convergence policy")
                envelope = CascadeTransitionEnvelope.create(previous_damage_state=current_damage, damage_state=staged.state, material_event=staged.event, mutation_plan=plan, pre_delete_raw=current_pre, post_delete_unrelaxed=unrelaxed, post_event_relaxed=post, law=self.law, field=self.field, registry=self.registry)
            except Exception as error:
                rollback_error: BaseException | None = None
                try:
                    self.backend.restore(checkpoint); self.backend.audit_topology(current_topology)
                    restored = self.backend.observe_restored(control=control, topology_state=current_topology, damage_state=current_damage)
                    self._validate_observation(restored, control, current_damage, current_topology, expected_phase="pre_delete_relaxed")
                    if not self._same_mechanical_state(restored, current_pre):
                        raise FractureExecutionError("restored mechanics differ from last accepted checkpoint")
                except BaseException as restore_error:
                    rollback_error = restore_error
                if rollback_error is not None:
                    return self._outcome(CascadeStatus.ROLLBACK_FAILED, tuple(transitions), current_damage, current_topology, current_pre, CascadeDiagnostic.create("rollback_failed", f"mutation={error}; restore={rollback_error}"), control)
                return self._outcome(CascadeStatus.ROLLED_BACK, tuple(transitions), current_damage, current_topology, current_pre, CascadeDiagnostic.create("rolled_back", str(error)), control)
            transitions.append(envelope); current_damage = staged.state; current_topology = next_topology; current_pre = post.rephase("pre_delete_relaxed")

    def _validate_before_commands(self, control: QuasiStaticControlStep, damage: DamageState, topology: TopologyState) -> None:
        if not isinstance(control, QuasiStaticControlStep) or not isinstance(damage, DamageState) or not isinstance(topology, TopologyState):
            raise FractureExecutionError("validated control/damage/topology objects are required")
        self.registry.validate_state(topology)
        if tuple(stable_id for stable_id in damage.physical_bond_ids if damage.alive_mask[stable_id]) != topology.alive_bond_ids:
            raise FractureExecutionError("logical damage and physical topology alive masks differ")
        if control.reference_state_id != self.law.reference_state_id or damage.reference_state_id != self.law.reference_state_id:
            raise FractureExecutionError("control/damage/law reference identity differs")
        if damage.physics_profile_id != self.law.physics_profile_id or damage.physics_profile_hash != self.law.physics_profile_hash:
            raise FractureExecutionError("damage/law physics profile differs")
        if damage.law_id != self.law.law_id or damage.law_fingerprint != self.law.fingerprint or damage.threshold_realization_id != self.field.realization_id:
            raise FractureExecutionError("damage law/threshold realization differs")
        registry_bonds = {bond.stable_bond_id for bond in self.registry.bonds}
        if not isinstance(self.field, ThresholdField) or (
            self.field.law_id != self.law.law_id
            or self.field.law_fingerprint != self.law.fingerprint
            or self.field.physics_profile_id != self.law.physics_profile_id
            or self.field.physics_profile_hash != self.law.physics_profile_hash
            or self.field.reference_state_id != self.law.reference_state_id
            or self.field.criterion != self.law.criterion
            or self.field.criterion_unit != self.law.criterion_unit
            or self.field.predictor_visibility != self.law.predictor_visibility
            or set(self.field.thresholds) != registry_bonds
            or set(damage.physical_bond_ids) != registry_bonds
        ):
            raise FractureExecutionError("threshold field/law/damage/registry provenance or bond universe differs")
        if self.law.criterion != "bond_extension_ratio" or self.law.criterion_unit != "dimensionless":
            raise FractureExecutionError("P02-03 backend supports bond_extension_ratio only")
        if control.control_kind != "deformation_gradient":
            raise FractureExecutionError("unsupported pressure/tension control in P02-03 backend")
        if not np.allclose(control.axes.basis, np.eye(2), rtol=0.0, atol=1e-12):
            raise FractureExecutionError("unsupported rotated/reflected control mapping")
        for matrix in (control.absolute_deformation_gradient, control.incremental_deformation_gradient):
            assert matrix is not None
            if abs(float(matrix[0, 1])) > 1e-12 or abs(float(matrix[1, 0])) > 1e-12:
                raise FractureExecutionError("P02-03 supports restricted diagonal deformation mappings only")

    def _validate_observation(self, observation: BackendObservation, control: QuasiStaticControlStep, damage: DamageState, topology: TopologyState, *, expected_phase: str) -> None:
        if not isinstance(observation, BackendObservation): raise FractureExecutionError("backend returned an invalid observation")
        if observation.phase != expected_phase:
            raise FractureExecutionError("backend observation phase differs from requested phase")
        if observation.registry_id != self.registry.registry_id or observation.topology != topology or observation.damage_state_id != damage.state_id:
            raise FractureExecutionError("backend observation differs from logical state")
        if (
            observation.law_id != damage.law_id
            or dict(observation.alive_mask) != dict(damage.alive_mask)
            or dict(observation.rupture_mask) != dict(damage.rupture_mask)
            or dict(observation.prescribed_removal_mask) != dict(damage.prescribed_removal_mask)
        ):
            raise FractureExecutionError("backend observation law/masks differ from DamageState")
        if (observation.control_id, observation.load_coordinate, observation.path_progress, observation.physics_profile_id, observation.physics_profile_hash, observation.reference_state_id) != (control.control_id, control.lambda_load, control.path_progress, self.law.physics_profile_id, self.law.physics_profile_hash, self.law.reference_state_id):
            raise FractureExecutionError("backend observation changed control/profile/reference")
        if observation.control.as_record() != control.as_record():
            raise FractureExecutionError("backend observation changed full control record")
        assert control.absolute_deformation_gradient is not None
        expected_cell = control.absolute_deformation_gradient @ self.registry.cell.matrix_nm
        if not np.allclose(observation.cell.matrix_nm, expected_cell, rtol=1e-12, atol=1e-12):
            raise FractureExecutionError("backend observation cell does not realize scheduled absolute deformation")
        if observation.cell.periodic != self.registry.cell.periodic:
            raise FractureExecutionError("backend observation changed periodic flags")
        if observation.criterion_unit != self.law.criterion_unit:
            raise FractureExecutionError("backend criterion unit differs from damage law")
        CascadeTransitionEnvelope._validate_observation_against_registry(observation, self.registry, self.law)

    @staticmethod
    def _same_mechanical_state(left: BackendObservation, right: BackendObservation) -> bool:
        return (
            left.topology == right.topology
            and left.damage_state_id == right.damage_state_id
            and left.solver_atom_ids == right.solver_atom_ids
            and left.stable_node_ids == right.stable_node_ids
            and np.array_equal(left.cell.matrix_nm, right.cell.matrix_nm)
            and np.array_equal(left.cell.origin_nm, right.cell.origin_nm)
            and left.cell.periodic == right.cell.periodic
            and np.allclose(left.positions_nm, right.positions_nm, rtol=0.0, atol=1e-12)
            and np.allclose(left.forces_pN, right.forces_pN, rtol=0.0, atol=1e-10)
            and np.allclose(left.total_tension_pN_per_nm, right.total_tension_pN_per_nm, rtol=0.0, atol=1e-10)
            and np.allclose(left.reference_total_tension_pN_per_nm, right.reference_total_tension_pN_per_nm, rtol=0.0, atol=1e-12)
            and np.allclose(left.incremental_tension_pN_per_nm, right.incremental_tension_pN_per_nm, rtol=0.0, atol=1e-10)
            and dict(left.raw_energies_pN_nm) == dict(right.raw_energies_pN_nm)
            and dict(left.criterion_values) == dict(right.criterion_values)
            and dict(left.source_edge_image_offsets_n_ij) == dict(right.source_edge_image_offsets_n_ij)
            and dict(left.current_edge_image_offsets_n_ij) == dict(right.current_edge_image_offsets_n_ij)
            and _plain(left.boundary_conditions) == _plain(right.boundary_conditions)
        )

    def _assess(self, observation: BackendObservation, damage: DamageState, control: QuasiStaticControlStep) -> DamageAssessment:
        rows = tuple(CriterionObservation(stable_id, self.law.criterion, self.law.criterion_unit, value) for stable_id, value in observation.criterion_values.items())
        return assess_material_rupture(self.law, self.field, damage, rows, phase="accepted_equilibrium", control_id=control.control_id, load_coordinate=control.lambda_load, load_coordinate_unit=control.load_coordinate_unit, path_progress=control.path_progress)

    def _outcome(self, status: CascadeStatus, transitions: tuple[CascadeTransitionEnvelope, ...], damage: DamageState, topology: TopologyState, snapshot: BackendObservation | None, diagnostic: CascadeDiagnostic | None, control: QuasiStaticControlStep) -> dict[str, object]:
        privileged = {
            "access": "reference_only_never_predictor_input",
            "law_id": self.law.law_id,
            "law_fingerprint": self.law.fingerprint,
            "threshold_realization_id": self.field.realization_id,
            "predictor_visibility": self.law.predictor_visibility,
            "physics_profile_id": self.law.physics_profile_id,
            "physics_profile_hash": self.law.physics_profile_hash,
            "reference_state_id": self.law.reference_state_id,
            "damage_law": self.law.as_record(),
            "threshold_field": self.field.as_record(),
            "topology_registry": self.registry.as_record(),
        }
        return {"status": status, "transitions": transitions, "damage_state": damage, "topology_state": topology, "final_snapshot": snapshot, "diagnostic": diagnostic, "control": control, "control_id": control.control_id, "physics_profile_id": self.law.physics_profile_id, "physics_profile_hash": self.law.physics_profile_hash, "reference_state_id": self.law.reference_state_id, "backend_closed": False, "privileged_reference_metadata": privileged}


class LammpsFractureBackend:
    """Serial LAMMPS adapter with exact group+type topology deletion."""

    def __init__(self, *, solver: Any, solver_factory: Any, registry: TopologyRegistry, profile: Any, work_directory: Path, reference_total_tension_pN_per_nm: object):
        self._solver = solver; self._solver_factory = solver_factory; self.registry = registry; self.profile = profile
        self.work_directory = Path(work_directory).resolve(); self.work_directory.mkdir(parents=True, exist_ok=True)
        self.reference_total_tension_pN_per_nm = _array(reference_total_tension_pN_per_nm, (2, 2), "reference tension")
        self.closed = False; self._group_counter = 0; self._live_groups: set[str] = set(); self._command_trace: list[str] = []
        self._checkpoint_counter = 0; self.force_tolerance_pN = 1e-8; self.maximum_iterations = 1000; self.maximum_evaluations = 10000
        degree = {node.stable_node_id: 0 for node in registry.nodes}
        for bond in registry.bonds:
            degree[bond.node_i] += 1; degree[bond.node_j] += 1
        endpoint_nodes = tuple(sorted(node_id for node_id, value in degree.items() if value == 1))
        if len(endpoint_nodes) < 2:
            raise FractureExecutionError("tiny fixture requires at least two degree-one load-bearing endpoints")
        self._anchored_stable_node_ids = endpoint_nodes
        self._anchored_solver_ids = tuple(registry.node(node_id).solver_atom_id for node_id in endpoint_nodes)
        self._reference_criterion_values: Mapping[str, float] = MappingProxyType({})
        self._reference_convergence: ConvergenceDiagnostics | None = None
        self._reference_cell: Cell2D | None = None
        self._last_topology_audit: Mapping[str, object] | None = None

    @classmethod
    def tiny_harmonic_fixture(cls, *, registry: TopologyRegistry, profile: Any, work_directory: Path) -> "LammpsFractureBackend":
        from lammps import lammps
        def factory(): return lammps(cmdargs=["-log", "none", "-screen", "none"])
        solver = factory(); backend = cls(solver=solver, solver_factory=factory, registry=registry, profile=profile, work_directory=work_directory, reference_total_tension_pN_per_nm=np.zeros((2, 2)))
        try:
            backend._configure_fixture()
            convergence = backend._minimize()
            if not convergence.accepted:
                raise FractureExecutionError("fixed-cell fixture reference did not converge")
            backend._command("run 0 post no")
            initial = backend._raw_tension()
            backend.reference_total_tension_pN_per_nm = initial
            _, _, _, _, criteria, cell = backend._gather_geometry(registry.initial_state)
            if not np.array_equal(cell.matrix_nm, registry.cell.matrix_nm) or not np.array_equal(cell.origin_nm, registry.cell.origin_nm):
                raise FractureExecutionError("fixed-cell reference changed the registry cell")
            backend._reference_criterion_values = MappingProxyType(dict(sorted(criteria.items())))
            backend._reference_convergence = convergence
            backend._reference_cell = cell
            return backend
        except Exception:
            backend.close(); raise

    def _command(self, command: str) -> None:
        if "bond/break" in command: raise FractureExecutionError("fix bond/break is forbidden")
        self._command_trace.append(command); self._solver.command(command)

    def _configure_fixture(self) -> None:
        if int(self._solver.version()) != 20260902: raise FractureExecutionError("tiny fixture requires LAMMPS 20260902")
        H = self.registry.cell.matrix_nm
        if abs(float(H[1, 0])) > 1e-12 or abs(float(H[0, 1])) > 1e-12: raise FractureExecutionError("tiny LAMMPS fixture supports orthogonal cells only")
        if self.registry.cell.periodic != (True, True):
            raise FractureExecutionError("tiny LAMMPS fixture requires periodic x/y registry flags")
        solver_ids = tuple(sorted(node.solver_atom_id for node in self.registry.nodes))
        if solver_ids != tuple(range(1, len(solver_ids) + 1)):
            raise FractureExecutionError("tiny LAMMPS fixture requires sequential solver atom IDs")
        angle_selectors: set[tuple[int, tuple[int, int, int]]] = set()
        for angle in self.registry.angles:
            selector = (
                angle.solver_angle_type,
                tuple(sorted(self.registry.node(node_id).solver_atom_id for node_id in angle.node_ids)),
            )
            if selector in angle_selectors:
                raise FractureExecutionError("LAMMPS group+type angle selector is ambiguous")
            angle_selectors.add(selector)
        origin = self.registry.cell.origin_nm; xhi = origin[0] + H[0, 0]; yhi = origin[1] + H[1, 1]
        self._command("units nano"); self._command("dimension 2"); self._command("boundary p p p"); self._command("atom_style angle")
        self._command(f"region p0203 block {origin[0]:.17g} {xhi:.17g} {origin[1]:.17g} {yhi:.17g} -0.5 0.5 units box")
        max_bond_type = max((bond.solver_bond_type for bond in self.registry.bonds), default=1); max_angle_type = max((angle.solver_angle_type for angle in self.registry.angles), default=1)
        self._command(f"create_box 1 p0203 bond/types {max_bond_type} angle/types {max_angle_type} extra/bond/per/atom 4 extra/angle/per/atom 4 extra/special/per/atom 8")
        mass = self.profile.expanded_snapshot()["mass"]["value_ag"] or 1.0
        self._command(f"mass 1 {float(mass):.17g}")
        for node in sorted(self.registry.nodes, key=lambda row: row.solver_atom_id):
            position = self.registry.source_wrapped_positions_nm[node.stable_node_id]
            self._command(f"create_atoms 1 single {position[0]:.17g} {position[1]:.17g} 0.0 units box")
        for bond in self.registry.bonds:
            self._command(f"create_bonds single/bond {bond.solver_bond_type} {self.registry.node(bond.node_i).solver_atom_id} {self.registry.node(bond.node_j).solver_atom_id}")
        for angle in self.registry.angles:
            atom_ids = [self.registry.node(node).solver_atom_id for node in angle.node_ids]
            self._command(f"create_bonds single/angle {angle.solver_angle_type} {atom_ids[0]} {atom_ids[1]} {atom_ids[2]}")
        snapshot = self.profile.expanded_snapshot(); bond_parameters = snapshot["potentials"]["harmonic_bond"]["parameters"]; angle_parameters = snapshot["potentials"]["harmonic_angle"]["parameters"]
        self._command("bond_style harmonic")
        for type_id in sorted({bond.solver_bond_type for bond in self.registry.bonds}): self._command(f"bond_coeff {type_id} {bond_parameters['K_pN_per_nm']:.17g} {bond_parameters['r0_nm']:.17g}")
        self._command("angle_style harmonic")
        for type_id in sorted({angle.solver_angle_type for angle in self.registry.angles}): self._command(f"angle_coeff {type_id} {angle_parameters['K_pN_nm']:.17g} {angle_parameters['theta0_degrees']:.17g}")
        self._command("pair_style zero 5.0"); self._command("pair_coeff * *"); self._setup_observers(); self._command("run 0 post no")
        self._install_endpoint_constraints()

    def _install_endpoint_constraints(self) -> None:
        atom_ids = " ".join(str(item) for item in self._anchored_solver_ids)
        self._command(f"group p0203_anchor id {atom_ids}")
        self._command("fix p0203_anchor_lock p0203_anchor setforce 0.0 0.0 0.0")

    def _boundary_condition_record(self) -> dict[str, object]:
        return {
            "kind": "fixture_only_fixed_endpoints_after_affine_cell_remap",
            "anchored_stable_node_ids": list(self._anchored_stable_node_ids),
            "anchored_solver_atom_ids": list(self._anchored_solver_ids),
            "constrained_components": ["x", "y"],
            "equilibrium_scope": "free_degrees_of_freedom_only",
            "reaction_forces_recorded": False,
            "node_force_scope": "post_constraint_reactions_excluded",
            "convergence_residual_scope": "free_degrees_of_freedom_post_constraint",
        }

    def _setup_observers(self) -> None:
        self._command("compute p0203_config all pressure NULL virial")
        self._command("thermo_style custom step pe ebond eangle fnorm fmax c_p0203_config c_p0203_config[1] c_p0203_config[2] c_p0203_config[4]")
        self._command("thermo_modify norm no")

    @property
    def temporary_groups_live(self) -> tuple[str, ...]: return tuple(sorted(self._live_groups))
    @property
    def command_trace(self) -> tuple[str, ...]: return tuple(self._command_trace)

    @property
    def fixed_reference_criterion_values(self) -> Mapping[str, float]:
        if not self._reference_criterion_values:
            raise FractureExecutionError("fixed-cell reference has not been prepared")
        return self._reference_criterion_values

    @property
    def fixed_reference_convergence(self) -> ConvergenceDiagnostics:
        if self._reference_convergence is None:
            raise FractureExecutionError("fixed-cell reference has not been prepared")
        return self._reference_convergence

    @property
    def fixed_reference_cell(self) -> Cell2D:
        if self._reference_cell is None:
            raise FractureExecutionError("fixed-cell reference has not been prepared")
        return self._reference_cell

    @property
    def last_topology_audit(self) -> Mapping[str, object]:
        if self._last_topology_audit is None:
            raise FractureExecutionError("no solver topology audit has completed")
        return self._last_topology_audit

    def apply_control(self, control: QuasiStaticControlStep) -> None:
        matrix = control.incremental_deformation_gradient; assert matrix is not None
        self._command(f"change_box all x scale {float(matrix[0,0]):.17g} y scale {float(matrix[1,1]):.17g} remap units box")

    def relax_and_observe(self, *, phase: str, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation:
        convergence = self._minimize()
        return self._observe(phase, control, topology_state, damage_state, convergence)

    def _minimize(self) -> ConvergenceDiagnostics:
        self._command("min_style cg")
        step_before = int(self._solver.get_thermo("step"))
        self._command(f"minimize 0.0 {self.force_tolerance_pN:.17g} {self.maximum_iterations} {self.maximum_evaluations}")
        residual = abs(float(self._solver.get_thermo("fmax")))
        iterations = int(self._solver.get_thermo("step")) - step_before
        if residual <= self.force_tolerance_pN and iterations < self.maximum_iterations:
            return ConvergenceDiagnostics.successful(residual, iterations, self.maximum_iterations, self.force_tolerance_pN)
        return ConvergenceDiagnostics.rejected(
            "max_iterations_or_residual_above_tolerance",
            residual,
            min(iterations, self.maximum_iterations),
            self.maximum_iterations,
            self.force_tolerance_pN,
        )

    def observe_unrelaxed(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation:
        self._command("run 0 post no")
        residual = abs(float(self._solver.get_thermo("fmax")))
        return self._observe("post_delete_unrelaxed", control, topology_state, damage_state, ConvergenceDiagnostics.rejected("phase_not_relaxed", max(residual, self.force_tolerance_pN * 2.0), 0, self.maximum_iterations, self.force_tolerance_pN))

    def _observe(self, phase: str, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState, convergence: ConvergenceDiagnostics) -> BackendObservation:
        tags, positions, forces, current_offsets, criteria, cell = self._gather_geometry(topology_state)
        tension = self._raw_tension()
        energies = {"pe": float(self._solver.get_thermo("pe")), "ebond": float(self._solver.get_thermo("ebond")), "eangle": float(self._solver.get_thermo("eangle"))}
        return BackendObservation.from_solver_rows(phase=phase, registry=self.registry, topology_state=topology_state, solver_atom_ids=tuple(int(item) for item in tags), positions_nm=positions, forces_pN=forces, criterion_values=criteria, criterion_unit="dimensionless", cell=cell, total_tension_pN_per_nm=tension, reference_total_tension_pN_per_nm=self.reference_total_tension_pN_per_nm, raw_energies_pN_nm=energies, convergence=convergence, control=control, profile_id=self.profile.profile_id, profile_hash=self.profile.canonical_hash, reference_state_id=damage_state.reference_state_id, damage_state=damage_state, current_edge_image_offsets_n_ij=current_offsets, boundary_conditions=self._boundary_condition_record())

    def _gather_geometry(self, topology_state: TopologyState) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, tuple[int, int]], dict[str, float], Cell2D]:
        ids_view = self._solver.numpy.extract_atom("id"); x_view = self._solver.numpy.extract_atom("x"); f_view = self._solver.numpy.extract_atom("f"); image_view = self._solver.numpy.extract_atom("image")
        nlocal = int(self._solver.extract_global("nlocal")); tags = np.array(ids_view[:nlocal], dtype=int, copy=True)
        positions = np.array(x_view[:nlocal, :2], dtype=float, copy=True); forces = np.array(f_view[:nlocal, :2], dtype=float, copy=True)
        if image_view is None:
            raise FractureExecutionError("solver does not expose periodic image flags")
        images: dict[int, tuple[int, int]] = {}
        # The numpy image view may be packed; gather_atoms with count=3 requests decoded flags.
        try:
            gathered = self._solver.gather_atoms("image", 0, 3)
            flat = np.ctypeslib.as_array(gathered, shape=(3 * len(self.registry.nodes),)).copy().reshape((-1, 3))
            ordered_tags = tuple(sorted(node.solver_atom_id for node in self.registry.nodes))
            if len(flat) != len(ordered_tags):
                raise FractureExecutionError("decoded image row count differs from registry atom count")
            for index, tag in enumerate(ordered_tags): images[tag] = (int(flat[index, 0]), int(flat[index, 1]))
        except Exception as error:
            raise FractureExecutionError("could not decode solver image flags") from error
        tag_by_node = {node.stable_node_id: node.solver_atom_id for node in self.registry.nodes}
        current_offsets = {}
        for bond_id in topology_state.alive_bond_ids:
            bond = self.registry.bond(bond_id); image_i = images[tag_by_node[bond.node_i]]; image_j = images[tag_by_node[bond.node_j]]
            current_offsets[bond_id] = (bond.image_offset_n_ij[0] + image_j[0] - image_i[0], bond.image_offset_n_ij[1] + image_j[1] - image_i[1])
        order = np.argsort(tags); sorted_positions = positions[order]; sorted_tags = tags[order]
        cell = self._current_cell(); position_by_node = {node.stable_node_id: sorted_positions[list(sorted_tags).index(node.solver_atom_id)] for node in self.registry.nodes}
        criteria: dict[str, float] = {}
        for bond_id in topology_state.alive_bond_ids:
            bond = self.registry.bond(bond_id); displacement = position_by_node[bond.node_j] - position_by_node[bond.node_i] + cell.matrix_nm @ np.asarray(current_offsets[bond_id], dtype=float)
            length = float(np.linalg.norm(displacement)); reference = float(np.linalg.norm(bond.source_displacement_nm))
            criteria[bond_id] = length / reference
        return tags, positions, forces, current_offsets, criteria, cell

    def _raw_tension(self) -> np.ndarray:
        vector = self._solver.extract_compute("p0203_config", 0, 1)
        pressure = np.array([[float(vector[0]), float(vector[3])], [float(vector[3]), float(vector[1])]])
        return -pressure

    def _current_cell(self) -> Cell2D:
        boxlo, boxhi, xy, yz, xz, periodicity, box_change = self._solver.extract_box()
        return Cell2D(((float(boxhi[0]-boxlo[0]), float(xy)), (0.0, float(boxhi[1]-boxlo[1]))), (float(boxlo[0]), float(boxlo[1])), (bool(periodicity[0]), bool(periodicity[1])))

    def _with_group(self, atom_ids: Sequence[int], command: str) -> None:
        self._group_counter += 1; group = f"p0203g{self._group_counter:08d}"
        self._command(f"group {group} id {' '.join(str(item) for item in atom_ids)}"); self._live_groups.add(group)
        try: self._command(command.format(group=group))
        finally:
            self._command(f"group {group} delete")
            self._live_groups.discard(group)

    def delete_angle(self, angle: AngleTopology) -> None:
        atoms = [self.registry.node(node).solver_atom_id for node in angle.node_ids]
        self._with_group(atoms, f"delete_bonds {{group}} angle {angle.solver_angle_type} remove special")

    def delete_bond(self, bond: BondTopology) -> None:
        atoms = [self.registry.node(bond.node_i).solver_atom_id, self.registry.node(bond.node_j).solver_atom_id]
        self._with_group(atoms, f"delete_bonds {{group}} bond {bond.solver_bond_type} remove special")

    def topology_counts(self) -> dict[str, int]:
        return {"atoms": int(self._solver.get_natoms()), "bonds": int(self._solver.gather_bonds()[0]), "angles": int(self._solver.gather_angles()[0])}

    def alive_solver_bonds(self) -> tuple[tuple[int, int, int], ...]:
        count, raw = self._solver.gather_bonds(); values = [int(raw[index]) for index in range(3 * count)]
        return tuple(sorted((values[index], min(values[index+1], values[index+2]), max(values[index+1], values[index+2])) for index in range(0, len(values), 3)))

    def _alive_solver_angles(self) -> tuple[tuple[int, int, int, int], ...]:
        count, raw = self._solver.gather_angles(); values = [int(raw[index]) for index in range(4 * count)]
        return tuple(sorted((values[index], values[index+1], values[index+2], values[index+3]) for index in range(0, len(values), 4)))

    def audit_topology(self, topology_state: TopologyState) -> None:
        expected_bonds = tuple(sorted((self.registry.bond(key).solver_bond_type, min(self.registry.node(self.registry.bond(key).node_i).solver_atom_id, self.registry.node(self.registry.bond(key).node_j).solver_atom_id), max(self.registry.node(self.registry.bond(key).node_i).solver_atom_id, self.registry.node(self.registry.bond(key).node_j).solver_atom_id)) for key in topology_state.alive_bond_ids))
        expected_angles = tuple(sorted((self.registry.angle(key).solver_angle_type, *(self.registry.node(node).solver_atom_id for node in self.registry.angle(key).node_ids)) for key in topology_state.alive_angle_ids))
        tags = tuple(sorted(int(item) for item in np.array(self._solver.numpy.extract_atom("id")[:int(self._solver.extract_global("nlocal"))], copy=True)))
        expected_tags = tuple(sorted(node.solver_atom_id for node in self.registry.nodes))
        actual_bonds = self.alive_solver_bonds(); actual_angles = self._alive_solver_angles()
        if tags != expected_tags or actual_bonds != expected_bonds or actual_angles != expected_angles:
            raise FractureExecutionError("solver topology audit differs from exact logical topology")
        self._last_topology_audit = MappingProxyType({
            "topology_state_id": topology_state.topology_state_id,
            "atom_ids": tags,
            "bonds": actual_bonds,
            "angles": actual_angles,
            "counts": MappingProxyType({"atoms": len(tags), "bonds": len(actual_bonds), "angles": len(actual_angles)}),
        })

    def checkpoint(self) -> object:
        self._checkpoint_counter += 1; path = self.work_directory / f"p0203-checkpoint-{self._checkpoint_counter:04d}.restart"
        self._command(f"write_restart {path}"); return path

    def restore(self, checkpoint: object) -> None:
        path = Path(checkpoint)
        if not path.is_file(): raise FractureExecutionError("checkpoint does not exist")
        old = self._solver; old.close(); self._solver = self._solver_factory(); self.closed = False
        self._command(f"read_restart {path}"); self._setup_observers(); self._install_endpoint_constraints(); self._command("run 0 post no")

    def observe_restored(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation:
        self._command("run 0 post no")
        residual = abs(float(self._solver.get_thermo("fmax")))
        if residual > self.force_tolerance_pN:
            raise FractureExecutionError("restored checkpoint no longer satisfies convergence residual")
        return self._observe("pre_delete_relaxed", control, topology_state, damage_state, ConvergenceDiagnostics.successful(residual, 0, self.maximum_iterations, self.force_tolerance_pN))

    def close(self) -> None:
        if self.closed: return
        errors: list[BaseException] = []
        for group in tuple(sorted(self._live_groups)):
            try: self._command(f"group {group} delete")
            except BaseException as error: errors.append(error)
            self._live_groups.discard(group)
        try: self._solver.close()
        except BaseException as error: errors.append(error)
        self.closed = True
        if errors: raise FractureExecutionError("backend close/temporary-group cleanup failed") from errors[0]


__all__ = [
    "FRACTURE_SCHEMA_VERSION", "BackendObservation", "CascadeBudget", "CascadeDiagnostic",
    "CascadeResult", "CascadeStatus", "CascadeTransitionEnvelope", "ConvergenceDiagnostics",
    "FractureBackend", "FractureExecutionError", "LammpsFractureBackend", "QuasiStaticFractureCascade",
]
