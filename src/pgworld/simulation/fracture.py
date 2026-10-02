"""Transactional quasi-static rupture/relaxation execution.

This module executes the P02-02 logical event contract against an injected
mechanics backend. P02-04 adds bounded first-crossing localization and strict
five-phase energy accounting for the certified harmonic fixture; general
nonlinear localization and physical-time claims remain out of scope.
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
LOCALIZATION_SCHEMA_VERSION = "pgworld.fracture_localization.v1"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PHASES = {
    "after_control_before_relax",
    "pre_delete_relaxed",
    "post_delete_unrelaxed",
    "post_event_relaxed",
}
_RELAXED_PHASES = {"pre_delete_relaxed", "post_event_relaxed"}
_LOAD_UNITS = {"dimensionless", "pN/nm^2"}
_RETRYABLE_LOCALIZATION_TERMINATIONS = {"diagnosed_transient_solver_interruption"}


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
        if self.phase in {"after_control_before_relax", "post_delete_unrelaxed"} and self.convergence.accepted:
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
class LocalizationBudget:
    """Independent deterministic budgets for one first-crossing search."""

    max_refinements: int
    max_solver_trials: int
    max_retries_per_trial: int
    load_tolerance: float
    path_tolerance: float

    def __post_init__(self) -> None:
        _integer(self.max_refinements, "max_refinements")
        _integer(self.max_solver_trials, "max_solver_trials", minimum=1)
        _integer(self.max_retries_per_trial, "max_retries_per_trial")
        if self.max_retries_per_trial > 1:
            raise FractureExecutionError("max_retries_per_trial must be at most one diagnosed transient retry")
        load = _finite(self.load_tolerance, "load_tolerance")
        path = _finite(self.path_tolerance, "path_tolerance")
        if load <= 0.0 or path <= 0.0:
            raise FractureExecutionError("localization tolerances must be positive")
        object.__setattr__(self, "load_tolerance", load)
        object.__setattr__(self, "path_tolerance", path)

    def as_record(self) -> dict[str, object]:
        return {
            "max_refinements": self.max_refinements,
            "max_solver_trials": self.max_solver_trials,
            "max_retries_per_trial": self.max_retries_per_trial,
            "load_tolerance": self.load_tolerance,
            "path_tolerance": self.path_tolerance,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "LocalizationBudget":
        value = _mapping(value, "localization budget")
        _keys(value, {"max_refinements", "max_solver_trials", "max_retries_per_trial", "load_tolerance", "path_tolerance"}, "localization budget")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class TrialDomainCertificate:
    """Hash-bound declaration of the domain enforced for localization trials.

    P02-04 executes only the bounded harmonic-fixture certificate.  An
    endpoint-only nonlinear margin record is intentionally non-executable:
    it cannot prove that minimizer iterates remain away from a nonlinear pole.
    """

    certificate_id: str
    domain_kind: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    registry_id: str
    physical_bond_ids: tuple[str, ...]
    potential_family: str
    path_response_contract: str
    backend_response_contract_id: str
    per_evaluation_domain_guard: bool
    stated_minimum_margin_nm: float | None
    schema_version: str = LOCALIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LOCALIZATION_SCHEMA_VERSION:
            raise FractureExecutionError("invalid trial-domain certificate schema")
        if self.domain_kind not in {
            "bounded_harmonic_fixture_no_singular_bonds",
            "nonlinear_endpoint_margin_only_unvalidated",
        }:
            raise FractureExecutionError("unsupported trial-domain certificate kind")
        _string(self.physics_profile_id, "physics_profile_id")
        if _HASH_RE.fullmatch(self.physics_profile_hash) is None:
            raise FractureExecutionError("physics_profile_hash must be sha256")
        _string(self.reference_state_id, "reference_state_id")
        if _HASH_RE.fullmatch(self.registry_id) is None:
            raise FractureExecutionError("registry_id must be sha256")
        ids = tuple(_string(item, "physical_bond_id") for item in _sequence(self.physical_bond_ids, "physical_bond_ids"))
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)) or not ids:
            raise FractureExecutionError("certificate bond IDs must be canonical unique IDs")
        object.__setattr__(self, "physical_bond_ids", ids)
        if self.potential_family not in {"harmonic_quadratic_fixture", "nonlinear_peptide_unvalidated"}:
            raise FractureExecutionError("unsupported trial potential family")
        if self.path_response_contract not in {
            "monotone_extension_ratio_on_one_certified_path_segment",
            "endpoint_only_no_path_monotonicity_proof",
        }:
            raise FractureExecutionError("unsupported path-response certificate")
        if _HASH_RE.fullmatch(self.backend_response_contract_id) is None:
            raise FractureExecutionError("backend_response_contract_id must be sha256")
        if type(self.per_evaluation_domain_guard) is not bool:
            raise FractureExecutionError("per_evaluation_domain_guard must be boolean")
        if self.domain_kind == "bounded_harmonic_fixture_no_singular_bonds":
            if (
                not self.per_evaluation_domain_guard
                or self.stated_minimum_margin_nm is not None
                or self.potential_family != "harmonic_quadratic_fixture"
                or self.path_response_contract != "monotone_extension_ratio_on_one_certified_path_segment"
            ):
                raise FractureExecutionError("harmonic certificate has no nonlinear pole margin")
            expected_backend_contract = _hash({
                "contract": "p0204_bounded_harmonic_monotone_path_v1",
                "registry_id": self.registry_id,
            })
        else:
            margin = _finite(self.stated_minimum_margin_nm, "stated_minimum_margin_nm")
            if margin <= 0.0 or self.per_evaluation_domain_guard:
                raise FractureExecutionError("endpoint-only nonlinear margin cannot claim an iteration guard")
            if (
                self.potential_family != "nonlinear_peptide_unvalidated"
                or self.path_response_contract != "endpoint_only_no_path_monotonicity_proof"
            ):
                raise FractureExecutionError("nonlinear endpoint certificate cannot claim harmonic monotonicity")
            expected_backend_contract = _hash({
                "contract": "p0204_nonlinear_endpoint_only_unvalidated_v1",
                "registry_id": self.registry_id,
            })
            object.__setattr__(self, "stated_minimum_margin_nm", margin)
        if self.backend_response_contract_id != expected_backend_contract:
            raise FractureExecutionError("backend response contract ID differs from the certified registry/kind")
        if self.certificate_id != _hash(self._body()):
            raise FractureExecutionError("certificate_id does not match trial-domain record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "domain_kind": self.domain_kind,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "registry_id": self.registry_id,
            "physical_bond_ids": list(self.physical_bond_ids),
            "potential_family": self.potential_family,
            "path_response_contract": self.path_response_contract,
            "backend_response_contract_id": self.backend_response_contract_id,
            "per_evaluation_domain_guard": self.per_evaluation_domain_guard,
            "stated_minimum_margin_nm": self.stated_minimum_margin_nm,
        }

    def as_record(self) -> dict[str, object]:
        return {"certificate_id": self.certificate_id, **self._body()}

    @classmethod
    def bounded_harmonic_fixture(
        cls, *, physics_profile_id: str, physics_profile_hash: str,
        reference_state_id: str, registry_id: str,
        physical_bond_ids: Sequence[str],
    ) -> "TrialDomainCertificate":
        ids = tuple(_string(item, "physical_bond_id") for item in _sequence(physical_bond_ids, "physical_bond_ids"))
        body = {
            "schema_version": LOCALIZATION_SCHEMA_VERSION,
            "domain_kind": "bounded_harmonic_fixture_no_singular_bonds",
            "physics_profile_id": physics_profile_id,
            "physics_profile_hash": physics_profile_hash,
            "reference_state_id": reference_state_id,
            "registry_id": registry_id,
            "physical_bond_ids": list(sorted(ids)),
            "potential_family": "harmonic_quadratic_fixture",
            "path_response_contract": "monotone_extension_ratio_on_one_certified_path_segment",
            "backend_response_contract_id": _hash({
                "contract": "p0204_bounded_harmonic_monotone_path_v1",
                "registry_id": registry_id,
            }),
            "per_evaluation_domain_guard": True,
            "stated_minimum_margin_nm": None,
        }
        return cls(certificate_id=_hash(body), **body)  # type: ignore[arg-type]

    @classmethod
    def unvalidated_nonlinear_endpoint_margin(
        cls, *, physics_profile_id: str, physics_profile_hash: str,
        reference_state_id: str, registry_id: str,
        physical_bond_ids: Sequence[str],
        stated_minimum_margin_nm: float,
    ) -> "TrialDomainCertificate":
        ids = tuple(_string(item, "physical_bond_id") for item in _sequence(physical_bond_ids, "physical_bond_ids"))
        body = {
            "schema_version": LOCALIZATION_SCHEMA_VERSION,
            "domain_kind": "nonlinear_endpoint_margin_only_unvalidated",
            "physics_profile_id": physics_profile_id,
            "physics_profile_hash": physics_profile_hash,
            "reference_state_id": reference_state_id,
            "registry_id": registry_id,
            "physical_bond_ids": list(sorted(ids)),
            "potential_family": "nonlinear_peptide_unvalidated",
            "path_response_contract": "endpoint_only_no_path_monotonicity_proof",
            "backend_response_contract_id": _hash({
                "contract": "p0204_nonlinear_endpoint_only_unvalidated_v1",
                "registry_id": registry_id,
            }),
            "per_evaluation_domain_guard": False,
            "stated_minimum_margin_nm": stated_minimum_margin_nm,
        }
        return cls(certificate_id=_hash(body), **body)  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "TrialDomainCertificate":
        value = _mapping(value, "trial-domain certificate")
        _keys(value, {"certificate_id", "schema_version", "domain_kind", "physics_profile_id", "physics_profile_hash", "reference_state_id", "registry_id", "physical_bond_ids", "potential_family", "path_response_contract", "backend_response_contract_id", "per_evaluation_domain_guard", "stated_minimum_margin_nm"}, "trial-domain certificate")
        body = dict(value)
        body["physical_bond_ids"] = tuple(_sequence(body["physical_bond_ids"], "physical_bond_ids"))
        return cls(**body)  # type: ignore[arg-type]


class LocalizationStatus(str, Enum):
    LOCALIZED = "localized"
    INVALID_LOWER_BRACKET = "invalid_lower_bracket"
    UPPER_DOES_NOT_CROSS = "upper_does_not_cross"
    DOMAIN_REJECTED = "domain_rejected"
    LIVE_LOWER_MISMATCH = "live_lower_mismatch"
    REFINEMENT_BUDGET_EXHAUSTED = "refinement_budget_exhausted"
    SOLVER_BUDGET_EXHAUSTED = "solver_budget_exhausted"
    RETRY_BUDGET_EXHAUSTED = "retry_budget_exhausted"
    NONCONVERGENCE_REJECTED = "nonconvergence_rejected"
    TRIAL_REJECTED = "trial_rejected"
    RESTORE_FAILED = "restore_failed"
    FINAL_TRANSACTION_ROLLED_BACK = "final_transaction_rolled_back"
    FINAL_TRANSACTION_ROLLBACK_FAILED = "final_transaction_rollback_failed"


@dataclass(frozen=True)
class LocalizationDiagnostic:
    diagnostic_id: str
    kind: str
    detail: str
    counts_as_physical_failure: bool = False
    counts_as_mechanical_instability: bool = False
    schema_version: str = LOCALIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LOCALIZATION_SCHEMA_VERSION:
            raise FractureExecutionError("invalid localization diagnostic schema")
        _string(self.kind, "localization diagnostic kind")
        _string(self.detail, "localization diagnostic detail")
        if self.counts_as_physical_failure is not False or self.counts_as_mechanical_instability is not False:
            raise FractureExecutionError("localization diagnostics cannot claim physical failure or instability")
        if self.diagnostic_id != _hash(self._body()):
            raise FractureExecutionError("localization diagnostic ID does not match record")

    def _body(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "kind": self.kind, "detail": self.detail, "counts_as_physical_failure": False, "counts_as_mechanical_instability": False}

    def as_record(self) -> dict[str, object]:
        return {"diagnostic_id": self.diagnostic_id, **self._body()}

    @classmethod
    def create(cls, kind: str, detail: str) -> "LocalizationDiagnostic":
        body = {"schema_version": LOCALIZATION_SCHEMA_VERSION, "kind": kind, "detail": detail, "counts_as_physical_failure": False, "counts_as_mechanical_instability": False}
        return cls(_hash(body), kind, detail)

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "LocalizationDiagnostic":
        value = _mapping(value, "localization diagnostic")
        _keys(value, {"diagnostic_id", "schema_version", "kind", "detail", "counts_as_physical_failure", "counts_as_mechanical_instability"}, "localization diagnostic")
        return cls(**dict(value))  # type: ignore[arg-type]


def _same_control_path(left: QuasiStaticControlStep, right: QuasiStaticControlStep) -> bool:
    return (
        left.control_kind == right.control_kind == "deformation_gradient"
        and left.loading_mode == right.loading_mode
        and left.axes.as_record() == right.axes.as_record()
        and left.reference_state_id == right.reference_state_id
        and left.load_coordinate_unit == right.load_coordinate_unit
        and left.progress_unit == right.progress_unit
    )


def _path_coordinate(control: QuasiStaticControlStep, initial_lower: QuasiStaticControlStep) -> float:
    return initial_lower.path_progress + abs(control.lambda_load - initial_lower.lambda_load)


def _validate_segment_control(
    control: QuasiStaticControlStep,
    initial_lower: QuasiStaticControlStep,
    initial_upper: QuasiStaticControlStep,
) -> None:
    if not _same_control_path(initial_lower, control):
        raise FractureExecutionError("localization controls do not share one control path")
    denominator = initial_upper.lambda_load - initial_lower.lambda_load
    if abs(denominator) <= 1e-15:
        raise FractureExecutionError("localization segment has no load-coordinate extent")
    alpha = (control.lambda_load - initial_lower.lambda_load) / denominator
    if alpha < -1e-12 or alpha > 1.0 + 1e-12:
        raise FractureExecutionError("localization control lies outside the initial load segment")
    if not math.isclose(
        control.path_progress, _path_coordinate(control, initial_lower),
        rel_tol=0.0, abs_tol=1e-12,
    ):
        raise FractureExecutionError("localization control path progress is not cumulative absolute lambda increment")
    assert initial_lower.absolute_deformation_gradient is not None
    assert initial_upper.absolute_deformation_gradient is not None
    assert control.absolute_deformation_gradient is not None
    assert control.incremental_deformation_gradient is not None
    expected_absolute = (
        (1.0 - alpha) * initial_lower.absolute_deformation_gradient
        + alpha * initial_upper.absolute_deformation_gradient
    )
    expected_incremental = expected_absolute @ np.linalg.inv(
        initial_lower.absolute_deformation_gradient
    )
    if not np.allclose(control.absolute_deformation_gradient, expected_absolute, rtol=0.0, atol=1e-12):
        raise FractureExecutionError("localization control F is not the segment interpolation")
    if not np.allclose(control.incremental_deformation_gradient, expected_incremental, rtol=0.0, atol=1e-12):
        raise FractureExecutionError("localization control incremental F does not map the accepted lower state")
    if not math.isclose(
        control.progress_increment,
        control.path_progress - initial_lower.path_progress,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise FractureExecutionError("localization control progress increment is not relative to the accepted lower state")


@dataclass(frozen=True, eq=False)
class EventLocalizationRecord:
    localization_id: str
    status: LocalizationStatus
    budget: LocalizationBudget
    domain_certificate: TrialDomainCertificate
    initial_lower_control: QuasiStaticControlStep
    initial_upper_control: QuasiStaticControlStep
    lower_bracket_control: QuasiStaticControlStep
    upper_bracket_control: QuasiStaticControlStep
    localized_control: QuasiStaticControlStep | None
    solver_trials: int
    refinements: int
    retries: int
    previous_accepted_observation_id: str
    topology_state_id: str
    damage_state_id: str
    diagnostic: LocalizationDiagnostic | None
    schema_version: str = LOCALIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LOCALIZATION_SCHEMA_VERSION or not isinstance(self.status, LocalizationStatus):
            raise FractureExecutionError("invalid localization record schema/status")
        if not isinstance(self.budget, LocalizationBudget) or not isinstance(self.domain_certificate, TrialDomainCertificate):
            raise FractureExecutionError("localization record requires validated budget/certificate")
        controls = (self.initial_lower_control, self.initial_upper_control, self.lower_bracket_control, self.upper_bracket_control)
        if any(not isinstance(item, QuasiStaticControlStep) for item in controls):
            raise FractureExecutionError("localization bracket requires validated controls")
        if self.initial_upper_control.step_index != self.initial_lower_control.step_index + 1:
            raise FractureExecutionError("initial upper control must be the next scheduled step after the accepted lower")
        for item in (self.lower_bracket_control, self.upper_bracket_control):
            expected_step = (
                self.initial_lower_control.step_index
                if item.as_record() == self.initial_lower_control.as_record()
                else self.initial_upper_control.step_index
            )
            if item.step_index != expected_step:
                raise FractureExecutionError("synthetic bracket control has inconsistent step lineage")
        initial_progress = self.initial_lower_control.path_progress
        terminal_progress = self.initial_upper_control.path_progress
        if terminal_progress <= initial_progress:
            raise FractureExecutionError("localization path progress must increase")
        for item in controls[1:]:
            _validate_segment_control(item, self.initial_lower_control, self.initial_upper_control)
            if item.path_progress < initial_progress - 1e-12 or item.path_progress > terminal_progress + 1e-12:
                raise FractureExecutionError("localization bracket lies outside initial segment")
        if self.lower_bracket_control.path_progress >= self.upper_bracket_control.path_progress:
            raise FractureExecutionError("localization lower bracket must precede crossing upper bracket")
        for value, field in ((self.solver_trials, "solver_trials"), (self.refinements, "refinements"), (self.retries, "retries")):
            _integer(value, field)
        if self.solver_trials > self.budget.max_solver_trials or self.refinements > self.budget.max_refinements:
            raise FractureExecutionError("localization counters exceed their explicit budgets")
        if self.retries > self.solver_trials:
            raise FractureExecutionError("localization retries cannot exceed solver trials")
        if self.retries > self.budget.max_retries_per_trial:
            raise FractureExecutionError("localization retries exceed the diagnosed-transient retry budget")
        if self.refinements > max(0, self.solver_trials - 1):
            raise FractureExecutionError("accepted refinements cannot exceed solver trials after the upper trial")
        if self.status in {
            LocalizationStatus.DOMAIN_REJECTED,
            LocalizationStatus.LIVE_LOWER_MISMATCH,
            LocalizationStatus.INVALID_LOWER_BRACKET,
        } and (self.solver_trials != 0 or self.refinements != 0 or self.retries != 0):
            raise FractureExecutionError("pre-trial localization status cannot report trial counters")
        if self.status in {
            LocalizationStatus.LOCALIZED,
            LocalizationStatus.UPPER_DOES_NOT_CROSS,
            LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED,
            LocalizationStatus.FINAL_TRANSACTION_ROLLED_BACK,
            LocalizationStatus.FINAL_TRANSACTION_ROLLBACK_FAILED,
        } and self.solver_trials < 1:
            raise FractureExecutionError("localization status requires at least one accepted solver trial")
        if self.status is LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED and self.refinements != self.budget.max_refinements:
            raise FractureExecutionError("refinement-budget status must stop at the exact refinement budget")
        if self.status is LocalizationStatus.SOLVER_BUDGET_EXHAUSTED and self.solver_trials != self.budget.max_solver_trials:
            raise FractureExecutionError("solver-budget status must stop at the exact solver budget")
        if self.status is LocalizationStatus.SOLVER_BUDGET_EXHAUSTED and self.solver_trials not in {
            self.refinements + self.retries,
            1 + self.refinements + self.retries,
        }:
            raise FractureExecutionError("solver-budget counters are not reachable from upper/refinement/retry attempts")
        if self.status is LocalizationStatus.UPPER_DOES_NOT_CROSS and self.refinements != 0:
            raise FractureExecutionError("upper-no-cross status cannot contain refinements")
        if self.status is LocalizationStatus.UPPER_DOES_NOT_CROSS and self.solver_trials != 1 + self.retries:
            raise FractureExecutionError("upper-no-cross counters do not match upper/retry attempts")
        if self.status is LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED and self.solver_trials != 1 + self.refinements + self.retries:
            raise FractureExecutionError("refinement-budget counters do not match upper/refinement/retry attempts")
        if self.status is LocalizationStatus.RETRY_BUDGET_EXHAUSTED and self.retries != self.budget.max_retries_per_trial:
            raise FractureExecutionError("retry-budget status must stop at the exact retry budget")
        if self.status is LocalizationStatus.NONCONVERGENCE_REJECTED and self.solver_trials < 1:
            raise FractureExecutionError("nonretryable nonconvergence requires a solver trial")
        if self.status is LocalizationStatus.LOCALIZED and self.solver_trials != 1 + self.refinements + self.retries:
            raise FractureExecutionError("localized counters do not match upper/refinement/retry attempts")
        for identity, field in ((self.previous_accepted_observation_id, "previous_accepted_observation_id"), (self.topology_state_id, "topology_state_id"), (self.damage_state_id, "damage_state_id")):
            if _HASH_RE.fullmatch(identity) is None:
                raise FractureExecutionError(f"{field} must be sha256")
        if self.status is LocalizationStatus.LOCALIZED:
            if self.localized_control is None or self.localized_control.as_record() != self.upper_bracket_control.as_record() or self.diagnostic is not None:
                raise FractureExecutionError("localized result must publish exactly the crossing upper bound")
            _validate_segment_control(self.localized_control, self.initial_lower_control, self.initial_upper_control)
            if (
                abs(self.upper_bracket_control.lambda_load - self.lower_bracket_control.lambda_load) > self.budget.load_tolerance + 1e-15
                or self.upper_bracket_control.path_progress - self.lower_bracket_control.path_progress > self.budget.path_tolerance + 1e-15
            ):
                raise FractureExecutionError("localized result does not satisfy the recorded bracket tolerances")
        elif self.status in {
            LocalizationStatus.FINAL_TRANSACTION_ROLLED_BACK,
            LocalizationStatus.FINAL_TRANSACTION_ROLLBACK_FAILED,
        }:
            if (
                abs(self.upper_bracket_control.lambda_load - self.lower_bracket_control.lambda_load) > self.budget.load_tolerance + 1e-15
                or self.upper_bracket_control.path_progress - self.lower_bracket_control.path_progress > self.budget.path_tolerance + 1e-15
                or self.solver_trials != 1 + self.refinements + self.retries
            ):
                raise FractureExecutionError("final-transaction status lacks a fully localized bracket/counter trace")
            if self.localized_control is not None or not isinstance(self.diagnostic, LocalizationDiagnostic):
                raise FractureExecutionError("failed final transaction cannot publish a localized control")
        elif self.localized_control is not None or not isinstance(self.diagnostic, LocalizationDiagnostic):
            raise FractureExecutionError("nonlocalized result requires only a typed diagnostic")
        expected_diagnostic = {
            LocalizationStatus.INVALID_LOWER_BRACKET: "invalid_lower_bracket",
            LocalizationStatus.UPPER_DOES_NOT_CROSS: "upper_does_not_cross",
            LocalizationStatus.DOMAIN_REJECTED: "nonlinear_iteration_domain_unvalidated",
            LocalizationStatus.LIVE_LOWER_MISMATCH: "live_lower_mismatch",
            LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED: "refinement_budget_exhausted",
            LocalizationStatus.SOLVER_BUDGET_EXHAUSTED: "solver_budget_exhausted",
            LocalizationStatus.RETRY_BUDGET_EXHAUSTED: "trial_nonconvergence",
            LocalizationStatus.NONCONVERGENCE_REJECTED: "nonretryable_nonconvergence",
            LocalizationStatus.TRIAL_REJECTED: "trial_rejected",
            LocalizationStatus.RESTORE_FAILED: "restore_failed",
            LocalizationStatus.FINAL_TRANSACTION_ROLLED_BACK: "final_transaction_rolled_back",
            LocalizationStatus.FINAL_TRANSACTION_ROLLBACK_FAILED: "final_transaction_rollback_failed",
        }
        if self.diagnostic is not None and self.diagnostic.kind != expected_diagnostic.get(self.status):
            raise FractureExecutionError("localization status and diagnostic kind differ")
        expected_budget_detail = {
            LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED: f"max_refinements={self.budget.max_refinements}",
            LocalizationStatus.SOLVER_BUDGET_EXHAUSTED: f"max_solver_trials={self.budget.max_solver_trials}",
            LocalizationStatus.RETRY_BUDGET_EXHAUSTED: f"max_retries_per_trial={self.budget.max_retries_per_trial}",
        }
        if (
            self.diagnostic is not None
            and self.status in expected_budget_detail
            and self.diagnostic.detail != expected_budget_detail[self.status]
        ):
            raise FractureExecutionError("localization diagnostic detail differs from the recorded budget")
        if (
            self.status is not LocalizationStatus.DOMAIN_REJECTED
            and (
                self.domain_certificate.domain_kind != "bounded_harmonic_fixture_no_singular_bonds"
                or self.domain_certificate.potential_family != "harmonic_quadratic_fixture"
                or self.domain_certificate.path_response_contract
                != "monotone_extension_ratio_on_one_certified_path_segment"
                or not self.domain_certificate.per_evaluation_domain_guard
                or self.domain_certificate.stated_minimum_margin_nm is not None
            )
        ):
            raise FractureExecutionError("executed localization status requires the executable harmonic certificate")
        if self.localization_id != _hash(self._body()):
            raise FractureExecutionError("localization_id does not match record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "budget": self.budget.as_record(),
            "domain_certificate": self.domain_certificate.as_record(),
            "initial_lower_control": self.initial_lower_control.as_record(),
            "initial_upper_control": self.initial_upper_control.as_record(),
            "lower_bracket_control": self.lower_bracket_control.as_record(),
            "upper_bracket_control": self.upper_bracket_control.as_record(),
            "localized_control": None if self.localized_control is None else self.localized_control.as_record(),
            "solver_trials": self.solver_trials,
            "refinements": self.refinements,
            "retries": self.retries,
            "previous_accepted_observation_id": self.previous_accepted_observation_id,
            "topology_state_id": self.topology_state_id,
            "damage_state_id": self.damage_state_id,
            "diagnostic": None if self.diagnostic is None else self.diagnostic.as_record(),
        }

    def as_record(self) -> dict[str, object]:
        return {"localization_id": self.localization_id, **self._body()}

    @classmethod
    def create(cls, **kwargs: object) -> "EventLocalizationRecord":
        temporary = dict(kwargs)
        temporary.setdefault("schema_version", LOCALIZATION_SCHEMA_VERSION)
        body = {
            "schema_version": temporary["schema_version"],
            "status": temporary["status"].value,
            "budget": temporary["budget"].as_record(),
            "domain_certificate": temporary["domain_certificate"].as_record(),
            "initial_lower_control": temporary["initial_lower_control"].as_record(),
            "initial_upper_control": temporary["initial_upper_control"].as_record(),
            "lower_bracket_control": temporary["lower_bracket_control"].as_record(),
            "upper_bracket_control": temporary["upper_bracket_control"].as_record(),
            "localized_control": None if temporary["localized_control"] is None else temporary["localized_control"].as_record(),
            "solver_trials": temporary["solver_trials"], "refinements": temporary["refinements"], "retries": temporary["retries"],
            "previous_accepted_observation_id": temporary["previous_accepted_observation_id"], "topology_state_id": temporary["topology_state_id"], "damage_state_id": temporary["damage_state_id"],
            "diagnostic": None if temporary["diagnostic"] is None else temporary["diagnostic"].as_record(),
        }
        return cls(localization_id=_hash(body), **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EventLocalizationRecord":
        value = _mapping(value, "event localization")
        _keys(value, {"localization_id", "schema_version", "status", "budget", "domain_certificate", "initial_lower_control", "initial_upper_control", "lower_bracket_control", "upper_bracket_control", "localized_control", "solver_trials", "refinements", "retries", "previous_accepted_observation_id", "topology_state_id", "damage_state_id", "diagnostic"}, "event localization")
        return cls(
            localization_id=value["localization_id"], status=LocalizationStatus(value["status"]),
            budget=LocalizationBudget.from_record(value["budget"]), domain_certificate=TrialDomainCertificate.from_record(value["domain_certificate"]),
            initial_lower_control=_control_from_record(value["initial_lower_control"]), initial_upper_control=_control_from_record(value["initial_upper_control"]),
            lower_bracket_control=_control_from_record(value["lower_bracket_control"]), upper_bracket_control=_control_from_record(value["upper_bracket_control"]),
            localized_control=None if value["localized_control"] is None else _control_from_record(value["localized_control"]),
            solver_trials=value["solver_trials"], refinements=value["refinements"], retries=value["retries"],
            previous_accepted_observation_id=value["previous_accepted_observation_id"], topology_state_id=value["topology_state_id"], damage_state_id=value["damage_state_id"],
            diagnostic=None if value["diagnostic"] is None else LocalizationDiagnostic.from_record(value["diagnostic"]), schema_version=value["schema_version"],
        )  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EventLocalizationRecord) and self.as_record() == other.as_record()


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


_ENERGY_PHASE_NAMES = (
    "U_previous_accepted",
    "U_after_control_before_relax",
    "U_pre_event_relaxed",
    "U_post_delete_unrelaxed",
    "U_post_event_relaxed",
)


@dataclass(frozen=True, eq=False)
class FractureEnergyAccounting:
    """Phase-correct potential-energy accounting for one material event.

    The signed deletion term is not fracture toughness or dissipation.  The
    conservative loading input is narrowly the instantaneous fixed-topology
    potential change produced by the supported prescribed-deformation step.
    Its partition into equilibrium stored-energy change and pre-event
    relaxation loss is retained explicitly.
    """

    accounting_id: str
    previous_accepted: BackendObservation
    after_control_before_relax: BackendObservation
    transition: CascadeTransitionEnvelope
    control_application_kind: str
    calculation_kind: str
    energy_unit: str
    phase_energies_pN_nm: Mapping[str, float]
    fixed_topology_conservative_loading_work_pN_nm: float
    equilibrium_stored_energy_change_pN_nm: float
    pre_event_relaxation_loss_pN_nm: float
    same_coordinate_deletion_energy_change_pN_nm: float
    held_control_boundary_work_pN_nm: float
    post_delete_relaxation_loss_pN_nm: float
    numerical_tolerance_pN_nm: float
    schema_version: str = LOCALIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LOCALIZATION_SCHEMA_VERSION:
            raise FractureExecutionError("invalid fracture-accounting schema")
        if not isinstance(self.previous_accepted, BackendObservation) or not isinstance(self.after_control_before_relax, BackendObservation) or not isinstance(self.transition, CascadeTransitionEnvelope):
            raise FractureExecutionError("accounting requires exact raw phase observations and transition")
        if self.control_application_kind not in {"new_diagonal_deformation", "no_new_control_same_accepted_state"}:
            raise FractureExecutionError("unsupported accounting control-application kind")
        if self.calculation_kind != "conservative_fixed_topology_instantaneous_control_delta_pe":
            raise FractureExecutionError("unsupported loading-work calculation kind")
        if self.energy_unit != "pN nm":
            raise FractureExecutionError("fracture accounting energy unit must be pN nm")
        tolerance = _finite(self.numerical_tolerance_pN_nm, "numerical_tolerance_pN_nm")
        if tolerance <= 0.0:
            raise FractureExecutionError("accounting numerical tolerance must be positive")
        object.__setattr__(self, "numerical_tolerance_pN_nm", tolerance)
        if not self.previous_accepted.convergence.accepted or self.previous_accepted.phase != "pre_delete_relaxed":
            raise FractureExecutionError("U_previous_accepted must come from an accepted equilibrium")
        if self.control_application_kind == "new_diagonal_deformation":
            if self.after_control_before_relax.phase != "after_control_before_relax" or self.after_control_before_relax.convergence.accepted:
                raise FractureExecutionError("U_after_control_before_relax must be a raw unrelaxed control phase")
        elif self.after_control_before_relax != self.transition.pre_delete_raw:
            raise FractureExecutionError("same-control cascade must alias its already accepted pre-event state")
        pre = self.transition.pre_delete_raw
        if (
            self.previous_accepted.topology != pre.topology
            or self.previous_accepted.damage_state_id != pre.damage_state_id
            or self.after_control_before_relax.topology != pre.topology
            or self.after_control_before_relax.damage_state_id != pre.damage_state_id
        ):
            raise FractureExecutionError("loading phases changed topology or damage before the event")
        if self.after_control_before_relax.control.as_record() != pre.control.as_record():
            raise FractureExecutionError("after-control and pre-event phases use different controls")
        if not _same_control_path(self.previous_accepted.control, pre.control):
            raise FractureExecutionError("accounting phases do not share one control path")
        if (
            pre.control.control_kind != "deformation_gradient"
            or not np.allclose(pre.control.axes.basis, np.eye(2), rtol=0.0, atol=1e-12)
            or pre.control.absolute_deformation_gradient is None
            or pre.control.incremental_deformation_gradient is None
            or abs(float(pre.control.absolute_deformation_gradient[0, 1])) > 1e-12
            or abs(float(pre.control.absolute_deformation_gradient[1, 0])) > 1e-12
        ):
            raise FractureExecutionError("energy accounting supports only identity-axis diagonal fixed deformation")
        if self.control_application_kind == "new_diagonal_deformation":
            _validate_segment_control(pre.control, self.previous_accepted.control, pre.control)
        elif self.previous_accepted.control.as_record() != pre.control.as_record():
            raise FractureExecutionError("same-control accounting cannot change the accepted control")
        phase_observations = (
            self.previous_accepted,
            self.after_control_before_relax,
            pre,
            self.transition.post_delete_unrelaxed,
            self.transition.post_event_relaxed,
        )
        provenance = (
            pre.physics_profile_id,
            pre.physics_profile_hash,
            pre.reference_state_id,
            pre.law_id,
            pre.registry_id,
        )
        if any(
            (item.physics_profile_id, item.physics_profile_hash, item.reference_state_id, item.law_id, item.registry_id) != provenance
            for item in phase_observations
        ):
            raise FractureExecutionError("accounting phases mix profile/reference/law/registry provenance")
        if any(
            not np.allclose(
                item.reference_total_tension_pN_per_nm,
                pre.reference_total_tension_pN_per_nm,
                rtol=0.0,
                atol=1e-12,
            )
            for item in phase_observations
        ):
            raise FractureExecutionError("accounting phases mix fixed reference-tension tensors")
        if any(
            _plain(item.boundary_conditions) != _plain(pre.boundary_conditions)
            for item in phase_observations
        ):
            raise FractureExecutionError("accounting phases mix boundary-condition provenance")
        metadata = _mapping(
            self.transition.privileged_reference_metadata,
            "transition privileged metadata",
        )
        try:
            replayed_law = DamageLaw.from_record(metadata["damage_law"])  # type: ignore[arg-type]
            replayed_registry = TopologyRegistry.from_record(metadata["topology_registry"])  # type: ignore[arg-type]
            self.transition._validate_observation_against_registry(
                self.previous_accepted, replayed_registry, replayed_law
            )
            self.transition._validate_observation_against_registry(
                self.after_control_before_relax, replayed_registry, replayed_law
            )
        except Exception as error:
            raise FractureExecutionError("accounting raw loading phases fail registry/law replay") from error
        if self.transition.material_event.event_source != "material_rupture":
            raise FractureExecutionError("accounting requires an accepted material rupture")
        if not np.array_equal(self.after_control_before_relax.cell.matrix_nm, pre.cell.matrix_nm):
            raise FractureExecutionError("after-control and pre-event cells differ")
        if not np.array_equal(pre.cell.matrix_nm, self.transition.post_event_relaxed.cell.matrix_nm):
            raise FractureExecutionError("event relaxation did not hold deformation control fixed")
        source = _mapping(self.phase_energies_pN_nm, "phase_energies_pN_nm")
        if tuple(source) != _ENERGY_PHASE_NAMES:
            raise FractureExecutionError("energy phases must use the exact canonical five-phase order")
        energies = MappingProxyType({name: _finite(source[name], name) for name in _ENERGY_PHASE_NAMES})
        object.__setattr__(self, "phase_energies_pN_nm", energies)
        expected_values = {
            "fixed_topology_conservative_loading_work_pN_nm": energies["U_after_control_before_relax"] - energies["U_previous_accepted"],
            "equilibrium_stored_energy_change_pN_nm": energies["U_pre_event_relaxed"] - energies["U_previous_accepted"],
            "pre_event_relaxation_loss_pN_nm": energies["U_after_control_before_relax"] - energies["U_pre_event_relaxed"],
            "same_coordinate_deletion_energy_change_pN_nm": energies["U_post_delete_unrelaxed"] - energies["U_pre_event_relaxed"],
            "held_control_boundary_work_pN_nm": 0.0,
            "post_delete_relaxation_loss_pN_nm": energies["U_post_delete_unrelaxed"] - energies["U_post_event_relaxed"],
        }
        for field, expected in expected_values.items():
            actual = _finite(getattr(self, field), field)
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
                raise FractureExecutionError(f"{field} differs from raw phase equation")
            object.__setattr__(self, field, actual)
        if self.pre_event_relaxation_loss_pN_nm < -tolerance or self.post_delete_relaxation_loss_pN_nm < -tolerance:
            raise FractureExecutionError("fixed-topology relaxation increased potential energy beyond tolerance")
        if not math.isclose(
            self.fixed_topology_conservative_loading_work_pN_nm,
            self.equilibrium_stored_energy_change_pN_nm
            + self.pre_event_relaxation_loss_pN_nm,
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            raise FractureExecutionError("loading input does not equal stored-energy change plus relaxation loss")
        if self.accounting_id != _hash(self._body()):
            raise FractureExecutionError("accounting_id does not match record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "previous_accepted": self.previous_accepted.as_record(),
            "after_control_before_relax": self.after_control_before_relax.as_record(),
            "transition": self.transition.as_record(),
            "control_application_kind": self.control_application_kind,
            "calculation_kind": self.calculation_kind,
            "energy_unit": self.energy_unit,
            "phase_energies_pN_nm": dict(self.phase_energies_pN_nm),
            "fixed_topology_conservative_loading_work_pN_nm": self.fixed_topology_conservative_loading_work_pN_nm,
            "equilibrium_stored_energy_change_pN_nm": self.equilibrium_stored_energy_change_pN_nm,
            "pre_event_relaxation_loss_pN_nm": self.pre_event_relaxation_loss_pN_nm,
            "same_coordinate_deletion_energy_change_pN_nm": self.same_coordinate_deletion_energy_change_pN_nm,
            "held_control_boundary_work_pN_nm": self.held_control_boundary_work_pN_nm,
            "post_delete_relaxation_loss_pN_nm": self.post_delete_relaxation_loss_pN_nm,
            "numerical_tolerance_pN_nm": self.numerical_tolerance_pN_nm,
        }

    def as_record(self) -> dict[str, object]:
        return {"accounting_id": self.accounting_id, **self._body()}

    @classmethod
    def create(
        cls, *, previous_accepted: BackendObservation,
        after_control_before_relax: BackendObservation,
        transition: CascadeTransitionEnvelope,
        control_application_kind: str = "new_diagonal_deformation",
        numerical_tolerance_pN_nm: float = 1e-8,
    ) -> "FractureEnergyAccounting":
        observations = (
            previous_accepted,
            after_control_before_relax,
            transition.pre_delete_raw,
            transition.post_delete_unrelaxed,
            transition.post_event_relaxed,
        )
        energies = {name: observation.raw_energies_pN_nm["pe"] for name, observation in zip(_ENERGY_PHASE_NAMES, observations)}
        values = {
            "fixed_topology_conservative_loading_work_pN_nm": energies["U_after_control_before_relax"] - energies["U_previous_accepted"],
            "equilibrium_stored_energy_change_pN_nm": energies["U_pre_event_relaxed"] - energies["U_previous_accepted"],
            "pre_event_relaxation_loss_pN_nm": energies["U_after_control_before_relax"] - energies["U_pre_event_relaxed"],
            "same_coordinate_deletion_energy_change_pN_nm": energies["U_post_delete_unrelaxed"] - energies["U_pre_event_relaxed"],
            "held_control_boundary_work_pN_nm": 0.0,
            "post_delete_relaxation_loss_pN_nm": energies["U_post_delete_unrelaxed"] - energies["U_post_event_relaxed"],
        }
        kwargs = {
            "previous_accepted": previous_accepted,
            "after_control_before_relax": after_control_before_relax,
            "transition": transition,
            "control_application_kind": control_application_kind,
            "calculation_kind": "conservative_fixed_topology_instantaneous_control_delta_pe",
            "energy_unit": "pN nm",
            "phase_energies_pN_nm": energies,
            **values,
            "numerical_tolerance_pN_nm": numerical_tolerance_pN_nm,
            "schema_version": LOCALIZATION_SCHEMA_VERSION,
        }
        body = cls._body_from_kwargs(kwargs)
        return cls(accounting_id=_hash(body), **kwargs)  # type: ignore[arg-type]

    @staticmethod
    def _body_from_kwargs(kwargs: Mapping[str, object]) -> dict[str, object]:
        return {
            "schema_version": kwargs["schema_version"],
            "previous_accepted": kwargs["previous_accepted"].as_record(),
            "after_control_before_relax": kwargs["after_control_before_relax"].as_record(),
            "transition": kwargs["transition"].as_record(),
            "control_application_kind": kwargs["control_application_kind"],
            "calculation_kind": kwargs["calculation_kind"], "energy_unit": kwargs["energy_unit"],
            "phase_energies_pN_nm": dict(kwargs["phase_energies_pN_nm"]),
            "fixed_topology_conservative_loading_work_pN_nm": kwargs["fixed_topology_conservative_loading_work_pN_nm"],
            "equilibrium_stored_energy_change_pN_nm": kwargs["equilibrium_stored_energy_change_pN_nm"],
            "pre_event_relaxation_loss_pN_nm": kwargs["pre_event_relaxation_loss_pN_nm"],
            "same_coordinate_deletion_energy_change_pN_nm": kwargs["same_coordinate_deletion_energy_change_pN_nm"],
            "held_control_boundary_work_pN_nm": kwargs["held_control_boundary_work_pN_nm"],
            "post_delete_relaxation_loss_pN_nm": kwargs["post_delete_relaxation_loss_pN_nm"],
            "numerical_tolerance_pN_nm": kwargs["numerical_tolerance_pN_nm"],
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "FractureEnergyAccounting":
        value = _mapping(value, "fracture energy accounting")
        _keys(value, {"accounting_id", "schema_version", "previous_accepted", "after_control_before_relax", "transition", "control_application_kind", "calculation_kind", "energy_unit", "phase_energies_pN_nm", "fixed_topology_conservative_loading_work_pN_nm", "equilibrium_stored_energy_change_pN_nm", "pre_event_relaxation_loss_pN_nm", "same_coordinate_deletion_energy_change_pN_nm", "held_control_boundary_work_pN_nm", "post_delete_relaxation_loss_pN_nm", "numerical_tolerance_pN_nm"}, "fracture energy accounting")
        body = dict(value)
        body["previous_accepted"] = BackendObservation.from_record(body["previous_accepted"])
        body["after_control_before_relax"] = BackendObservation.from_record(body["after_control_before_relax"])
        body["transition"] = CascadeTransitionEnvelope.from_record(body["transition"])
        return cls(**body)  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FractureEnergyAccounting) and self.as_record() == other.as_record()


@dataclass(frozen=True, eq=False)
class LocalizedCascadeResult:
    result_id: str
    localization: EventLocalizationRecord
    cascade_result: CascadeResult | None
    energy_accounting: tuple[FractureEnergyAccounting, ...]
    final_damage_state: DamageState
    final_topology_state: TopologyState
    final_snapshot: BackendObservation
    privileged_reference_metadata: Mapping[str, object]
    backend_closed: bool
    schema_version: str = LOCALIZATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LOCALIZATION_SCHEMA_VERSION or not isinstance(self.localization, EventLocalizationRecord):
            raise FractureExecutionError("invalid localized cascade schema")
        rows = tuple(_sequence(self.energy_accounting, "energy_accounting"))
        if any(not isinstance(item, FractureEnergyAccounting) for item in rows):
            raise FractureExecutionError("energy_accounting must contain validated records")
        object.__setattr__(self, "energy_accounting", rows)
        if not isinstance(self.final_damage_state, DamageState) or not isinstance(self.final_topology_state, TopologyState) or not isinstance(self.final_snapshot, BackendObservation):
            raise FractureExecutionError("localized result final state is invalid")
        metadata = _mapping(self.privileged_reference_metadata, "localized privileged metadata")
        _keys(metadata, {"access", "damage_law", "threshold_field", "topology_registry"}, "localized privileged metadata")
        try:
            law = DamageLaw.from_record(metadata["damage_law"])  # type: ignore[arg-type]
            field = ThresholdField.from_record(metadata["threshold_field"])  # type: ignore[arg-type]
            registry = TopologyRegistry.from_record(metadata["topology_registry"])  # type: ignore[arg-type]
        except Exception as error:
            raise FractureExecutionError("localized privileged replay metadata is invalid") from error
        if (
            metadata["access"] != "diagnostic_reference_only_never_predictor_input"
            or field.law_id != law.law_id
            or field.law_fingerprint != law.fingerprint
            or field.physics_profile_id != law.physics_profile_id
            or field.physics_profile_hash != law.physics_profile_hash
            or field.reference_state_id != law.reference_state_id
            or field.criterion != law.criterion
            or field.criterion_unit != law.criterion_unit
            or field.predictor_visibility != law.predictor_visibility
            or tuple(sorted(field.thresholds)) != tuple(sorted(bond.stable_bond_id for bond in registry.bonds))
            or self.final_damage_state.law_id != law.law_id
            or self.final_damage_state.law_fingerprint != law.fingerprint
            or self.final_damage_state.threshold_realization_id != field.realization_id
            or self.final_damage_state.physics_profile_id != law.physics_profile_id
            or self.final_damage_state.physics_profile_hash != law.physics_profile_hash
            or self.final_damage_state.reference_state_id != law.reference_state_id
            or self.final_damage_state.physical_bond_ids != tuple(sorted(field.thresholds))
            or self.final_topology_state.registry_id != registry.registry_id
            or tuple(
                bond_id for bond_id in self.final_damage_state.physical_bond_ids
                if self.final_damage_state.alive_mask[bond_id]
            ) != self.final_topology_state.alive_bond_ids
            or self.localization.domain_certificate.physics_profile_id != law.physics_profile_id
            or self.localization.domain_certificate.physics_profile_hash != law.physics_profile_hash
            or self.localization.domain_certificate.reference_state_id != law.reference_state_id
            or self.localization.domain_certificate.registry_id != registry.registry_id
            or self.localization.domain_certificate.physical_bond_ids != tuple(sorted(field.thresholds))
        ):
            raise FractureExecutionError("localized law/field/registry provenance is inconsistent")
        registry.validate_state(self.final_topology_state)
        if (
            self.final_snapshot.topology != self.final_topology_state
            or self.final_snapshot.damage_state_id != self.final_damage_state.state_id
            or self.final_snapshot.law_id != self.final_damage_state.law_id
            or dict(self.final_snapshot.alive_mask) != dict(self.final_damage_state.alive_mask)
            or dict(self.final_snapshot.rupture_mask) != dict(self.final_damage_state.rupture_mask)
            or dict(self.final_snapshot.prescribed_removal_mask) != dict(self.final_damage_state.prescribed_removal_mask)
        ):
            raise FractureExecutionError("localized final snapshot differs from exact logical final state")
        CascadeTransitionEnvelope._validate_observation_against_registry(self.final_snapshot, registry, law)
        object.__setattr__(self, "privileged_reference_metadata", _deep_freeze(metadata))
        if type(self.backend_closed) is not bool or not self.backend_closed:
            raise FractureExecutionError("localized operation must close its owned backend")
        if self.localization.status is LocalizationStatus.LOCALIZED:
            if self.cascade_result is None or not rows:
                raise FractureExecutionError("localized crossing requires cascade and accounting")
            if (
                self.cascade_result.status is not CascadeStatus.STABLE
                or self.cascade_result.diagnostic is not None
            ):
                raise FractureExecutionError(
                    "localized crossing requires a complete stable cascade"
                )
            first_event = self.cascade_result.transitions[0].material_event
            localized = self.localization.localized_control
            assert localized is not None
            if (
                first_event.control_id != localized.control_id
                or first_event.load_coordinate != localized.lambda_load
                or first_event.path_progress != localized.path_progress
                or self.cascade_result.damage_state != self.final_damage_state
                or self.cascade_result.topology_state != self.final_topology_state
                or self.cascade_result.final_snapshot != self.final_snapshot
                or len(rows) != len(self.cascade_result.transitions)
                or self.cascade_result.control.as_record() != localized.as_record()
                or rows[0].previous_accepted.observation_id != self.localization.previous_accepted_observation_id
                or rows[0].previous_accepted.control.as_record() != self.localization.initial_lower_control.as_record()
                or rows[0].previous_accepted.damage_state_id != self.localization.damage_state_id
                or rows[0].previous_accepted.topology.topology_state_id != self.localization.topology_state_id
            ):
                raise FractureExecutionError("localized event/cascade/accounting bindings differ")
            if any(row.transition != transition for row, transition in zip(rows, self.cascade_result.transitions)):
                raise FractureExecutionError("accounting transition order differs from cascade")
            for index in range(1, len(rows)):
                if rows[index].previous_accepted != rows[index - 1].transition.post_event_relaxed.rephase("pre_delete_relaxed"):
                    raise FractureExecutionError("accounting phases do not form one accepted event chain")
        else:
            if self.cascade_result is not None or rows:
                raise FractureExecutionError("failed localization cannot publish cascade/event/accounting")
            if self.final_snapshot.observation_id != self.localization.previous_accepted_observation_id:
                raise FractureExecutionError("failed localization must return original lower accepted snapshot")
            if (
                self.final_snapshot.control.as_record() != self.localization.initial_lower_control.as_record()
                or self.final_snapshot.damage_state_id != self.localization.damage_state_id
                or self.final_snapshot.topology.topology_state_id != self.localization.topology_state_id
                or not self.final_snapshot.convergence.accepted
                or self.final_snapshot.phase != "pre_delete_relaxed"
            ):
                raise FractureExecutionError("failed localization did not return the accepted lower state")
        if self.result_id != _hash(self._body()):
            raise FractureExecutionError("localized result ID does not match record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "localization": self.localization.as_record(),
            "cascade_result": None if self.cascade_result is None else self.cascade_result.as_record(),
            "energy_accounting": [item.as_record() for item in self.energy_accounting],
            "final_damage_state": self.final_damage_state.as_record(),
            "final_topology_state": self.final_topology_state.as_record(),
            "final_snapshot": self.final_snapshot.as_record(),
            "privileged_reference_metadata": _plain(self.privileged_reference_metadata),
            "backend_closed": self.backend_closed,
        }

    def as_record(self) -> dict[str, object]:
        return {"result_id": self.result_id, **self._body()}

    def as_observable_record(self) -> dict[str, object]:
        accepted = self.localization.status is LocalizationStatus.LOCALIZED
        return {
            "schema_version": self.schema_version,
            "localization_status": self.localization.status.value,
            "accepted_label": accepted,
            "label_eligible": accepted,
            "exclusion_kind": (
                None if accepted else self.localization.diagnostic.kind  # type: ignore[union-attr]
            ),
            "requested_control": self.localization.initial_upper_control.as_record(),
            "cascade": (
                None if not accepted else self.cascade_result.as_observable_record()  # type: ignore[union-attr]
            ),
            "physical_time": None,
            "physical_time_valid": False,
        }

    @classmethod
    def create(cls, **kwargs: object) -> "LocalizedCascadeResult":
        temporary = dict(kwargs)
        temporary.setdefault("schema_version", LOCALIZATION_SCHEMA_VERSION)
        rows = tuple(_sequence(temporary["energy_accounting"], "energy_accounting"))
        temporary["energy_accounting"] = rows
        body = {
            "schema_version": temporary["schema_version"],
            "localization": temporary["localization"].as_record(),
            "cascade_result": None if temporary["cascade_result"] is None else temporary["cascade_result"].as_record(),
            "energy_accounting": [item.as_record() for item in rows],
            "final_damage_state": temporary["final_damage_state"].as_record(),
            "final_topology_state": temporary["final_topology_state"].as_record(),
            "final_snapshot": temporary["final_snapshot"].as_record(),
            "privileged_reference_metadata": _plain(temporary["privileged_reference_metadata"]),
            "backend_closed": temporary["backend_closed"],
        }
        temporary.pop("result_id", None)
        return cls(result_id=_hash(body), **temporary)  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "LocalizedCascadeResult":
        value = _mapping(value, "localized cascade result")
        _keys(value, {"result_id", "schema_version", "localization", "cascade_result", "energy_accounting", "final_damage_state", "final_topology_state", "final_snapshot", "privileged_reference_metadata", "backend_closed"}, "localized cascade result")
        return cls(
            result_id=value["result_id"], localization=EventLocalizationRecord.from_record(value["localization"]),
            cascade_result=None if value["cascade_result"] is None else CascadeResult.from_record(value["cascade_result"]),
            energy_accounting=tuple(FractureEnergyAccounting.from_record(item) for item in _sequence(value["energy_accounting"], "energy_accounting")),
            final_damage_state=DamageState.from_record(value["final_damage_state"]), final_topology_state=TopologyState.from_record(value["final_topology_state"]),
            final_snapshot=BackendObservation.from_record(value["final_snapshot"]), privileged_reference_metadata=value["privileged_reference_metadata"],
            backend_closed=value["backend_closed"], schema_version=value["schema_version"],
        )  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LocalizedCascadeResult) and self.as_record() == other.as_record()


class FractureBackend(Protocol):
    @property
    def localization_response_contract_id(self) -> str: ...
    def apply_control(self, control: QuasiStaticControlStep) -> None: ...
    def observe_after_control_unrelaxed(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def relax_and_observe(self, *, phase: str, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def observe_unrelaxed(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def delete_angle(self, angle: AngleTopology) -> None: ...
    def delete_bond(self, bond: BondTopology) -> None: ...
    def audit_topology(self, topology_state: TopologyState) -> None: ...
    def checkpoint(self) -> object: ...
    def restore(self, checkpoint: object) -> None: ...
    def observe_restored(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation: ...
    def audit_trial_runtime(self) -> None: ...
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

    def run_localized_step(
        self,
        *,
        lower_control: QuasiStaticControlStep,
        upper_control: QuasiStaticControlStep,
        previous_accepted: BackendObservation,
        damage_state: DamageState,
        topology_state: TopologyState,
        localization_budget: LocalizationBudget,
        domain_certificate: TrialDomainCertificate,
    ) -> LocalizedCascadeResult:
        """Localize and transact the first accepted rupture on one control segment.

        Trial states are deliberately private.  Every nonfinal trial starts
        from, and is followed by restoration of, the caller-supplied accepted
        lower checkpoint.  Only the final crossing is handed to the existing
        exact deletion/relaxation transaction.
        """

        payload: dict[str, object] | None = None
        active_error: BaseException | None = None
        try:
            payload = self._execute_localized(
                lower_control=lower_control,
                upper_control=upper_control,
                previous_accepted=previous_accepted,
                damage_state=damage_state,
                topology_state=topology_state,
                budget=localization_budget,
                certificate=domain_certificate,
            )
        except BaseException as error:
            active_error = error
        close_error: BaseException | None = None
        try:
            self.backend.close()
        except BaseException as error:
            close_error = error
        if active_error is not None:
            if close_error is not None:
                raise FractureExecutionError(
                    f"localized execution failed ({active_error}); backend close also failed ({close_error})"
                ) from active_error
            raise active_error
        assert payload is not None
        if close_error is not None:
            raise FractureExecutionError(f"localized backend close failed: {close_error}") from close_error
        cascade_outcome = payload.pop("cascade_outcome", None)
        if cascade_outcome is not None:
            cascade_values = dict(cascade_outcome)  # type: ignore[arg-type]
            cascade_values["backend_closed"] = True
            payload["cascade_result"] = CascadeResult.create(**cascade_values)
        payload["backend_closed"] = True
        return LocalizedCascadeResult.create(**payload)

    def _execute_localized(
        self,
        *,
        lower_control: QuasiStaticControlStep,
        upper_control: QuasiStaticControlStep,
        previous_accepted: BackendObservation,
        damage_state: DamageState,
        topology_state: TopologyState,
        budget: LocalizationBudget,
        certificate: TrialDomainCertificate,
    ) -> dict[str, object]:
        self._validate_before_commands(lower_control, damage_state, topology_state)
        self._validate_localization_inputs(
            lower_control, upper_control, previous_accepted, damage_state,
            topology_state, budget, certificate,
        )
        privileged = {
            "access": "diagnostic_reference_only_never_predictor_input",
            "damage_law": self.law.as_record(),
            "threshold_field": self.field.as_record(),
            "topology_registry": self.registry.as_record(),
        }
        degree = {node.stable_node_id: 0 for node in self.registry.nodes}
        for bond in self.registry.bonds:
            degree[bond.node_i] += 1
            degree[bond.node_j] += 1
        angle = self.registry.angles[0] if len(self.registry.angles) == 1 else None
        ordered_source_legs: list[np.ndarray] = []
        if angle is not None:
            for node_i, node_j, bond_id in (
                (angle.node_ids[0], angle.node_ids[1], angle.dependent_bond_ids[0]),
                (angle.node_ids[1], angle.node_ids[2], angle.dependent_bond_ids[1]),
            ):
                bond = self.registry.bond(bond_id)
                stored = np.asarray(bond.source_displacement_nm, dtype=float)
                if (bond.node_i, bond.node_j) == (node_i, node_j):
                    ordered_source_legs.append(stored)
                elif (bond.node_i, bond.node_j) == (node_j, node_i):
                    ordered_source_legs.append(-stored)
                else:
                    ordered_source_legs = []
                    break
        collinear_positive_axial = len(ordered_source_legs) == 2 and all(
            vector[0] > 0.0 and abs(float(vector[1])) <= 1e-12
            for vector in ordered_source_legs
        )
        cell_matrix = self.registry.cell.matrix_nm
        orthogonal_cell = (
            abs(float(cell_matrix[0, 1])) <= 1e-12
            and abs(float(cell_matrix[1, 0])) <= 1e-12
        )
        assert lower_control.absolute_deformation_gradient is not None
        assert upper_control.absolute_deformation_gradient is not None
        axial_path = (
            lower_control.loading_mode in {"axial", "cyclic"}
            and math.isclose(
                float(upper_control.absolute_deformation_gradient[1, 1]),
                float(lower_control.absolute_deformation_gradient[1, 1]),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            and math.isclose(
                float(upper_control.absolute_deformation_gradient[0, 0]
                      - lower_control.absolute_deformation_gradient[0, 0]),
                upper_control.lambda_load - lower_control.lambda_load,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )
        exact_bounded_fixture = (
            len(self.registry.nodes) == 3
            and len(self.registry.bonds) == 2
            and len(self.registry.angles) == 1
            and sorted(degree.values()) == [1, 1, 2]
            and all(bond.chemical_type == "glycan" for bond in self.registry.bonds)
            and collinear_positive_axial
            and orthogonal_cell
            and axial_path
            and certificate.registry_id == self.registry.registry_id
            and getattr(self.backend, "localization_response_contract_id", None)
            == certificate.backend_response_contract_id
        )
        if (
            certificate.domain_kind != "bounded_harmonic_fixture_no_singular_bonds"
            or not exact_bounded_fixture
        ):
            return self._localized_failure_payload(
                status=LocalizationStatus.DOMAIN_REJECTED,
                diagnostic=LocalizationDiagnostic.create(
                    "nonlinear_iteration_domain_unvalidated",
                    "trial path lacks the exact harmonic/monotone backend certificate; endpoint-only nonlinear margins and peptide fixtures are non-executable",
                ),
                initial_lower=lower_control,
                initial_upper=upper_control,
                lower=lower_control,
                upper=upper_control,
                previous=previous_accepted,
                damage=damage_state,
                topology=topology_state,
                budget=budget,
                certificate=certificate,
                solver_trials=0,
                refinements=0,
                retries=0,
                privileged=privileged,
            )

        if damage_state.has_initial_threshold_violation:
            return self._localized_failure_payload(
                status=LocalizationStatus.INVALID_LOWER_BRACKET,
                diagnostic=LocalizationDiagnostic.create(
                    "invalid_lower_bracket",
                    "initial threshold violation marks the fixed reference invalid",
                ),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=lower_control, upper=upper_control,
                previous=previous_accepted, damage=damage_state,
                topology=topology_state, budget=budget, certificate=certificate,
                solver_trials=0, refinements=0, retries=0,
                privileged=privileged,
            )

        lower_assessment = self._assess(previous_accepted, damage_state, lower_control)
        if lower_assessment.candidates:
            return self._localized_failure_payload(
                status=LocalizationStatus.INVALID_LOWER_BRACKET,
                diagnostic=LocalizationDiagnostic.create(
                    "invalid_lower_bracket", "accepted lower control already crosses the rupture threshold"
                ),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=lower_control, upper=upper_control,
                previous=previous_accepted, damage=damage_state,
                topology=topology_state, budget=budget, certificate=certificate,
                solver_trials=0, refinements=0, retries=0, privileged=privileged,
            )

        self.backend.audit_topology(topology_state)
        self.backend.audit_trial_runtime()
        live_lower = self.backend.observe_restored(
            control=lower_control, topology_state=topology_state,
            damage_state=damage_state,
        )
        self._validate_observation(
            live_lower, lower_control, damage_state, topology_state,
            expected_phase="pre_delete_relaxed",
        )
        if not live_lower.convergence.accepted or not self._same_mechanical_state(
            live_lower, previous_accepted
        ):
            return self._localized_failure_payload(
                status=LocalizationStatus.LIVE_LOWER_MISMATCH,
                diagnostic=LocalizationDiagnostic.create(
                    "live_lower_mismatch",
                    "live backend mechanics differ from the supplied accepted lower snapshot",
                ),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=lower_control, upper=upper_control,
                previous=previous_accepted, damage=damage_state,
                topology=topology_state, budget=budget, certificate=certificate,
                solver_trials=0, refinements=0, retries=0,
                privileged=privileged,
            )
        lower_checkpoint = self.backend.checkpoint()
        frozen_field = self.field.as_record()
        frozen_damage = damage_state.as_record()
        frozen_topology = topology_state.as_record()
        bracket_lower = lower_control
        bracket_upper = upper_control
        upper_checkpoint: object | None = None
        upper_after_control: BackendObservation | None = None
        upper_relaxed: BackendObservation | None = None
        solver_trials = 0
        refinements = 0
        retries = 0
        trial_failure_detail = ""

        def restore_lower() -> None:
            self.backend.restore(lower_checkpoint)
            self.backend.audit_topology(topology_state)
            self.backend.audit_trial_runtime()
            restored = self.backend.observe_restored(
                control=lower_control, topology_state=topology_state,
                damage_state=damage_state,
            )
            self._validate_observation(
                restored, lower_control, damage_state, topology_state,
                expected_phase="pre_delete_relaxed",
            )
            if not restored.convergence.accepted or not self._same_mechanical_state(restored, previous_accepted):
                raise FractureExecutionError("localization restore differs from the original accepted lower checkpoint")
            if (
                self.field.as_record() != frozen_field
                or damage_state.as_record() != frozen_damage
                or topology_state.as_record() != frozen_topology
            ):
                raise FractureExecutionError("localization trial mutated frozen law/state/topology data")

        def evaluate(control: QuasiStaticControlStep) -> tuple[BackendObservation, BackendObservation, DamageAssessment, object] | LocalizationStatus:
            nonlocal solver_trials, retries, trial_failure_detail
            failures = 0
            while True:
                if solver_trials >= budget.max_solver_trials:
                    return LocalizationStatus.SOLVER_BUDGET_EXHAUSTED
                try:
                    self.backend.apply_control(control)
                    after = self.backend.observe_after_control_unrelaxed(
                        control=control, topology_state=topology_state,
                        damage_state=damage_state,
                    )
                    self._validate_observation(
                        after, control, damage_state, topology_state,
                        expected_phase="after_control_before_relax",
                    )
                    solver_trials += 1
                    relaxed = self.backend.relax_and_observe(
                        phase="pre_delete_relaxed", control=control,
                        topology_state=topology_state, damage_state=damage_state,
                    )
                    self._validate_observation(
                        relaxed, control, damage_state, topology_state,
                        expected_phase="pre_delete_relaxed",
                    )
                    if relaxed.convergence.accepted:
                        assessment = self._assess(relaxed, damage_state, control)
                        checkpoint = self.backend.checkpoint()
                        restore_lower()
                        return after, relaxed, assessment, checkpoint
                    failures += 1
                    restore_lower()
                    if relaxed.convergence.termination_reason not in _RETRYABLE_LOCALIZATION_TERMINATIONS:
                        trial_failure_detail = (
                            "nonretryable accepted-policy rejection: "
                            + relaxed.convergence.termination_reason
                        )
                        return LocalizationStatus.NONCONVERGENCE_REJECTED
                except Exception as error:
                    try:
                        restore_lower()
                    except Exception as restore_error:
                        trial_failure_detail = f"trial={error}; lower restore={restore_error}"
                        return LocalizationStatus.RESTORE_FAILED
                    trial_failure_detail = str(error)
                    return LocalizationStatus.TRIAL_REJECTED
                if (
                    failures > budget.max_retries_per_trial
                    or retries >= budget.max_retries_per_trial
                ):
                    return LocalizationStatus.RETRY_BUDGET_EXHAUSTED
                retries += 1

        def diagnostic_for(status: LocalizationStatus) -> LocalizationDiagnostic:
            if status is LocalizationStatus.SOLVER_BUDGET_EXHAUSTED:
                return LocalizationDiagnostic.create("solver_budget_exhausted", f"max_solver_trials={budget.max_solver_trials}")
            if status is LocalizationStatus.RETRY_BUDGET_EXHAUSTED:
                return LocalizationDiagnostic.create("trial_nonconvergence", f"max_retries_per_trial={budget.max_retries_per_trial}")
            if status is LocalizationStatus.NONCONVERGENCE_REJECTED:
                return LocalizationDiagnostic.create("nonretryable_nonconvergence", trial_failure_detail)
            if status is LocalizationStatus.RESTORE_FAILED:
                return LocalizationDiagnostic.create("restore_failed", trial_failure_detail)
            if status is LocalizationStatus.TRIAL_REJECTED:
                return LocalizationDiagnostic.create("trial_rejected", trial_failure_detail)
            raise FractureExecutionError("unexpected localization trial terminal status")

        first = evaluate(upper_control)
        if isinstance(first, LocalizationStatus):
            return self._localized_failure_payload(
                status=first, diagnostic=diagnostic_for(first), initial_lower=lower_control,
                initial_upper=upper_control, lower=bracket_lower, upper=bracket_upper,
                previous=previous_accepted, damage=damage_state, topology=topology_state,
                budget=budget, certificate=certificate, solver_trials=solver_trials,
                refinements=refinements, retries=retries, privileged=privileged,
            )
        upper_after_control, upper_relaxed, upper_assessment, upper_checkpoint = first
        if not upper_assessment.candidates:
            return self._localized_failure_payload(
                status=LocalizationStatus.UPPER_DOES_NOT_CROSS,
                diagnostic=LocalizationDiagnostic.create("upper_does_not_cross", "accepted upper control has no rupture candidate"),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=lower_control, upper=upper_control, previous=previous_accepted,
                damage=damage_state, topology=topology_state, budget=budget,
                certificate=certificate, solver_trials=solver_trials,
                refinements=refinements, retries=retries, privileged=privileged,
            )

        while not self._bracket_within_tolerance(bracket_lower, bracket_upper, budget):
            if refinements >= budget.max_refinements:
                return self._localized_failure_payload(
                    status=LocalizationStatus.REFINEMENT_BUDGET_EXHAUSTED,
                    diagnostic=LocalizationDiagnostic.create("refinement_budget_exhausted", f"max_refinements={budget.max_refinements}"),
                    initial_lower=lower_control, initial_upper=upper_control,
                    lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                    damage=damage_state, topology=topology_state, budget=budget,
                    certificate=certificate, solver_trials=solver_trials,
                    refinements=refinements, retries=retries, privileged=privileged,
                )
            if solver_trials >= budget.max_solver_trials:
                return self._localized_failure_payload(
                    status=LocalizationStatus.SOLVER_BUDGET_EXHAUSTED,
                    diagnostic=LocalizationDiagnostic.create("solver_budget_exhausted", f"max_solver_trials={budget.max_solver_trials}"),
                    initial_lower=lower_control, initial_upper=upper_control,
                    lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                    damage=damage_state, topology=topology_state, budget=budget,
                    certificate=certificate, solver_trials=solver_trials,
                    refinements=refinements, retries=retries, privileged=privileged,
                )
            trial = self._interpolate_control(lower_control, bracket_lower, bracket_upper)
            evaluated = evaluate(trial)
            if isinstance(evaluated, LocalizationStatus):
                return self._localized_failure_payload(
                    status=evaluated, diagnostic=diagnostic_for(evaluated),
                    initial_lower=lower_control, initial_upper=upper_control,
                    lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                    damage=damage_state, topology=topology_state, budget=budget,
                    certificate=certificate, solver_trials=solver_trials,
                    refinements=refinements, retries=retries, privileged=privileged,
                )
            after, relaxed, assessment, checkpoint = evaluated
            refinements += 1
            if assessment.candidates:
                bracket_upper = trial
                upper_after_control = after
                upper_relaxed = relaxed
                upper_checkpoint = checkpoint
            else:
                bracket_lower = trial

        assert upper_checkpoint is not None and upper_after_control is not None and upper_relaxed is not None
        try:
            self.backend.restore(upper_checkpoint)
            self.backend.audit_topology(topology_state)
            self.backend.audit_trial_runtime()
            restored_upper = self.backend.observe_restored(
                control=bracket_upper, topology_state=topology_state,
                damage_state=damage_state,
            )
            self._validate_observation(
                restored_upper, bracket_upper, damage_state, topology_state,
                expected_phase="pre_delete_relaxed",
            )
            if not self._same_mechanical_state(restored_upper, upper_relaxed):
                raise FractureExecutionError("localized crossing checkpoint changed before final transaction")
        except Exception as error:
            try:
                restore_lower()
            except Exception as restore_error:
                return self._localized_failure_payload(
                    status=LocalizationStatus.RESTORE_FAILED,
                    diagnostic=LocalizationDiagnostic.create("restore_failed", f"crossing={error}; lower={restore_error}"),
                    initial_lower=lower_control, initial_upper=upper_control,
                    lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                    damage=damage_state, topology=topology_state, budget=budget,
                    certificate=certificate, solver_trials=solver_trials,
                    refinements=refinements, retries=retries, privileged=privileged,
                )
            return self._localized_failure_payload(
                status=LocalizationStatus.RESTORE_FAILED,
                diagnostic=LocalizationDiagnostic.create("restore_failed", str(error)),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                damage=damage_state, topology=topology_state, budget=budget,
                certificate=certificate, solver_trials=solver_trials,
                refinements=refinements, retries=retries, privileged=privileged,
            )

        cascade_outcome = self._cascade_from_accepted_pre(
            bracket_upper, damage_state, topology_state, restored_upper
        )
        transitions = tuple(cascade_outcome["transitions"])  # type: ignore[arg-type]
        if cascade_outcome["status"] is not CascadeStatus.STABLE or not transitions:
            cascade_status = cascade_outcome["status"]
            try:
                restore_lower()
            except Exception as restore_error:
                status = LocalizationStatus.FINAL_TRANSACTION_ROLLBACK_FAILED
                detail = f"cascade={cascade_status.value}; lower restore={restore_error}"  # type: ignore[union-attr]
                kind = "final_transaction_rollback_failed"
            else:
                status = LocalizationStatus.FINAL_TRANSACTION_ROLLED_BACK
                detail = f"cascade ended with {cascade_status.value}; localized event was not published"  # type: ignore[union-attr]
                kind = "final_transaction_rolled_back"
            return self._localized_failure_payload(
                status=status, diagnostic=LocalizationDiagnostic.create(kind, detail),
                initial_lower=lower_control, initial_upper=upper_control,
                lower=bracket_lower, upper=bracket_upper, previous=previous_accepted,
                damage=damage_state, topology=topology_state, budget=budget,
                certificate=certificate, solver_trials=solver_trials,
                refinements=refinements, retries=retries, privileged=privileged,
            )

        localization = EventLocalizationRecord.create(
            status=LocalizationStatus.LOCALIZED, budget=budget,
            domain_certificate=certificate, initial_lower_control=lower_control,
            initial_upper_control=upper_control, lower_bracket_control=bracket_lower,
            upper_bracket_control=bracket_upper, localized_control=bracket_upper,
            solver_trials=solver_trials, refinements=refinements, retries=retries,
            previous_accepted_observation_id=previous_accepted.observation_id,
            topology_state_id=topology_state.topology_state_id,
            damage_state_id=damage_state.state_id, diagnostic=None,
        )
        accounting: list[FractureEnergyAccounting] = []
        prior = previous_accepted
        for index, transition in enumerate(transitions):
            after = upper_after_control if index == 0 else transition.pre_delete_raw
            accounting.append(
                FractureEnergyAccounting.create(
                    previous_accepted=prior,
                    after_control_before_relax=after,
                    transition=transition,
                    control_application_kind=(
                        "new_diagonal_deformation" if index == 0 else "no_new_control_same_accepted_state"
                    ),
                )
            )
            prior = transition.post_event_relaxed.rephase("pre_delete_relaxed")
        return {
            "localization": localization,
            "cascade_outcome": cascade_outcome,
            "cascade_result": None,
            "energy_accounting": tuple(accounting),
            "final_damage_state": cascade_outcome["damage_state"],
            "final_topology_state": cascade_outcome["topology_state"],
            "final_snapshot": cascade_outcome["final_snapshot"],
            "privileged_reference_metadata": privileged,
            "backend_closed": False,
        }

    def _cascade_from_accepted_pre(
        self,
        control: QuasiStaticControlStep,
        damage_state: DamageState,
        topology_state: TopologyState,
        pre: BackendObservation,
    ) -> dict[str, object]:
        current_damage = damage_state
        current_topology = topology_state
        current_pre = pre
        transitions: list[CascadeTransitionEnvelope] = []
        relaxation_count = 1
        while True:
            assessment = self._assess(current_pre, current_damage, control)
            if not assessment.candidates:
                return self._outcome(
                    CascadeStatus.STABLE, tuple(transitions), current_damage,
                    current_topology, current_pre, None, control,
                )
            if len(transitions) >= self.budget.max_events:
                return self._outcome(
                    CascadeStatus.EVENT_BUDGET_EXHAUSTED, tuple(transitions),
                    current_damage, current_topology, current_pre,
                    CascadeDiagnostic.create("event_budget_exhausted", f"max_events={self.budget.max_events}"),
                    control,
                )
            if relaxation_count >= self.budget.max_relaxations:
                return self._outcome(
                    CascadeStatus.RELAXATION_BUDGET_EXHAUSTED, tuple(transitions),
                    current_damage, current_topology, current_pre,
                    CascadeDiagnostic.create("relaxation_budget_exhausted", f"max_relaxations={self.budget.max_relaxations}"),
                    control,
                )
            checkpoint = self.backend.checkpoint()
            candidate = assessment.candidates[0]
            try:
                plan = self.registry.plan_bond_removal(current_topology, candidate.physical_bond_id)
                staged = accept_next_material_rupture(current_damage, assessment)
                next_topology = self.registry.apply_plan(current_topology, plan)
                for angle_id in plan.removed_angle_ids:
                    self.backend.delete_angle(self.registry.angle(angle_id))
                self.backend.delete_bond(self.registry.bond(plan.removed_bond_id))
                self.backend.audit_topology(next_topology)
                unrelaxed = self.backend.observe_unrelaxed(
                    control=control, topology_state=next_topology,
                    damage_state=staged.state,
                )
                self._validate_observation(
                    unrelaxed, control, staged.state, next_topology,
                    expected_phase="post_delete_unrelaxed",
                )
                if not np.array_equal(current_pre.positions_nm, unrelaxed.positions_nm):
                    raise FractureExecutionError("post-delete unrelaxed capture changed atom positions")
                post = self.backend.relax_and_observe(
                    phase="post_event_relaxed", control=control,
                    topology_state=next_topology, damage_state=staged.state,
                )
                relaxation_count += 1
                self._validate_observation(
                    post, control, staged.state, next_topology,
                    expected_phase="post_event_relaxed",
                )
                self.backend.audit_topology(next_topology)
                if not post.convergence.accepted:
                    raise FractureExecutionError("post-event relaxation did not satisfy convergence policy")
                envelope = CascadeTransitionEnvelope.create(
                    previous_damage_state=current_damage,
                    damage_state=staged.state,
                    material_event=staged.event,
                    mutation_plan=plan,
                    pre_delete_raw=current_pre,
                    post_delete_unrelaxed=unrelaxed,
                    post_event_relaxed=post,
                    law=self.law, field=self.field, registry=self.registry,
                )
            except Exception as error:
                rollback_error: BaseException | None = None
                try:
                    self.backend.restore(checkpoint)
                    self.backend.audit_topology(current_topology)
                    self.backend.audit_trial_runtime()
                    restored = self.backend.observe_restored(
                        control=control, topology_state=current_topology,
                        damage_state=current_damage,
                    )
                    self._validate_observation(
                        restored, control, current_damage, current_topology,
                        expected_phase="pre_delete_relaxed",
                    )
                    if not self._same_mechanical_state(restored, current_pre):
                        raise FractureExecutionError("restored mechanics differ from last accepted checkpoint")
                except BaseException as restore_error:
                    rollback_error = restore_error
                if rollback_error is not None:
                    return self._outcome(
                        CascadeStatus.ROLLBACK_FAILED, tuple(transitions),
                        current_damage, current_topology, current_pre,
                        CascadeDiagnostic.create("rollback_failed", f"mutation={error}; restore={rollback_error}"),
                        control,
                    )
                return self._outcome(
                    CascadeStatus.ROLLED_BACK, tuple(transitions), current_damage,
                    current_topology, current_pre,
                    CascadeDiagnostic.create("rolled_back", str(error)), control,
                )
            transitions.append(envelope)
            current_damage = staged.state
            current_topology = next_topology
            current_pre = post.rephase("pre_delete_relaxed")

    def _validate_localization_inputs(
        self,
        lower: QuasiStaticControlStep,
        upper: QuasiStaticControlStep,
        previous: BackendObservation,
        damage: DamageState,
        topology: TopologyState,
        budget: LocalizationBudget,
        certificate: TrialDomainCertificate,
    ) -> None:
        if not isinstance(budget, LocalizationBudget) or not isinstance(certificate, TrialDomainCertificate):
            raise FractureExecutionError("validated localization budget/certificate are required")
        self._validate_before_commands(upper, damage, topology)
        self._validate_observation(previous, lower, damage, topology, expected_phase="pre_delete_relaxed")
        if not previous.convergence.accepted:
            raise FractureExecutionError("localization lower state must be an accepted equilibrium")
        if not _same_control_path(lower, upper):
            raise FractureExecutionError("localization controls must lie on one P02-01 control path")
        if upper.path_progress <= lower.path_progress:
            raise FractureExecutionError("localization upper path progress must exceed lower progress")
        _validate_segment_control(upper, lower, upper)
        if (
            certificate.physics_profile_id != self.law.physics_profile_id
            or certificate.physics_profile_hash != self.law.physics_profile_hash
            or certificate.reference_state_id != self.law.reference_state_id
            or certificate.registry_id != self.registry.registry_id
            or certificate.physical_bond_ids != tuple(sorted(damage.physical_bond_ids))
        ):
            raise FractureExecutionError("trial-domain certificate provenance/bond universe differs")

    @staticmethod
    def _bracket_within_tolerance(
        lower: QuasiStaticControlStep,
        upper: QuasiStaticControlStep,
        budget: LocalizationBudget,
    ) -> bool:
        return (
            abs(upper.lambda_load - lower.lambda_load) <= budget.load_tolerance
            and upper.path_progress - lower.path_progress <= budget.path_tolerance
        )

    @staticmethod
    def _interpolate_control(
        initial_lower: QuasiStaticControlStep,
        lower: QuasiStaticControlStep,
        upper: QuasiStaticControlStep,
    ) -> QuasiStaticControlStep:
        lambda_trial = 0.5 * (lower.lambda_load + upper.lambda_load)
        alpha_denominator = upper.lambda_load - lower.lambda_load
        if abs(alpha_denominator) <= 1e-15:
            raise FractureExecutionError("localization bracket has no load-coordinate extent")
        alpha = (lambda_trial - lower.lambda_load) / alpha_denominator
        assert lower.absolute_deformation_gradient is not None
        assert upper.absolute_deformation_gradient is not None
        absolute = (
            (1.0 - alpha) * lower.absolute_deformation_gradient
            + alpha * upper.absolute_deformation_gradient
        )
        assert initial_lower.absolute_deformation_gradient is not None
        incremental = absolute @ np.linalg.inv(initial_lower.absolute_deformation_gradient)
        progress = initial_lower.path_progress + abs(
            lambda_trial - initial_lower.lambda_load
        )
        body = {
            "initial_lower_control_id": initial_lower.control_id,
            "lambda_load": lambda_trial,
            "path_progress": progress,
            "absolute_deformation_gradient": absolute.tolist(),
        }
        return QuasiStaticControlStep(
            control_id="p0204-localized:" + _hash(body).split(":", 1)[1],
            step_index=upper.step_index,
            control_kind="deformation_gradient",
            loading_mode=upper.loading_mode,
            axes=upper.axes,
            reference_state_id=upper.reference_state_id,
            lambda_load=lambda_trial,
            load_coordinate_unit=upper.load_coordinate_unit,
            progress_unit=upper.progress_unit,
            path_progress=progress,
            progress_increment=abs(lambda_trial - initial_lower.lambda_load),
            absolute_deformation_gradient=absolute,
            incremental_deformation_gradient=incremental,
            absolute_tension_target_pN_per_nm=None,
            incremental_tension_target_pN_per_nm=None,
        )

    @staticmethod
    def _localized_failure_payload(
        *, status: LocalizationStatus, diagnostic: LocalizationDiagnostic,
        initial_lower: QuasiStaticControlStep, initial_upper: QuasiStaticControlStep,
        lower: QuasiStaticControlStep, upper: QuasiStaticControlStep,
        previous: BackendObservation, damage: DamageState, topology: TopologyState,
        budget: LocalizationBudget, certificate: TrialDomainCertificate,
        solver_trials: int, refinements: int, retries: int,
        privileged: Mapping[str, object],
    ) -> dict[str, object]:
        localization = EventLocalizationRecord.create(
            status=status, budget=budget, domain_certificate=certificate,
            initial_lower_control=initial_lower, initial_upper_control=initial_upper,
            lower_bracket_control=lower, upper_bracket_control=upper,
            localized_control=None, solver_trials=solver_trials,
            refinements=refinements, retries=retries,
            previous_accepted_observation_id=previous.observation_id,
            topology_state_id=topology.topology_state_id,
            damage_state_id=damage.state_id, diagnostic=diagnostic,
        )
        return {
            "localization": localization,
            "cascade_result": None,
            "cascade_outcome": None,
            "energy_accounting": (),
            "final_damage_state": damage,
            "final_topology_state": topology,
            "final_snapshot": previous,
            "privileged_reference_metadata": privileged,
            "backend_closed": False,
        }

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
        self._anchor_constraint_installed = False
        self.localization_response_contract_id = _hash({
            "contract": "p0204_bounded_harmonic_monotone_path_v1",
            "registry_id": registry.registry_id,
        })
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
        self._anchor_constraint_installed = True

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

    def observe_after_control_unrelaxed(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation:
        self._command("run 0 post no")
        residual = abs(float(self._solver.get_thermo("fmax")))
        return self._observe(
            "after_control_before_relax", control, topology_state, damage_state,
            ConvergenceDiagnostics.rejected(
                "phase_not_relaxed", max(residual, self.force_tolerance_pN * 2.0),
                0, self.maximum_iterations, self.force_tolerance_pN,
            ),
        )

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
        self._anchor_constraint_installed = False
        self._command(f"read_restart {path}"); self._setup_observers(); self._install_endpoint_constraints(); self._command("run 0 post no")

    def observe_restored(self, *, control: QuasiStaticControlStep, topology_state: TopologyState, damage_state: DamageState) -> BackendObservation:
        self._command("run 0 post no")
        residual = abs(float(self._solver.get_thermo("fmax")))
        if residual > self.force_tolerance_pN:
            raise FractureExecutionError("restored checkpoint no longer satisfies convergence residual")
        return self._observe("pre_delete_relaxed", control, topology_state, damage_state, ConvergenceDiagnostics.successful(residual, 0, self.maximum_iterations, self.force_tolerance_pN))

    def audit_trial_runtime(self) -> None:
        if self.closed:
            raise FractureExecutionError("closed backend cannot execute a localization trial")
        if self._live_groups:
            raise FractureExecutionError("temporary deletion groups remain live between localization trials")
        if not self._anchor_constraint_installed:
            raise FractureExecutionError("fixture endpoint constraint is not installed")
        self._command("run 0 post no")

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
        self._anchor_constraint_installed = False
        if errors: raise FractureExecutionError("backend close/temporary-group cleanup failed") from errors[0]


__all__ = [
    "FRACTURE_SCHEMA_VERSION", "LOCALIZATION_SCHEMA_VERSION", "BackendObservation",
    "CascadeBudget", "CascadeDiagnostic", "CascadeResult", "CascadeStatus",
    "CascadeTransitionEnvelope", "ConvergenceDiagnostics", "EventLocalizationRecord",
    "FractureBackend", "FractureEnergyAccounting", "FractureExecutionError",
    "LammpsFractureBackend", "LocalizationBudget", "LocalizationDiagnostic",
    "LocalizationStatus", "LocalizedCascadeResult", "QuasiStaticFractureCascade",
    "TrialDomainCertificate",
]
