"""Reproducible conditional replicas with sample-once material disorder.

P02-05 deliberately selects the already accepted P02-02 quenched-threshold
reference.  Material thresholds are delegated to ``materialize_thresholds``;
this module does not implement a second sampler.  The event RNG namespace is
recorded but unconsumed because no stochastic event-process law has been
validated for the quasi-static study.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
import re
from typing import Mapping, Sequence

from pgworld.physics.damage import DamageLaw, ThresholdField, materialize_thresholds


STOCHASTICITY_SCHEMA_VERSION = "pgworld.conditional_stochasticity.v1"
PREDICTOR_VIEW_SCHEMA_VERSION = "pgworld.stochasticity_predictor_view.v1"
RNG_NAMESPACE_VERSION = "pgworld-pg-rng-v1"
RNG_BACKEND = "p01_04_named_nonnegative_integer_seeds"
SEED_UNIT = "nonnegative_integer_seed"
MATERIAL_SAMPLING_BACKEND = "p02_02_keyed_sha256_u64"
MATERIAL_VARIATION_KIND = "quenched_threshold_field"
THRESHOLD_SAMPLING = "sample_once_per_physical_bond_then_frozen"
EVENT_PROCESS_DISABLED = "disabled_no_validated_hazard"
CONDITIONAL_DYNAMICS = "deterministic_given_frozen_threshold_field"
LOAD_COORDINATE_KIND = "quasi_static_not_physical_time"
_VARIATION_AXIS = "hidden_quenched_material_disorder"
_PREDICTOR_ACCESS = "predictor_input_allowlist"
_MATERIAL_STATE_SEMANTICS = "persistent_sample_once_material_disorder"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RNG_ROLES = ("geometry", "material_disorder", "events", "model_training")
_CRITERION_UNITS = {
    "bond_extension_ratio": "dimensionless",
    "bond_tension": "pN",
    "bond_energy": "pN nm",
}


class StochasticityValidationError(ValueError):
    """Raised when stochasticity/provenance records fail closed."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise StochasticityValidationError(
            f"{field} must be a nonempty trimmed string"
        )
    if any(ord(character) < 32 for character in value):
        raise StochasticityValidationError(
            f"{field} cannot contain control characters"
        )
    return value


def _digest(value: object, field: str) -> str:
    value = _text(value, field)
    if _HASH_RE.fullmatch(value) is None:
        raise StochasticityValidationError(
            f"{field} must be a lowercase sha256: digest"
        )
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StochasticityValidationError(
            f"{field} must be a nonnegative integer"
        )
    return value


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise StochasticityValidationError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise StochasticityValidationError(f"{field} must be finite")
    return result


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise StochasticityValidationError(f"{field} must be a boolean")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise StochasticityValidationError(f"{field} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise StochasticityValidationError(f"{field} keys must be strings")
    return value


def _exact_keys(
    value: Mapping[str, object], expected: set[str], field: str
) -> None:
    if any(not isinstance(key, str) for key in value):
        raise StochasticityValidationError(f"{field} keys must be strings")
    keys = set(value)
    missing = sorted(expected - keys)
    extra = sorted(keys - expected)
    if missing or extra:
        raise StochasticityValidationError(
            f"{field} keys mismatch; missing={missing}, unexpected={extra}"
        )


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise StochasticityValidationError(
            f"{field} must be a concrete non-string sequence"
        )
    return value


def _stable_ids(
    value: object, field: str, *, require_canonical: bool
) -> tuple[str, ...]:
    sequence = _sequence(value, field)
    identifiers = tuple(_text(item, field) for item in sequence)
    if not identifiers:
        raise StochasticityValidationError(f"{field} cannot be empty")
    if len(set(identifiers)) != len(identifiers):
        raise StochasticityValidationError(f"{field} contains duplicate stable IDs")
    canonical = tuple(sorted(identifiers))
    if require_canonical and identifiers != canonical:
        raise StochasticityValidationError(f"{field} must be in canonical order")
    return canonical


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _record_id(body: Mapping[str, object]) -> str:
    digest = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class RNGNamespaceRecord:
    """P01-04 namespace roles and integer seeds, without mutable RNG state."""

    namespace_id: str
    geometry_seed: int
    material_disorder_seed: int
    events_seed: int
    model_training_seed: int
    schema_version: str = STOCHASTICITY_SCHEMA_VERSION
    namespace_version: str = RNG_NAMESPACE_VERSION
    rng_backend: str = RNG_BACKEND
    seed_unit: str = SEED_UNIT

    def __post_init__(self) -> None:
        if self.schema_version != STOCHASTICITY_SCHEMA_VERSION:
            raise StochasticityValidationError("invalid stochasticity schema_version")
        if self.namespace_version != RNG_NAMESPACE_VERSION:
            raise StochasticityValidationError("invalid RNG namespace_version")
        if self.rng_backend != RNG_BACKEND:
            raise StochasticityValidationError("unsupported RNG namespace backend")
        if self.seed_unit != SEED_UNIT:
            raise StochasticityValidationError("invalid seed unit")
        for field in (
            "geometry_seed",
            "material_disorder_seed",
            "events_seed",
            "model_training_seed",
        ):
            object.__setattr__(self, field, _nonnegative_int(getattr(self, field), field))
        _digest(self.namespace_id, "namespace_id")
        if self.namespace_id != _record_id(self._body()):
            raise StochasticityValidationError(
                "namespace_id does not match the exact RNG namespace record"
            )

    @property
    def roles(self) -> tuple[str, ...]:
        return _RNG_ROLES

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "namespace_version": self.namespace_version,
            "rng_backend": self.rng_backend,
            "seed_unit": self.seed_unit,
            "geometry_seed": self.geometry_seed,
            "material_disorder_seed": self.material_disorder_seed,
            "events_seed": self.events_seed,
            "model_training_seed": self.model_training_seed,
        }

    def as_record(self) -> dict[str, object]:
        return {"namespace_id": self.namespace_id, **self._body()}

    def as_seed_mapping(self) -> dict[str, int]:
        return {
            "geometry": self.geometry_seed,
            "material_disorder": self.material_disorder_seed,
            "events": self.events_seed,
            "model_training": self.model_training_seed,
        }

    @classmethod
    def from_p01_04_mapping(
        cls, value: Mapping[str, object]
    ) -> "RNGNamespaceRecord":
        value = _mapping(value, "P01-04 seed mapping")
        _exact_keys(value, set(_RNG_ROLES), "P01-04 seed mapping")
        body = {
            "schema_version": STOCHASTICITY_SCHEMA_VERSION,
            "namespace_version": RNG_NAMESPACE_VERSION,
            "rng_backend": RNG_BACKEND,
            "seed_unit": SEED_UNIT,
            "geometry_seed": _nonnegative_int(value["geometry"], "geometry seed"),
            "material_disorder_seed": _nonnegative_int(
                value["material_disorder"], "material_disorder seed"
            ),
            "events_seed": _nonnegative_int(value["events"], "events seed"),
            "model_training_seed": _nonnegative_int(
                value["model_training"], "model_training seed"
            ),
        }
        return cls(namespace_id=_record_id(body), **body)

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "RNGNamespaceRecord":
        value = _mapping(value, "RNG namespace record")
        _exact_keys(
            value,
            {
                "namespace_id",
                "schema_version",
                "namespace_version",
                "rng_backend",
                "seed_unit",
                "geometry_seed",
                "material_disorder_seed",
                "events_seed",
                "model_training_seed",
            },
            "RNG namespace record",
        )
        return cls(**dict(value))  # type: ignore[arg-type]


def _validate_event_process(
    event_process_kind: object,
    events_seed_consumed: object,
    event_process_exposure_unit: object,
) -> None:
    if event_process_kind != EVENT_PROCESS_DISABLED:
        raise StochasticityValidationError(
            "event-process randomness is disabled: no validated hazard, rate, or probability law exists"
        )
    if _boolean(events_seed_consumed, "events_seed_consumed") is not False:
        raise StochasticityValidationError(
            "the reserved event seed must remain unconsumed"
        )
    if event_process_exposure_unit is not None:
        raise StochasticityValidationError(
            "event-process exposure unit must be null while the event process is disabled"
        )


@dataclass(frozen=True)
class ConditionalReplicate:
    """One hidden-material realization conditioned on one observable graph."""

    replicate_id: str
    cohort_id: str
    replicate_index: int
    parent_network_id: str
    graph_identity_hash: str
    geometry_realization_id: str
    conditioned_observable_state_id: str
    physical_bond_ids: tuple[str, ...]
    rng_namespace: RNGNamespaceRecord
    damage_law: DamageLaw
    threshold_field: ThresholdField
    law_id: str
    law_fingerprint: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    criterion: str
    criterion_unit: str
    predictor_visibility: str
    threshold_realization_id: str
    material_variation_kind: str = MATERIAL_VARIATION_KIND
    material_sampling_backend: str = MATERIAL_SAMPLING_BACKEND
    threshold_sampling: str = THRESHOLD_SAMPLING
    event_process_kind: str = EVENT_PROCESS_DISABLED
    events_seed_consumed: bool = False
    event_process_exposure_unit: None = None
    conditional_dynamics: str = CONDITIONAL_DYNAMICS
    load_coordinate_kind: str = LOAD_COORDINATE_KIND
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = STOCHASTICITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != STOCHASTICITY_SCHEMA_VERSION:
            raise StochasticityValidationError("invalid replicate schema_version")
        _text(self.cohort_id, "cohort_id")
        object.__setattr__(
            self, "replicate_index", _nonnegative_int(self.replicate_index, "replicate_index")
        )
        _text(self.parent_network_id, "parent_network_id")
        _digest(self.graph_identity_hash, "graph_identity_hash")
        _digest(self.geometry_realization_id, "geometry_realization_id")
        _digest(self.conditioned_observable_state_id, "conditioned_observable_state_id")
        object.__setattr__(
            self,
            "physical_bond_ids",
            _stable_ids(
                self.physical_bond_ids,
                "physical_bond_ids",
                require_canonical=True,
            ),
        )
        if not isinstance(self.rng_namespace, RNGNamespaceRecord):
            raise StochasticityValidationError(
                "rng_namespace must be a validated RNGNamespaceRecord"
            )
        if not isinstance(self.damage_law, DamageLaw):
            raise StochasticityValidationError("damage_law must be validated")
        if not isinstance(self.threshold_field, ThresholdField):
            raise StochasticityValidationError("threshold_field must be validated")
        if self.damage_law.law_kind != "quenched_heterogeneous_threshold":
            raise StochasticityValidationError(
                "conditional material replicas require a quenched heterogeneous threshold law"
            )
        law_pairs = (
            (self.law_id, self.damage_law.law_id, "law ID"),
            (self.law_fingerprint, self.damage_law.fingerprint, "law fingerprint"),
            (self.physics_profile_id, self.damage_law.physics_profile_id, "physics profile ID"),
            (self.physics_profile_hash, self.damage_law.physics_profile_hash, "physics profile hash"),
            (self.reference_state_id, self.damage_law.reference_state_id, "reference state"),
            (self.criterion, self.damage_law.criterion, "criterion"),
            (self.criterion_unit, self.damage_law.criterion_unit, "criterion unit"),
            (self.predictor_visibility, self.damage_law.predictor_visibility, "predictor visibility"),
            (
                self.threshold_realization_id,
                self.threshold_field.realization_id,
                "threshold realization",
            ),
        )
        for recorded, expected, label in law_pairs:
            if recorded != expected:
                raise StochasticityValidationError(
                    f"replicate {label} does not match the embedded law/field"
                )
        field_pairs = (
            (self.threshold_field.law_id, self.damage_law.law_id, "law ID"),
            (
                self.threshold_field.law_fingerprint,
                self.damage_law.fingerprint,
                "law fingerprint",
            ),
            (
                self.threshold_field.physics_profile_id,
                self.damage_law.physics_profile_id,
                "physics profile ID",
            ),
            (
                self.threshold_field.physics_profile_hash,
                self.damage_law.physics_profile_hash,
                "physics profile hash",
            ),
            (
                self.threshold_field.reference_state_id,
                self.damage_law.reference_state_id,
                "reference state",
            ),
            (self.threshold_field.criterion, self.damage_law.criterion, "criterion"),
            (
                self.threshold_field.criterion_unit,
                self.damage_law.criterion_unit,
                "criterion unit",
            ),
            (
                self.threshold_field.predictor_visibility,
                self.damage_law.predictor_visibility,
                "predictor visibility",
            ),
        )
        for recorded, expected, label in field_pairs:
            if recorded != expected:
                raise StochasticityValidationError(
                    f"threshold field {label} does not match the damage law"
                )
        if self.threshold_field.material_disorder_seed != self.rng_namespace.material_disorder_seed:
            raise StochasticityValidationError(
                "threshold-field material seed does not match the material_disorder namespace"
            )
        if tuple(self.threshold_field.thresholds) != self.physical_bond_ids:
            raise StochasticityValidationError(
                "threshold-field bond universe does not match physical_bond_ids"
            )
        canonical_field = materialize_thresholds(
            self.damage_law,
            self.physical_bond_ids,
            material_disorder_seed=self.rng_namespace.material_disorder_seed,
        )
        if self.threshold_field.as_record() != canonical_field.as_record():
            raise StochasticityValidationError(
                "threshold field is not the canonical P02-02 keyed-sampler output"
            )
        if self.material_variation_kind != MATERIAL_VARIATION_KIND:
            raise StochasticityValidationError("unsupported material variation kind")
        if self.material_sampling_backend != MATERIAL_SAMPLING_BACKEND:
            raise StochasticityValidationError(
                "material sampling backend must be the P02-02 keyed SHA-256/U64 policy"
            )
        if self.threshold_sampling != THRESHOLD_SAMPLING:
            raise StochasticityValidationError(
                "material thresholds must be sampled once then frozen"
            )
        if self.event_process_kind != EVENT_PROCESS_DISABLED:
            raise StochasticityValidationError(
                "event-process randomness is disabled in predictor views"
            )
        if self.event_process_exposure_unit is not None:
            raise StochasticityValidationError(
                "event-process exposure unit must be null in predictor views"
            )
        if self.conditional_dynamics != CONDITIONAL_DYNAMICS:
            raise StochasticityValidationError(
                "conditional dynamics must be deterministic given the frozen field"
            )
        if self.load_coordinate_kind != LOAD_COORDINATE_KIND:
            raise StochasticityValidationError(
                "replicate must use a quasi-static load coordinate"
            )
        if self.physical_time is not None or _boolean(
            self.physical_time_valid, "physical_time_valid"
        ) is not False:
            raise StochasticityValidationError(
                "physical time is invalid for the quasi-static stochasticity contract"
            )
        _digest(self.replicate_id, "replicate_id")
        if self.replicate_id != _record_id(self._body()):
            raise StochasticityValidationError(
                "replicate_id does not match the exact conditional-replicate record"
            )

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "replicate_index": self.replicate_index,
            "parent_network_id": self.parent_network_id,
            "graph_identity_hash": self.graph_identity_hash,
            "geometry_realization_id": self.geometry_realization_id,
            "conditioned_observable_state_id": self.conditioned_observable_state_id,
            "physical_bond_ids": list(self.physical_bond_ids),
            "rng_namespace": self.rng_namespace.as_record(),
            "damage_law": self.damage_law.as_record(),
            "threshold_field": self.threshold_field.as_record(),
            "law_id": self.law_id,
            "law_fingerprint": self.law_fingerprint,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "predictor_visibility": self.predictor_visibility,
            "threshold_realization_id": self.threshold_realization_id,
            "material_variation_kind": self.material_variation_kind,
            "material_sampling_backend": self.material_sampling_backend,
            "threshold_sampling": self.threshold_sampling,
            "event_process_kind": self.event_process_kind,
            "events_seed_consumed": self.events_seed_consumed,
            "event_process_exposure_unit": self.event_process_exposure_unit,
            "conditional_dynamics": self.conditional_dynamics,
            "load_coordinate_kind": self.load_coordinate_kind,
            "physical_time": self.physical_time,
            "physical_time_valid": self.physical_time_valid,
        }

    def as_record(self) -> dict[str, object]:
        return {"replicate_id": self.replicate_id, **self._body()}

    def predictor_view(self) -> "PredictorReplicateView":
        return PredictorReplicateView.create(self)

    @classmethod
    def create(
        cls,
        *,
        cohort_id: str,
        replicate_index: int,
        parent_network_id: str,
        graph_identity_hash: str,
        geometry_realization_id: str,
        conditioned_observable_state_id: str,
        physical_bond_ids: tuple[str, ...],
        rng_namespace: RNGNamespaceRecord,
        damage_law: DamageLaw,
        threshold_field: ThresholdField,
    ) -> "ConditionalReplicate":
        body = {
            "schema_version": STOCHASTICITY_SCHEMA_VERSION,
            "cohort_id": cohort_id,
            "replicate_index": replicate_index,
            "parent_network_id": parent_network_id,
            "graph_identity_hash": graph_identity_hash,
            "geometry_realization_id": geometry_realization_id,
            "conditioned_observable_state_id": conditioned_observable_state_id,
            "physical_bond_ids": list(physical_bond_ids),
            "rng_namespace": rng_namespace.as_record(),
            "damage_law": damage_law.as_record(),
            "threshold_field": threshold_field.as_record(),
            "law_id": damage_law.law_id,
            "law_fingerprint": damage_law.fingerprint,
            "physics_profile_id": damage_law.physics_profile_id,
            "physics_profile_hash": damage_law.physics_profile_hash,
            "reference_state_id": damage_law.reference_state_id,
            "criterion": damage_law.criterion,
            "criterion_unit": damage_law.criterion_unit,
            "predictor_visibility": damage_law.predictor_visibility,
            "threshold_realization_id": threshold_field.realization_id,
            "material_variation_kind": MATERIAL_VARIATION_KIND,
            "material_sampling_backend": MATERIAL_SAMPLING_BACKEND,
            "threshold_sampling": THRESHOLD_SAMPLING,
            "event_process_kind": EVENT_PROCESS_DISABLED,
            "events_seed_consumed": False,
            "event_process_exposure_unit": None,
            "conditional_dynamics": CONDITIONAL_DYNAMICS,
            "load_coordinate_kind": LOAD_COORDINATE_KIND,
            "physical_time": None,
            "physical_time_valid": False,
        }
        return cls(
            replicate_id=_record_id(body),
            cohort_id=cohort_id,
            replicate_index=replicate_index,
            parent_network_id=parent_network_id,
            graph_identity_hash=graph_identity_hash,
            geometry_realization_id=geometry_realization_id,
            conditioned_observable_state_id=conditioned_observable_state_id,
            physical_bond_ids=physical_bond_ids,
            rng_namespace=rng_namespace,
            damage_law=damage_law,
            threshold_field=threshold_field,
            law_id=damage_law.law_id,
            law_fingerprint=damage_law.fingerprint,
            physics_profile_id=damage_law.physics_profile_id,
            physics_profile_hash=damage_law.physics_profile_hash,
            reference_state_id=damage_law.reference_state_id,
            criterion=damage_law.criterion,
            criterion_unit=damage_law.criterion_unit,
            predictor_visibility=damage_law.predictor_visibility,
            threshold_realization_id=threshold_field.realization_id,
        )

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ConditionalReplicate":
        value = _mapping(value, "conditional replicate record")
        expected = {
            "replicate_id",
            "schema_version",
            "cohort_id",
            "replicate_index",
            "parent_network_id",
            "graph_identity_hash",
            "geometry_realization_id",
            "conditioned_observable_state_id",
            "physical_bond_ids",
            "rng_namespace",
            "damage_law",
            "threshold_field",
            "law_id",
            "law_fingerprint",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "criterion",
            "criterion_unit",
            "predictor_visibility",
            "threshold_realization_id",
            "material_variation_kind",
            "material_sampling_backend",
            "threshold_sampling",
            "event_process_kind",
            "events_seed_consumed",
            "event_process_exposure_unit",
            "conditional_dynamics",
            "load_coordinate_kind",
            "physical_time",
            "physical_time_valid",
        }
        _exact_keys(value, expected, "conditional replicate record")
        physical_bonds = _stable_ids(
            value["physical_bond_ids"],
            "physical_bond_ids",
            require_canonical=True,
        )
        kwargs = dict(value)
        kwargs["physical_bond_ids"] = physical_bonds
        kwargs["rng_namespace"] = RNGNamespaceRecord.from_record(
            _mapping(value["rng_namespace"], "rng_namespace")
        )
        kwargs["damage_law"] = DamageLaw.from_record(
            _mapping(value["damage_law"], "damage_law")
        )
        kwargs["threshold_field"] = ThresholdField.from_record(
            _mapping(value["threshold_field"], "threshold_field")
        )
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True)
class PredictorReplicateView:
    """Strict scientific-feature allowlist derived from one replicate."""

    projection_id: str
    criterion: str
    criterion_unit: str
    predictor_visibility: str
    threshold_values: tuple[tuple[str, str, float], ...] | None
    schema_version: str = PREDICTOR_VIEW_SCHEMA_VERSION
    access: str = _PREDICTOR_ACCESS
    material_state_semantics: str = _MATERIAL_STATE_SEMANTICS
    conditional_dynamics: str = CONDITIONAL_DYNAMICS
    event_process_kind: str = EVENT_PROCESS_DISABLED
    event_process_exposure_unit: None = None
    load_coordinate_kind: str = LOAD_COORDINATE_KIND
    physical_time_valid: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != PREDICTOR_VIEW_SCHEMA_VERSION:
            raise StochasticityValidationError("invalid predictor-view schema_version")
        if self.access != _PREDICTOR_ACCESS:
            raise StochasticityValidationError("predictor view must use the strict allowlist")
        if self.criterion not in _CRITERION_UNITS:
            raise StochasticityValidationError("unsupported predictor criterion")
        if self.criterion_unit != _CRITERION_UNITS[self.criterion]:
            raise StochasticityValidationError("predictor criterion unit mismatch")
        if self.predictor_visibility not in {
            "visible_to_predictor",
            "hidden_from_predictor",
        }:
            raise StochasticityValidationError("invalid predictor visibility")
        normalized: tuple[tuple[str, str, float], ...] | None
        if self.predictor_visibility == "hidden_from_predictor":
            if self.threshold_values is not None:
                raise StochasticityValidationError(
                    "hidden predictor view cannot contain threshold values"
                )
            normalized = None
        else:
            rows = _sequence(self.threshold_values, "threshold_values")
            built: list[tuple[str, str, float]] = []
            for index, raw in enumerate(rows):
                row = _sequence(raw, f"threshold_values[{index}]")
                if len(row) != 3:
                    raise StochasticityValidationError(
                        "threshold value row must contain bond ID, unit, and value"
                    )
                bond_id = _text(row[0], f"threshold_values[{index}].physical_bond_id")
                unit = _text(row[1], f"threshold_values[{index}].unit")
                if unit != self.criterion_unit:
                    raise StochasticityValidationError("visible threshold unit mismatch")
                value = _finite_float(row[2], f"threshold_values[{index}].value")
                if value <= 0.0:
                    raise StochasticityValidationError("visible thresholds must be positive")
                built.append((bond_id, unit, value))
            identifiers = tuple(row[0] for row in built)
            if identifiers != tuple(sorted(identifiers)) or len(set(identifiers)) != len(identifiers):
                raise StochasticityValidationError(
                    "visible threshold IDs must be unique and canonical"
                )
            normalized = tuple(built)
        object.__setattr__(self, "threshold_values", normalized)
        if self.material_state_semantics != _MATERIAL_STATE_SEMANTICS:
            raise StochasticityValidationError("invalid material-state semantics")
        if self.conditional_dynamics != CONDITIONAL_DYNAMICS:
            raise StochasticityValidationError("invalid conditional dynamics")
        if self.event_process_kind != EVENT_PROCESS_DISABLED:
            raise StochasticityValidationError(
                "event-process randomness is disabled in predictor views"
            )
        if self.event_process_exposure_unit is not None:
            raise StochasticityValidationError(
                "event-process exposure unit must be null in predictor views"
            )
        if self.load_coordinate_kind != LOAD_COORDINATE_KIND:
            raise StochasticityValidationError("predictor view cannot imply physical time")
        if _boolean(self.physical_time_valid, "physical_time_valid") is not False:
            raise StochasticityValidationError("predictor view cannot imply physical time")
        _digest(self.projection_id, "projection_id")
        if self.projection_id != _record_id(self._body()):
            raise StochasticityValidationError(
                "projection_id does not match the exact predictor allowlist"
            )

    def _body(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": self.schema_version,
            "access": self.access,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "predictor_visibility": self.predictor_visibility,
            "material_state_semantics": self.material_state_semantics,
            "conditional_dynamics": self.conditional_dynamics,
            "event_process_kind": self.event_process_kind,
            "event_process_exposure_unit": self.event_process_exposure_unit,
            "load_coordinate_kind": self.load_coordinate_kind,
            "physical_time_valid": self.physical_time_valid,
        }
        if self.threshold_values is not None:
            body["threshold_values"] = [
                {"physical_bond_id": bond_id, "unit": unit, "value": value}
                for bond_id, unit, value in self.threshold_values
            ]
        return body

    def as_record(self) -> dict[str, object]:
        return {"projection_id": self.projection_id, **self._body()}

    @classmethod
    def create(cls, replicate: ConditionalReplicate) -> "PredictorReplicateView":
        if not isinstance(replicate, ConditionalReplicate):
            raise StochasticityValidationError(
                "predictor view parent must be a validated ConditionalReplicate"
            )
        values = None
        if replicate.predictor_visibility == "visible_to_predictor":
            values = tuple(
                (
                    bond_id,
                    replicate.criterion_unit,
                    replicate.threshold_field.threshold_for(bond_id),
                )
                for bond_id in replicate.physical_bond_ids
            )
        prototype = {
            "schema_version": PREDICTOR_VIEW_SCHEMA_VERSION,
            "access": _PREDICTOR_ACCESS,
            "criterion": replicate.criterion,
            "criterion_unit": replicate.criterion_unit,
            "predictor_visibility": replicate.predictor_visibility,
            "material_state_semantics": _MATERIAL_STATE_SEMANTICS,
            "conditional_dynamics": CONDITIONAL_DYNAMICS,
            "event_process_kind": EVENT_PROCESS_DISABLED,
            "event_process_exposure_unit": None,
            "load_coordinate_kind": LOAD_COORDINATE_KIND,
            "physical_time_valid": False,
        }
        if values is not None:
            prototype["threshold_values"] = [
                {"physical_bond_id": bond_id, "unit": unit, "value": value}
                for bond_id, unit, value in values
            ]
        return cls(
            projection_id=_record_id(prototype),
            criterion=replicate.criterion,
            criterion_unit=replicate.criterion_unit,
            predictor_visibility=replicate.predictor_visibility,
            threshold_values=values,
        )

    def validate_against(self, parent: ConditionalReplicate) -> None:
        expected = self.create(parent)
        if self.as_record() != expected.as_record():
            raise StochasticityValidationError(
                "predictor projection is not exactly derived from replicate"
            )

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "PredictorReplicateView":
        value = _mapping(value, "predictor replicate view")
        visibility = value.get("predictor_visibility")
        base = {
            "projection_id",
            "schema_version",
            "access",
            "criterion",
            "criterion_unit",
            "predictor_visibility",
            "material_state_semantics",
            "conditional_dynamics",
            "event_process_kind",
            "event_process_exposure_unit",
            "load_coordinate_kind",
            "physical_time_valid",
        }
        expected = base | ({"threshold_values"} if visibility == "visible_to_predictor" else set())
        _exact_keys(value, expected, "predictor replicate view")
        threshold_values = None
        if "threshold_values" in value:
            rows = _sequence(value["threshold_values"], "threshold_values")
            built = []
            for index, raw in enumerate(rows):
                row = _mapping(raw, f"threshold_values[{index}]")
                _exact_keys(
                    row,
                    {"physical_bond_id", "unit", "value"},
                    f"threshold_values[{index}]",
                )
                built.append(
                    (row["physical_bond_id"], row["unit"], row["value"])
                )
            threshold_values = tuple(built)
        kwargs = dict(value)
        kwargs["threshold_values"] = threshold_values
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ConditionalReplicateCohort:
    """Canonical cohort varying hidden material disorder and nothing else."""

    cohort_record_id: str
    cohort_id: str
    replicates: tuple[ConditionalReplicate, ...]
    parent_network_id: str
    graph_identity_hash: str
    geometry_realization_id: str
    conditioned_observable_state_id: str
    physical_bond_ids: tuple[str, ...]
    law_id: str
    law_fingerprint: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    criterion: str
    criterion_unit: str
    predictor_visibility: str
    variation_axis: str = _VARIATION_AXIS
    material_sampling_backend: str = MATERIAL_SAMPLING_BACKEND
    event_process_kind: str = EVENT_PROCESS_DISABLED
    events_seed_consumed: bool = False
    event_process_exposure_unit: None = None
    load_coordinate_kind: str = LOAD_COORDINATE_KIND
    physical_time_valid: bool = False
    schema_version: str = STOCHASTICITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != STOCHASTICITY_SCHEMA_VERSION:
            raise StochasticityValidationError("invalid cohort schema_version")
        _text(self.cohort_id, "cohort_id")
        rows = _sequence(self.replicates, "replicates")
        if any(not isinstance(row, ConditionalReplicate) for row in rows):
            raise StochasticityValidationError(
                "replicates must contain validated ConditionalReplicate records"
            )
        replicates = tuple(rows)  # type: ignore[arg-type]
        if len(replicates) < 2:
            raise StochasticityValidationError(
                "conditional material cohort requires at least two replicates"
            )
        indices = tuple(row.replicate_index for row in replicates)
        if len(set(indices)) != len(indices):
            raise StochasticityValidationError("replicate indices must be unique")
        if indices != tuple(sorted(indices)):
            raise StochasticityValidationError("replicates must be in canonical index order")
        if indices != tuple(range(len(replicates))):
            raise StochasticityValidationError(
                "replicate indices must be contiguous from zero"
            )
        object.__setattr__(self, "replicates", replicates)
        first = replicates[0]
        graph_values = (
            self.parent_network_id,
            self.graph_identity_hash,
            self.geometry_realization_id,
            self.conditioned_observable_state_id,
        )
        expected_graph = (
            first.parent_network_id,
            first.graph_identity_hash,
            first.geometry_realization_id,
            first.conditioned_observable_state_id,
        )
        if graph_values != expected_graph:
            raise StochasticityValidationError("cohort observable graph identity mismatch")
        object.__setattr__(
            self,
            "physical_bond_ids",
            _stable_ids(
                self.physical_bond_ids,
                "physical_bond_ids",
                require_canonical=True,
            ),
        )
        if self.physical_bond_ids != first.physical_bond_ids:
            raise StochasticityValidationError("cohort bond universe mismatch")
        law_values = (
            self.law_id,
            self.law_fingerprint,
            self.physics_profile_id,
            self.physics_profile_hash,
            self.reference_state_id,
            self.criterion,
            self.criterion_unit,
            self.predictor_visibility,
        )
        expected_law = (
            first.law_id,
            first.law_fingerprint,
            first.physics_profile_id,
            first.physics_profile_hash,
            first.reference_state_id,
            first.criterion,
            first.criterion_unit,
            first.predictor_visibility,
        )
        if law_values != expected_law:
            raise StochasticityValidationError(
                "cohort law/profile/reference/criterion identity mismatch"
            )
        if self.predictor_visibility != "hidden_from_predictor":
            raise StochasticityValidationError(
                "hidden material-disorder cohorts require hidden_from_predictor thresholds"
            )
        for row in replicates:
            if row.cohort_id != self.cohort_id:
                raise StochasticityValidationError("replicate cohort_id mismatch")
            if (
                row.parent_network_id,
                row.graph_identity_hash,
                row.geometry_realization_id,
                row.conditioned_observable_state_id,
            ) != expected_graph:
                raise StochasticityValidationError(
                    "conditional cohort cannot mix the observable graph or geometry realization"
                )
            if row.physical_bond_ids != self.physical_bond_ids:
                raise StochasticityValidationError("conditional cohort bond universe mismatch")
            if (
                row.law_id,
                row.law_fingerprint,
                row.physics_profile_id,
                row.physics_profile_hash,
                row.reference_state_id,
                row.criterion,
                row.criterion_unit,
                row.predictor_visibility,
            ) != expected_law:
                raise StochasticityValidationError(
                    "conditional cohort law/profile/reference identity mismatch"
                )
            if (
                row.rng_namespace.geometry_seed
                != first.rng_namespace.geometry_seed
                or row.rng_namespace.events_seed
                != first.rng_namespace.events_seed
                or row.rng_namespace.model_training_seed
                != first.rng_namespace.model_training_seed
            ):
                raise StochasticityValidationError(
                    "conditional material cohort may vary only material_disorder seed"
                )
        material_seeds = tuple(
            row.rng_namespace.material_disorder_seed for row in replicates
        )
        if len(set(material_seeds)) != len(material_seeds):
            raise StochasticityValidationError(
                "conditional cohort material_disorder seeds must be unique"
            )
        for field, label in (
            ((row.replicate_id for row in replicates), "replicate IDs"),
            (
                (row.threshold_realization_id for row in replicates),
                "threshold realizations",
            ),
        ):
            values = tuple(field)
            if len(set(values)) != len(values):
                raise StochasticityValidationError(
                    f"conditional cohort {label} must be unique"
                )
        if self.variation_axis != _VARIATION_AXIS:
            raise StochasticityValidationError(
                "conditional cohort variation axis must be hidden material disorder"
            )
        if self.material_sampling_backend != MATERIAL_SAMPLING_BACKEND:
            raise StochasticityValidationError("cohort material sampling backend mismatch")
        _validate_event_process(
            self.event_process_kind,
            self.events_seed_consumed,
            self.event_process_exposure_unit,
        )
        if self.load_coordinate_kind != LOAD_COORDINATE_KIND:
            raise StochasticityValidationError("cohort cannot imply physical time")
        if _boolean(self.physical_time_valid, "physical_time_valid") is not False:
            raise StochasticityValidationError("cohort cannot imply physical time")
        _digest(self.cohort_record_id, "cohort_record_id")
        if self.cohort_record_id != _record_id(self._body()):
            raise StochasticityValidationError(
                "cohort_record_id does not match the exact conditional cohort"
            )

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "replicates": [replicate.as_record() for replicate in self.replicates],
            "parent_network_id": self.parent_network_id,
            "graph_identity_hash": self.graph_identity_hash,
            "geometry_realization_id": self.geometry_realization_id,
            "conditioned_observable_state_id": self.conditioned_observable_state_id,
            "physical_bond_ids": list(self.physical_bond_ids),
            "law_id": self.law_id,
            "law_fingerprint": self.law_fingerprint,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "predictor_visibility": self.predictor_visibility,
            "variation_axis": self.variation_axis,
            "material_sampling_backend": self.material_sampling_backend,
            "event_process_kind": self.event_process_kind,
            "events_seed_consumed": self.events_seed_consumed,
            "event_process_exposure_unit": self.event_process_exposure_unit,
            "load_coordinate_kind": self.load_coordinate_kind,
            "physical_time_valid": self.physical_time_valid,
        }

    def as_record(self) -> dict[str, object]:
        return {"cohort_record_id": self.cohort_record_id, **self._body()}

    @classmethod
    def create(cls, replicates: Sequence[ConditionalReplicate]) -> "ConditionalReplicateCohort":
        rows = _sequence(replicates, "replicates")
        if any(not isinstance(row, ConditionalReplicate) for row in rows):
            raise StochasticityValidationError(
                "replicates must contain validated ConditionalReplicate records"
            )
        canonical = tuple(sorted(rows, key=lambda row: row.replicate_index))  # type: ignore[union-attr]
        if not canonical:
            raise StochasticityValidationError("replicates cannot be empty")
        first = canonical[0]
        body = {
            "schema_version": STOCHASTICITY_SCHEMA_VERSION,
            "cohort_id": first.cohort_id,
            "replicates": [row.as_record() for row in canonical],
            "parent_network_id": first.parent_network_id,
            "graph_identity_hash": first.graph_identity_hash,
            "geometry_realization_id": first.geometry_realization_id,
            "conditioned_observable_state_id": first.conditioned_observable_state_id,
            "physical_bond_ids": list(first.physical_bond_ids),
            "law_id": first.law_id,
            "law_fingerprint": first.law_fingerprint,
            "physics_profile_id": first.physics_profile_id,
            "physics_profile_hash": first.physics_profile_hash,
            "reference_state_id": first.reference_state_id,
            "criterion": first.criterion,
            "criterion_unit": first.criterion_unit,
            "predictor_visibility": first.predictor_visibility,
            "variation_axis": _VARIATION_AXIS,
            "material_sampling_backend": MATERIAL_SAMPLING_BACKEND,
            "event_process_kind": EVENT_PROCESS_DISABLED,
            "events_seed_consumed": False,
            "event_process_exposure_unit": None,
            "load_coordinate_kind": LOAD_COORDINATE_KIND,
            "physical_time_valid": False,
        }
        return cls(
            cohort_record_id=_record_id(body),
            cohort_id=first.cohort_id,
            replicates=canonical,
            parent_network_id=first.parent_network_id,
            graph_identity_hash=first.graph_identity_hash,
            geometry_realization_id=first.geometry_realization_id,
            conditioned_observable_state_id=first.conditioned_observable_state_id,
            physical_bond_ids=first.physical_bond_ids,
            law_id=first.law_id,
            law_fingerprint=first.law_fingerprint,
            physics_profile_id=first.physics_profile_id,
            physics_profile_hash=first.physics_profile_hash,
            reference_state_id=first.reference_state_id,
            criterion=first.criterion,
            criterion_unit=first.criterion_unit,
            predictor_visibility=first.predictor_visibility,
        )

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ConditionalReplicateCohort":
        value = _mapping(value, "conditional replicate cohort")
        expected = {
            "cohort_record_id",
            "schema_version",
            "cohort_id",
            "replicates",
            "parent_network_id",
            "graph_identity_hash",
            "geometry_realization_id",
            "conditioned_observable_state_id",
            "physical_bond_ids",
            "law_id",
            "law_fingerprint",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "criterion",
            "criterion_unit",
            "predictor_visibility",
            "variation_axis",
            "material_sampling_backend",
            "event_process_kind",
            "events_seed_consumed",
            "event_process_exposure_unit",
            "load_coordinate_kind",
            "physical_time_valid",
        }
        _exact_keys(value, expected, "conditional replicate cohort")
        raw_rows = _sequence(value["replicates"], "replicates")
        rows = tuple(
            ConditionalReplicate.from_record(
                _mapping(row, f"replicates[{index}]")
            )
            for index, row in enumerate(raw_rows)
        )
        kwargs = dict(value)
        kwargs["replicates"] = rows
        kwargs["physical_bond_ids"] = _stable_ids(
            value["physical_bond_ids"],
            "physical_bond_ids",
            require_canonical=True,
        )
        return cls(**kwargs)  # type: ignore[arg-type]


def build_quenched_replicate(
    *,
    cohort_id: str,
    replicate_index: int,
    parent_network_id: str,
    graph_identity_hash: str,
    geometry_realization_id: str,
    conditioned_observable_state_id: str,
    physical_bond_ids: Sequence[object],
    rng_namespace: RNGNamespaceRecord,
    law: DamageLaw,
    event_process_kind: str = EVENT_PROCESS_DISABLED,
) -> ConditionalReplicate:
    """Materialize one P02-02 field; never consume the reserved event seed."""

    _validate_event_process(event_process_kind, False, None)
    if not isinstance(rng_namespace, RNGNamespaceRecord):
        raise StochasticityValidationError(
            "rng_namespace must be a validated RNGNamespaceRecord"
        )
    if not isinstance(law, DamageLaw):
        raise StochasticityValidationError("law must be a validated DamageLaw")
    if law.law_kind != "quenched_heterogeneous_threshold":
        raise StochasticityValidationError(
            "conditional material replicas require a quenched heterogeneous threshold law"
        )
    canonical_bonds = _stable_ids(
        physical_bond_ids, "physical_bond_ids", require_canonical=False
    )
    field = materialize_thresholds(
        law,
        canonical_bonds,
        material_disorder_seed=rng_namespace.material_disorder_seed,
    )
    return ConditionalReplicate.create(
        cohort_id=cohort_id,
        replicate_index=replicate_index,
        parent_network_id=parent_network_id,
        graph_identity_hash=graph_identity_hash,
        geometry_realization_id=geometry_realization_id,
        conditioned_observable_state_id=conditioned_observable_state_id,
        physical_bond_ids=canonical_bonds,
        rng_namespace=rng_namespace,
        damage_law=law,
        threshold_field=field,
    )


def build_conditional_material_cohort(
    replicates: Sequence[ConditionalReplicate],
) -> ConditionalReplicateCohort:
    """Build a fixed-observable cohort varying hidden material disorder only."""

    return ConditionalReplicateCohort.create(replicates)


__all__ = [
    "CONDITIONAL_DYNAMICS",
    "EVENT_PROCESS_DISABLED",
    "MATERIAL_SAMPLING_BACKEND",
    "STOCHASTICITY_SCHEMA_VERSION",
    "ConditionalReplicate",
    "ConditionalReplicateCohort",
    "PredictorReplicateView",
    "RNGNamespaceRecord",
    "StochasticityValidationError",
    "build_conditional_material_cohort",
    "build_quenched_replicate",
]
