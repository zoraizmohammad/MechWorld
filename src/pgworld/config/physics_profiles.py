"""Strict, immutable identities for PG computational physics profiles.

These profiles describe what a run used; they do not certify the biological
interpretation of inherited coefficients.  Loading is deliberately fail-closed:
the registered file, profile ID, canonical SHA-256 digest, shape, scalar types,
and route-specific inherited numbers must all agree.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "pgworld.physics_profile.v2"
_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONFIG_DIRECTORY = Path(__file__).resolve().parents[3] / "configs" / "physics"

_PROFILE_FILES = {
    "legacy_python_2026_03_12_v1": "legacy_python_2026_03_12_v1.json",
    "legacy_direct_isotropic_pre_unit_fix_v1": (
        "legacy_direct_isotropic_pre_unit_fix_v1.json"
    ),
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": (
        "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1.json"
    ),
    "reviewed_physics_provisional_v0": "reviewed_physics_provisional_v0.json",
}

# Filled with the canonical digests committed beside this module.  Pinning the
# values here means recomputing a digest after editing a JSON file is not enough
# to make a changed profile load under an existing immutable ID.
_PROFILE_HASHES = {
    "legacy_python_2026_03_12_v1": (
        "sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b"
    ),
    "legacy_direct_isotropic_pre_unit_fix_v1": (
        "sha256:9307aa15c01a557f671fff08d50793dccbf4837f0cd3c78eb0d3d9d7ab3b1df0"
    ),
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": (
        "sha256:58b5271932856c040992306c19e393788bd28f829245348951de2e4733fb7f6a"
    ),
    "reviewed_physics_provisional_v0": (
        "sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5"
    ),
}

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "profile_version",
    "profile_id",
    "canonical_hash",
    "family",
    "route",
    "intended_use",
    "review_status",
    "biological_parameter_certified",
    "final_science_campaign_allowed",
    "coarse_graining_status",
    "nonlinear_fit_status",
    "angle_resolution_status",
    "spacing",
    "mass",
    "units",
    "potentials",
    "reference_state",
    "historical_execution",
    "required_new_output_policy",
    "axes",
    "dimensional_scope",
    "rupture_law",
    "derived_numerical_facts",
    "review_requests",
    "sources",
    "provenance",
}

_NESTED_FIELDS = {
    "spacing": {
        "code_edge_rest_length_nm",
        "mapping_status",
        "candidate_two_edge_hypothesis",
        "candidate_angle_scaling",
    },
    "mass": {"status", "value_ag", "physical_time_valid"},
    "units": {
        "lammps_style",
        "energy",
        "force",
        "length",
        "angle_input",
        "angle_internal",
        "membrane_tension_internal",
        "membrane_tension_summary",
        "pN_per_nm_to_N_per_m",
        "pN_nm_to_J",
    },
    "reference_state": {
        "name",
        "cell_policy",
        "zero_tension_claim",
        "coordinates_required",
        "full_cell_matrix_required",
        "achieved_geometry_required",
        "minimization_diagnostics_required",
        "initial_tension_required",
    },
    "historical_execution": {
        "scope",
        "entry_points",
        "loading_or_evaluation",
        "pressure_compute",
        "kinetic_term_semantics",
        "nve_deform_segment",
        "tangent_output",
    },
    "required_new_output_policy": {
        "scope",
        "source",
        "kinetic_term_included",
        "dimensionality",
        "sign_convention",
        "primary",
        "secondary",
    },
    "axes": {"x", "y", "laboratory_mapping_status"},
    "dimensional_scope": {
        "native_quantity",
        "thickness_nm",
        "stress_3d_allowed",
        "cylinder_display_label",
    },
    "rupture_law": {
        "status",
        "primary_endpoint",
        "deterministic_version",
        "heterogeneous_version",
        "threshold_visibility",
        "fresh_lottery_per_step",
    },
    "derived_numerical_facts": {
        "one_edge_harmonic_tangent_pN_per_nm",
        "two_edge_series_tangent_pN_per_nm",
        "two_edge_series_rest_length_nm",
        "nonlinear_local_tangent_pN_per_nm",
        "nonlinear_extension_pole_nm",
        "angle_curvature_pN_nm_per_rad2",
        "status",
    },
    "provenance": {
        "source_routes",
        "source_revision",
        "decision_record",
        "provisional_base_identity",
        "notes",
    },
}

_HISTORICAL_TANGENT_FIELDS = {
    "status",
    "declared_tangent_unit",
    "tangent_conversion_factor",
    "dimensional_status",
}

_POTENTIAL_FIELDS = {
    "style",
    "equation",
    "parameter_units",
    "parameters",
    "parameter_metadata",
    "fit_artifact",
    "status",
}
_POTENTIAL_PARAMETER_FIELDS = {
    "harmonic_bond": {"K_pN_per_nm", "r0_nm"},
    "nonlinear_bond": {"epsilon_pN_nm", "r0_nm", "lambda_nm"},
    "harmonic_angle": {"K_pN_nm", "theta0_degrees"},
}
_PARAMETER_METADATA_FIELDS = {"uncertainty_status", "range_status", "range"}
_FIT_ARTIFACT_FIELDS = {
    "artifact_status",
    "path",
    "sha256_status",
    "sha256",
}
_SOURCE_FIELDS = {"id", "kind", "citation_or_path", "claim_scope"}
_REVIEW_REQUEST_FIELDS = {"person", "role", "status"}
_REQUIRED_LAMMPS_SOURCE_URLS = {
    "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/units.rst",
    "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_harmonic.rst",
    "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_nonlinear.rst",
    "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/angle_harmonic.rst",
    "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/compute_pressure.rst",
}

_ROUTE_NUMERICS = {
    "legacy_python_2026_03_12_v1": {
        "mass": 0.0004271587301788674,
        "harmonic_bond": (5570.0, 1.03),
        "nonlinear_bond": (185.328520541486, 1.0, 4.034069292365436),
        "harmonic_angle": (41.8, 180.0),
    },
    "legacy_direct_isotropic_pre_unit_fix_v1": {
        "mass": None,
        "harmonic_bond": (5.57, 1.03),
        "nonlinear_bond": (0.185567402281798, 1.0, 4.035190236993014),
        "harmonic_angle": (0.0418, 180.0),
    },
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": {
        "mass": None,
        "harmonic_bond": (5.57, 1.03),
        "nonlinear_bond": (0.1709, 0.9065, 4.0878),
        "harmonic_angle": (0.0418, 180.0),
    },
    "reviewed_physics_provisional_v0": {
        "mass": 0.0004271587301788674,
        "harmonic_bond": (5570.0, 1.03),
        "nonlinear_bond": (185.328520541486, 1.0, 4.034069292365436),
        "harmonic_angle": (41.8, 180.0),
    },
}


class PhysicsProfileError(ValueError):
    """Raised when a physics profile cannot be trusted or interpreted."""


class ProfileMixingError(PhysicsProfileError):
    """Raised when profile identities are silently or inconsistently mixed."""


@dataclass(frozen=True)
class PhysicsProfile:
    """An immutable loaded profile with a fresh serializable snapshot API."""

    profile_id: str
    canonical_hash: str
    _snapshot_json: str

    def __post_init__(self) -> None:
        """Reject direct construction unless the complete snapshot validates."""

        try:
            data = json.loads(
                self._snapshot_json, parse_constant=_reject_nonfinite_constant
            )
        except PhysicsProfileError:
            raise
        except (TypeError, json.JSONDecodeError) as error:
            raise PhysicsProfileError(
                f"cannot construct PhysicsProfile from snapshot: {error}"
            ) from error
        data = _require_mapping(data, "profile")
        normalized = _validate_snapshot_data(
            data,
            expected_profile_id=self.profile_id,
            expected_canonical_hash=self.canonical_hash,
        )
        object.__setattr__(self, "_snapshot_json", normalized)

    @property
    def identity(self) -> dict[str, str]:
        return {
            "profile_id": self.profile_id,
            "canonical_hash": self.canonical_hash,
        }

    def expanded_snapshot(self) -> dict[str, Any]:
        """Return a detached JSON-serializable record for run/artifact metadata."""

        return json.loads(self._snapshot_json)


def available_profile_ids() -> tuple[str, ...]:
    """Return registered IDs in stable provenance order."""

    return tuple(_PROFILE_FILES)


def _canonical_payload(data: Mapping[str, Any]) -> bytes:
    payload = dict(data)
    payload.pop("canonical_hash", None)
    try:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise PhysicsProfileError(f"profile is not canonical JSON: {error}") from error
    return encoded.encode("utf-8")


def canonical_profile_hash(data: Mapping[str, Any]) -> str:
    """Hash a profile excluding its self-referential ``canonical_hash`` field."""

    return "sha256:" + hashlib.sha256(_canonical_payload(data)).hexdigest()


def _reject_nonfinite_constant(value: str) -> None:
    raise PhysicsProfileError(f"non-finite JSON constant is forbidden: {value}")


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PhysicsProfileError(f"{path} must be an object")
    return value


def _require_exact_fields(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise PhysicsProfileError(
            f"unknown field at {path}: {', '.join(sorted(unknown))}"
        )
    if missing:
        raise PhysicsProfileError(
            f"missing field at {path}: {', '.join(sorted(missing))}"
        )


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhysicsProfileError(f"{path} must be a non-empty string")
    return value


def _require_boolean(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise PhysicsProfileError(f"{path} must be a boolean")
    return value


def _require_number(
    value: Any, path: str, *, allow_none: bool = False, positive: bool = False
) -> float | int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhysicsProfileError(f"{path} must be a number")
    if not math.isfinite(value):
        raise PhysicsProfileError(f"{path} must be finite; non-finite values are forbidden")
    if positive and value <= 0:
        raise PhysicsProfileError(f"{path} must be positive")
    return value


def _validate_scalar_tree(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _require_string(key, f"{path} key")
            _validate_scalar_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_scalar_tree(child, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise PhysicsProfileError(f"{path} contains a non-finite value")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise PhysicsProfileError(f"{path} contains a non-JSON value")


def _validate_profile(data: Mapping[str, Any], expected_profile_id: str | None) -> None:
    _require_exact_fields(data, _TOP_LEVEL_FIELDS, "profile")
    _validate_scalar_tree(data, "profile")

    profile_id = _require_string(data["profile_id"], "profile.profile_id")
    if expected_profile_id is not None and profile_id != expected_profile_id:
        raise PhysicsProfileError(
            f"profile ID mismatch: expected {expected_profile_id!r}, found {profile_id!r}"
        )
    if profile_id not in _PROFILE_FILES:
        raise PhysicsProfileError(f"unknown profile ID: {profile_id}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise PhysicsProfileError(
            f"unsupported schema version: {data['schema_version']!r}"
        )

    for field in (
        "profile_version",
        "family",
        "route",
        "intended_use",
        "review_status",
        "coarse_graining_status",
        "nonlinear_fit_status",
        "angle_resolution_status",
    ):
        _require_string(data[field], f"profile.{field}")
    for field in ("biological_parameter_certified", "final_science_campaign_allowed"):
        _require_boolean(data[field], f"profile.{field}")

    for name, fields in _NESTED_FIELDS.items():
        nested = _require_mapping(data[name], f"profile.{name}")
        _require_exact_fields(nested, fields, f"profile.{name}")

    spacing = data["spacing"]
    _require_number(
        spacing["code_edge_rest_length_nm"],
        "profile.spacing.code_edge_rest_length_nm",
        positive=True,
    )
    for field in (
        "mapping_status",
        "candidate_two_edge_hypothesis",
        "candidate_angle_scaling",
    ):
        _require_string(spacing[field], f"profile.spacing.{field}")

    mass = data["mass"]
    _require_string(mass["status"], "profile.mass.status")
    _require_number(mass["value_ag"], "profile.mass.value_ag", allow_none=True, positive=True)
    _require_boolean(mass["physical_time_valid"], "profile.mass.physical_time_valid")

    units = data["units"]
    for field in set(_NESTED_FIELDS["units"]) - {
        "pN_per_nm_to_N_per_m",
        "pN_nm_to_J",
    }:
        _require_string(units[field], f"profile.units.{field}")
    _require_number(
        units["pN_per_nm_to_N_per_m"],
        "profile.units.pN_per_nm_to_N_per_m",
        positive=True,
    )
    _require_number(units["pN_nm_to_J"], "profile.units.pN_nm_to_J", positive=True)
    required_units = {
        "lammps_style": "nano",
        "energy": "pN nm",
        "force": "pN",
        "length": "nm",
        "angle_input": "degree",
        "angle_internal": "radian",
        "membrane_tension_internal": "pN/nm",
        "membrane_tension_summary": "N/m",
        "pN_per_nm_to_N_per_m": 0.001,
        "pN_nm_to_J": 1e-21,
    }
    if units != required_units:
        raise PhysicsProfileError("profile.units does not match the v2 2D nano contract")

    potentials = _require_mapping(data["potentials"], "profile.potentials")
    _require_exact_fields(potentials, set(_POTENTIAL_PARAMETER_FIELDS), "profile.potentials")
    expected_equations = {
        "harmonic_bond": "E=K*(r-r0)^2",
        "nonlinear_bond": "E=epsilon*(r-r0)^2/(lambda^2-(r-r0)^2)",
        "harmonic_angle": "E=K*(theta-theta0)^2",
    }
    expected_styles = {
        "harmonic_bond": "LAMMPS bond_style harmonic",
        "nonlinear_bond": "LAMMPS bond_style nonlinear",
        "harmonic_angle": "LAMMPS angle_style harmonic",
    }
    for name, parameter_fields in _POTENTIAL_PARAMETER_FIELDS.items():
        potential = _require_mapping(potentials[name], f"profile.potentials.{name}")
        _require_exact_fields(
            potential, _POTENTIAL_FIELDS, f"profile.potentials.{name}"
        )
        if potential["equation"] != expected_equations[name]:
            raise PhysicsProfileError(f"profile.potentials.{name}.equation is invalid")
        if potential["style"] != expected_styles[name]:
            raise PhysicsProfileError(f"profile.potentials.{name}.style is invalid")
        _require_string(potential["parameter_units"], f"profile.potentials.{name}.parameter_units")
        _require_string(potential["status"], f"profile.potentials.{name}.status")
        parameters = _require_mapping(
            potential["parameters"], f"profile.potentials.{name}.parameters"
        )
        _require_exact_fields(
            parameters, parameter_fields, f"profile.potentials.{name}.parameters"
        )
        for parameter_name, parameter_value in parameters.items():
            _require_number(
                parameter_value,
                f"profile.potentials.{name}.parameters.{parameter_name}",
                positive=True,
            )
        metadata = _require_mapping(
            potential["parameter_metadata"],
            f"profile.potentials.{name}.parameter_metadata",
        )
        _require_exact_fields(
            metadata, parameter_fields, f"profile.potentials.{name}.parameter_metadata"
        )
        for parameter_name, parameter_metadata in metadata.items():
            parameter_metadata = _require_mapping(
                parameter_metadata,
                f"profile.potentials.{name}.parameter_metadata.{parameter_name}",
            )
            _require_exact_fields(
                parameter_metadata,
                _PARAMETER_METADATA_FIELDS,
                f"profile.potentials.{name}.parameter_metadata.{parameter_name}",
            )
            if parameter_metadata != {
                "uncertainty_status": "unknown",
                "range_status": "not_reported",
                "range": None,
            }:
                raise PhysicsProfileError(
                    f"profile.potentials.{name}.parameter_metadata.{parameter_name} "
                    "must preserve unknown/not-reported uncertainty"
                )
        fit_artifact = _require_mapping(
            potential["fit_artifact"], f"profile.potentials.{name}.fit_artifact"
        )
        _require_exact_fields(
            fit_artifact,
            _FIT_ARTIFACT_FIELDS,
            f"profile.potentials.{name}.fit_artifact",
        )
        expected_fit_status = "unavailable" if name == "nonlinear_bond" else "not_applicable"
        if fit_artifact != {
            "artifact_status": expected_fit_status,
            "path": None,
            "sha256_status": expected_fit_status,
            "sha256": None,
        }:
            raise PhysicsProfileError(
                f"profile.potentials.{name}.fit_artifact must be explicit and unavailable"
            )

    for field in (
        "zero_tension_claim",
        "coordinates_required",
        "full_cell_matrix_required",
        "achieved_geometry_required",
        "minimization_diagnostics_required",
        "initial_tension_required",
    ):
        _require_boolean(data["reference_state"][field], f"profile.reference_state.{field}")
    for field in ("name", "cell_policy"):
        _require_string(data["reference_state"][field], f"profile.reference_state.{field}")
    historical = data["historical_execution"]
    if not isinstance(historical["entry_points"], list):
        raise PhysicsProfileError("profile.historical_execution.entry_points must be an array")
    for index, entry_point in enumerate(historical["entry_points"]):
        _require_string(
            entry_point, f"profile.historical_execution.entry_points[{index}]"
        )
    for field in (
        "scope",
        "loading_or_evaluation",
        "pressure_compute",
        "kinetic_term_semantics",
    ):
        _require_string(historical[field], f"profile.historical_execution.{field}")
    _require_boolean(
        historical["nve_deform_segment"],
        "profile.historical_execution.nve_deform_segment",
    )
    tangent = _require_mapping(
        historical["tangent_output"],
        "profile.historical_execution.tangent_output",
    )
    _require_exact_fields(
        tangent,
        _HISTORICAL_TANGENT_FIELDS,
        "profile.historical_execution.tangent_output",
    )
    _require_string(tangent["status"], "profile.historical_execution.tangent_output.status")
    for field in ("declared_tangent_unit", "dimensional_status"):
        if tangent[field] is not None:
            _require_string(
                tangent[field], f"profile.historical_execution.tangent_output.{field}"
            )
    _require_number(
        tangent["tangent_conversion_factor"],
        "profile.historical_execution.tangent_output.tangent_conversion_factor",
        allow_none=True,
        positive=True,
    )

    output_policy = data["required_new_output_policy"]
    _require_boolean(
        output_policy["kinetic_term_included"],
        "profile.required_new_output_policy.kinetic_term_included",
    )
    for field in set(_NESTED_FIELDS["required_new_output_policy"]) - {
        "kinetic_term_included"
    }:
        _require_string(
            output_policy[field], f"profile.required_new_output_policy.{field}"
        )
    for field in _NESTED_FIELDS["axes"]:
        _require_string(data["axes"][field], f"profile.axes.{field}")
    _require_string(
        data["dimensional_scope"]["native_quantity"],
        "profile.dimensional_scope.native_quantity",
    )
    _require_number(
        data["dimensional_scope"]["thickness_nm"],
        "profile.dimensional_scope.thickness_nm",
        allow_none=True,
        positive=True,
    )
    _require_boolean(
        data["dimensional_scope"]["stress_3d_allowed"],
        "profile.dimensional_scope.stress_3d_allowed",
    )
    _require_string(
        data["dimensional_scope"]["cylinder_display_label"],
        "profile.dimensional_scope.cylinder_display_label",
    )
    for field in (
        "status",
        "primary_endpoint",
        "deterministic_version",
        "heterogeneous_version",
        "threshold_visibility",
    ):
        _require_string(data["rupture_law"][field], f"profile.rupture_law.{field}")
    _require_boolean(
        data["rupture_law"]["fresh_lottery_per_step"],
        "profile.rupture_law.fresh_lottery_per_step",
    )
    for field in set(_NESTED_FIELDS["derived_numerical_facts"]) - {"status"}:
        _require_number(
            data["derived_numerical_facts"][field],
            f"profile.derived_numerical_facts.{field}",
            positive=True,
        )
    _require_string(
        data["derived_numerical_facts"]["status"],
        "profile.derived_numerical_facts.status",
    )
    review_requests = data["review_requests"]
    if not isinstance(review_requests, list):
        raise PhysicsProfileError("profile.review_requests must be an array")
    for index, request in enumerate(review_requests):
        request = _require_mapping(request, f"profile.review_requests[{index}]")
        _require_exact_fields(
            request, _REVIEW_REQUEST_FIELDS, f"profile.review_requests[{index}]"
        )
        for field in _REVIEW_REQUEST_FIELDS:
            _require_string(request[field], f"profile.review_requests[{index}].{field}")

    sources = data["sources"]
    if not isinstance(sources, list) or not sources:
        raise PhysicsProfileError("profile.sources must be a non-empty array")
    for index, source in enumerate(sources):
        source = _require_mapping(source, f"profile.sources[{index}]")
        _require_exact_fields(source, _SOURCE_FIELDS, f"profile.sources[{index}]")
        for field in _SOURCE_FIELDS:
            _require_string(source[field], f"profile.sources[{index}].{field}")
    source_locations = {source["citation_or_path"] for source in sources}
    missing_lammps_sources = _REQUIRED_LAMMPS_SOURCE_URLS - source_locations
    if missing_lammps_sources:
        raise PhysicsProfileError(
            "profile.sources lacks installed-version LAMMPS documentation: "
            + ", ".join(sorted(missing_lammps_sources))
        )

    provenance = data["provenance"]
    if not isinstance(provenance["source_routes"], list) or not provenance["source_routes"]:
        raise PhysicsProfileError("profile.provenance.source_routes must be non-empty")
    for index, route in enumerate(provenance["source_routes"]):
        _require_string(route, f"profile.provenance.source_routes[{index}]")
    for field in ("source_revision", "decision_record", "notes"):
        _require_string(provenance[field], f"profile.provenance.{field}")
    base_identity = provenance["provisional_base_identity"]
    if base_identity is not None:
        base_identity = _require_mapping(
            base_identity, "profile.provenance.provisional_base_identity"
        )
        _require_exact_fields(
            base_identity,
            {"profile_id", "canonical_hash"},
            "profile.provenance.provisional_base_identity",
        )
        _require_string(
            base_identity["profile_id"],
            "profile.provenance.provisional_base_identity.profile_id",
        )
        _require_string(
            base_identity["canonical_hash"],
            "profile.provenance.provisional_base_identity.canonical_hash",
        )

    if data["profile_id"] in {
        "legacy_python_2026_03_12_v1",
        "reviewed_physics_provisional_v0",
    }:
        required_current_sources = {
            "src/simulation_constants_settings.py",
            "src/units.py",
            "src/assemble_pg_network.py",
            "src/run_lammps_isotropic_strain.py",
            "src/run_lammps_elastic_tensor.py",
            "src/process_network_ensembles.py",
        }
        if not required_current_sources.issubset(set(provenance["source_routes"])):
            raise PhysicsProfileError(
                "current-route provenance must list every coefficient/unit/entrypoint source"
            )

    _validate_fixed_contract(data)
    _validate_route_numerics(data)


def _validate_fixed_contract(data: Mapping[str, Any]) -> None:
    required = {
        "biological_parameter_certified": False,
        "final_science_campaign_allowed": False,
        "coarse_graining_status": "unresolved",
        "nonlinear_fit_status": "unreproduced",
        "angle_resolution_status": "unreviewed",
    }
    for field, expected in required.items():
        if data[field] != expected:
            raise PhysicsProfileError(f"profile.{field} must remain {expected!r}")
    if data["spacing"]["candidate_angle_scaling"] != "not_frozen_pending_review":
        raise PhysicsProfileError("candidate angle scaling must not be frozen")
    if data["mass"]["physical_time_valid"] is not False:
        raise PhysicsProfileError("physical-time claims are forbidden")
    if data["reference_state"] != {
        "name": "fixed_cell_equilibrated",
        "cell_policy": "fixed_cell_coordinate_minimization",
        "zero_tension_claim": False,
        "coordinates_required": True,
        "full_cell_matrix_required": True,
        "achieved_geometry_required": True,
        "minimization_diagnostics_required": True,
        "initial_tension_required": True,
    }:
        raise PhysicsProfileError("reference_state does not match the fixed-cell contract")
    if data["required_new_output_policy"] != {
        "scope": "required_for_new_runs_and_reanalysis_not_historical_fact",
        "source": "configurational_virial",
        "kinetic_term_included": False,
        "dimensionality": "2D membrane force_per_length",
        "sign_convention": "positive_tension_equals_negative_LAMMPS_pressure",
        "primary": "total",
        "secondary": "incremental_from_reference",
    }:
        raise PhysicsProfileError(
            "required_new_output_policy does not match the v2 2D contract"
        )
    if data["axes"] != {
        "x": "axial",
        "y": "hoop",
        "laboratory_mapping_status": "dataset_specific_unconfirmed",
    }:
        raise PhysicsProfileError("axes do not match the computational convention")
    dimensional = data["dimensional_scope"]
    if dimensional["thickness_nm"] is not None or dimensional["stress_3d_allowed"] is not False:
        raise PhysicsProfileError("3D stress requires a separately approved thickness")
    if data["rupture_law"] != {
        "status": "phenomenological_provisional",
        "primary_endpoint": "damage_initiation",
        "deterministic_version": "not_configured",
        "heterogeneous_version": "not_configured",
        "threshold_visibility": "must_be_recorded_when_configured",
        "fresh_lottery_per_step": False,
    }:
        raise PhysicsProfileError("rupture_law does not match the provisional contract")

    expected_historical = {
        "legacy_python_2026_03_12_v1": {
            "scope": "historical_execution_provenance_not_new_output_policy",
            "entry_points": [
                "src/run_lammps_isotropic_strain.py::run_isotropic_prestrain_minimize",
                "src/run_lammps_isotropic_strain.py::run_isotropic_prestrain_nve",
                "src/run_lammps_elastic_tensor.py::lammps_calculate_elastic_tensor",
            ],
            "loading_or_evaluation": (
                "fixed_cell_minimize_route_plus_retained_nve_deform_route_and_"
                "elastic_minimize_route"
            ),
            "pressure_compute": "default_LAMMPS_thermo_pressure",
            "kinetic_term_semantics": (
                "default_pressure_includes_kinetic_and_virial_terms; minimize_run0_"
                "states_may_have_zero_velocity_but_the_retained_nve_deform_route_can_"
                "carry_kinetic_pressure"
            ),
            "nve_deform_segment": True,
            "tangent_output": {
                "status": "present_in_current_elastic_entry_point",
                "declared_tangent_unit": "MPa*nm",
                "tangent_conversion_factor": 1.0,
                "dimensional_status": "dimensionally_2d_but_legacy_label_deprecated",
            },
        },
        "legacy_direct_isotropic_pre_unit_fix_v1": {
            "scope": "historical_execution_provenance_not_new_output_policy",
            "entry_points": ["src/IsotropicPrestrain"],
            "loading_or_evaluation": "initial_minimize_then_nve_deform_then_minimize",
            "pressure_compute": "default_LAMMPS_thermo_pressure",
            "kinetic_term_semantics": (
                "default_pressure_includes_kinetic_and_virial_terms; the_nve_deform_"
                "segment_can_carry_kinetic_pressure"
            ),
            "nve_deform_segment": True,
            "tangent_output": {
                "status": "not_applicable",
                "declared_tangent_unit": None,
                "tangent_conversion_factor": None,
                "dimensional_status": "script_does_not_compute_tangent_output",
            },
        },
        "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": {
            "scope": "historical_execution_provenance_not_new_output_policy",
            "entry_points": [
                "ELASTIC_2D_ZERO_TEMP/PG_2D_main.elastic",
                "ELASTIC_2D_ZERO_TEMP/PG_2D_displace_deform.mod",
            ],
            "loading_or_evaluation": "central_deformations_using_nve_deform_then_minimize",
            "pressure_compute": "default_LAMMPS_thermo_pressure",
            "kinetic_term_semantics": (
                "default_pressure_includes_kinetic_and_virial_terms; velocities_from_"
                "nve_deform_are_not_explicitly_zeroed_before_post_deformation_pressure"
            ),
            "nve_deform_segment": True,
            "tangent_output": {
                "status": "present",
                "declared_tangent_unit": "GPa",
                "tangent_conversion_factor": 1.01325e-8,
                "dimensional_status": "known_invalid_3d_label_without_thickness",
            },
        },
        "reviewed_physics_provisional_v0": {
            "scope": "not_applicable_new_provisional_profile",
            "entry_points": [],
            "loading_or_evaluation": "not_executed_as_a_historical_route",
            "pressure_compute": "not_applicable",
            "kinetic_term_semantics": "not_applicable",
            "nve_deform_segment": False,
            "tangent_output": {
                "status": "not_applicable",
                "declared_tangent_unit": None,
                "tangent_conversion_factor": None,
                "dimensional_status": "new_profile_has_no_historical_output",
            },
        },
    }
    if data["historical_execution"] != expected_historical[data["profile_id"]]:
        raise PhysicsProfileError(
            f"historical execution semantics changed for {data['profile_id']}"
        )

    if data["profile_id"] == "reviewed_physics_provisional_v0":
        if data["review_status"] != "pending" or data["mass"]["status"] != "placeholder":
            raise PhysicsProfileError("the provisional reviewed profile must remain pending")
        expected_requests = [
            {
                "person": "Prof. Christoph Schmidt",
                "role": "proposed scientific reviewer",
                "status": "proposed_unconfirmed",
            },
            {
                "person": "Octavio",
                "role": "proposed inherited implementation and provenance checker",
                "status": "proposed_unconfirmed",
            },
        ]
        if data["review_requests"] != expected_requests:
            raise PhysicsProfileError("provisional reviewer requests must remain unconfirmed")
        if data["provenance"]["provisional_base_identity"] != {
            "profile_id": "legacy_python_2026_03_12_v1",
            "canonical_hash": _PROFILE_HASHES["legacy_python_2026_03_12_v1"],
        }:
            raise PhysicsProfileError(
                "provisional base identity must include the exact legacy ID and hash"
            )
    elif data["provenance"]["provisional_base_identity"] is not None:
        raise PhysicsProfileError(
            "legacy profiles must not declare a provisional base identity"
        )


def _validate_route_numerics(data: Mapping[str, Any]) -> None:
    expected = _ROUTE_NUMERICS[data["profile_id"]]
    actual = {
        "mass": data["mass"]["value_ag"],
        "harmonic_bond": (
            data["potentials"]["harmonic_bond"]["parameters"]["K_pN_per_nm"],
            data["potentials"]["harmonic_bond"]["parameters"]["r0_nm"],
        ),
        "nonlinear_bond": (
            data["potentials"]["nonlinear_bond"]["parameters"]["epsilon_pN_nm"],
            data["potentials"]["nonlinear_bond"]["parameters"]["r0_nm"],
            data["potentials"]["nonlinear_bond"]["parameters"]["lambda_nm"],
        ),
        "harmonic_angle": (
            data["potentials"]["harmonic_angle"]["parameters"]["K_pN_nm"],
            data["potentials"]["harmonic_angle"]["parameters"]["theta0_degrees"],
        ),
    }
    if actual != expected:
        raise PhysicsProfileError(
            f"route-specific inherited values changed for {data['profile_id']}"
        )

    K, r0 = actual["harmonic_bond"]
    epsilon, nonlinear_r0, lambd = actual["nonlinear_bond"]
    angle_K, _theta0 = actual["harmonic_angle"]
    expected_derived = {
        "one_edge_harmonic_tangent_pN_per_nm": 2 * K,
        "two_edge_series_tangent_pN_per_nm": K,
        "two_edge_series_rest_length_nm": 2 * r0,
        "nonlinear_local_tangent_pN_per_nm": 2 * epsilon / lambd**2,
        "nonlinear_extension_pole_nm": nonlinear_r0 + lambd,
        "angle_curvature_pN_nm_per_rad2": 2 * angle_K,
        "status": "mechanical_derivations_not_biological_certification",
    }
    if data["derived_numerical_facts"] != expected_derived:
        raise PhysicsProfileError("derived numerical facts are inconsistent with parameters")


def _validate_snapshot_data(
    data: Mapping[str, Any],
    *,
    expected_profile_id: str | None = None,
    expected_canonical_hash: str | None = None,
) -> str:
    declared_hash = data.get("canonical_hash")
    if not isinstance(declared_hash, str) or not _HASH_PATTERN.fullmatch(declared_hash):
        raise PhysicsProfileError("canonical_hash must be sha256:<64 lowercase hex digits>")
    computed_hash = canonical_profile_hash(data)
    if declared_hash != computed_hash:
        raise PhysicsProfileError(
            f"canonical hash mismatch: declared {declared_hash}, computed {computed_hash}"
        )
    if expected_canonical_hash is not None and declared_hash != expected_canonical_hash:
        raise PhysicsProfileError(
            "PhysicsProfile canonical_hash does not match its expanded snapshot"
        )

    _validate_profile(data, expected_profile_id)
    profile_id = data["profile_id"]
    pinned_hash = _PROFILE_HASHES[profile_id]
    if declared_hash != pinned_hash:
        raise PhysicsProfileError(
            f"registered hash mismatch for {profile_id}: expected {pinned_hash}, "
            f"found {declared_hash}"
        )
    return json.dumps(
        data,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def validate_expanded_profile_snapshot(snapshot: Mapping[str, Any]) -> PhysicsProfile:
    """Validate a persisted expanded snapshot and return a trusted profile."""

    try:
        normalized_input = json.loads(
            json.dumps(
                snapshot,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            parse_constant=_reject_nonfinite_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise PhysicsProfileError(
            f"expanded physics profile snapshot is not strict JSON: {error}"
        ) from error
    data = _require_mapping(normalized_input, "profile")
    snapshot_json = _validate_snapshot_data(data)
    return PhysicsProfile(data["profile_id"], data["canonical_hash"], snapshot_json)


def load_physics_profile_file(
    path: str | Path, *, expected_profile_id: str | None = None
) -> PhysicsProfile:
    """Load and validate a profile file, including its pinned canonical digest."""

    profile_path = Path(path)
    try:
        data = json.loads(
            profile_path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite_constant,
        )
    except PhysicsProfileError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PhysicsProfileError(f"cannot read physics profile {profile_path}: {error}") from error
    data = _require_mapping(data, "profile")

    snapshot_json = _validate_snapshot_data(
        data, expected_profile_id=expected_profile_id
    )
    return PhysicsProfile(data["profile_id"], data["canonical_hash"], snapshot_json)


def load_physics_profile(profile_id: str) -> PhysicsProfile:
    """Load a registered route-specific physics profile by immutable ID."""

    if profile_id not in _PROFILE_FILES:
        raise PhysicsProfileError(f"unknown profile ID: {profile_id}")
    return load_physics_profile_file(
        _CONFIG_DIRECTORY / _PROFILE_FILES[profile_id], expected_profile_id=profile_id
    )


def validate_profile_aggregation(
    profiles_or_snapshots: Sequence[PhysicsProfile | Mapping[str, Any]],
    *,
    comparison_mode: str | None = None,
) -> dict[str, str]:
    """Reject silent mixing; allow only a declared profile-stratified comparison."""

    if not profiles_or_snapshots:
        raise ProfileMixingError("at least one validated profile is required")
    grouped: dict[str, set[str]] = {}
    for index, candidate in enumerate(profiles_or_snapshots):
        try:
            if isinstance(candidate, PhysicsProfile):
                validated = validate_expanded_profile_snapshot(
                    candidate.expanded_snapshot()
                )
            elif isinstance(candidate, Mapping):
                validated = validate_expanded_profile_snapshot(candidate)
            else:
                raise PhysicsProfileError(
                    f"aggregation input {index} is neither a PhysicsProfile nor a snapshot"
                )
        except PhysicsProfileError as error:
            raise ProfileMixingError(
                "aggregation requires validated PhysicsProfile objects or complete "
                f"expanded snapshots; input {index} failed: {error}"
            ) from error
        grouped.setdefault(validated.profile_id, set()).add(validated.canonical_hash)

    conflicts = sorted(profile_id for profile_id, hashes in grouped.items() if len(hashes) > 1)
    if conflicts:
        raise ProfileMixingError(
            "profile ID has multiple hashes: " + ", ".join(conflicts)
        )

    verified: dict[str, str] = {}
    for profile_id, hashes in grouped.items():
        registered = load_physics_profile(profile_id)
        profile_hash = next(iter(hashes))
        if profile_hash != registered.canonical_hash:
            raise ProfileMixingError(
                f"identity hash does not match registered profile {profile_id}"
            )
        verified[profile_id] = profile_hash

    if len(verified) > 1 and comparison_mode != "stratified_by_profile":
        raise ProfileMixingError(
            "silent mixed-profile aggregation is forbidden; use "
            "comparison_mode='stratified_by_profile'"
        )
    if comparison_mode not in (None, "stratified_by_profile"):
        raise ProfileMixingError(f"unsupported comparison mode: {comparison_mode}")
    return verified
