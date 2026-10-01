"""Versioned, solver-independent quasi-static controls.

This module describes loading targets and prescribed interventions.  It does
not advance a solver, implement a rupture law, or attach physical time to an
energy-minimization sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np


CONTROL_SCHEMA_VERSION = "pgworld.quasistatic_control.v1"
_AXIS_MEANINGS = {"x": "axial", "y": "hoop"}
_REFERENCE_STATE = "fixed_cell_equilibrated"
_REFERENCE_RESET_POLICY = "never"
_LOAD_COORDINATE_KIND = "quasi_static_not_physical_time"
_FLOAT_TOLERANCE = 1.0e-12


class ControlValidationError(ValueError):
    """Raised when a loading or intervention contract is ambiguous or invalid."""


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ControlValidationError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ControlValidationError(f"{field} must be a finite number") from error
    if not np.isfinite(result):
        raise ControlValidationError(f"{field} must be finite")
    return result


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ControlValidationError(f"{field} must be a non-empty string")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ControlValidationError(f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise ControlValidationError(f"{field} keys must be strings")
    return value


def _exact_keys(
    value: Mapping[str, object], *, required: set[str], optional: set[str] | None = None
) -> None:
    optional = set() if optional is None else optional
    missing = sorted(required - set(value))
    unexpected = sorted(set(value) - required - optional)
    if missing:
        raise ControlValidationError(f"missing required fields: {missing}")
    if unexpected:
        raise ControlValidationError(f"unexpected fields: {unexpected}")


def _matrix2(value: object, field: str, *, nonsingular: bool) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise ControlValidationError(f"{field} must be a 2x2 numeric matrix") from error
    if matrix.shape != (2, 2):
        raise ControlValidationError(f"{field} must have shape (2, 2)")
    if not np.all(np.isfinite(matrix)):
        raise ControlValidationError(f"{field} must contain finite values")
    if nonsingular and abs(float(np.linalg.det(matrix))) <= _FLOAT_TOLERANCE:
        raise ControlValidationError(f"{field} must be nonsingular")
    result = np.array(matrix, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _optional_matrix_record(value: np.ndarray | None) -> list[list[float]] | None:
    return None if value is None else value.tolist()


def _deep_freeze(value: object) -> object:
    """Recursively freeze JSON-like metadata retained by frozen dataclasses."""

    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_record(value: object) -> object:
    """Return a detached JSON-compatible copy of recursively frozen metadata."""

    if isinstance(value, Mapping):
        return {str(key): _deep_record(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_record(item) for item in value]
    return value


def _normalized_mode_parameters(
    control_family: str, mode: str, value: object
) -> Mapping[str, object]:
    parameters = _mapping(value, "mode_parameters")
    if control_family == "pressure_derived_tension":
        if mode != "pressure_derived_tension":
            raise ControlValidationError("pressure schedule mode is inconsistent")
        _exact_keys(parameters, required=set())
        return _deep_freeze({})
    if control_family != "deformation":
        raise ControlValidationError("unsupported schedule control_family")
    if mode in {"isotropic", "axial", "hoop"}:
        _exact_keys(parameters, required=set())
        normalized: dict[str, object] = {}
    elif mode == "unequal_biaxial":
        _exact_keys(parameters, required={"strain_direction"})
        direction = _mapping(parameters["strain_direction"], "strain_direction")
        _exact_keys(direction, required={"epsilon_xx", "epsilon_yy"})
        axial = _finite_float(direction["epsilon_xx"], "strain_direction.epsilon_xx")
        hoop = _finite_float(direction["epsilon_yy"], "strain_direction.epsilon_yy")
        if (axial == 0.0 and hoop == 0.0) or np.isclose(axial, hoop):
            raise ControlValidationError(
                "unequal_biaxial mode_parameters require distinct nonzero direction"
            )
        normalized = {
            "strain_direction": {"epsilon_xx": axial, "epsilon_yy": hoop}
        }
    elif mode == "engineering_simple_shear":
        _exact_keys(parameters, required={"shear_component"})
        component = parameters["shear_component"]
        if component not in {"xy", "yx"}:
            raise ControlValidationError("shear_component must be explicitly xy or yx")
        normalized = {"shear_component": component}
    elif mode == "cyclic":
        base_mode = parameters.get("base_mode")
        if base_mode not in {
            "isotropic",
            "axial",
            "hoop",
            "unequal_biaxial",
            "engineering_simple_shear",
        }:
            raise ControlValidationError("cyclic base_mode is unsupported")
        expected = {"base_mode"}
        if base_mode == "unequal_biaxial":
            expected.add("strain_direction")
        elif base_mode == "engineering_simple_shear":
            expected.add("shear_component")
        _exact_keys(parameters, required=expected)
        nested = {key: item for key, item in parameters.items() if key != "base_mode"}
        base_parameters = _normalized_mode_parameters(
            "deformation", str(base_mode), nested
        )
        normalized = {"base_mode": base_mode, **_deep_record(base_parameters)}
    else:
        raise ControlValidationError("unsupported deformation schedule mode")
    return _deep_freeze(normalized)


@dataclass(frozen=True, init=False)
class AxisFrame:
    """Physical axial/hoop meanings and their basis vectors in coordinates."""

    x_meaning: str
    y_meaning: str
    basis: np.ndarray

    def __init__(
        self,
        x_meaning: str = "axial",
        y_meaning: str = "hoop",
        basis: object = ((1.0, 0.0), (0.0, 1.0)),
    ) -> None:
        if x_meaning != "axial" or y_meaning != "hoop":
            raise ControlValidationError(
                "axis meanings must be x=axial and y=hoop in the computational frame"
            )
        object.__setattr__(self, "x_meaning", x_meaning)
        object.__setattr__(self, "y_meaning", y_meaning)
        matrix = _matrix2(basis, "axis basis", nonsingular=True)
        if not np.allclose(matrix.T @ matrix, np.eye(2), rtol=0.0, atol=1.0e-12):
            raise ControlValidationError("axis basis must be orthogonal")
        object.__setattr__(self, "basis", matrix)

    @property
    def axis_meanings(self) -> tuple[str, str]:
        return (self.x_meaning, self.y_meaning)

    def as_record(self) -> dict[str, object]:
        return {
            "axis_meanings": {"x": self.x_meaning, "y": self.y_meaning},
            "basis_columns_in_current_coordinates": self.basis.tolist(),
        }


def _parse_axes(value: object) -> AxisFrame:
    axes = _mapping(value, "axes")
    _exact_keys(axes, required={"x", "y"})
    if dict(axes) != _AXIS_MEANINGS:
        raise ControlValidationError("axes must explicitly declare x=axial and y=hoop")
    return AxisFrame()


def _validate_common_contract(config: Mapping[str, object]) -> None:
    if config.get("schema_version") != CONTROL_SCHEMA_VERSION:
        raise ControlValidationError(
            f"schema_version must equal {CONTROL_SCHEMA_VERSION!r}"
        )
    _nonempty_string(config.get("config_id"), "config_id")
    if config.get("absolute_reference") != _REFERENCE_STATE:
        raise ControlValidationError(
            "absolute_reference must be fixed_cell_equilibrated"
        )
    _nonempty_string(config.get("fixed_reference_id"), "fixed_reference_id")
    if config.get("reference_reset_policy") != _REFERENCE_RESET_POLICY:
        raise ControlValidationError("reference_reset_policy must be never")
    if config.get("load_coordinate_kind") != _LOAD_COORDINATE_KIND:
        raise ControlValidationError(
            "load_coordinate_kind must be quasi_static_not_physical_time"
        )


@dataclass(frozen=True)
class QuasiStaticControlStep:
    """One absolute target plus the increment from the prior accepted state."""

    control_id: str
    step_index: int
    control_kind: str
    loading_mode: str
    axes: AxisFrame
    reference_state_id: str
    lambda_load: float
    load_coordinate_unit: str
    progress_unit: str
    path_progress: float
    progress_increment: float
    absolute_deformation_gradient: np.ndarray | None
    incremental_deformation_gradient: np.ndarray | None
    absolute_tension_target_pN_per_nm: np.ndarray | None
    incremental_tension_target_pN_per_nm: np.ndarray | None
    pressure_derivation: Mapping[str, object] | None = None
    physical_time: None = None
    physical_time_valid: bool = False

    def __post_init__(self) -> None:
        _nonempty_string(self.control_id, "control_id")
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or self.step_index < 0
        ):
            raise ControlValidationError("step_index must be a nonnegative integer")
        _nonempty_string(self.loading_mode, "loading_mode")
        _nonempty_string(self.reference_state_id, "reference_state_id")
        _nonempty_string(self.load_coordinate_unit, "load_coordinate_unit")
        if self.load_coordinate_unit not in {"dimensionless", "pN/nm^2"}:
            raise ControlValidationError(
                "load_coordinate_unit must be dimensionless or pN/nm^2"
            )
        if self.progress_unit != self.load_coordinate_unit:
            raise ControlValidationError(
                "progress_unit must equal load_coordinate_unit for this control"
            )
        _nonempty_string(self.progress_unit, "progress_unit")
        lambda_load = _finite_float(self.lambda_load, "lambda_load")
        path_progress = _finite_float(self.path_progress, "path_progress")
        progress_increment = _finite_float(
            self.progress_increment, "progress_increment"
        )
        if path_progress < 0.0 or progress_increment < 0.0:
            raise ControlValidationError("path progress values must be nonnegative")
        if progress_increment > path_progress + _FLOAT_TOLERANCE:
            raise ControlValidationError(
                "progress_increment cannot exceed cumulative path_progress"
            )
        object.__setattr__(self, "lambda_load", lambda_load)
        object.__setattr__(self, "path_progress", path_progress)
        object.__setattr__(self, "progress_increment", progress_increment)
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise ControlValidationError(
                "quasi-static controls cannot carry a valid physical time"
            )

        if self.control_kind == "deformation_gradient":
            if (
                self.absolute_deformation_gradient is None
                or self.incremental_deformation_gradient is None
                or self.absolute_tension_target_pN_per_nm is not None
                or self.incremental_tension_target_pN_per_nm is not None
            ):
                raise ControlValidationError(
                    "deformation controls require only absolute/incremental F"
                )
            object.__setattr__(
                self,
                "absolute_deformation_gradient",
                _matrix2(
                    self.absolute_deformation_gradient,
                    "absolute_deformation_gradient",
                    nonsingular=True,
                ),
            )
            object.__setattr__(
                self,
                "incremental_deformation_gradient",
                _matrix2(
                    self.incremental_deformation_gradient,
                    "incremental_deformation_gradient",
                    nonsingular=True,
                ),
            )
            if (
                float(np.linalg.det(self.absolute_deformation_gradient))
                <= _FLOAT_TOLERANCE
                or float(np.linalg.det(self.incremental_deformation_gradient))
                <= _FLOAT_TOLERANCE
            ):
                raise ControlValidationError(
                    "deformation gradients must have positive determinant; inverted controls are forbidden"
                )
            if self.pressure_derivation is not None:
                raise ControlValidationError(
                    "deformation controls cannot carry a pressure derivation"
                )
        elif self.control_kind == "membrane_tension_target":
            if (
                self.absolute_tension_target_pN_per_nm is None
                or self.incremental_tension_target_pN_per_nm is None
                or self.absolute_deformation_gradient is not None
                or self.incremental_deformation_gradient is not None
            ):
                raise ControlValidationError(
                    "tension controls require only absolute/incremental tension targets"
                )
            object.__setattr__(
                self,
                "absolute_tension_target_pN_per_nm",
                _matrix2(
                    self.absolute_tension_target_pN_per_nm,
                    "absolute_tension_target_pN_per_nm",
                    nonsingular=False,
                ),
            )
            object.__setattr__(
                self,
                "incremental_tension_target_pN_per_nm",
                _matrix2(
                    self.incremental_tension_target_pN_per_nm,
                    "incremental_tension_target_pN_per_nm",
                    nonsingular=False,
                ),
            )
            if self.pressure_derivation is None:
                raise ControlValidationError(
                    "pressure-derived tension control requires derivation metadata"
                )
            object.__setattr__(
                self, "pressure_derivation", _deep_freeze(self.pressure_derivation)
            )
        else:
            raise ControlValidationError(f"unsupported control_kind {self.control_kind!r}")

    def as_record(self) -> dict[str, object]:
        pressure = _deep_record(self.pressure_derivation)
        return {
            "control_id": self.control_id,
            "step_index": self.step_index,
            "control_kind": self.control_kind,
            "loading_mode": self.loading_mode,
            "axes": self.axes.as_record(),
            "reference_state_id": self.reference_state_id,
            "reference_reset_policy": _REFERENCE_RESET_POLICY,
            "lambda_load": self.lambda_load,
            "load_coordinate_kind": _LOAD_COORDINATE_KIND,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_increment": self.progress_increment,
            "progress_unit": self.progress_unit,
            "progress_semantics": "cumulative_absolute_lambda_increment",
            "absolute_control_semantics": (
                "F_absolute_maps_fixed_reference_to_target"
                if self.control_kind == "deformation_gradient"
                else "N_absolute_is_total_membrane_tension_target"
            ),
            "increment_control_semantics": (
                "F_increment_maps_previous_accepted_state_to_target"
                if self.control_kind == "deformation_gradient"
                else "Delta_N_target_is_additive_from_previous_target"
            ),
            "absolute_deformation_gradient": _optional_matrix_record(
                self.absolute_deformation_gradient
            ),
            "incremental_deformation_gradient": _optional_matrix_record(
                self.incremental_deformation_gradient
            ),
            "absolute_tension_target_pN_per_nm": _optional_matrix_record(
                self.absolute_tension_target_pN_per_nm
            ),
            "incremental_tension_target_pN_per_nm": _optional_matrix_record(
                self.incremental_tension_target_pN_per_nm
            ),
            "pressure_derivation": pressure,
            "physical_time": None,
            "physical_time_valid": False,
        }


@dataclass(frozen=True)
class QuasiStaticSchedule:
    """A validated series of targets sharing one immutable reference state."""

    config_id: str
    control_family: str
    mode: str
    reference_state_id: str
    axes: AxisFrame
    steps: tuple[QuasiStaticControlStep, ...]
    load_coordinate_unit: str
    progress_unit: str
    mode_parameters: Mapping[str, object]
    schema_version: str = CONTROL_SCHEMA_VERSION
    absolute_reference: str = _REFERENCE_STATE
    reference_reset_policy: str = _REFERENCE_RESET_POLICY
    load_coordinate_kind: str = _LOAD_COORDINATE_KIND
    progress_semantics: str = "cumulative_absolute_lambda_increment"

    def __post_init__(self) -> None:
        _nonempty_string(self.config_id, "config_id")
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.schema_version != CONTROL_SCHEMA_VERSION:
            raise ControlValidationError(
                f"schema_version must equal {CONTROL_SCHEMA_VERSION!r}"
            )
        if self.absolute_reference != _REFERENCE_STATE:
            raise ControlValidationError(
                "absolute_reference must be fixed_cell_equilibrated"
            )
        if self.reference_reset_policy != _REFERENCE_RESET_POLICY:
            raise ControlValidationError("reference_reset_policy must be never")
        if self.load_coordinate_kind != _LOAD_COORDINATE_KIND:
            raise ControlValidationError(
                "load_coordinate_kind must be quasi_static_not_physical_time"
            )
        if self.progress_semantics != "cumulative_absolute_lambda_increment":
            raise ControlValidationError(
                "progress_semantics must be cumulative_absolute_lambda_increment"
            )
        if not isinstance(self.axes, AxisFrame):
            raise ControlValidationError("axes must be an AxisFrame")
        mode_parameters = _normalized_mode_parameters(
            self.control_family, self.mode, self.mode_parameters
        )
        object.__setattr__(self, "mode_parameters", mode_parameters)
        if isinstance(self.steps, (str, bytes)):
            raise ControlValidationError("steps must be control objects")
        steps = tuple(self.steps)
        object.__setattr__(self, "steps", steps)
        if not steps:
            raise ControlValidationError("schedule must contain at least one step")
        if any(not isinstance(step, QuasiStaticControlStep) for step in steps):
            raise ControlValidationError("steps must contain QuasiStaticControlStep objects")
        if self.control_family == "deformation":
            if self.mode not in {
                "isotropic",
                "axial",
                "hoop",
                "unequal_biaxial",
                "engineering_simple_shear",
                "cyclic",
            }:
                raise ControlValidationError("unsupported deformation schedule mode")
            expected_kind = "deformation_gradient"
            expected_loading_mode = (
                "cyclic_loading_unloading" if self.mode == "cyclic" else self.mode
            )
            expected_unit = "dimensionless"
        elif self.control_family == "pressure_derived_tension":
            if self.mode != "pressure_derived_tension":
                raise ControlValidationError(
                    "pressure control_family requires pressure_derived_tension mode"
                )
            expected_kind = "membrane_tension_target"
            expected_loading_mode = "pressure_derived_tension"
            expected_unit = "pN/nm^2"
        else:
            raise ControlValidationError("unsupported schedule control_family")
        if self.load_coordinate_unit != expected_unit or self.progress_unit != expected_unit:
            raise ControlValidationError(
                f"schedule load/progress units must both be {expected_unit}"
            )
        if any(step.reference_state_id != self.reference_state_id for step in steps):
            raise ControlValidationError("schedule cannot reset its fixed reference")
        if any(
            step.control_kind != expected_kind
            or step.loading_mode != expected_loading_mode
            or step.load_coordinate_unit != expected_unit
            or step.progress_unit != expected_unit
            for step in steps
        ):
            raise ControlValidationError("schedule step kind, mode, or units are inconsistent")
        if any(
            step.axes.axis_meanings != self.axes.axis_meanings
            or not np.allclose(
                step.axes.basis, self.axes.basis, rtol=0.0, atol=_FLOAT_TOLERANCE
            )
            for step in steps
        ):
            raise ControlValidationError("schedule step axes are inconsistent")
        if len({step.control_id for step in steps}) != len(steps):
            raise ControlValidationError("schedule control_id values must be unique")
        if self.control_family == "deformation":
            semantic_mode = self.mode
            semantic_parameters = dict(self.mode_parameters)
            if self.mode == "cyclic":
                semantic_mode = str(semantic_parameters.pop("base_mode"))
            direction = _deformation_direction(semantic_mode, semantic_parameters)
            previous_absolute = np.eye(2)
            for step in steps:
                semantic_absolute = (
                    self.axes.basis
                    @ _deformation_gradient(step.lambda_load, direction)
                    @ self.axes.basis.T
                )
                if not np.allclose(
                    step.absolute_deformation_gradient,
                    semantic_absolute,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                ):
                    raise ControlValidationError(
                        "absolute deformation target is inconsistent with mode, mode_parameters, and lambda_load semantics"
                    )
                replayed = (
                    step.incremental_deformation_gradient @ previous_absolute
                )
                if not np.allclose(
                    replayed,
                    step.absolute_deformation_gradient,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                ):
                    raise ControlValidationError(
                        "deformation increment replay does not reproduce absolute target"
                    )
                previous_absolute = step.absolute_deformation_gradient
        else:
            previous_target = np.zeros((2, 2), dtype=float)
            schedule_radius: float | None = None
            for step in steps:
                derivation = _mapping(
                    step.pressure_derivation, "pressure_derivation"
                )
                _exact_keys(
                    derivation,
                    required={
                        "pressure",
                        "pressure_unit",
                        "radius",
                        "radius_unit",
                        "tension_unit",
                        "shell_geometry",
                        "location_assumption",
                        "equations",
                        "isotropic_strain_relabelled_as_turgor",
                        "target_kind",
                    },
                )
                pressure = _finite_float(derivation["pressure"], "pressure")
                radius = _finite_float(derivation["radius"], "radius")
                if pressure < 0.0 or radius <= 0.0:
                    raise ControlValidationError(
                        "pressure must be nonnegative and radius must be positive"
                    )
                if not np.isclose(
                    pressure, step.lambda_load, rtol=0.0, atol=_FLOAT_TOLERANCE
                ):
                    raise ControlValidationError(
                        "pressure metadata must equal lambda_load"
                    )
                if schedule_radius is None:
                    schedule_radius = radius
                elif not np.isclose(
                    radius, schedule_radius, rtol=0.0, atol=_FLOAT_TOLERANCE
                ):
                    raise ControlValidationError(
                        "pressure schedule radius must remain fixed"
                    )
                expected_metadata = {
                    "pressure_unit": "pN/nm^2",
                    "radius_unit": "nm",
                    "tension_unit": "pN/nm",
                    "shell_geometry": "closed_thin_cylinder",
                    "location_assumption": "away_from_end_effects",
                    "target_kind": "membrane_tension_force_balance_not_normal_inflation",
                }
                for field, expected_value in expected_metadata.items():
                    if derivation[field] != expected_value:
                        raise ControlValidationError(
                            f"pressure derivation {field} must be {expected_value!r}"
                        )
                equations = _mapping(derivation["equations"], "equations")
                _exact_keys(equations, required={"N_axial", "N_hoop"})
                if dict(equations) != {"N_axial": "p*R/2", "N_hoop": "p*R"}:
                    raise ControlValidationError(
                        "pressure derivation equations must encode closed-cylinder balance"
                    )
                if derivation["isotropic_strain_relabelled_as_turgor"] is not False:
                    raise ControlValidationError(
                        "isotropic strain cannot be relabelled as turgor"
                    )
                canonical_target = np.diag(
                    (pressure * radius / 2.0, pressure * radius)
                )
                semantic_target = (
                    self.axes.basis @ canonical_target @ self.axes.basis.T
                )
                if not np.allclose(
                    step.absolute_tension_target_pN_per_nm,
                    semantic_target,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                ):
                    raise ControlValidationError(
                        "absolute tension target is inconsistent with pressure derivation semantics"
                    )
                replayed = previous_target + step.incremental_tension_target_pN_per_nm
                if not np.allclose(
                    replayed,
                    step.absolute_tension_target_pN_per_nm,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                ):
                    raise ControlValidationError(
                        "tension increment replay does not reproduce absolute target"
                    )
                previous_target = step.absolute_tension_target_pN_per_nm
        expected = 0.0
        previous_lambda = 0.0
        for index, step in enumerate(steps):
            expected_increment = abs(step.lambda_load - previous_lambda)
            if not np.isclose(
                step.progress_increment,
                expected_increment,
                rtol=0.0,
                atol=_FLOAT_TOLERANCE,
            ):
                raise ControlValidationError(
                    "progress_increment must equal absolute lambda_load increment"
                )
            expected += expected_increment
            if step.step_index != index or not np.isclose(
                step.path_progress, expected, rtol=0.0, atol=_FLOAT_TOLERANCE
            ):
                raise ControlValidationError("inconsistent schedule path progress")
            previous_lambda = step.lambda_load

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "config_id": self.config_id,
            "control_family": self.control_family,
            "mode": self.mode,
            "mode_parameters": _deep_record(self.mode_parameters),
            "axes": self.axes.as_record(),
            "fixed_reference_id": self.reference_state_id,
            "absolute_reference": self.absolute_reference,
            "reference_reset_policy": self.reference_reset_policy,
            "load_coordinate_kind": self.load_coordinate_kind,
            "load_coordinate_unit": self.load_coordinate_unit,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
            "physical_time_claim": False,
            "steps": [step.as_record() for step in self.steps],
        }


def _lambda_values(config: Mapping[str, object], field: str) -> tuple[float, ...]:
    raw = config.get(field)
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence) or not raw:
        raise ControlValidationError(f"{field} must be a non-empty numeric array")
    return tuple(_finite_float(value, f"{field}[{index}]") for index, value in enumerate(raw))


def _deformation_direction(
    mode: str, config: Mapping[str, object]
) -> tuple[float, float, str | None]:
    if mode == "isotropic":
        return 1.0, 1.0, None
    if mode == "axial":
        return 1.0, 0.0, None
    if mode == "hoop":
        return 0.0, 1.0, None
    if mode == "unequal_biaxial":
        direction = _mapping(config.get("strain_direction"), "strain_direction")
        _exact_keys(direction, required={"epsilon_xx", "epsilon_yy"})
        axial = _finite_float(direction["epsilon_xx"], "strain_direction.epsilon_xx")
        hoop = _finite_float(direction["epsilon_yy"], "strain_direction.epsilon_yy")
        if axial == 0.0 and hoop == 0.0:
            raise ControlValidationError("strain_direction cannot be zero")
        if np.isclose(axial, hoop):
            raise ControlValidationError(
                "unequal_biaxial requires distinct axial and hoop directions"
            )
        return axial, hoop, None
    if mode == "engineering_simple_shear":
        component = config.get("shear_component")
        if component not in {"xy", "yx"}:
            raise ControlValidationError("shear_component must be explicitly xy or yx")
        return 0.0, 0.0, str(component)
    raise ControlValidationError(f"unsupported deformation mode {mode!r}")


def _deformation_gradient(
    lambda_load: float, direction: tuple[float, float, str | None]
) -> np.ndarray:
    axial, hoop, shear = direction
    if shear is None:
        result = np.array(
            [[1.0 + axial * lambda_load, 0.0], [0.0, 1.0 + hoop * lambda_load]],
            dtype=float,
        )
    elif shear == "xy":
        result = np.array([[1.0, lambda_load], [0.0, 1.0]], dtype=float)
    else:
        result = np.array([[1.0, 0.0], [lambda_load, 1.0]], dtype=float)
    if float(np.linalg.det(result)) <= _FLOAT_TOLERANCE:
        raise ControlValidationError(
            "deformation target is singular, inverted, or has nonpositive area"
        )
    return result


def build_deformation_schedule(config: Mapping[str, object]) -> QuasiStaticSchedule:
    """Build absolute and multiplicative-increment deformation controls."""

    config = _mapping(config, "control config")
    common = {
        "schema_version",
        "config_id",
        "control_family",
        "mode",
        "axes",
        "fixed_reference_id",
        "absolute_reference",
        "reference_reset_policy",
        "load_coordinate_kind",
        "strain_unit",
        "lambda_values",
    }
    mode = config.get("mode")
    required = set(common)
    if mode == "unequal_biaxial":
        required.add("strain_direction")
    elif mode == "engineering_simple_shear":
        required.add("shear_component")
    elif mode == "cyclic":
        required.add("base_mode")
        if config.get("base_mode") == "unequal_biaxial":
            required.add("strain_direction")
        elif config.get("base_mode") == "engineering_simple_shear":
            required.add("shear_component")
    _exact_keys(config, required=required)
    _validate_common_contract(config)
    if config.get("control_family") != "deformation":
        raise ControlValidationError("control_family must be deformation")
    if config.get("strain_unit") != "dimensionless":
        raise ControlValidationError("strain_unit must be dimensionless")
    axes = _parse_axes(config["axes"])

    if mode == "cyclic":
        base_mode = config.get("base_mode")
        if base_mode not in {
            "isotropic",
            "axial",
            "hoop",
            "unequal_biaxial",
            "engineering_simple_shear",
        }:
            raise ControlValidationError("cyclic base_mode is unsupported")
        direction = _deformation_direction(str(base_mode), config)
        loading_mode = "cyclic_loading_unloading"
    else:
        direction = _deformation_direction(str(mode), config)
        loading_mode = str(mode)

    values = _lambda_values(config, "lambda_values")
    previous_lambda = 0.0
    previous_f = np.eye(2)
    progress = 0.0
    steps: list[QuasiStaticControlStep] = []
    for index, lambda_load in enumerate(values):
        absolute_f = _deformation_gradient(lambda_load, direction)
        increment_f = absolute_f @ np.linalg.inv(previous_f)
        progress_increment = abs(lambda_load - previous_lambda)
        progress += progress_increment
        steps.append(
            QuasiStaticControlStep(
                control_id=f"{config['config_id']}:{index:06d}",
                step_index=index,
                control_kind="deformation_gradient",
                loading_mode=loading_mode,
                axes=axes,
                reference_state_id=str(config["fixed_reference_id"]),
                lambda_load=lambda_load,
                load_coordinate_unit="dimensionless",
                path_progress=progress,
                progress_increment=progress_increment,
                progress_unit="dimensionless",
                absolute_deformation_gradient=absolute_f,
                incremental_deformation_gradient=increment_f,
                absolute_tension_target_pN_per_nm=None,
                incremental_tension_target_pN_per_nm=None,
            )
        )
        previous_lambda = lambda_load
        previous_f = absolute_f
    return QuasiStaticSchedule(
        config_id=str(config["config_id"]),
        control_family="deformation",
        mode=str(mode),
        reference_state_id=str(config["fixed_reference_id"]),
        axes=axes,
        steps=tuple(steps),
        load_coordinate_unit="dimensionless",
        progress_unit="dimensionless",
        mode_parameters=(
            {
                "base_mode": config["base_mode"],
                **(
                    {"strain_direction": dict(config["strain_direction"])}
                    if config.get("base_mode") == "unequal_biaxial"
                    else {}
                ),
                **(
                    {"shear_component": config["shear_component"]}
                    if config.get("base_mode") == "engineering_simple_shear"
                    else {}
                ),
            }
            if mode == "cyclic"
            else (
                {"strain_direction": dict(config["strain_direction"])}
                if mode == "unequal_biaxial"
                else (
                    {"shear_component": config["shear_component"]}
                    if mode == "engineering_simple_shear"
                    else {}
                )
            )
        ),
    )


def build_pressure_schedule(config: Mapping[str, object]) -> QuasiStaticSchedule:
    """Build total 2D tension targets from a declared cylinder force balance."""

    config = _mapping(config, "control config")
    required = {
        "schema_version",
        "config_id",
        "control_family",
        "mode",
        "axes",
        "fixed_reference_id",
        "absolute_reference",
        "reference_reset_policy",
        "load_coordinate_kind",
        "pressure_values",
        "pressure_unit",
        "radius",
        "radius_unit",
        "tension_unit",
        "shell_geometry",
        "location_assumption",
    }
    _exact_keys(config, required=required)
    _validate_common_contract(config)
    if config.get("control_family") != "pressure_derived_tension":
        raise ControlValidationError("control_family must be pressure_derived_tension")
    if config.get("mode") != "pressure_derived_tension":
        raise ControlValidationError("mode must be pressure_derived_tension")
    expected = {
        "pressure_unit": "pN/nm^2",
        "radius_unit": "nm",
        "tension_unit": "pN/nm",
        "shell_geometry": "closed_thin_cylinder",
        "location_assumption": "away_from_end_effects",
    }
    for field, value in expected.items():
        if config.get(field) != value:
            raise ControlValidationError(f"{field} must be {value!r}")
    axes = _parse_axes(config["axes"])
    radius = _finite_float(config["radius"], "radius")
    if radius <= 0.0:
        raise ControlValidationError("radius must be positive")
    pressure_values = _lambda_values(config, "pressure_values")
    if any(pressure < 0.0 for pressure in pressure_values):
        raise ControlValidationError("pressure_values must be nonnegative")

    previous_pressure = 0.0
    previous_target = np.zeros((2, 2), dtype=float)
    progress = 0.0
    steps: list[QuasiStaticControlStep] = []
    for index, pressure in enumerate(pressure_values):
        total_target = np.diag((pressure * radius / 2.0, pressure * radius))
        delta_target = total_target - previous_target
        progress_increment = abs(pressure - previous_pressure)
        progress += progress_increment
        derivation = {
            "pressure": pressure,
            "pressure_unit": "pN/nm^2",
            "radius": radius,
            "radius_unit": "nm",
            "tension_unit": "pN/nm",
            "shell_geometry": "closed_thin_cylinder",
            "location_assumption": "away_from_end_effects",
            "equations": {"N_axial": "p*R/2", "N_hoop": "p*R"},
            "isotropic_strain_relabelled_as_turgor": False,
            "target_kind": "membrane_tension_force_balance_not_normal_inflation",
        }
        steps.append(
            QuasiStaticControlStep(
                control_id=f"{config['config_id']}:{index:06d}",
                step_index=index,
                control_kind="membrane_tension_target",
                loading_mode="pressure_derived_tension",
                axes=axes,
                reference_state_id=str(config["fixed_reference_id"]),
                lambda_load=pressure,
                load_coordinate_unit="pN/nm^2",
                path_progress=progress,
                progress_increment=progress_increment,
                progress_unit="pN/nm^2",
                absolute_deformation_gradient=None,
                incremental_deformation_gradient=None,
                absolute_tension_target_pN_per_nm=total_target,
                incremental_tension_target_pN_per_nm=delta_target,
                pressure_derivation=derivation,
            )
        )
        previous_pressure = pressure
        previous_target = total_target
    return QuasiStaticSchedule(
        config_id=str(config["config_id"]),
        control_family="pressure_derived_tension",
        mode="pressure_derived_tension",
        reference_state_id=str(config["fixed_reference_id"]),
        axes=axes,
        steps=tuple(steps),
        load_coordinate_unit="pN/nm^2",
        progress_unit="pN/nm^2",
        mode_parameters={},
    )


def transform_control_step(
    step: QuasiStaticControlStep, coordinate_transform: object
) -> QuasiStaticControlStep:
    """Express a control in a rotated/reflected orthonormal coordinate frame."""

    transform = _matrix2(
        coordinate_transform, "coordinate_transform", nonsingular=True
    )
    if not np.allclose(
        transform.T @ transform, np.eye(2), rtol=0.0, atol=1.0e-12
    ):
        raise ControlValidationError(
            "coordinate_transform must be orthogonal; general curvilinear bases are unsupported"
        )
    axes = AxisFrame(
        step.axes.x_meaning,
        step.axes.y_meaning,
        transform @ step.axes.basis,
    )
    if step.control_kind == "deformation_gradient":
        absolute_f = transform @ step.absolute_deformation_gradient @ transform.T
        increment_f = transform @ step.incremental_deformation_gradient @ transform.T
        absolute_n = None
        increment_n = None
    else:
        absolute_f = None
        increment_f = None
        absolute_n = (
            transform @ step.absolute_tension_target_pN_per_nm @ transform.T
        )
        increment_n = (
            transform @ step.incremental_tension_target_pN_per_nm @ transform.T
        )
    return QuasiStaticControlStep(
        control_id=step.control_id,
        step_index=step.step_index,
        control_kind=step.control_kind,
        loading_mode=step.loading_mode,
        axes=axes,
        reference_state_id=step.reference_state_id,
        lambda_load=step.lambda_load,
        load_coordinate_unit=step.load_coordinate_unit,
        path_progress=step.path_progress,
        progress_increment=step.progress_increment,
        progress_unit=step.progress_unit,
        absolute_deformation_gradient=absolute_f,
        incremental_deformation_gradient=increment_f,
        absolute_tension_target_pN_per_nm=absolute_n,
        incremental_tension_target_pN_per_nm=increment_n,
        pressure_derivation=step.pressure_derivation,
    )


@dataclass(frozen=True, init=False)
class PhysicalInteraction:
    """Stable physical interaction with immutable chemical type and parameters."""

    interaction_id: str
    chemical_type: str
    parameters: Mapping[str, float]
    alive: bool

    def __init__(
        self,
        interaction_id: str,
        chemical_type: str,
        parameters: Mapping[str, object],
        alive: bool = True,
    ) -> None:
        interaction_id = _nonempty_string(interaction_id, "interaction_id")
        chemical_type = _nonempty_string(chemical_type, "chemical_type")
        parameter_map = _mapping(parameters, "parameters")
        if not parameter_map:
            raise ControlValidationError("parameters cannot be empty")
        normalized = {
            _nonempty_string(name, "parameter name"): _finite_float(
                value, f"parameters.{name}"
            )
            for name, value in sorted(parameter_map.items())
        }
        if not isinstance(alive, bool):
            raise ControlValidationError("alive must be boolean")
        object.__setattr__(self, "interaction_id", interaction_id)
        object.__setattr__(self, "chemical_type", chemical_type)
        object.__setattr__(self, "parameters", MappingProxyType(normalized))
        object.__setattr__(self, "alive", alive)


@dataclass(frozen=True)
class PrescribedIntervention:
    """A local user-prescribed control, explicitly not material rupture."""

    config_id: str
    action: str
    interaction_ids: tuple[str, ...]
    reference_state_id: str
    lambda_load: float
    load_coordinate_unit: str
    progress_unit: str
    path_progress: float
    progress_increment: float
    factor: float | None = None
    parameter_names: tuple[str, ...] = ()
    schema_version: str = CONTROL_SCHEMA_VERSION
    control_family: str = "prescribed_intervention"
    source: str = "prescribed_intervention"
    selection_kind: str = "stable_physical_interaction_id"
    reference_reset_policy: str = _REFERENCE_RESET_POLICY
    load_coordinate_kind: str = _LOAD_COORDINATE_KIND

    def __post_init__(self) -> None:
        _nonempty_string(self.config_id, "config_id")
        if self.schema_version != CONTROL_SCHEMA_VERSION:
            raise ControlValidationError(
                f"schema_version must equal {CONTROL_SCHEMA_VERSION!r}"
            )
        if self.control_family != "prescribed_intervention":
            raise ControlValidationError(
                "control_family must be prescribed_intervention"
            )
        if self.reference_reset_policy != _REFERENCE_RESET_POLICY:
            raise ControlValidationError("reference_reset_policy must be never")
        if self.load_coordinate_kind != _LOAD_COORDINATE_KIND:
            raise ControlValidationError(
                "load_coordinate_kind must be quasi_static_not_physical_time"
            )
        if self.action not in {"weaken", "remove"}:
            raise ControlValidationError("intervention action must be weaken or remove")
        if isinstance(self.interaction_ids, (str, bytes)):
            raise ControlValidationError("interaction_ids must be an array")
        interaction_ids = tuple(self.interaction_ids)
        object.__setattr__(self, "interaction_ids", interaction_ids)
        if not interaction_ids:
            raise ControlValidationError("interaction_ids cannot be empty")
        if any(not isinstance(value, str) or not value for value in interaction_ids):
            raise ControlValidationError("interaction_ids must be non-empty strings")
        if len(set(interaction_ids)) != len(interaction_ids):
            raise ControlValidationError("duplicate stable interaction_ids are forbidden")
        if self.source != "prescribed_intervention":
            raise ControlValidationError("source must be prescribed_intervention")
        if self.selection_kind != "stable_physical_interaction_id":
            raise ControlValidationError(
                "selection_kind must be stable_physical_interaction_id"
            )
        _nonempty_string(self.reference_state_id, "fixed_reference_id")
        lambda_load = _finite_float(self.lambda_load, "lambda_load")
        path_progress = _finite_float(self.path_progress, "path_progress")
        progress_increment = _finite_float(
            self.progress_increment, "progress_increment"
        )
        if path_progress < 0.0 or progress_increment < 0.0:
            raise ControlValidationError("path progress values must be nonnegative")
        object.__setattr__(self, "lambda_load", lambda_load)
        object.__setattr__(self, "path_progress", path_progress)
        object.__setattr__(self, "progress_increment", progress_increment)
        _nonempty_string(self.load_coordinate_unit, "load_coordinate_unit")
        if self.load_coordinate_unit not in {"dimensionless", "pN/nm^2"}:
            raise ControlValidationError(
                "load_coordinate_unit must be dimensionless or pN/nm^2"
            )
        if self.progress_unit != self.load_coordinate_unit:
            raise ControlValidationError(
                "progress_unit must equal load_coordinate_unit for this control"
            )
        if progress_increment > path_progress + _FLOAT_TOLERANCE:
            raise ControlValidationError(
                "progress_increment cannot exceed cumulative path_progress"
            )
        if isinstance(self.parameter_names, (str, bytes)):
            raise ControlValidationError("parameter_names must be an array")
        parameter_names = tuple(self.parameter_names)
        if any(
            not isinstance(name, str) or not name.strip() for name in parameter_names
        ):
            raise ControlValidationError(
                "parameter_names must contain non-empty strings"
            )
        object.__setattr__(self, "parameter_names", parameter_names)
        if self.action == "weaken":
            factor = _finite_float(self.factor, "factor")
            if not 0.0 < factor < 1.0:
                raise ControlValidationError("weakening factor must satisfy 0 < factor < 1")
            if not parameter_names or len(set(parameter_names)) != len(parameter_names):
                raise ControlValidationError(
                    "weakening parameter_names must be non-empty and unique"
                )
            object.__setattr__(self, "factor", factor)
        elif self.factor is not None or self.parameter_names:
            raise ControlValidationError(
                "removal controls cannot carry weakening factor or parameter_names"
            )

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "config_id": self.config_id,
            "control_family": self.control_family,
            "action": self.action,
            "source": self.source,
            "selection_kind": self.selection_kind,
            "interaction_ids": list(self.interaction_ids),
            "fixed_reference_id": self.reference_state_id,
            "absolute_reference": _REFERENCE_STATE,
            "reference_reset_policy": self.reference_reset_policy,
            "load_coordinate_kind": self.load_coordinate_kind,
            "load_coordinate_unit": self.load_coordinate_unit,
            "progress_unit": self.progress_unit,
            "lambda_load": self.lambda_load,
            "path_progress": self.path_progress,
            "progress_increment": self.progress_increment,
            "progress_semantics": "cumulative_absolute_lambda_increment",
            "physical_time": None,
            "physical_time_valid": False,
            "factor": self.factor,
            "parameter_names": list(self.parameter_names),
            "application_scope": "per_interaction_effective_parameters_and_alive_mask",
            "shared_lammps_type_coefficient_mutated": False,
        }


@dataclass(frozen=True)
class EffectiveInteractionState:
    interaction_id: str
    chemical_type: str
    effective_parameters: Mapping[str, float]
    alive: bool

    def as_record(self) -> dict[str, object]:
        return {
            "interaction_id": self.interaction_id,
            "chemical_type": self.chemical_type,
            "effective_parameters": dict(self.effective_parameters),
            "alive": self.alive,
        }


@dataclass(frozen=True)
class InterventionResult:
    interactions: tuple[EffectiveInteractionState, ...]
    event: Mapping[str, object]

    @property
    def alive_mask(self) -> dict[str, bool]:
        return {item.interaction_id: item.alive for item in self.interactions}

    def as_record(self) -> dict[str, object]:
        return {
            "interactions": [item.as_record() for item in self.interactions],
            "alive_mask": self.alive_mask,
            "event": _deep_record(self.event),
        }


def _build_intervention(config: Mapping[str, object]) -> PrescribedIntervention:
    common = {
        "schema_version",
        "config_id",
        "control_family",
        "action",
        "source",
        "selection_kind",
        "interaction_ids",
        "fixed_reference_id",
        "absolute_reference",
        "reference_reset_policy",
        "load_coordinate_kind",
        "load_coordinate_unit",
        "progress_unit",
        "lambda_load",
        "path_progress",
        "progress_increment",
    }
    action = config.get("action")
    optional = {"factor", "parameter_names"} if action == "weaken" else set()
    _exact_keys(config, required=common, optional=optional)
    if config.get("schema_version") != CONTROL_SCHEMA_VERSION:
        raise ControlValidationError(
            f"schema_version must equal {CONTROL_SCHEMA_VERSION!r}"
        )
    if config.get("control_family") != "prescribed_intervention":
        raise ControlValidationError("control_family must be prescribed_intervention")
    if config.get("absolute_reference") != _REFERENCE_STATE:
        raise ControlValidationError(
            "absolute_reference must be fixed_cell_equilibrated"
        )
    if config.get("reference_reset_policy") != _REFERENCE_RESET_POLICY:
        raise ControlValidationError("reference_reset_policy must be never")
    if config.get("load_coordinate_kind") != _LOAD_COORDINATE_KIND:
        raise ControlValidationError(
            "load_coordinate_kind must be quasi_static_not_physical_time"
        )
    ids = config.get("interaction_ids")
    if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
        raise ControlValidationError("interaction_ids must be an array")
    parameters = config.get("parameter_names", ())
    if isinstance(parameters, (str, bytes)) or not isinstance(parameters, Sequence):
        raise ControlValidationError("parameter_names must be an array")
    return PrescribedIntervention(
        config_id=_nonempty_string(config.get("config_id"), "config_id"),
        action=str(action),
        interaction_ids=tuple(ids),
        reference_state_id=_nonempty_string(
            config.get("fixed_reference_id"), "fixed_reference_id"
        ),
        lambda_load=config.get("lambda_load"),
        load_coordinate_unit=_nonempty_string(
            config.get("load_coordinate_unit"), "load_coordinate_unit"
        ),
        progress_unit=_nonempty_string(config.get("progress_unit"), "progress_unit"),
        path_progress=config.get("path_progress"),
        progress_increment=config.get("progress_increment"),
        factor=config.get("factor"),
        parameter_names=tuple(parameters),
        source=str(config.get("source")),
        selection_kind=str(config.get("selection_kind")),
    )


def apply_prescribed_intervention(
    interactions: Sequence[PhysicalInteraction], intervention: PrescribedIntervention
) -> InterventionResult:
    """Apply a local intervention without changing a shared chemical type."""

    if not isinstance(intervention, PrescribedIntervention):
        raise TypeError("intervention must be a PrescribedIntervention")
    universe = tuple(interactions)
    if any(not isinstance(item, PhysicalInteraction) for item in universe):
        raise TypeError("interactions must contain only PhysicalInteraction objects")
    identifiers = [item.interaction_id for item in universe]
    if len(set(identifiers)) != len(identifiers):
        raise ControlValidationError("duplicate stable IDs in interaction universe")
    by_id = {item.interaction_id: item for item in universe}
    unknown = sorted(set(intervention.interaction_ids) - set(by_id))
    if unknown:
        raise ControlValidationError(f"unknown stable interaction IDs: {unknown}")
    selected = set(intervention.interaction_ids)
    effective: list[EffectiveInteractionState] = []
    old_new: list[dict[str, object]] = []
    for item in universe:
        parameters = dict(item.parameters)
        alive = item.alive
        if item.interaction_id in selected:
            if not item.alive:
                raise ControlValidationError(
                    f"selected interaction {item.interaction_id!r} is already inactive"
                )
            old_parameters = dict(parameters)
            if intervention.action == "weaken":
                missing = sorted(set(intervention.parameter_names) - set(parameters))
                if missing:
                    raise ControlValidationError(
                        f"selected interaction {item.interaction_id!r} lacks parameters {missing}"
                    )
                for name in intervention.parameter_names:
                    parameters[name] *= intervention.factor
            else:
                alive = False
            old_new.append(
                {
                    "interaction_id": item.interaction_id,
                    "chemical_type": item.chemical_type,
                    "old_alive": item.alive,
                    "new_alive": alive,
                    "old_parameters": old_parameters,
                    "new_effective_parameters": dict(parameters),
                }
            )
        effective.append(
            EffectiveInteractionState(
                interaction_id=item.interaction_id,
                chemical_type=item.chemical_type,
                effective_parameters=MappingProxyType(dict(parameters)),
                alive=alive,
            )
        )
    event_kind = (
        "prescribed_weakening"
        if intervention.action == "weaken"
        else "prescribed_removal"
    )
    event = {
        "event_id": f"{intervention.config_id}:event",
        "event_kind": event_kind,
        "source": "prescribed_intervention",
        "counts_as_damage_initiation": False,
        "selection_kind": "stable_physical_interaction_id",
        "selected_interaction_ids": list(intervention.interaction_ids),
        "fixed_reference_id": intervention.reference_state_id,
        "absolute_reference": _REFERENCE_STATE,
        "reference_reset_policy": "never",
        "load_coordinate_kind": intervention.load_coordinate_kind,
        "load_coordinate_unit": intervention.load_coordinate_unit,
        "progress_unit": intervention.progress_unit,
        "lambda_load": intervention.lambda_load,
        "path_progress": intervention.path_progress,
        "progress_increment": intervention.progress_increment,
        "progress_semantics": "cumulative_absolute_lambda_increment",
        "physical_time": None,
        "physical_time_valid": False,
        "interaction_changes": old_new,
        "application_scope": "per_interaction_effective_parameters_and_alive_mask",
        "shared_lammps_type_coefficient_mutated": False,
        "material_rupture_law_invoked": False,
    }
    return InterventionResult(tuple(effective), _deep_freeze(event))


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ControlValidationError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def load_control_config(
    source: str | Path | Mapping[str, object],
) -> QuasiStaticSchedule | PrescribedIntervention:
    """Load one strict JSON/mapping control config and return its typed form."""

    if isinstance(source, Mapping):
        config = dict(source)
    else:
        path = Path(source)
        try:
            config = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ControlValidationError(f"non-finite JSON constant {value!r}")
                ),
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ControlValidationError(f"cannot load control config {path}: {error}") from error
    config = _mapping(config, "control config")
    family = config.get("control_family")
    if family == "deformation":
        return build_deformation_schedule(config)
    if family == "pressure_derived_tension":
        return build_pressure_schedule(config)
    if family == "prescribed_intervention":
        return _build_intervention(config)
    raise ControlValidationError(f"unsupported control_family {family!r}")


__all__ = [
    "CONTROL_SCHEMA_VERSION",
    "AxisFrame",
    "ControlValidationError",
    "EffectiveInteractionState",
    "InterventionResult",
    "PhysicalInteraction",
    "PrescribedIntervention",
    "QuasiStaticControlStep",
    "QuasiStaticSchedule",
    "apply_prescribed_intervention",
    "build_deformation_schedule",
    "build_pressure_schedule",
    "load_control_config",
    "transform_control_step",
]
