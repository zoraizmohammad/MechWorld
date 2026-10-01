"""Phenomenological quasi-static damage and failure-endpoint contract.

This module deliberately does not mutate a LAMMPS topology or run a cascade.
It defines the solver-independent reference law and immutable event semantics
that those later operations must consume.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
import re
from types import MappingProxyType
from typing import Mapping, Sequence


DAMAGE_SCHEMA_VERSION = "pgworld.quasistatic_damage.v1"
_LOAD_COORDINATE_KIND = "quasi_static_not_physical_time"
_MECHANISM_CLAIM = (
    "phenomenological_not_experimentally_constrained_molecular_cleavage"
)
_SAMPLING_SEMANTICS = "sample_once_per_physical_bond_then_frozen"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CRITERION_UNITS = {
    "bond_extension_ratio": "dimensionless",
    "bond_tension": "pN",
    "bond_energy": "pN nm",
}
_LOAD_UNITS = {"dimensionless", "pN/nm^2"}
_PROGRESS_SEMANTICS = "cumulative_absolute_lambda_increment"
_ASSESSMENT_PHASES = {
    "accepted_equilibrium",
    "reference_preparation",
    "rejected_numerical_trial",
    "solver_error",
}
_ENDPOINT_EVIDENCE = {
    "damage_initiation": "accepted_material_rupture",
    "load_bearing_connectivity_loss": (
        "predeclared_load_bearing_connectivity_analysis"
    ),
    "load_or_stiffness_degradation": (
        "predeclared_load_or_stiffness_criterion"
    ),
    "mechanical_instability": "predeclared_mechanical_stability_criterion",
}


class DamageValidationError(ValueError):
    """Raised when damage/event records violate the frozen contract."""


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise DamageValidationError(f"{field} must be a nonempty trimmed string")
    if any(ord(character) < 32 for character in value):
        raise DamageValidationError(f"{field} cannot contain control characters")
    return value


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise DamageValidationError(f"{field} must be a finite real number")
    number = float(value)
    if not math.isfinite(number):
        raise DamageValidationError(f"{field} must be finite")
    return number


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DamageValidationError(f"{field} must be a nonnegative integer")
    return value


def _exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise DamageValidationError(f"{field} must be a boolean")
    return value


def _profile_hash(value: object) -> str:
    value = _nonempty_string(value, "physics_profile_hash")
    if _HASH_RE.fullmatch(value) is None:
        raise DamageValidationError(
            "physics_profile_hash must be a lowercase sha256: digest"
        )
    return value


def _registered_profile_identity(profile_id: object, profile_hash: object) -> None:
    profile_id = _nonempty_string(profile_id, "physics_profile_id")
    profile_hash = _profile_hash(profile_hash)
    try:
        from pgworld.config.physics_profiles import (
            PhysicsProfileError,
            load_physics_profile,
        )

        registered = load_physics_profile(profile_id)
    except (ImportError, PhysicsProfileError) as error:
        raise DamageValidationError(
            "physics profile must be a registered physics profile identity/hash pair"
        ) from error
    if registered.canonical_hash != profile_hash:
        raise DamageValidationError(
            "physics profile must be a registered physics profile identity/hash pair"
        )


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DamageValidationError(f"{field} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise DamageValidationError(f"{field} keys must be strings")
    return value


def _exact_keys(
    value: Mapping[str, object], expected: set[str], field: str
) -> None:
    if any(not isinstance(key, str) for key in value):
        raise DamageValidationError(f"{field} keys must be strings")
    keys = set(value)
    missing = sorted(expected - keys)
    extra = sorted(keys - expected)
    if missing or extra:
        raise DamageValidationError(
            f"{field} keys mismatch; missing={missing}, unexpected={extra}"
        )


def _stable_ids(values: Sequence[object], field: str) -> tuple[str, ...]:
    if (
        isinstance(values, (str, bytes, Mapping))
        or not isinstance(values, Sequence)
    ):
        raise DamageValidationError(f"{field} must be a sequence of stable IDs")
    identifiers = tuple(_nonempty_string(value, field) for value in values)
    if len(set(identifiers)) != len(identifiers):
        raise DamageValidationError(f"{field} contains duplicate stable IDs")
    return identifiers


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_record(value: object) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _freeze_mapping(
    value: Mapping[str, object], field: str
) -> Mapping[str, object]:
    frozen: dict[str, object] = {}
    for key, item in value.items():
        key = _nonempty_string(key, f"{field} key")
        if isinstance(item, Mapping):
            frozen[key] = _freeze_mapping(item, f"{field}.{key}")
        elif isinstance(item, list):
            frozen[key] = tuple(item)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _validate_identity_match(
    *,
    profile_id: str,
    profile_hash: str,
    reference_state_id: str,
    expected_profile_id: str,
    expected_profile_hash: str,
    expected_reference_state_id: str,
    context: str,
) -> None:
    if (
        profile_id != expected_profile_id
        or profile_hash != expected_profile_hash
        or reference_state_id != expected_reference_state_id
    ):
        raise DamageValidationError(
            f"{context} cannot mix physics profile identity/hash or reference state"
        )


@dataclass(frozen=True)
class DamageLaw:
    """Versioned deterministic or quenched-threshold reference law."""

    law_id: str
    law_kind: str
    criterion: str
    criterion_unit: str
    base_threshold: float
    distribution: Mapping[str, object] | None
    predictor_visibility: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    schema_version: str = DAMAGE_SCHEMA_VERSION
    load_coordinate_kind: str = _LOAD_COORDINATE_KIND
    physical_time_valid: bool = False
    accepted_event_source: str = "material_rupture"
    mechanism_claim: str = _MECHANISM_CLAIM
    threshold_sampling: str = _SAMPLING_SEMANTICS

    def __post_init__(self) -> None:
        _nonempty_string(self.law_id, "law_id")
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError(
                f"schema_version must equal {DAMAGE_SCHEMA_VERSION!r}"
            )
        if self.law_kind not in {
            "deterministic_threshold",
            "quenched_heterogeneous_threshold",
        }:
            raise DamageValidationError("unsupported law_kind")
        if self.criterion not in _CRITERION_UNITS:
            raise DamageValidationError("unsupported damage criterion")
        if self.criterion_unit != _CRITERION_UNITS[self.criterion]:
            raise DamageValidationError(
                f"criterion_unit must be {_CRITERION_UNITS[self.criterion]!r}"
            )
        threshold = _finite_float(self.base_threshold, "base_threshold")
        if threshold <= 0.0:
            raise DamageValidationError("base_threshold must be positive")
        object.__setattr__(self, "base_threshold", threshold)

        if self.law_kind == "deterministic_threshold":
            if self.distribution is not None:
                raise DamageValidationError(
                    "deterministic_threshold cannot define a distribution"
                )
        else:
            distribution = _mapping(self.distribution, "distribution")
            _exact_keys(
                distribution,
                {"kind", "relative_half_width"},
                "distribution",
            )
            if distribution["kind"] != "uniform_relative":
                raise DamageValidationError(
                    "quenched threshold distribution must be uniform_relative"
                )
            width = _finite_float(
                distribution["relative_half_width"],
                "distribution.relative_half_width",
            )
            if not 0.0 < width < 1.0:
                raise DamageValidationError(
                    "relative_half_width must be strictly between zero and one"
                )
            object.__setattr__(
                self,
                "distribution",
                MappingProxyType(
                    {"kind": "uniform_relative", "relative_half_width": width}
                ),
            )

        if self.predictor_visibility not in {
            "visible_to_predictor",
            "hidden_from_predictor",
        }:
            raise DamageValidationError(
                "predictor_visibility must explicitly be visible or hidden"
            )
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.load_coordinate_kind != _LOAD_COORDINATE_KIND:
            raise DamageValidationError(
                "damage law must use a quasi-static, non-time load coordinate"
            )
        if self.physical_time_valid is not False:
            raise DamageValidationError("physical time is invalid for this law")
        if self.accepted_event_source != "material_rupture":
            raise DamageValidationError(
                "accepted_event_source must be material_rupture"
            )
        if self.mechanism_claim != _MECHANISM_CLAIM:
            raise DamageValidationError(
                "law cannot claim an experimentally confirmed cleavage mechanism"
            )
        if self.threshold_sampling != _SAMPLING_SEMANTICS:
            raise DamageValidationError(
                "thresholds must be sampled once per bond and frozen"
            )

    @property
    def fingerprint(self) -> str:
        return _sha256_record(self.as_record())

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "law_id": self.law_id,
            "law_kind": self.law_kind,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "base_threshold": self.base_threshold,
            "distribution": _plain(self.distribution),
            "predictor_visibility": self.predictor_visibility,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "load_coordinate_kind": self.load_coordinate_kind,
            "physical_time_valid": self.physical_time_valid,
            "accepted_event_source": self.accepted_event_source,
            "mechanism_claim": self.mechanism_claim,
            "threshold_sampling": self.threshold_sampling,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "DamageLaw":
        value = _mapping(value, "damage law record")
        _exact_keys(value, set(cls._record_keys()), "damage law record")
        return cls(**dict(value))  # type: ignore[arg-type]

    @staticmethod
    def _record_keys() -> tuple[str, ...]:
        return (
            "schema_version",
            "law_id",
            "law_kind",
            "criterion",
            "criterion_unit",
            "base_threshold",
            "distribution",
            "predictor_visibility",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "load_coordinate_kind",
            "physical_time_valid",
            "accepted_event_source",
            "mechanism_claim",
            "threshold_sampling",
        )


def _threshold_field_body(
    *,
    law_id: str,
    law_fingerprint: str,
    physics_profile_id: str,
    physics_profile_hash: str,
    reference_state_id: str,
    criterion: str,
    criterion_unit: str,
    predictor_visibility: str,
    thresholds: Mapping[str, float],
    material_disorder_seed: int | None,
) -> dict[str, object]:
    return {
        "schema_version": DAMAGE_SCHEMA_VERSION,
        "law_id": law_id,
        "law_fingerprint": law_fingerprint,
        "physics_profile_id": physics_profile_id,
        "physics_profile_hash": physics_profile_hash,
        "reference_state_id": reference_state_id,
        "criterion": criterion,
        "criterion_unit": criterion_unit,
        "predictor_visibility": predictor_visibility,
        "thresholds": [
            {"physical_bond_id": bond_id, "threshold": thresholds[bond_id]}
            for bond_id in sorted(thresholds)
        ],
        "material_disorder_seed": material_disorder_seed,
        "threshold_sampling": _SAMPLING_SEMANTICS,
        "physical_time_valid": False,
    }


@dataclass(frozen=True)
class ThresholdField:
    """Immutable per-physical-bond thresholds for one realization."""

    realization_id: str
    law_id: str
    law_fingerprint: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    criterion: str
    criterion_unit: str
    predictor_visibility: str
    thresholds: Mapping[str, float]
    material_disorder_seed: int | None
    schema_version: str = DAMAGE_SCHEMA_VERSION
    threshold_sampling: str = _SAMPLING_SEMANTICS
    physical_time_valid: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid threshold field schema_version")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.law_fingerprint) is None:
            raise DamageValidationError("law_fingerprint must be a sha256 digest")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.criterion not in _CRITERION_UNITS:
            raise DamageValidationError("unsupported threshold criterion")
        if self.criterion_unit != _CRITERION_UNITS[self.criterion]:
            raise DamageValidationError("threshold criterion unit mismatch")
        if self.predictor_visibility not in {
            "visible_to_predictor",
            "hidden_from_predictor",
        }:
            raise DamageValidationError("invalid predictor_visibility")
        raw = _mapping(self.thresholds, "thresholds")
        if not raw:
            raise DamageValidationError("threshold field cannot be empty")
        normalized: dict[str, float] = {}
        for bond_id, threshold in raw.items():
            bond_id = _nonempty_string(bond_id, "physical_bond_id")
            number = _finite_float(threshold, f"thresholds[{bond_id!r}]")
            if number <= 0.0:
                raise DamageValidationError("all thresholds must be positive")
            normalized[bond_id] = number
        object.__setattr__(
            self, "thresholds", MappingProxyType(dict(sorted(normalized.items())))
        )
        if self.material_disorder_seed is not None:
            _nonnegative_int(self.material_disorder_seed, "material_disorder_seed")
        if self.threshold_sampling != _SAMPLING_SEMANTICS:
            raise DamageValidationError("threshold sampling semantics changed")
        if self.physical_time_valid is not False:
            raise DamageValidationError("threshold field cannot imply physical time")
        expected = _sha256_record(
            _threshold_field_body(
                law_id=self.law_id,
                law_fingerprint=self.law_fingerprint,
                physics_profile_id=self.physics_profile_id,
                physics_profile_hash=self.physics_profile_hash,
                reference_state_id=self.reference_state_id,
                criterion=self.criterion,
                criterion_unit=self.criterion_unit,
                predictor_visibility=self.predictor_visibility,
                thresholds=self.thresholds,
                material_disorder_seed=self.material_disorder_seed,
            )
        )
        if self.realization_id != expected:
            raise DamageValidationError(
                "realization_id does not match the immutable threshold record"
            )

    def threshold_for(self, physical_bond_id: str) -> float:
        physical_bond_id = _nonempty_string(
            physical_bond_id, "physical_bond_id"
        )
        try:
            return self.thresholds[physical_bond_id]
        except KeyError as error:
            raise DamageValidationError(
                f"unknown physical_bond_id {physical_bond_id!r}"
            ) from error

    def as_record(self) -> dict[str, object]:
        record = _threshold_field_body(
            law_id=self.law_id,
            law_fingerprint=self.law_fingerprint,
            physics_profile_id=self.physics_profile_id,
            physics_profile_hash=self.physics_profile_hash,
            reference_state_id=self.reference_state_id,
            criterion=self.criterion,
            criterion_unit=self.criterion_unit,
            predictor_visibility=self.predictor_visibility,
            thresholds=self.thresholds,
            material_disorder_seed=self.material_disorder_seed,
        )
        return {"realization_id": self.realization_id, **record}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ThresholdField":
        value = _mapping(value, "threshold field record")
        expected = {
            "realization_id",
            "schema_version",
            "law_id",
            "law_fingerprint",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "criterion",
            "criterion_unit",
            "predictor_visibility",
            "thresholds",
            "material_disorder_seed",
            "threshold_sampling",
            "physical_time_valid",
        }
        _exact_keys(value, expected, "threshold field record")
        rows = value["thresholds"]
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise DamageValidationError("thresholds must be a sequence of rows")
        thresholds: dict[str, float] = {}
        for index, raw_row in enumerate(rows):
            row = _mapping(raw_row, f"thresholds[{index}]")
            _exact_keys(
                row,
                {"physical_bond_id", "threshold"},
                f"thresholds[{index}]",
            )
            bond_id = _nonempty_string(
                row["physical_bond_id"], f"thresholds[{index}].physical_bond_id"
            )
            if bond_id in thresholds:
                raise DamageValidationError("duplicate threshold physical_bond_id")
            thresholds[bond_id] = row["threshold"]  # type: ignore[assignment]
        kwargs = dict(value)
        kwargs["thresholds"] = thresholds
        return cls(**kwargs)  # type: ignore[arg-type]


def materialize_thresholds(
    law: DamageLaw,
    physical_bond_ids: Sequence[object],
    *,
    material_disorder_seed: int | None = None,
) -> ThresholdField:
    """Materialize immutable stable-ID-keyed thresholds exactly once."""

    if not isinstance(law, DamageLaw):
        raise DamageValidationError("law must be a validated DamageLaw")
    bond_ids = _stable_ids(physical_bond_ids, "physical_bond_ids")
    if not bond_ids:
        raise DamageValidationError("physical_bond_ids cannot be empty")
    if law.law_kind == "deterministic_threshold":
        if material_disorder_seed is not None:
            raise DamageValidationError(
                "deterministic threshold law does not consume a disorder seed"
            )
        thresholds = {bond_id: law.base_threshold for bond_id in bond_ids}
    else:
        seed = _nonnegative_int(material_disorder_seed, "material_disorder_seed")
        assert law.distribution is not None
        width = float(law.distribution["relative_half_width"])
        thresholds = {}
        for bond_id in bond_ids:
            key = (
                f"{DAMAGE_SCHEMA_VERSION}\0{law.fingerprint}\0{seed}\0{bond_id}"
            ).encode("utf-8")
            integer = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
            uniform = integer / float(1 << 64)
            multiplier = 1.0 + width * (2.0 * uniform - 1.0)
            thresholds[bond_id] = law.base_threshold * multiplier
    body = _threshold_field_body(
        law_id=law.law_id,
        law_fingerprint=law.fingerprint,
        physics_profile_id=law.physics_profile_id,
        physics_profile_hash=law.physics_profile_hash,
        reference_state_id=law.reference_state_id,
        criterion=law.criterion,
        criterion_unit=law.criterion_unit,
        predictor_visibility=law.predictor_visibility,
        thresholds=thresholds,
        material_disorder_seed=material_disorder_seed,
    )
    return ThresholdField(
        realization_id=_sha256_record(body),
        law_id=law.law_id,
        law_fingerprint=law.fingerprint,
        physics_profile_id=law.physics_profile_id,
        physics_profile_hash=law.physics_profile_hash,
        reference_state_id=law.reference_state_id,
        criterion=law.criterion,
        criterion_unit=law.criterion_unit,
        predictor_visibility=law.predictor_visibility,
        thresholds=thresholds,
        material_disorder_seed=material_disorder_seed,
    )


@dataclass(frozen=True)
class CriterionObservation:
    """One accepted or trial criterion value for a stable physical bond."""

    physical_bond_id: str
    criterion: str
    unit: str
    value: float

    def __post_init__(self) -> None:
        _nonempty_string(self.physical_bond_id, "physical_bond_id")
        if self.criterion not in _CRITERION_UNITS:
            raise DamageValidationError("unsupported observation criterion")
        if self.unit != _CRITERION_UNITS[self.criterion]:
            raise DamageValidationError("observation criterion unit mismatch")
        object.__setattr__(self, "value", _finite_float(self.value, "value"))

    def as_record(self) -> dict[str, object]:
        return {
            "physical_bond_id": self.physical_bond_id,
            "criterion": self.criterion,
            "unit": self.unit,
            "value": self.value,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CriterionObservation":
        value = _mapping(value, "criterion observation")
        _exact_keys(
            value,
            {"physical_bond_id", "criterion", "unit", "value"},
            "criterion observation",
        )
        return cls(**dict(value))  # type: ignore[arg-type]


def _bool_mask(
    value: Mapping[str, object], bond_ids: tuple[str, ...], field: str
) -> Mapping[str, bool]:
    value = _mapping(value, field)
    if set(value) != set(bond_ids):
        raise DamageValidationError(f"{field} must cover the exact bond universe")
    result: dict[str, bool] = {}
    for bond_id in bond_ids:
        result[bond_id] = _exact_bool(value[bond_id], f"{field}[{bond_id!r}]")
    return MappingProxyType(result)


@dataclass(frozen=True)
class DamageState:
    """Immutable alive/rupture/removal masks over one stable bond universe."""

    law_id: str
    law_fingerprint: str
    threshold_realization_id: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    physical_bond_ids: tuple[str, ...]
    alive_mask: Mapping[str, bool]
    rupture_mask: Mapping[str, bool]
    prescribed_removal_mask: Mapping[str, bool]
    initial_threshold_violation_mask: Mapping[str, bool]
    accepted_material_event_ids: tuple[str, ...] = ()
    first_damage_event_id: str | None = None
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid damage state schema_version")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.law_fingerprint) is None:
            raise DamageValidationError("invalid law_fingerprint")
        if _HASH_RE.fullmatch(self.threshold_realization_id) is None:
            raise DamageValidationError("invalid threshold_realization_id")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        bond_ids = _stable_ids(self.physical_bond_ids, "physical_bond_ids")
        if not bond_ids or bond_ids != tuple(sorted(bond_ids)):
            raise DamageValidationError(
                "physical_bond_ids must be a nonempty canonical sorted tuple"
            )
        object.__setattr__(self, "physical_bond_ids", bond_ids)
        alive = _bool_mask(self.alive_mask, bond_ids, "alive_mask")
        ruptured = _bool_mask(self.rupture_mask, bond_ids, "rupture_mask")
        prescribed = _bool_mask(
            self.prescribed_removal_mask, bond_ids, "prescribed_removal_mask"
        )
        initial = _bool_mask(
            self.initial_threshold_violation_mask,
            bond_ids,
            "initial_threshold_violation_mask",
        )
        for bond_id in bond_ids:
            if ruptured[bond_id] and prescribed[bond_id]:
                raise DamageValidationError(
                    "a bond cannot be both mechanically ruptured and prescribed-removed"
                )
            if alive[bond_id] != (not ruptured[bond_id] and not prescribed[bond_id]):
                raise DamageValidationError(
                    "alive mask must be the complement of rupture/removal masks"
                )
        object.__setattr__(self, "alive_mask", alive)
        object.__setattr__(self, "rupture_mask", ruptured)
        object.__setattr__(self, "prescribed_removal_mask", prescribed)
        object.__setattr__(self, "initial_threshold_violation_mask", initial)
        event_ids = _stable_ids(
            self.accepted_material_event_ids, "accepted_material_event_ids"
        )
        if any(_HASH_RE.fullmatch(event_id) is None for event_id in event_ids):
            raise DamageValidationError(
                "accepted material event IDs must be sha256 digests"
            )
        object.__setattr__(self, "accepted_material_event_ids", event_ids)
        if event_ids:
            if (
                not isinstance(self.first_damage_event_id, str)
                or _HASH_RE.fullmatch(self.first_damage_event_id) is None
            ):
                raise DamageValidationError(
                    "first_damage_event_id must be a sha256 digest"
                )
            if self.first_damage_event_id != event_ids[0]:
                raise DamageValidationError(
                    "first_damage_event_id must be the first accepted material event"
                )
            if sum(ruptured.values()) != len(event_ids):
                raise DamageValidationError(
                    "rupture mask count must equal accepted material event count"
                )
        elif self.first_damage_event_id is not None:
            raise DamageValidationError(
                "first_damage_event_id requires an accepted material event"
            )
        if any(initial.values()) and (
            any(ruptured.values()) or event_ids or self.first_damage_event_id is not None
        ):
            raise DamageValidationError(
                "invalid reference flags cannot coexist with material rupture history"
            )

    @property
    def state_id(self) -> str:
        return _sha256_record(self.as_record())

    @property
    def has_initial_threshold_violation(self) -> bool:
        return any(self.initial_threshold_violation_mask.values())

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "law_id": self.law_id,
            "law_fingerprint": self.law_fingerprint,
            "threshold_realization_id": self.threshold_realization_id,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "physical_bond_ids": list(self.physical_bond_ids),
            "alive_mask": dict(self.alive_mask),
            "rupture_mask": dict(self.rupture_mask),
            "prescribed_removal_mask": dict(self.prescribed_removal_mask),
            "initial_threshold_violation_mask": dict(
                self.initial_threshold_violation_mask
            ),
            "accepted_material_event_ids": list(self.accepted_material_event_ids),
            "first_damage_event_id": self.first_damage_event_id,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "DamageState":
        value = _mapping(value, "damage state record")
        expected = {
            "schema_version",
            "law_id",
            "law_fingerprint",
            "threshold_realization_id",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "physical_bond_ids",
            "alive_mask",
            "rupture_mask",
            "prescribed_removal_mask",
            "initial_threshold_violation_mask",
            "accepted_material_event_ids",
            "first_damage_event_id",
        }
        _exact_keys(value, expected, "damage state record")
        if (
            isinstance(value["physical_bond_ids"], (str, bytes, Mapping))
            or not isinstance(value["physical_bond_ids"], Sequence)
        ):
            raise DamageValidationError(
                "physical_bond_ids must be a sequence of stable IDs"
            )
        if (
            isinstance(
                value["accepted_material_event_ids"], (str, bytes, Mapping)
            )
            or not isinstance(value["accepted_material_event_ids"], Sequence)
        ):
            raise DamageValidationError(
                "accepted_material_event_ids must be a sequence of stable IDs"
            )
        kwargs = dict(value)
        kwargs["physical_bond_ids"] = tuple(value["physical_bond_ids"])  # type: ignore[arg-type]
        kwargs["accepted_material_event_ids"] = tuple(
            value["accepted_material_event_ids"]  # type: ignore[arg-type]
        )
        return cls(**kwargs)  # type: ignore[arg-type]


def _validate_law_field_state(
    law: DamageLaw, field: ThresholdField, state: DamageState | None = None
) -> None:
    if not isinstance(law, DamageLaw) or not isinstance(field, ThresholdField):
        raise DamageValidationError("law and threshold field must be validated")
    if field.law_id != law.law_id or field.law_fingerprint != law.fingerprint:
        raise DamageValidationError("threshold field does not belong to damage law")
    _validate_identity_match(
        profile_id=field.physics_profile_id,
        profile_hash=field.physics_profile_hash,
        reference_state_id=field.reference_state_id,
        expected_profile_id=law.physics_profile_id,
        expected_profile_hash=law.physics_profile_hash,
        expected_reference_state_id=law.reference_state_id,
        context="threshold field",
    )
    if (
        field.criterion != law.criterion
        or field.criterion_unit != law.criterion_unit
        or field.predictor_visibility != law.predictor_visibility
    ):
        raise DamageValidationError("threshold field semantics differ from law")
    if state is not None:
        if (
            state.law_id != law.law_id
            or state.law_fingerprint != law.fingerprint
            or state.threshold_realization_id != field.realization_id
        ):
            raise DamageValidationError("damage state does not belong to law/field")
        _validate_identity_match(
            profile_id=state.physics_profile_id,
            profile_hash=state.physics_profile_hash,
            reference_state_id=state.reference_state_id,
            expected_profile_id=law.physics_profile_id,
            expected_profile_hash=law.physics_profile_hash,
            expected_reference_state_id=law.reference_state_id,
            context="damage state",
        )
        if set(state.physical_bond_ids) != set(field.thresholds):
            raise DamageValidationError(
                "damage state and threshold field bond universes differ"
            )


def _observation_map(
    observations: Sequence[CriterionObservation],
    *,
    expected_ids: set[str],
    law: DamageLaw,
) -> Mapping[str, CriterionObservation]:
    if isinstance(observations, (str, bytes)):
        raise DamageValidationError("observations must be criterion objects")
    result: dict[str, CriterionObservation] = {}
    for observation in observations:
        if not isinstance(observation, CriterionObservation):
            raise DamageValidationError(
                "observations must contain CriterionObservation objects"
            )
        if observation.physical_bond_id in result:
            raise DamageValidationError("duplicate observation physical_bond_id")
        if (
            observation.criterion != law.criterion
            or observation.unit != law.criterion_unit
        ):
            raise DamageValidationError("observation criterion/unit differs from law")
        result[observation.physical_bond_id] = observation
    if set(result) != expected_ids:
        raise DamageValidationError(
            "observations must cover the exact required physical-bond IDs"
        )
    return MappingProxyType(result)


def initialize_damage_state(
    law: DamageLaw,
    threshold_field: ThresholdField,
    reference_observations: Sequence[CriterionObservation],
) -> DamageState:
    """Create an intact state and flag, but never rupture, invalid references."""

    _validate_law_field_state(law, threshold_field)
    observations = _observation_map(
        reference_observations,
        expected_ids=set(threshold_field.thresholds),
        law=law,
    )
    bond_ids = tuple(sorted(threshold_field.thresholds))
    initial = {
        bond_id: observations[bond_id].value
        >= threshold_field.thresholds[bond_id]
        for bond_id in bond_ids
    }
    return DamageState(
        law_id=law.law_id,
        law_fingerprint=law.fingerprint,
        threshold_realization_id=threshold_field.realization_id,
        physics_profile_id=law.physics_profile_id,
        physics_profile_hash=law.physics_profile_hash,
        reference_state_id=law.reference_state_id,
        physical_bond_ids=bond_ids,
        alive_mask={bond_id: True for bond_id in bond_ids},
        rupture_mask={bond_id: False for bond_id in bond_ids},
        prescribed_removal_mask={bond_id: False for bond_id in bond_ids},
        initial_threshold_violation_mask=initial,
    )


@dataclass(frozen=True)
class RuptureCandidate:
    candidate_id: str
    rank: int
    physical_bond_id: str
    criterion: str
    criterion_unit: str
    criterion_value: float
    threshold_value: float
    utilization: float
    control_id: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    progress_semantics: str
    state_id: str
    law_id: str
    threshold_realization_id: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    event_source: str = "material_rupture"
    solver_state: str = "accepted_equilibrium"
    initial_threshold_violation: bool = False
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid rupture candidate schema_version")
        _nonnegative_int(self.rank, "rank")
        _nonempty_string(self.physical_bond_id, "physical_bond_id")
        if self.criterion not in _CRITERION_UNITS:
            raise DamageValidationError("unsupported rupture criterion")
        if self.criterion_unit != _CRITERION_UNITS[self.criterion]:
            raise DamageValidationError("rupture candidate unit mismatch")
        value = _finite_float(self.criterion_value, "criterion_value")
        threshold = _finite_float(self.threshold_value, "threshold_value")
        utilization = _finite_float(self.utilization, "utilization")
        if threshold <= 0.0 or value / threshold != utilization:
            raise DamageValidationError("rupture candidate utilization is inconsistent")
        if utilization < 1.0:
            raise DamageValidationError("rupture candidate has not reached threshold")
        object.__setattr__(self, "criterion_value", value)
        object.__setattr__(self, "threshold_value", threshold)
        object.__setattr__(self, "utilization", utilization)
        _nonempty_string(self.control_id, "control_id")
        object.__setattr__(
            self,
            "load_coordinate",
            _finite_float(self.load_coordinate, "load_coordinate"),
        )
        if self.load_coordinate_unit not in _LOAD_UNITS:
            raise DamageValidationError("unsupported load_coordinate_unit")
        progress = _finite_float(self.path_progress, "path_progress")
        if progress < 0.0:
            raise DamageValidationError("path_progress must be nonnegative")
        object.__setattr__(self, "path_progress", progress)
        if self.progress_unit != self.load_coordinate_unit:
            raise DamageValidationError(
                "progress_unit must equal load_coordinate_unit"
            )
        if self.progress_semantics != _PROGRESS_SEMANTICS:
            raise DamageValidationError("invalid path progress semantics")
        if _HASH_RE.fullmatch(self.state_id) is None:
            raise DamageValidationError("state_id must be a sha256 digest")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.threshold_realization_id) is None:
            raise DamageValidationError("invalid threshold_realization_id")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.event_source != "material_rupture":
            raise DamageValidationError("candidate source must be material_rupture")
        if self.solver_state != "accepted_equilibrium":
            raise DamageValidationError(
                "only accepted equilibria can produce rupture candidates"
            )
        if self.initial_threshold_violation is not False:
            raise DamageValidationError(
                "initial threshold violations are not rupture candidates"
            )
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise DamageValidationError("rupture candidate cannot carry physical time")
        body = self._body()
        if self.candidate_id != _sha256_record(body):
            raise DamageValidationError("candidate_id does not match candidate record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "rank": self.rank,
            "physical_bond_id": self.physical_bond_id,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "criterion_value": self.criterion_value,
            "threshold_value": self.threshold_value,
            "utilization": self.utilization,
            "control_id": self.control_id,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
            "state_id": self.state_id,
            "law_id": self.law_id,
            "threshold_realization_id": self.threshold_realization_id,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "event_source": self.event_source,
            "solver_state": self.solver_state,
            "initial_threshold_violation": self.initial_threshold_violation,
            "physical_time": self.physical_time,
            "physical_time_valid": self.physical_time_valid,
        }

    def as_record(self) -> dict[str, object]:
        return {"candidate_id": self.candidate_id, **self._body()}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "RuptureCandidate":
        value = _mapping(value, "rupture candidate record")
        expected = {
            "candidate_id",
            "schema_version",
            "rank",
            "physical_bond_id",
            "criterion",
            "criterion_unit",
            "criterion_value",
            "threshold_value",
            "utilization",
            "control_id",
            "load_coordinate",
            "load_coordinate_unit",
            "path_progress",
            "progress_unit",
            "progress_semantics",
            "state_id",
            "law_id",
            "threshold_realization_id",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "event_source",
            "solver_state",
            "initial_threshold_violation",
            "physical_time",
            "physical_time_valid",
        }
        _exact_keys(value, expected, "rupture candidate record")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class DamageAssessment:
    assessment_id: str
    phase: str
    eligible_for_material_rupture: bool
    exclusion_reason: str | None
    candidates: tuple[RuptureCandidate, ...]
    state_id: str
    law_id: str
    threshold_realization_id: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    control_id: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    progress_semantics: str = _PROGRESS_SEMANTICS
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid assessment schema_version")
        if self.phase not in _ASSESSMENT_PHASES:
            raise DamageValidationError("unsupported assessment phase")
        _exact_bool(
            self.eligible_for_material_rupture,
            "eligible_for_material_rupture",
        )
        if self.phase == "accepted_equilibrium":
            if not self.eligible_for_material_rupture or self.exclusion_reason is not None:
                raise DamageValidationError(
                    "accepted equilibrium must be eligible unless invalid reference"
                )
        elif self.eligible_for_material_rupture or not isinstance(
            self.exclusion_reason, str
        ):
            raise DamageValidationError(
                "non-accepted phases must be explicitly excluded"
            )
        if self.phase == "reference_preparation" and self.exclusion_reason not in {
            "reference_preparation_not_a_damage_event",
            "initial_threshold_violation_invalid_reference",
        }:
            raise DamageValidationError(
                "reference preparation requires a canonical exclusion_reason"
            )
        if (
            self.phase == "rejected_numerical_trial"
            and self.exclusion_reason != "rejected_trial_not_scientific_state"
        ):
            raise DamageValidationError(
                "rejected trial requires its canonical exclusion_reason"
            )
        if (
            self.phase == "solver_error"
            and self.exclusion_reason != "solver_error_not_physical_failure"
        ):
            raise DamageValidationError(
                "solver error requires its canonical exclusion_reason"
            )
        if _HASH_RE.fullmatch(self.state_id) is None:
            raise DamageValidationError("invalid assessment state_id")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.threshold_realization_id) is None:
            raise DamageValidationError("invalid threshold_realization_id")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        _nonempty_string(self.control_id, "control_id")
        object.__setattr__(
            self,
            "load_coordinate",
            _finite_float(self.load_coordinate, "load_coordinate"),
        )
        if self.load_coordinate_unit not in _LOAD_UNITS:
            raise DamageValidationError("unsupported load_coordinate_unit")
        progress = _finite_float(self.path_progress, "path_progress")
        if progress < 0.0:
            raise DamageValidationError("path_progress must be nonnegative")
        object.__setattr__(self, "path_progress", progress)
        if self.progress_unit != self.load_coordinate_unit:
            raise DamageValidationError(
                "progress_unit must equal load_coordinate_unit"
            )
        if self.progress_semantics != _PROGRESS_SEMANTICS:
            raise DamageValidationError("invalid path progress semantics")
        if isinstance(self.candidates, (str, bytes)):
            raise DamageValidationError("candidates must be rupture candidates")
        candidates = tuple(self.candidates)
        object.__setattr__(self, "candidates", candidates)
        if not self.eligible_for_material_rupture and candidates:
            raise DamageValidationError("excluded assessment cannot have candidates")
        if any(not isinstance(candidate, RuptureCandidate) for candidate in candidates):
            raise DamageValidationError("candidates must be RuptureCandidate objects")
        if len({candidate.physical_bond_id for candidate in candidates}) != len(
            candidates
        ):
            raise DamageValidationError(
                "assessment contains duplicate physical-bond candidates"
            )
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, RuptureCandidate) or candidate.rank != index:
                raise DamageValidationError("candidate ranks must be contiguous")
            if (
                candidate.state_id != self.state_id
                or candidate.law_id != self.law_id
                or candidate.threshold_realization_id
                != self.threshold_realization_id
                or candidate.physics_profile_id != self.physics_profile_id
                or candidate.physics_profile_hash != self.physics_profile_hash
                or candidate.reference_state_id != self.reference_state_id
                or candidate.control_id != self.control_id
                or candidate.load_coordinate != self.load_coordinate
                or candidate.load_coordinate_unit != self.load_coordinate_unit
                or candidate.path_progress != self.path_progress
                or candidate.progress_unit != self.progress_unit
                or candidate.progress_semantics != self.progress_semantics
            ):
                raise DamageValidationError(
                    "candidate identity/context differs from assessment"
                )
        if candidates != tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    -candidate.utilization,
                    candidate.physical_bond_id,
                ),
            )
        ):
            raise DamageValidationError(
                "assessment candidates violate canonical candidate order"
            )
        if self.assessment_id != _sha256_record(self._body()):
            raise DamageValidationError(
                "assessment_id does not match assessment record"
            )

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "eligible_for_material_rupture": self.eligible_for_material_rupture,
            "exclusion_reason": self.exclusion_reason,
            "candidates": [candidate.as_record() for candidate in self.candidates],
            "state_id": self.state_id,
            "law_id": self.law_id,
            "threshold_realization_id": self.threshold_realization_id,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "control_id": self.control_id,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
        }

    def as_record(self) -> dict[str, object]:
        return {"assessment_id": self.assessment_id, **self._body()}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "DamageAssessment":
        value = _mapping(value, "damage assessment record")
        expected = {
            "assessment_id",
            "schema_version",
            "phase",
            "eligible_for_material_rupture",
            "exclusion_reason",
            "candidates",
            "state_id",
            "law_id",
            "threshold_realization_id",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "control_id",
            "load_coordinate",
            "load_coordinate_unit",
            "path_progress",
            "progress_unit",
            "progress_semantics",
        }
        _exact_keys(value, expected, "damage assessment record")
        candidates = value["candidates"]
        if isinstance(candidates, (str, bytes)) or not isinstance(
            candidates, Sequence
        ):
            raise DamageValidationError("candidates must be a sequence")
        kwargs = dict(value)
        kwargs["candidates"] = tuple(
            RuptureCandidate.from_record(candidate) for candidate in candidates
        )
        return cls(**kwargs)  # type: ignore[arg-type]


def assess_material_rupture(
    law: DamageLaw,
    threshold_field: ThresholdField,
    state: DamageState,
    observations: Sequence[CriterionObservation],
    *,
    phase: str,
    control_id: str,
    load_coordinate: float,
    load_coordinate_unit: str,
    path_progress: float,
) -> DamageAssessment:
    """Assess crossings without mutating the irreversible damage state."""

    _validate_law_field_state(law, threshold_field, state)
    if phase not in _ASSESSMENT_PHASES:
        raise DamageValidationError("unsupported assessment phase")
    control_id = _nonempty_string(control_id, "control_id")
    load_coordinate = _finite_float(load_coordinate, "load_coordinate")
    if load_coordinate_unit not in _LOAD_UNITS:
        raise DamageValidationError("unsupported load_coordinate_unit")
    path_progress = _finite_float(path_progress, "path_progress")
    if path_progress < 0.0:
        raise DamageValidationError("path_progress must be nonnegative")

    if state.has_initial_threshold_violation:
        phase_for_record = "reference_preparation"
        eligible = False
        reason = "initial_threshold_violation_invalid_reference"
        candidates: tuple[RuptureCandidate, ...] = ()
    elif phase != "accepted_equilibrium":
        phase_for_record = phase
        eligible = False
        reason = {
            "reference_preparation": "reference_preparation_not_a_damage_event",
            "rejected_numerical_trial": "rejected_trial_not_scientific_state",
            "solver_error": "solver_error_not_physical_failure",
        }[phase]
        candidates = ()
    else:
        phase_for_record = phase
        eligible = True
        reason = None
        alive_ids = {
            bond_id for bond_id, alive in state.alive_mask.items() if alive
        }
        observed = _observation_map(
            observations, expected_ids=alive_ids, law=law
        )
        crossing_rows: list[tuple[float, str, CriterionObservation, float]] = []
        for bond_id in alive_ids:
            threshold = threshold_field.thresholds[bond_id]
            utilization = observed[bond_id].value / threshold
            if utilization >= 1.0:
                crossing_rows.append(
                    (utilization, bond_id, observed[bond_id], threshold)
                )
        crossing_rows.sort(key=lambda row: (-row[0], row[1]))
        built: list[RuptureCandidate] = []
        for rank, (utilization, bond_id, observation, threshold) in enumerate(
            crossing_rows
        ):
            body = {
                "schema_version": DAMAGE_SCHEMA_VERSION,
                "rank": rank,
                "physical_bond_id": bond_id,
                "criterion": law.criterion,
                "criterion_unit": law.criterion_unit,
                "criterion_value": observation.value,
                "threshold_value": threshold,
                "utilization": utilization,
                "control_id": control_id,
                "load_coordinate": load_coordinate,
                "load_coordinate_unit": load_coordinate_unit,
                "path_progress": path_progress,
                "progress_unit": load_coordinate_unit,
                "progress_semantics": _PROGRESS_SEMANTICS,
                "state_id": state.state_id,
                "law_id": law.law_id,
                "threshold_realization_id": threshold_field.realization_id,
                "physics_profile_id": law.physics_profile_id,
                "physics_profile_hash": law.physics_profile_hash,
                "reference_state_id": law.reference_state_id,
                "event_source": "material_rupture",
                "solver_state": "accepted_equilibrium",
                "initial_threshold_violation": False,
                "physical_time": None,
                "physical_time_valid": False,
            }
            built.append(RuptureCandidate(candidate_id=_sha256_record(body), **body))
        candidates = tuple(built)

    body = {
        "schema_version": DAMAGE_SCHEMA_VERSION,
        "phase": phase_for_record,
        "eligible_for_material_rupture": eligible,
        "exclusion_reason": reason,
        "candidates": [candidate.as_record() for candidate in candidates],
        "state_id": state.state_id,
        "law_id": law.law_id,
        "threshold_realization_id": threshold_field.realization_id,
        "physics_profile_id": law.physics_profile_id,
        "physics_profile_hash": law.physics_profile_hash,
        "reference_state_id": law.reference_state_id,
        "control_id": control_id,
        "load_coordinate": load_coordinate,
        "load_coordinate_unit": load_coordinate_unit,
        "path_progress": path_progress,
        "progress_unit": load_coordinate_unit,
        "progress_semantics": _PROGRESS_SEMANTICS,
    }
    return DamageAssessment(
        assessment_id=_sha256_record(body),
        phase=phase_for_record,
        eligible_for_material_rupture=eligible,
        exclusion_reason=reason,
        candidates=candidates,
        state_id=state.state_id,
        law_id=law.law_id,
        threshold_realization_id=threshold_field.realization_id,
        physics_profile_id=law.physics_profile_id,
        physics_profile_hash=law.physics_profile_hash,
        reference_state_id=law.reference_state_id,
        control_id=control_id,
        load_coordinate=load_coordinate,
        load_coordinate_unit=load_coordinate_unit,
        path_progress=path_progress,
        progress_unit=load_coordinate_unit,
    )


@dataclass(frozen=True)
class MaterialRuptureEvent:
    event_id: str
    sequence_index: int
    pre_state_id: str
    assessment_id: str
    candidate_id: str
    law_id: str
    law_fingerprint: str
    threshold_realization_id: str
    physical_bond_id: str
    control_id: str
    load_coordinate: float
    load_coordinate_unit: str
    path_progress: float
    progress_unit: str
    progress_semantics: str
    criterion: str
    criterion_unit: str
    criterion_value: float
    threshold_value: float
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    event_source: str = "material_rupture"
    old_alive: bool = True
    new_alive: bool = False
    accepted: bool = True
    is_damage_initiation: bool = False
    initial_threshold_violation: bool = False
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid material event schema_version")
        _nonnegative_int(self.sequence_index, "sequence_index")
        if _HASH_RE.fullmatch(self.pre_state_id) is None:
            raise DamageValidationError("pre_state_id must be a sha256 digest")
        if _HASH_RE.fullmatch(self.assessment_id) is None:
            raise DamageValidationError("assessment_id must be a sha256 digest")
        if _HASH_RE.fullmatch(self.candidate_id) is None:
            raise DamageValidationError("candidate_id must be a sha256 digest")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.law_fingerprint) is None:
            raise DamageValidationError("law_fingerprint must be a sha256 digest")
        if _HASH_RE.fullmatch(self.threshold_realization_id) is None:
            raise DamageValidationError(
                "threshold_realization_id must be a sha256 digest"
            )
        _nonempty_string(self.physical_bond_id, "physical_bond_id")
        _nonempty_string(self.control_id, "control_id")
        object.__setattr__(
            self,
            "load_coordinate",
            _finite_float(self.load_coordinate, "load_coordinate"),
        )
        if self.load_coordinate_unit not in _LOAD_UNITS:
            raise DamageValidationError("unsupported load_coordinate_unit")
        progress = _finite_float(self.path_progress, "path_progress")
        if progress < 0.0:
            raise DamageValidationError("path_progress must be nonnegative")
        object.__setattr__(self, "path_progress", progress)
        if self.progress_unit != self.load_coordinate_unit:
            raise DamageValidationError(
                "progress_unit must equal load_coordinate_unit"
            )
        if self.progress_semantics != _PROGRESS_SEMANTICS:
            raise DamageValidationError("invalid path progress semantics")
        if self.criterion not in _CRITERION_UNITS:
            raise DamageValidationError("unsupported rupture event criterion")
        if self.criterion_unit != _CRITERION_UNITS[self.criterion]:
            raise DamageValidationError("rupture event criterion unit mismatch")
        criterion_value = _finite_float(self.criterion_value, "criterion_value")
        threshold_value = _finite_float(self.threshold_value, "threshold_value")
        if threshold_value <= 0.0 or criterion_value < threshold_value:
            raise DamageValidationError("rupture event did not reach threshold")
        object.__setattr__(self, "criterion_value", criterion_value)
        object.__setattr__(self, "threshold_value", threshold_value)
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.event_source != "material_rupture":
            raise DamageValidationError("material event source cannot be relabeled")
        if self.old_alive is not True or self.new_alive is not False:
            raise DamageValidationError("material rupture must be alive-to-dead")
        if self.accepted is not True:
            raise DamageValidationError("only accepted material rupture is recorded")
        if self.is_damage_initiation != (self.sequence_index == 0):
            raise DamageValidationError(
                "damage initiation must be exactly the first material rupture"
            )
        if self.initial_threshold_violation is not False:
            raise DamageValidationError(
                "initial threshold violation cannot be a rupture event"
            )
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise DamageValidationError("quasi-static event cannot carry physical time")
        if self.event_id != _sha256_record(self._body()):
            raise DamageValidationError("event_id does not match material event")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sequence_index": self.sequence_index,
            "pre_state_id": self.pre_state_id,
            "assessment_id": self.assessment_id,
            "candidate_id": self.candidate_id,
            "law_id": self.law_id,
            "law_fingerprint": self.law_fingerprint,
            "threshold_realization_id": self.threshold_realization_id,
            "physical_bond_id": self.physical_bond_id,
            "control_id": self.control_id,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
            "criterion": self.criterion,
            "criterion_unit": self.criterion_unit,
            "criterion_value": self.criterion_value,
            "threshold_value": self.threshold_value,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "event_source": self.event_source,
            "old_alive": self.old_alive,
            "new_alive": self.new_alive,
            "accepted": self.accepted,
            "is_damage_initiation": self.is_damage_initiation,
            "initial_threshold_violation": self.initial_threshold_violation,
            "physical_time": self.physical_time,
            "physical_time_valid": self.physical_time_valid,
        }

    def as_record(self) -> dict[str, object]:
        return {"event_id": self.event_id, **self._body()}

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "MaterialRuptureEvent":
        value = _mapping(value, "material rupture event")
        expected = {
            "event_id",
            "schema_version",
            "sequence_index",
            "pre_state_id",
            "assessment_id",
            "candidate_id",
            "law_id",
            "law_fingerprint",
            "threshold_realization_id",
            "physical_bond_id",
            "control_id",
            "load_coordinate",
            "load_coordinate_unit",
            "path_progress",
            "progress_unit",
            "progress_semantics",
            "criterion",
            "criterion_unit",
            "criterion_value",
            "threshold_value",
            "physics_profile_id",
            "physics_profile_hash",
            "reference_state_id",
            "event_source",
            "old_alive",
            "new_alive",
            "accepted",
            "is_damage_initiation",
            "initial_threshold_violation",
            "physical_time",
            "physical_time_valid",
        }
        _exact_keys(value, expected, "material rupture event")
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class DamageTransition:
    previous_state_id: str
    state: DamageState
    event: MaterialRuptureEvent

    def __post_init__(self) -> None:
        if _HASH_RE.fullmatch(self.previous_state_id) is None:
            raise DamageValidationError("invalid previous_state_id")
        if not isinstance(self.state, DamageState) or not isinstance(
            self.event, MaterialRuptureEvent
        ):
            raise DamageValidationError("transition requires validated state/event")
        if not self.state.accepted_material_event_ids:
            raise DamageValidationError(
                "transition state has empty material event history"
            )
        if self.state.accepted_material_event_ids[-1] != self.event.event_id:
            raise DamageValidationError("transition state does not contain event")
        if self.event.pre_state_id != self.previous_state_id:
            raise DamageValidationError("transition event pre-state is inconsistent")
        if self.event.sequence_index != len(self.state.accepted_material_event_ids) - 1:
            raise DamageValidationError(
                "transition event sequence differs from state event history"
            )
        if (
            self.event.law_id != self.state.law_id
            or self.event.law_fingerprint != self.state.law_fingerprint
            or self.event.threshold_realization_id
            != self.state.threshold_realization_id
        ):
            raise DamageValidationError(
                "transition event law/threshold identity differs from state"
            )
        _validate_identity_match(
            profile_id=self.event.physics_profile_id,
            profile_hash=self.event.physics_profile_hash,
            reference_state_id=self.event.reference_state_id,
            expected_profile_id=self.state.physics_profile_id,
            expected_profile_hash=self.state.physics_profile_hash,
            expected_reference_state_id=self.state.reference_state_id,
            context="transition event",
        )
        bond_id = self.event.physical_bond_id
        if bond_id not in self.state.alive_mask:
            raise DamageValidationError("transition event bond is unknown")
        if (
            self.state.alive_mask[bond_id]
            or not self.state.rupture_mask[bond_id]
            or self.state.prescribed_removal_mask[bond_id]
        ):
            raise DamageValidationError(
                "transition event bond is not the resulting mechanical rupture"
            )


def accept_next_material_rupture(
    state: DamageState, assessment: DamageAssessment
) -> DamageTransition:
    """Accept the deterministic first candidate and irreversibly mask its bond."""

    if not isinstance(state, DamageState) or not isinstance(
        assessment, DamageAssessment
    ):
        raise DamageValidationError("state and assessment must be validated")
    if state.state_id != assessment.state_id:
        raise DamageValidationError("assessment is stale for this damage state")
    if (
        assessment.law_id != state.law_id
        or assessment.threshold_realization_id != state.threshold_realization_id
    ):
        raise DamageValidationError(
            "assessment law/threshold realization differs from damage state"
        )
    _validate_identity_match(
        profile_id=assessment.physics_profile_id,
        profile_hash=assessment.physics_profile_hash,
        reference_state_id=assessment.reference_state_id,
        expected_profile_id=state.physics_profile_id,
        expected_profile_hash=state.physics_profile_hash,
        expected_reference_state_id=state.reference_state_id,
        context="assessment",
    )
    if not assessment.eligible_for_material_rupture:
        raise DamageValidationError("excluded assessment cannot rupture a bond")
    if not assessment.candidates:
        raise DamageValidationError("assessment has no threshold crossing")
    candidate = assessment.candidates[0]
    bond_id = candidate.physical_bond_id
    if bond_id not in state.alive_mask:
        raise DamageValidationError("candidate references unknown physical bond")
    if not state.alive_mask[bond_id]:
        raise DamageValidationError("cannot rupture an inactive physical bond")
    if state.initial_threshold_violation_mask[bond_id]:
        raise DamageValidationError(
            "initial threshold violation cannot become damage initiation"
        )
    sequence = len(state.accepted_material_event_ids)
    event_body = {
        "schema_version": DAMAGE_SCHEMA_VERSION,
        "sequence_index": sequence,
        "pre_state_id": state.state_id,
        "assessment_id": assessment.assessment_id,
        "candidate_id": candidate.candidate_id,
        "law_id": state.law_id,
        "law_fingerprint": state.law_fingerprint,
        "threshold_realization_id": state.threshold_realization_id,
        "physical_bond_id": bond_id,
        "control_id": candidate.control_id,
        "load_coordinate": candidate.load_coordinate,
        "load_coordinate_unit": candidate.load_coordinate_unit,
        "path_progress": candidate.path_progress,
        "progress_unit": candidate.progress_unit,
        "progress_semantics": candidate.progress_semantics,
        "criterion": candidate.criterion,
        "criterion_unit": candidate.criterion_unit,
        "criterion_value": candidate.criterion_value,
        "threshold_value": candidate.threshold_value,
        "physics_profile_id": candidate.physics_profile_id,
        "physics_profile_hash": candidate.physics_profile_hash,
        "reference_state_id": candidate.reference_state_id,
        "event_source": "material_rupture",
        "old_alive": True,
        "new_alive": False,
        "accepted": True,
        "is_damage_initiation": sequence == 0,
        "initial_threshold_violation": False,
        "physical_time": None,
        "physical_time_valid": False,
    }
    event = MaterialRuptureEvent(
        event_id=_sha256_record(event_body), **event_body
    )
    alive = dict(state.alive_mask)
    ruptured = dict(state.rupture_mask)
    alive[bond_id] = False
    ruptured[bond_id] = True
    next_state = DamageState(
        law_id=state.law_id,
        law_fingerprint=state.law_fingerprint,
        threshold_realization_id=state.threshold_realization_id,
        physics_profile_id=state.physics_profile_id,
        physics_profile_hash=state.physics_profile_hash,
        reference_state_id=state.reference_state_id,
        physical_bond_ids=state.physical_bond_ids,
        alive_mask=alive,
        rupture_mask=ruptured,
        prescribed_removal_mask=state.prescribed_removal_mask,
        initial_threshold_violation_mask=state.initial_threshold_violation_mask,
        accepted_material_event_ids=(
            *state.accepted_material_event_ids,
            event.event_id,
        ),
        first_damage_event_id=(state.first_damage_event_id or event.event_id),
    )
    return DamageTransition(
        previous_state_id=state.state_id, state=next_state, event=event
    )


@dataclass(frozen=True)
class ExcludedEventRecord:
    """Non-material origins that cannot count as damage initiation."""

    event_id: str
    source: str
    event_kind: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    accepted: bool
    physical_bond_id: str | None = None
    old_alive: bool | None = None
    new_alive: bool | None = None
    mechanical_trigger: bool = False
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid excluded event schema_version")
        if _HASH_RE.fullmatch(self.event_id) is None:
            raise DamageValidationError("excluded event_id must be a sha256 digest")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        _exact_bool(self.accepted, "accepted")
        if self.mechanical_trigger is not False:
            raise DamageValidationError(
                "excluded event cannot claim a mechanical rupture trigger"
            )
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise DamageValidationError("excluded event cannot carry physical time")
        expected_kind = {
            "computational_neighbor_change": "computational_neighbor_change",
            "rendering_change": "rendering_change",
            "solver_error": "solver_error",
        }
        if self.source == "prescribed_intervention":
            if self.event_kind not in {
                "prescribed_removal",
                "prescribed_weakening",
            }:
                raise DamageValidationError("unsupported prescribed event kind")
            _nonempty_string(self.physical_bond_id, "physical_bond_id")
            if self.old_alive is not True:
                raise DamageValidationError("prescribed event requires an alive bond")
            expected_new = self.event_kind == "prescribed_weakening"
            if self.new_alive is not expected_new or self.accepted is not True:
                raise DamageValidationError(
                    "prescribed event alive/accepted semantics are inconsistent"
                )
        elif self.source in expected_kind:
            if self.event_kind != expected_kind[self.source]:
                raise DamageValidationError("excluded event source/kind mismatch")
            if (
                self.physical_bond_id is not None
                or self.old_alive is not None
                or self.new_alive is not None
            ):
                raise DamageValidationError(
                    "computational/render/solver events cannot mutate physical bonds"
                )
            if self.source == "solver_error" and self.accepted is not False:
                raise DamageValidationError("solver errors are not accepted states")
        else:
            raise DamageValidationError("unsupported excluded event source")
        if self.event_id != _sha256_record(self._body()):
            raise DamageValidationError("event_id does not match excluded event record")

    def _body(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "event_kind": self.event_kind,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "accepted": self.accepted,
            "physical_bond_id": self.physical_bond_id,
            "old_alive": self.old_alive,
            "new_alive": self.new_alive,
            "mechanical_trigger": self.mechanical_trigger,
            "physical_time": self.physical_time,
            "physical_time_valid": self.physical_time_valid,
        }

    def as_record(self) -> dict[str, object]:
        return {"event_id": self.event_id, **self._body()}

    @classmethod
    def create(
        cls,
        *,
        source: str,
        event_kind: str,
        physics_profile_id: str,
        physics_profile_hash: str,
        reference_state_id: str,
        accepted: bool,
        physical_bond_id: str | None = None,
        old_alive: bool | None = None,
        new_alive: bool | None = None,
    ) -> "ExcludedEventRecord":
        body: dict[str, object] = {
            "schema_version": DAMAGE_SCHEMA_VERSION,
            "source": source,
            "event_kind": event_kind,
            "physics_profile_id": physics_profile_id,
            "physics_profile_hash": physics_profile_hash,
            "reference_state_id": reference_state_id,
            "accepted": accepted,
            "physical_bond_id": physical_bond_id,
            "old_alive": old_alive,
            "new_alive": new_alive,
            "mechanical_trigger": False,
            "physical_time": None,
            "physical_time_valid": False,
        }
        return cls(event_id=_sha256_record(body), **body)  # type: ignore[arg-type]

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "ExcludedEventRecord":
        value = _mapping(value, "excluded event record")
        _exact_keys(
            value,
            {
                "event_id",
                "schema_version",
                "source",
                "event_kind",
                "physics_profile_id",
                "physics_profile_hash",
                "reference_state_id",
                "accepted",
                "physical_bond_id",
                "old_alive",
                "new_alive",
                "mechanical_trigger",
                "physical_time",
                "physical_time_valid",
            },
            "excluded event record",
        )
        return cls(**dict(value))  # type: ignore[arg-type]

    @property
    def counts_as_damage_initiation(self) -> bool:
        return False


def apply_excluded_event(
    state: DamageState, event: ExcludedEventRecord
) -> DamageState:
    """Apply only prescribed removal to physical alive state; never rupture it."""

    if not isinstance(state, DamageState) or not isinstance(
        event, ExcludedEventRecord
    ):
        raise DamageValidationError("state/event must be validated")
    _validate_identity_match(
        profile_id=event.physics_profile_id,
        profile_hash=event.physics_profile_hash,
        reference_state_id=event.reference_state_id,
        expected_profile_id=state.physics_profile_id,
        expected_profile_hash=state.physics_profile_hash,
        expected_reference_state_id=state.reference_state_id,
        context="excluded event",
    )
    if event.source == "prescribed_intervention":
        assert event.physical_bond_id is not None
        if event.physical_bond_id not in state.alive_mask:
            raise DamageValidationError("prescribed event references unknown bond")
        if not state.alive_mask[event.physical_bond_id]:
            raise DamageValidationError(
                "prescribed event cannot target an inactive bond"
            )
    if event.event_kind != "prescribed_removal":
        return state
    assert event.physical_bond_id is not None
    alive = dict(state.alive_mask)
    prescribed = dict(state.prescribed_removal_mask)
    alive[event.physical_bond_id] = False
    prescribed[event.physical_bond_id] = True
    return DamageState(
        law_id=state.law_id,
        law_fingerprint=state.law_fingerprint,
        threshold_realization_id=state.threshold_realization_id,
        physics_profile_id=state.physics_profile_id,
        physics_profile_hash=state.physics_profile_hash,
        reference_state_id=state.reference_state_id,
        physical_bond_ids=state.physical_bond_ids,
        alive_mask=alive,
        rupture_mask=state.rupture_mask,
        prescribed_removal_mask=prescribed,
        initial_threshold_violation_mask=state.initial_threshold_violation_mask,
        accepted_material_event_ids=state.accepted_material_event_ids,
        first_damage_event_id=state.first_damage_event_id,
    )


def validate_irreversible_transition(
    previous: DamageState, current: DamageState
) -> None:
    """Reject healing, mask reversals, and cross-profile/reference transitions."""

    if not isinstance(previous, DamageState) or not isinstance(current, DamageState):
        raise DamageValidationError("both states must be validated DamageState objects")
    if (
        previous.law_id != current.law_id
        or previous.law_fingerprint != current.law_fingerprint
        or previous.threshold_realization_id != current.threshold_realization_id
        or previous.physical_bond_ids != current.physical_bond_ids
    ):
        raise DamageValidationError("damage transition changed law or bond universe")
    _validate_identity_match(
        profile_id=current.physics_profile_id,
        profile_hash=current.physics_profile_hash,
        reference_state_id=current.reference_state_id,
        expected_profile_id=previous.physics_profile_id,
        expected_profile_hash=previous.physics_profile_hash,
        expected_reference_state_id=previous.reference_state_id,
        context="damage transition",
    )
    for bond_id in previous.physical_bond_ids:
        if not previous.alive_mask[bond_id] and current.alive_mask[bond_id]:
            raise DamageValidationError("healing/reactivation is forbidden")
        if previous.rupture_mask[bond_id] and not current.rupture_mask[bond_id]:
            raise DamageValidationError("rupture mask is irreversible")
        if (
            previous.prescribed_removal_mask[bond_id]
            and not current.prescribed_removal_mask[bond_id]
        ):
            raise DamageValidationError("prescribed removal mask is irreversible")
    if (
        current.initial_threshold_violation_mask
        != previous.initial_threshold_violation_mask
    ):
        raise DamageValidationError(
            "initial threshold violation flags are immutable"
        )
    if current.accepted_material_event_ids[: len(previous.accepted_material_event_ids)] != (
        previous.accepted_material_event_ids
    ):
        raise DamageValidationError("accepted material event history was rewritten")


@dataclass(frozen=True)
class EndpointObservation:
    """One endpoint result, with endpoint-specific admissible evidence."""

    endpoint_name: str
    status: str
    physics_profile_id: str
    physics_profile_hash: str
    reference_state_id: str
    evidence_kind: str
    evidence_id: str | None
    load_coordinate: float | None
    load_coordinate_unit: str | None
    load_coordinate_semantics: str | None
    path_progress: float | None
    progress_unit: str | None
    progress_semantics: str | None
    physical_time: None = None
    physical_time_valid: bool = False
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid endpoint schema_version")
        if self.endpoint_name not in _ENDPOINT_EVIDENCE:
            raise DamageValidationError("unsupported endpoint_name")
        if self.status not in {"observed", "right_censored", "not_evaluated"}:
            raise DamageValidationError("unsupported endpoint status")
        _registered_profile_identity(
            self.physics_profile_id, self.physics_profile_hash
        )
        _nonempty_string(self.reference_state_id, "reference_state_id")
        if self.physical_time is not None or self.physical_time_valid is not False:
            raise DamageValidationError("endpoint cannot carry physical time")
        if self.status == "observed":
            if self.evidence_kind != _ENDPOINT_EVIDENCE[self.endpoint_name]:
                raise DamageValidationError(
                    "endpoint evidence cannot be inferred from another endpoint, connectivity alone, or solver failure"
                )
            _nonempty_string(self.evidence_id, "evidence_id")
            if (
                self.endpoint_name == "damage_initiation"
                and _HASH_RE.fullmatch(self.evidence_id) is None
            ):
                raise DamageValidationError(
                    "damage initiation evidence_id must be a sha256 material-event ID"
                )
            coordinate = _finite_float(self.load_coordinate, "load_coordinate")
            if self.load_coordinate_unit not in _LOAD_UNITS:
                raise DamageValidationError("unsupported load_coordinate_unit")
            object.__setattr__(self, "load_coordinate", coordinate)
            if self.load_coordinate_semantics != "instantaneous_event_control_coordinate":
                raise DamageValidationError("invalid observed load coordinate semantics")
            progress = _finite_float(self.path_progress, "path_progress")
            if progress < 0.0:
                raise DamageValidationError("path_progress must be nonnegative")
            object.__setattr__(self, "path_progress", progress)
            if self.progress_unit != self.load_coordinate_unit:
                raise DamageValidationError(
                    "progress_unit must equal load_coordinate_unit"
                )
            if self.progress_semantics != _PROGRESS_SEMANTICS:
                raise DamageValidationError("invalid path progress semantics")
        elif self.status == "right_censored":
            expected = f"no_{self.endpoint_name}_observed_over_executed_schedule"
            if self.evidence_kind != expected or self.evidence_id is not None:
                raise DamageValidationError("invalid right-censoring evidence")
            coordinate = _finite_float(self.load_coordinate, "load_coordinate")
            if self.load_coordinate_unit not in _LOAD_UNITS:
                raise DamageValidationError("unsupported load_coordinate_unit")
            object.__setattr__(self, "load_coordinate", coordinate)
            if (
                self.load_coordinate_semantics
                != "terminal_control_coordinate_not_path_exposure_bound"
            ):
                raise DamageValidationError(
                    "invalid right-censor load coordinate semantics"
                )
            progress = _finite_float(self.path_progress, "path_progress")
            if progress < 0.0:
                raise DamageValidationError("path_progress must be nonnegative")
            object.__setattr__(self, "path_progress", progress)
            if self.progress_unit != self.load_coordinate_unit:
                raise DamageValidationError(
                    "progress_unit must equal load_coordinate_unit"
                )
            if self.progress_semantics != _PROGRESS_SEMANTICS:
                raise DamageValidationError("invalid path progress semantics")
        else:
            if (
                self.evidence_kind != "not_evaluated"
                or self.evidence_id is not None
                or self.load_coordinate is not None
                or self.load_coordinate_unit is not None
                or self.load_coordinate_semantics is not None
                or self.path_progress is not None
                or self.progress_unit is not None
                or self.progress_semantics is not None
            ):
                raise DamageValidationError("not_evaluated endpoint carries evidence")

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "endpoint_name": self.endpoint_name,
            "status": self.status,
            "physics_profile_id": self.physics_profile_id,
            "physics_profile_hash": self.physics_profile_hash,
            "reference_state_id": self.reference_state_id,
            "evidence_kind": self.evidence_kind,
            "evidence_id": self.evidence_id,
            "load_coordinate": self.load_coordinate,
            "load_coordinate_unit": self.load_coordinate_unit,
            "load_coordinate_semantics": self.load_coordinate_semantics,
            "path_progress": self.path_progress,
            "progress_unit": self.progress_unit,
            "progress_semantics": self.progress_semantics,
            "physical_time": self.physical_time,
            "physical_time_valid": self.physical_time_valid,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "EndpointObservation":
        value = _mapping(value, "endpoint observation")
        _exact_keys(
            value,
            {
                "schema_version",
                "endpoint_name",
                "status",
                "physics_profile_id",
                "physics_profile_hash",
                "reference_state_id",
                "evidence_kind",
                "evidence_id",
                "load_coordinate",
                "load_coordinate_unit",
                "load_coordinate_semantics",
                "path_progress",
                "progress_unit",
                "progress_semantics",
                "physical_time",
                "physical_time_valid",
            },
            "endpoint observation",
        )
        return cls(**dict(value))  # type: ignore[arg-type]


@dataclass(frozen=True)
class TrajectoryFailureEndpoints:
    law_id: str
    law_fingerprint: str
    threshold_realization_id: str
    damage_initiation: EndpointObservation
    load_bearing_connectivity_loss: EndpointObservation
    load_or_stiffness_degradation: EndpointObservation
    mechanical_instability: EndpointObservation
    schema_version: str = DAMAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DAMAGE_SCHEMA_VERSION:
            raise DamageValidationError("invalid failure-endpoint schema_version")
        _nonempty_string(self.law_id, "law_id")
        if _HASH_RE.fullmatch(self.law_fingerprint) is None:
            raise DamageValidationError("law_fingerprint must be a sha256 digest")
        if _HASH_RE.fullmatch(self.threshold_realization_id) is None:
            raise DamageValidationError(
                "threshold_realization_id must be a sha256 digest"
            )
        observations = (
            self.damage_initiation,
            self.load_bearing_connectivity_loss,
            self.load_or_stiffness_degradation,
            self.mechanical_instability,
        )
        expected_names = tuple(_ENDPOINT_EVIDENCE)
        if any(
            not isinstance(observation, EndpointObservation)
            for observation in observations
        ):
            raise DamageValidationError("all failure endpoints must be validated")
        if tuple(observation.endpoint_name for observation in observations) != (
            expected_names
        ):
            raise DamageValidationError("failure endpoint labels are not distinct")
        identity = (
            observations[0].physics_profile_id,
            observations[0].physics_profile_hash,
            observations[0].reference_state_id,
        )
        if any(
            (
                observation.physics_profile_id,
                observation.physics_profile_hash,
                observation.reference_state_id,
            )
            != identity
            for observation in observations[1:]
        ):
            raise DamageValidationError(
                "failure endpoints cannot mix profile/reference identities"
            )

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "law_id": self.law_id,
            "law_fingerprint": self.law_fingerprint,
            "threshold_realization_id": self.threshold_realization_id,
            "damage_initiation": self.damage_initiation.as_record(),
            "load_bearing_connectivity_loss": (
                self.load_bearing_connectivity_loss.as_record()
            ),
            "load_or_stiffness_degradation": (
                self.load_or_stiffness_degradation.as_record()
            ),
            "mechanical_instability": self.mechanical_instability.as_record(),
        }

    @classmethod
    def from_record(
        cls, value: Mapping[str, object]
    ) -> "TrajectoryFailureEndpoints":
        value = _mapping(value, "trajectory failure endpoints")
        _exact_keys(
            value,
            {
                "schema_version",
                "law_id",
                "law_fingerprint",
                "threshold_realization_id",
                "damage_initiation",
                "load_bearing_connectivity_loss",
                "load_or_stiffness_degradation",
                "mechanical_instability",
            },
            "trajectory failure endpoints",
        )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            law_id=value["law_id"],  # type: ignore[arg-type]
            law_fingerprint=value["law_fingerprint"],  # type: ignore[arg-type]
            threshold_realization_id=value[  # type: ignore[arg-type]
                "threshold_realization_id"
            ],
            damage_initiation=EndpointObservation.from_record(
                value["damage_initiation"]  # type: ignore[arg-type]
            ),
            load_bearing_connectivity_loss=EndpointObservation.from_record(
                value["load_bearing_connectivity_loss"]  # type: ignore[arg-type]
            ),
            load_or_stiffness_degradation=EndpointObservation.from_record(
                value["load_or_stiffness_degradation"]  # type: ignore[arg-type]
            ),
            mechanical_instability=EndpointObservation.from_record(
                value["mechanical_instability"]  # type: ignore[arg-type]
            ),
        )


def _not_evaluated_endpoint(
    endpoint_name: str,
    *,
    physics_profile_id: str,
    physics_profile_hash: str,
    reference_state_id: str,
) -> EndpointObservation:
    return EndpointObservation(
        endpoint_name=endpoint_name,
        status="not_evaluated",
        physics_profile_id=physics_profile_id,
        physics_profile_hash=physics_profile_hash,
        reference_state_id=reference_state_id,
        evidence_kind="not_evaluated",
        evidence_id=None,
        load_coordinate=None,
        load_coordinate_unit=None,
        load_coordinate_semantics=None,
        path_progress=None,
        progress_unit=None,
        progress_semantics=None,
    )


def build_failure_endpoints(
    material_events: Sequence[MaterialRuptureEvent],
    *,
    terminal_load_coordinate: float,
    terminal_path_progress: float,
    load_coordinate_unit: str,
    physics_profile_id: str,
    physics_profile_hash: str,
    reference_state_id: str,
    law_id: str,
    law_fingerprint: str,
    threshold_realization_id: str,
    load_bearing_connectivity_loss: EndpointObservation | None = None,
    load_or_stiffness_degradation: EndpointObservation | None = None,
    mechanical_instability: EndpointObservation | None = None,
) -> TrajectoryFailureEndpoints:
    """Build distinct endpoint labels and explicit no-event censoring."""

    terminal_load_coordinate = _finite_float(
        terminal_load_coordinate, "terminal_load_coordinate"
    )
    terminal_path_progress = _finite_float(
        terminal_path_progress, "terminal_path_progress"
    )
    if terminal_path_progress < 0.0:
        raise DamageValidationError("terminal_path_progress must be nonnegative")
    if load_coordinate_unit not in _LOAD_UNITS:
        raise DamageValidationError("unsupported load_coordinate_unit")
    _registered_profile_identity(physics_profile_id, physics_profile_hash)
    _nonempty_string(reference_state_id, "reference_state_id")
    law_id = _nonempty_string(law_id, "law_id")
    if _HASH_RE.fullmatch(law_fingerprint) is None:
        raise DamageValidationError("law_fingerprint must be a sha256 digest")
    if _HASH_RE.fullmatch(threshold_realization_id) is None:
        raise DamageValidationError(
            "threshold_realization_id must be a sha256 digest"
        )
    if isinstance(material_events, (str, bytes)):
        raise DamageValidationError("material_events must be event objects")
    events = tuple(material_events)
    event_ids: set[str] = set()
    ruptured_bond_ids: set[str] = set()
    event_law_identity: tuple[str, str, str] | None = None
    previous_path_progress = -math.inf
    for index, event in enumerate(events):
        if not isinstance(event, MaterialRuptureEvent):
            raise DamageValidationError(
                "excluded origins cannot populate material rupture events"
            )
        if event.sequence_index != index:
            raise DamageValidationError("material events must be in sequence order")
        if event.event_id in event_ids:
            raise DamageValidationError("duplicate material event ID")
        if event.physical_bond_id in ruptured_bond_ids:
            raise DamageValidationError("duplicate rupture of physical bond")
        if event.load_coordinate_unit != load_coordinate_unit:
            raise DamageValidationError(
                "material event load coordinate unit differs from executed schedule"
            )
        if event.progress_unit != load_coordinate_unit:
            raise DamageValidationError(
                "material event progress unit differs from executed schedule"
            )
        if event.path_progress < previous_path_progress:
            raise DamageValidationError(
                "material event path progress must be chronological and nondecreasing"
            )
        if event.path_progress > terminal_path_progress:
            raise DamageValidationError(
                "material event path progress exceeds terminal path progress"
            )
        previous_path_progress = event.path_progress
        identity = (
            event.law_id,
            event.law_fingerprint,
            event.threshold_realization_id,
        )
        if identity != (law_id, law_fingerprint, threshold_realization_id):
            raise DamageValidationError(
                "material events cannot mix damage law or threshold realization"
            )
        if event_law_identity is None:
            event_law_identity = identity
        elif identity != event_law_identity:
            raise DamageValidationError(
                "material events cannot mix damage law or threshold realization"
            )
        event_ids.add(event.event_id)
        ruptured_bond_ids.add(event.physical_bond_id)
        _validate_identity_match(
            profile_id=event.physics_profile_id,
            profile_hash=event.physics_profile_hash,
            reference_state_id=event.reference_state_id,
            expected_profile_id=physics_profile_id,
            expected_profile_hash=physics_profile_hash,
            expected_reference_state_id=reference_state_id,
            context="material event",
        )
    if events:
        first = events[0]
        damage = EndpointObservation(
            endpoint_name="damage_initiation",
            status="observed",
            physics_profile_id=physics_profile_id,
            physics_profile_hash=physics_profile_hash,
            reference_state_id=reference_state_id,
            evidence_kind="accepted_material_rupture",
            evidence_id=first.event_id,
            load_coordinate=first.load_coordinate,
            load_coordinate_unit=first.load_coordinate_unit,
            load_coordinate_semantics="instantaneous_event_control_coordinate",
            path_progress=first.path_progress,
            progress_unit=first.progress_unit,
            progress_semantics=first.progress_semantics,
        )
    else:
        damage = EndpointObservation(
            endpoint_name="damage_initiation",
            status="right_censored",
            physics_profile_id=physics_profile_id,
            physics_profile_hash=physics_profile_hash,
            reference_state_id=reference_state_id,
            evidence_kind="no_damage_initiation_observed_over_executed_schedule",
            evidence_id=None,
            load_coordinate=terminal_load_coordinate,
            load_coordinate_unit=load_coordinate_unit,
            load_coordinate_semantics=(
                "terminal_control_coordinate_not_path_exposure_bound"
            ),
            path_progress=terminal_path_progress,
            progress_unit=load_coordinate_unit,
            progress_semantics=_PROGRESS_SEMANTICS,
        )

    supplied = {
        "load_bearing_connectivity_loss": load_bearing_connectivity_loss,
        "load_or_stiffness_degradation": load_or_stiffness_degradation,
        "mechanical_instability": mechanical_instability,
    }
    completed: dict[str, EndpointObservation] = {}
    for endpoint_name, observation in supplied.items():
        if observation is None:
            observation = _not_evaluated_endpoint(
                endpoint_name,
                physics_profile_id=physics_profile_id,
                physics_profile_hash=physics_profile_hash,
                reference_state_id=reference_state_id,
            )
        if observation.endpoint_name != endpoint_name:
            raise DamageValidationError("failure endpoint was assigned wrong label")
        _validate_identity_match(
            profile_id=observation.physics_profile_id,
            profile_hash=observation.physics_profile_hash,
            reference_state_id=observation.reference_state_id,
            expected_profile_id=physics_profile_id,
            expected_profile_hash=physics_profile_hash,
            expected_reference_state_id=reference_state_id,
            context="failure endpoint",
        )
        if observation.status != "not_evaluated":
            assert observation.path_progress is not None
            if observation.progress_unit != load_coordinate_unit:
                raise DamageValidationError(
                    "failure endpoint progress unit differs from executed schedule"
                )
            if observation.path_progress > terminal_path_progress:
                raise DamageValidationError(
                    "failure endpoint path progress exceeds terminal path progress"
                )
        completed[endpoint_name] = observation
    return TrajectoryFailureEndpoints(
        law_id=law_id,
        law_fingerprint=law_fingerprint,
        threshold_realization_id=threshold_realization_id,
        damage_initiation=damage,
        load_bearing_connectivity_loss=completed[
            "load_bearing_connectivity_loss"
        ],
        load_or_stiffness_degradation=completed[
            "load_or_stiffness_degradation"
        ],
        mechanical_instability=completed["mechanical_instability"],
    )
