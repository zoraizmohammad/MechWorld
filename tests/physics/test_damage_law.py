"""Acceptance tests for the versioned quasi-static damage/event contract."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from pgworld.physics.damage import (  # noqa: E402
    DAMAGE_SCHEMA_VERSION,
    CriterionObservation,
    DamageAssessment,
    DamageLaw,
    DamageState,
    DamageValidationError,
    EndpointObservation,
    ExcludedEventRecord,
    MaterialRuptureEvent,
    RuptureCandidate,
    ThresholdField,
    accept_next_material_rupture,
    apply_excluded_event,
    assess_material_rupture,
    build_failure_endpoints,
    initialize_damage_state,
    materialize_thresholds,
    validate_irreversible_transition,
)


PROFILE_ID = "reviewed_physics_provisional_v0"
PROFILE_HASH = (
    "sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5"
)
REFERENCE_ID = "fixed-cell-equilibrated-fixture-v1"


def _record_hash(record: dict[str, object]) -> str:
    payload = json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _law(
    law_kind: str = "deterministic_threshold",
    *,
    criterion: str = "bond_energy",
    predictor_visibility: str = "visible_to_predictor",
) -> DamageLaw:
    units = {
        "bond_extension_ratio": "dimensionless",
        "bond_tension": "pN",
        "bond_energy": "pN nm",
    }
    return DamageLaw(
        law_id=f"{law_kind}-{criterion}-fixture-v1",
        law_kind=law_kind,
        criterion=criterion,
        criterion_unit=units[criterion],
        base_threshold=10.0,
        distribution=(
            {"kind": "uniform_relative", "relative_half_width": 0.2}
            if law_kind == "quenched_heterogeneous_threshold"
            else None
        ),
        predictor_visibility=predictor_visibility,
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
    )


def _observation(bond_id: str, value: float) -> CriterionObservation:
    return CriterionObservation(
        physical_bond_id=bond_id,
        criterion="bond_energy",
        unit="pN nm",
        value=value,
    )


def _intact_fixture(
    bond_ids: tuple[str, ...] = ("bond-a", "bond-b", "bond-c"),
) -> tuple[DamageLaw, ThresholdField, DamageState]:
    law = _law()
    field = materialize_thresholds(law, bond_ids)
    state = initialize_damage_state(
        law,
        field,
        [_observation(bond_id, 1.0) for bond_id in reversed(bond_ids)],
    )
    return law, field, state


def _endpoint_law_kwargs(
    event: MaterialRuptureEvent | None = None,
) -> dict[str, str]:
    if event is not None:
        return {
            "law_id": event.law_id,
            "law_fingerprint": event.law_fingerprint,
            "threshold_realization_id": event.threshold_realization_id,
        }
    law = _law()
    field = materialize_thresholds(law, ["endpoint-censor-bond"])
    return {
        "law_id": law.law_id,
        "law_fingerprint": law.fingerprint,
        "threshold_realization_id": field.realization_id,
    }


def test_deterministic_threshold_law_is_explicitly_phenomenological() -> None:
    law = DamageLaw(
        law_id="deterministic-energy-fixture-v1",
        law_kind="deterministic_threshold",
        criterion="bond_energy",
        criterion_unit="pN nm",
        base_threshold=12.5,
        distribution=None,
        predictor_visibility="visible_to_predictor",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
    )

    assert law.schema_version == DAMAGE_SCHEMA_VERSION
    assert law.mechanism_claim == (
        "phenomenological_not_experimentally_constrained_molecular_cleavage"
    )
    assert law.accepted_event_source == "material_rupture"
    assert law.load_coordinate_kind == "quasi_static_not_physical_time"
    assert law.physical_time_valid is False


@pytest.mark.parametrize(
    ("criterion", "unit"),
    [
        ("bond_extension_ratio", "dimensionless"),
        ("bond_tension", "pN"),
        ("bond_energy", "pN nm"),
    ],
)
def test_all_reference_criterion_modes_have_exact_units(
    criterion: str, unit: str
) -> None:
    law = _law(criterion=criterion)
    assert law.criterion_unit == unit


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"schema_version": "damage-v0"}, "schema_version"),
        ({"criterion_unit": "J"}, "criterion_unit"),
        ({"base_threshold": float("nan")}, "finite"),
        ({"base_threshold": True}, "finite"),
        ({"physical_time_valid": True}, "physical time"),
        ({"accepted_event_source": "prescribed_intervention"}, "material_rupture"),
        ({"mechanism_claim": "verified molecular cleavage"}, "cannot claim"),
        ({"predictor_visibility": "maybe"}, "visible or hidden"),
        ({"physics_profile_hash": "not-a-hash"}, "sha256"),
        ({"reference_state_id": 42}, "trimmed string"),
    ],
)
def test_law_constructor_rejects_forged_semantics(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(DamageValidationError, match=message):
        replace(_law(), **updates)


def test_law_record_replay_is_exact_and_unknown_fields_fail_closed() -> None:
    law = _law("quenched_heterogeneous_threshold", predictor_visibility="hidden_from_predictor")
    assert DamageLaw.from_record(law.as_record()) == law
    extra = law.as_record()
    extra["biology_certified"] = True
    with pytest.raises(DamageValidationError, match="unexpected"):
        DamageLaw.from_record(extra)
    mutated = law.as_record()
    mutated["distribution"] = {"kind": "uniform_relative", "relative_half_width": 1.0}
    with pytest.raises(DamageValidationError, match="strictly between"):
        DamageLaw.from_record(mutated)


def test_law_requires_a_registered_profile_id_hash_pair() -> None:
    with pytest.raises(DamageValidationError, match="registered physics profile"):
        replace(_law(), physics_profile_hash="sha256:" + "0" * 64)


def test_heterogeneous_thresholds_are_stable_id_keyed_sample_once_and_immutable() -> None:
    law = _law(
        "quenched_heterogeneous_threshold",
        predictor_visibility="hidden_from_predictor",
    )
    first = materialize_thresholds(
        law, ["bond-c", "bond-a", "bond-b"], material_disorder_seed=1729
    )
    reordered_retry = materialize_thresholds(
        law, ["bond-b", "bond-c", "bond-a"], material_disorder_seed=1729
    )

    assert first.as_record() == reordered_retry.as_record()
    assert first.realization_id == reordered_retry.realization_id
    assert first.predictor_visibility == "hidden_from_predictor"
    assert len(set(first.thresholds.values())) == 3
    with pytest.raises(TypeError):
        first.thresholds["bond-a"] = 999.0  # type: ignore[index]
    detached = first.as_record()
    detached["thresholds"][0]["threshold"] = 999.0  # type: ignore[index]
    assert first.threshold_for("bond-a") != 999.0
    second_seed = materialize_thresholds(
        law, ["bond-a", "bond-b", "bond-c"], material_disorder_seed=1730
    )
    assert second_seed.realization_id != first.realization_id


@pytest.mark.parametrize(
    ("bond_ids", "seed", "message"),
    [
        (["bond-a", "bond-a"], 1, "duplicate"),
        (["bond-a", 7], 1, "trimmed string"),
        (["bond-a"], True, "nonnegative integer"),
        ([], 1, "cannot be empty"),
    ],
)
def test_threshold_materialization_rejects_ambiguous_ids_and_seeds(
    bond_ids: list[object], seed: object, message: str
) -> None:
    law = _law("quenched_heterogeneous_threshold")
    with pytest.raises(DamageValidationError, match=message):
        materialize_thresholds(
            law, bond_ids, material_disorder_seed=seed  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid_ids", [{"bond-a"}, {"bond-a": 1}, 17])
def test_stable_id_collections_fail_closed_on_nonsequences(
    invalid_ids: object,
) -> None:
    with pytest.raises(DamageValidationError, match="sequence of stable IDs"):
        materialize_thresholds(
            _law(), invalid_ids  # type: ignore[arg-type]
        )


def test_record_mappings_reject_nonstring_keys_without_raw_sort_errors() -> None:
    record: dict[object, object] = _law().as_record()
    record[7] = "invalid-key"
    with pytest.raises(DamageValidationError, match="keys must be strings"):
        DamageLaw.from_record(record)  # type: ignore[arg-type]


def test_threshold_record_replay_rejects_duplicates_and_tampering() -> None:
    law = _law("quenched_heterogeneous_threshold")
    field = materialize_thresholds(
        law, ["bond-a", "bond-b"], material_disorder_seed=9
    )
    assert ThresholdField.from_record(field.as_record()).as_record() == field.as_record()
    duplicate = field.as_record()
    duplicate["thresholds"].append(dict(duplicate["thresholds"][0]))  # type: ignore[union-attr]
    with pytest.raises(DamageValidationError, match="duplicate"):
        ThresholdField.from_record(duplicate)
    tampered = field.as_record()
    tampered["thresholds"][0]["threshold"] *= 2.0  # type: ignore[index]
    with pytest.raises(DamageValidationError, match="realization_id"):
        ThresholdField.from_record(tampered)
    with pytest.raises(DamageValidationError, match="unknown physical_bond_id"):
        field.threshold_for("bond-z")


def test_criterion_observation_record_replay_is_strict() -> None:
    observation = _observation("bond-a", 3.5)
    assert CriterionObservation.from_record(
        observation.as_record()
    ).as_record() == observation.as_record()
    unexpected = observation.as_record()
    unexpected["physical_time"] = 0.0
    with pytest.raises(DamageValidationError, match="unexpected"):
        CriterionObservation.from_record(unexpected)


def test_damage_state_replay_rejects_string_id_collections() -> None:
    _, _, state = _intact_fixture(("bond-a",))
    physical_ids = state.as_record()
    physical_ids["physical_bond_ids"] = "bond-a"
    with pytest.raises(DamageValidationError, match="sequence of stable IDs"):
        DamageState.from_record(physical_ids)
    event_ids = state.as_record()
    event_ids["accepted_material_event_ids"] = "event-1"
    with pytest.raises(DamageValidationError, match="sequence of stable IDs"):
        DamageState.from_record(event_ids)


def test_damage_state_rejects_nonhash_material_event_ids() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 11.0)],
        phase="accepted_equilibrium",
        control_id="step",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    ruptured = accept_next_material_rupture(state, assessment).state.as_record()
    ruptured["accepted_material_event_ids"] = ["fake"]
    ruptured["first_damage_event_id"] = "fake"
    with pytest.raises(DamageValidationError, match="sha256"):
        DamageState.from_record(ruptured)


def test_invalid_reference_flags_cannot_coexist_with_material_rupture_history() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 11.0)],
        phase="accepted_equilibrium",
        control_id="step",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    record = accept_next_material_rupture(state, assessment).state.as_record()
    record["initial_threshold_violation_mask"] = {"bond-a": True}
    with pytest.raises(DamageValidationError, match="invalid reference"):
        DamageState.from_record(record)


def test_initial_threshold_violation_is_flagged_but_never_damage_initiation() -> None:
    law = _law()
    field = materialize_thresholds(law, ["bond-a", "bond-b"])
    state = initialize_damage_state(
        law, field, [_observation("bond-a", 10.0), _observation("bond-b", 1.0)]
    )
    assert state.initial_threshold_violation_mask == {
        "bond-a": True,
        "bond-b": False,
    }
    assert all(state.alive_mask.values())
    assert not any(state.rupture_mask.values())

    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 12.0), _observation("bond-b", 12.0)],
        phase="accepted_equilibrium",
        control_id="axial-step-1",
        load_coordinate=0.02,
        load_coordinate_unit="dimensionless",
        path_progress=0.02,
    )
    assert assessment.eligible_for_material_rupture is False
    assert assessment.phase == "reference_preparation"
    assert assessment.exclusion_reason == "initial_threshold_violation_invalid_reference"
    assert assessment.candidates == ()
    with pytest.raises(DamageValidationError, match="excluded assessment"):
        accept_next_material_rupture(state, assessment)


def test_accepted_crossings_have_deterministic_ties_and_retry_invariant_event() -> None:
    law, field, state = _intact_fixture()
    observations = [
        _observation("bond-c", 11.0),
        _observation("bond-b", 12.0),
        _observation("bond-a", 12.0),
    ]
    assessment = assess_material_rupture(
        law,
        field,
        state,
        observations,
        phase="accepted_equilibrium",
        control_id="axial-step-2",
        load_coordinate=0.04,
        load_coordinate_unit="dimensionless",
        path_progress=0.04,
    )
    retry = assess_material_rupture(
        law,
        field,
        state,
        list(reversed(observations)),
        phase="accepted_equilibrium",
        control_id="axial-step-2",
        load_coordinate=0.04,
        load_coordinate_unit="dimensionless",
        path_progress=0.04,
    )

    assert [candidate.physical_bond_id for candidate in assessment.candidates] == [
        "bond-a",
        "bond-b",
        "bond-c",
    ]
    assert retry.as_record() == assessment.as_record()
    first = accept_next_material_rupture(state, assessment)
    retried = accept_next_material_rupture(state, retry)
    assert retried.event.as_record() == first.event.as_record()
    assert retried.state.as_record() == first.state.as_record()
    assert first.event.is_damage_initiation is True
    assert first.state.alive_mask["bond-a"] is False
    assert first.state.rupture_mask["bond-a"] is True
    assert first.state.first_damage_event_id == first.event.event_id
    validate_irreversible_transition(state, first.state)
    with pytest.raises(DamageValidationError, match="stale"):
        accept_next_material_rupture(first.state, assessment)
    with pytest.raises(DamageValidationError, match="healing"):
        validate_irreversible_transition(first.state, state)
    with pytest.raises(DamageValidationError, match="pre-state"):
        replace(first, previous_state_id="sha256:" + "0" * 64)


def test_transition_constructor_binds_event_to_exact_resulting_rupture_mask() -> None:
    law, field, state = _intact_fixture(("bond-a", "bond-b"))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 12.0), _observation("bond-b", 11.0)],
        phase="accepted_equilibrium",
        control_id="step",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    transition = accept_next_material_rupture(state, assessment)
    forged = replace(
        transition.state,
        alive_mask={"bond-a": True, "bond-b": False},
        rupture_mask={"bond-a": False, "bond-b": True},
    )
    with pytest.raises(DamageValidationError, match="event bond"):
        replace(transition, state=forged)
    with pytest.raises(DamageValidationError, match="event history"):
        replace(transition, state=state)


@pytest.mark.parametrize(
    ("phase", "reason"),
    [
        ("reference_preparation", "not_a_damage_event"),
        ("rejected_numerical_trial", "rejected_trial"),
        ("solver_error", "solver_error_not_physical_failure"),
    ],
)
def test_nonaccepted_phases_cannot_create_material_events(
    phase: str, reason: str
) -> None:
    law, field, state = _intact_fixture()
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation(bond_id, 100.0) for bond_id in state.physical_bond_ids],
        phase=phase,
        control_id="trial-1",
        load_coordinate=0.02,
        load_coordinate_unit="dimensionless",
        path_progress=0.02,
    )
    assert assessment.candidates == ()
    assert assessment.eligible_for_material_rupture is False
    assert reason in assessment.exclusion_reason


def test_assessment_replay_rejects_noncanonical_exclusion_reason() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 100.0)],
        phase="solver_error",
        control_id="failed-trial",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    record = assessment.as_record()
    record["exclusion_reason"] = "physical_failure"
    body = dict(record)
    body.pop("assessment_id")
    record["assessment_id"] = _record_hash(body)
    with pytest.raises(DamageValidationError, match="canonical exclusion_reason"):
        DamageAssessment.from_record(record)


def test_observations_require_exact_alive_stable_ids_and_units() -> None:
    law, field, state = _intact_fixture(("bond-a", "bond-b"))
    with pytest.raises(DamageValidationError, match="duplicate"):
        assess_material_rupture(
            law,
            field,
            state,
            [_observation("bond-a", 1.0), _observation("bond-a", 1.0)],
            phase="accepted_equilibrium",
            control_id="step",
            load_coordinate=0.0,
            load_coordinate_unit="dimensionless",
            path_progress=0.0,
        )
    with pytest.raises(DamageValidationError, match="unit mismatch"):
        CriterionObservation("bond-a", "bond_energy", "J", 1.0)
    with pytest.raises(DamageValidationError, match="finite"):
        CriterionObservation("bond-a", "bond_energy", "pN nm", float("inf"))
    with pytest.raises(DamageValidationError, match="finite"):
        CriterionObservation("bond-a", "bond_energy", "pN nm", False)


def test_profile_and_reference_mixing_fail_before_assessment() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    with pytest.raises(DamageValidationError, match="registered physics profile"):
        replace(state, physics_profile_id="other_profile")
    with pytest.raises(DamageValidationError, match="mix physics profile"):
        assess_material_rupture(
            law,
            field,
            replace(state, reference_state_id="reset-reference"),
            [_observation("bond-a", 1.0)],
            phase="accepted_equilibrium",
            control_id="step",
            load_coordinate=0.0,
            load_coordinate_unit="dimensionless",
            path_progress=0.0,
        )


def test_acceptance_rejects_forged_cross_law_assessment_and_unknown_bond() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 11.0)],
        phase="accepted_equilibrium",
        control_id="step",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    record = assessment.as_record()
    candidate_record = dict(record["candidates"][0])  # type: ignore[index]
    candidate_record["law_id"] = "foreign-law"
    candidate_record["threshold_realization_id"] = "sha256:" + "1" * 64
    candidate_body = dict(candidate_record)
    candidate_body.pop("candidate_id")
    candidate_record["candidate_id"] = _record_hash(candidate_body)
    record["law_id"] = "foreign-law"
    record["threshold_realization_id"] = "sha256:" + "1" * 64
    record["candidates"] = [candidate_record]
    assessment_body = dict(record)
    assessment_body.pop("assessment_id")
    record["assessment_id"] = _record_hash(assessment_body)
    forged = DamageAssessment.from_record(record)
    with pytest.raises(DamageValidationError, match="law/threshold realization"):
        accept_next_material_rupture(state, forged)

    unknown_record = assessment.as_record()
    unknown_candidate = dict(unknown_record["candidates"][0])  # type: ignore[index]
    unknown_candidate["physical_bond_id"] = "bond-z"
    unknown_body = dict(unknown_candidate)
    unknown_body.pop("candidate_id")
    unknown_candidate["candidate_id"] = _record_hash(unknown_body)
    unknown_record["candidates"] = [unknown_candidate]
    unknown_assessment_body = dict(unknown_record)
    unknown_assessment_body.pop("assessment_id")
    unknown_record["assessment_id"] = _record_hash(unknown_assessment_body)
    unknown_assessment = DamageAssessment.from_record(unknown_record)
    with pytest.raises(DamageValidationError, match="unknown physical bond"):
        accept_next_material_rupture(state, unknown_assessment)


def test_assessment_replay_rejects_noncanonical_candidate_order() -> None:
    law, field, state = _intact_fixture(("bond-a", "bond-b"))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 12.0), _observation("bond-b", 11.0)],
        phase="accepted_equilibrium",
        control_id="step",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    record = assessment.as_record()
    reversed_rows: list[dict[str, object]] = []
    for rank, source in enumerate(reversed(record["candidates"])):  # type: ignore[arg-type]
        row = dict(source)
        row["rank"] = rank
        body = dict(row)
        body.pop("candidate_id")
        row["candidate_id"] = _record_hash(body)
        reversed_rows.append(row)
    record["candidates"] = reversed_rows
    body = dict(record)
    body.pop("assessment_id")
    record["assessment_id"] = _record_hash(body)
    with pytest.raises(DamageValidationError, match="canonical candidate order"):
        DamageAssessment.from_record(record)


def test_prescribed_removal_is_irreversible_but_not_material_rupture() -> None:
    _, _, state = _intact_fixture(("bond-a", "bond-b"))
    event = ExcludedEventRecord.create(
        source="prescribed_intervention",
        event_kind="prescribed_removal",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        accepted=True,
        physical_bond_id="bond-a",
        old_alive=True,
        new_alive=False,
    )
    updated = apply_excluded_event(state, event)
    assert event.counts_as_damage_initiation is False
    assert updated.alive_mask["bond-a"] is False
    assert updated.prescribed_removal_mask["bond-a"] is True
    assert updated.rupture_mask["bond-a"] is False
    assert updated.first_damage_event_id is None
    validate_irreversible_transition(state, updated)
    with pytest.raises(DamageValidationError, match="inactive bond"):
        apply_excluded_event(updated, event)


def test_excluded_event_record_replay_is_hash_bound_and_weakening_checks_bond() -> None:
    _, _, state = _intact_fixture(("bond-a",))
    event = ExcludedEventRecord.create(
        source="prescribed_intervention",
        event_kind="prescribed_weakening",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        accepted=True,
        physical_bond_id="bond-z",
        old_alive=True,
        new_alive=True,
    )
    record = event.as_record()
    assert ExcludedEventRecord.from_record(record).as_record() == record
    tampered = dict(record)
    tampered["event_kind"] = "prescribed_removal"
    tampered["new_alive"] = False
    with pytest.raises(DamageValidationError, match="event_id"):
        ExcludedEventRecord.from_record(tampered)
    with pytest.raises(DamageValidationError, match="unknown bond"):
        apply_excluded_event(state, event)


@pytest.mark.parametrize(
    ("source", "event_kind", "accepted"),
    [
        ("computational_neighbor_change", "computational_neighbor_change", True),
        ("rendering_change", "rendering_change", True),
        ("solver_error", "solver_error", False),
    ],
)
def test_computational_render_and_solver_events_never_mutate_damage(
    source: str, event_kind: str, accepted: bool
) -> None:
    _, _, state = _intact_fixture(("bond-a",))
    event = ExcludedEventRecord.create(
        source=source,
        event_kind=event_kind,
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        accepted=accepted,
    )
    assert event.counts_as_damage_initiation is False
    assert apply_excluded_event(state, event) is state


def test_initial_violation_flags_are_immutable_across_transitions() -> None:
    _, _, state = _intact_fixture(("bond-a",))
    forged = replace(
        state, initial_threshold_violation_mask={"bond-a": True}
    )
    with pytest.raises(DamageValidationError, match="initial threshold violation"):
        validate_irreversible_transition(state, forged)


def test_excluded_event_constructor_rejects_source_relabeling_and_physical_mutation() -> None:
    with pytest.raises(DamageValidationError, match="source/kind mismatch"):
        ExcludedEventRecord.create(
            source="rendering_change",
            event_kind="computational_neighbor_change",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            accepted=True,
        )
    with pytest.raises(DamageValidationError, match="cannot mutate physical bonds"):
        ExcludedEventRecord.create(
            source="computational_neighbor_change",
            event_kind="computational_neighbor_change",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            accepted=True,
            physical_bond_id="bond-a",
            old_alive=True,
            new_alive=False,
        )
    with pytest.raises(DamageValidationError, match="not accepted"):
        ExcludedEventRecord.create(
            source="solver_error",
            event_kind="solver_error",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            accepted=True,
        )


def _first_material_event() -> MaterialRuptureEvent:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 11.0)],
        phase="accepted_equilibrium",
        control_id="step-1",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    return accept_next_material_rupture(state, assessment).event


def test_no_material_event_is_explicitly_right_censored() -> None:
    endpoints = build_failure_endpoints(
        [],
        terminal_load_coordinate=0.25,
        terminal_path_progress=0.25,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(),
    )
    assert endpoints.damage_initiation.status == "right_censored"
    assert endpoints.damage_initiation.load_coordinate == 0.25
    assert endpoints.damage_initiation.evidence_kind == (
        "no_damage_initiation_observed_over_executed_schedule"
    )
    assert endpoints.damage_initiation.path_progress == 0.25
    assert endpoints.damage_initiation.progress_semantics == (
        "cumulative_absolute_lambda_increment"
    )
    assert endpoints.load_bearing_connectivity_loss.status == "not_evaluated"
    assert endpoints.load_or_stiffness_degradation.status == "not_evaluated"
    assert endpoints.mechanical_instability.status == "not_evaluated"


def test_cyclic_censor_keeps_terminal_lambda_separate_from_monotone_progress() -> None:
    endpoints = build_failure_endpoints(
        [],
        terminal_load_coordinate=0.0,
        terminal_path_progress=0.4,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(),
    )
    censor = endpoints.damage_initiation
    assert censor.status == "right_censored"
    assert censor.load_coordinate == 0.0
    assert censor.load_coordinate_semantics == (
        "terminal_control_coordinate_not_path_exposure_bound"
    )
    assert censor.path_progress == 0.4
    assert censor.progress_unit == "dimensionless"
    assert censor.progress_semantics == "cumulative_absolute_lambda_increment"


def test_first_accepted_material_event_alone_defines_damage_initiation() -> None:
    event = _first_material_event()
    endpoints = build_failure_endpoints(
        [event],
        terminal_load_coordinate=0.25,
        terminal_path_progress=0.25,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(event),
    )
    assert endpoints.damage_initiation.status == "observed"
    assert endpoints.damage_initiation.evidence_id == event.event_id
    assert endpoints.damage_initiation.load_coordinate == 0.1
    assert endpoints.damage_initiation.path_progress == 0.1

    excluded = ExcludedEventRecord.create(
        source="prescribed_intervention",
        event_kind="prescribed_removal",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        accepted=True,
        physical_bond_id="bond-z",
        old_alive=True,
        new_alive=False,
    )
    with pytest.raises(DamageValidationError, match="excluded origins"):
        build_failure_endpoints(
            [excluded],  # type: ignore[list-item]
            terminal_load_coordinate=0.25,
            terminal_path_progress=0.25,
            load_coordinate_unit="dimensionless",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            **_endpoint_law_kwargs(),
        )


def test_material_event_serialization_binds_prestate_assessment_law_and_thresholds() -> None:
    event = _first_material_event()
    assert {
        "pre_state_id",
        "assessment_id",
        "law_id",
        "law_fingerprint",
        "threshold_realization_id",
    } <= set(event.as_record())


def test_endpoint_builder_rejects_duplicate_bonds_and_mixed_load_units() -> None:
    first = _first_material_event()
    duplicate_record = first.as_record()
    duplicate_record["sequence_index"] = 1
    duplicate_record["is_damage_initiation"] = False
    duplicate_body = dict(duplicate_record)
    duplicate_body.pop("event_id")
    duplicate_record["event_id"] = _record_hash(duplicate_body)
    duplicate = MaterialRuptureEvent.from_record(duplicate_record)
    with pytest.raises(DamageValidationError, match="duplicate.*bond"):
        build_failure_endpoints(
            [first, duplicate],
            terminal_load_coordinate=0.25,
            terminal_path_progress=0.25,
            load_coordinate_unit="dimensionless",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            **_endpoint_law_kwargs(first),
        )


def test_endpoint_builder_rejects_mixed_law_and_threshold_realizations() -> None:
    law, field, state = _intact_fixture(("bond-a", "bond-b"))
    first_assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 12.0), _observation("bond-b", 1.0)],
        phase="accepted_equilibrium",
        control_id="step-1",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    first = accept_next_material_rupture(state, first_assessment)
    second_assessment = assess_material_rupture(
        law,
        field,
        first.state,
        [_observation("bond-b", 12.0)],
        phase="accepted_equilibrium",
        control_id="step-2",
        load_coordinate=0.2,
        load_coordinate_unit="dimensionless",
        path_progress=0.2,
    )
    second = accept_next_material_rupture(first.state, second_assessment).event
    foreign_record = second.as_record()
    foreign_record["law_id"] = "foreign-law"
    foreign_record["law_fingerprint"] = "sha256:" + "3" * 64
    foreign_record["threshold_realization_id"] = "sha256:" + "4" * 64
    foreign_body = dict(foreign_record)
    foreign_body.pop("event_id")
    foreign_record["event_id"] = _record_hash(foreign_body)
    foreign = MaterialRuptureEvent.from_record(foreign_record)
    with pytest.raises(DamageValidationError, match="mix damage law"):
        build_failure_endpoints(
            [first.event, foreign],
            terminal_load_coordinate=0.25,
            terminal_path_progress=0.25,
            load_coordinate_unit="dimensionless",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            **_endpoint_law_kwargs(first.event),
        )
    with pytest.raises(DamageValidationError, match="load coordinate unit"):
        build_failure_endpoints(
            [first.event],
            terminal_load_coordinate=0.25,
            terminal_path_progress=0.25,
            load_coordinate_unit="pN/nm^2",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            **_endpoint_law_kwargs(first.event),
        )


def test_connectivity_load_degradation_and_instability_require_distinct_evidence() -> None:
    connectivity = EndpointObservation(
        endpoint_name="load_bearing_connectivity_loss",
        status="observed",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        evidence_kind="predeclared_load_bearing_connectivity_analysis",
        evidence_id="connectivity-analysis-7",
        load_coordinate=0.14,
        load_coordinate_unit="dimensionless",
        load_coordinate_semantics="instantaneous_event_control_coordinate",
        path_progress=0.14,
        progress_unit="dimensionless",
        progress_semantics="cumulative_absolute_lambda_increment",
    )
    degradation = EndpointObservation(
        endpoint_name="load_or_stiffness_degradation",
        status="observed",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        evidence_kind="predeclared_load_or_stiffness_criterion",
        evidence_id="stiffness-criterion-3",
        load_coordinate=0.16,
        load_coordinate_unit="dimensionless",
        load_coordinate_semantics="instantaneous_event_control_coordinate",
        path_progress=0.16,
        progress_unit="dimensionless",
        progress_semantics="cumulative_absolute_lambda_increment",
    )
    instability = EndpointObservation(
        endpoint_name="mechanical_instability",
        status="observed",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        evidence_kind="predeclared_mechanical_stability_criterion",
        evidence_id="stability-analysis-4",
        load_coordinate=0.20,
        load_coordinate_unit="dimensionless",
        load_coordinate_semantics="instantaneous_event_control_coordinate",
        path_progress=0.20,
        progress_unit="dimensionless",
        progress_semantics="cumulative_absolute_lambda_increment",
    )
    endpoints = build_failure_endpoints(
        [],
        terminal_load_coordinate=0.25,
        terminal_path_progress=0.25,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(),
        load_bearing_connectivity_loss=connectivity,
        load_or_stiffness_degradation=degradation,
        mechanical_instability=instability,
    )
    assert [
        endpoints.damage_initiation.endpoint_name,
        endpoints.load_bearing_connectivity_loss.endpoint_name,
        endpoints.load_or_stiffness_degradation.endpoint_name,
        endpoints.mechanical_instability.endpoint_name,
    ] == [
        "damage_initiation",
        "load_bearing_connectivity_loss",
        "load_or_stiffness_degradation",
        "mechanical_instability",
    ]
    with pytest.raises(DamageValidationError, match="connectivity alone, or solver failure"):
        EndpointObservation(
            endpoint_name="mechanical_instability",
            status="observed",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            evidence_kind="minimizer_nonconvergence",
            evidence_id="solver-error-2",
            load_coordinate=0.18,
            load_coordinate_unit="dimensionless",
            load_coordinate_semantics="instantaneous_event_control_coordinate",
            path_progress=0.18,
            progress_unit="dimensionless",
            progress_semantics="cumulative_absolute_lambda_increment",
        )


def test_damage_initiation_endpoint_requires_a_material_event_hash() -> None:
    with pytest.raises(DamageValidationError, match="sha256 material-event"):
        EndpointObservation(
            endpoint_name="damage_initiation",
            status="observed",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            evidence_kind="accepted_material_rupture",
            evidence_id="fake",
            load_coordinate=0.1,
            load_coordinate_unit="dimensionless",
            load_coordinate_semantics="instantaneous_event_control_coordinate",
            path_progress=0.1,
            progress_unit="dimensionless",
            progress_semantics="cumulative_absolute_lambda_increment",
        )


def test_all_primary_records_round_trip_and_reject_tampered_sources() -> None:
    law, field, state = _intact_fixture(("bond-a",))
    assessment = assess_material_rupture(
        law,
        field,
        state,
        [_observation("bond-a", 11.0)],
        phase="accepted_equilibrium",
        control_id="step-1",
        load_coordinate=0.1,
        load_coordinate_unit="dimensionless",
        path_progress=0.1,
    )
    transition = accept_next_material_rupture(state, assessment)
    endpoint = build_failure_endpoints(
        [transition.event],
        terminal_load_coordinate=0.2,
        terminal_path_progress=0.2,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(transition.event),
    ).damage_initiation

    assert DamageState.from_record(state.as_record()).as_record() == state.as_record()
    assert DamageAssessment.from_record(assessment.as_record()).as_record() == assessment.as_record()
    assert RuptureCandidate.from_record(
        assessment.candidates[0].as_record()
    ).as_record() == assessment.candidates[0].as_record()
    assert MaterialRuptureEvent.from_record(
        transition.event.as_record()
    ).as_record() == transition.event.as_record()
    assert EndpointObservation.from_record(endpoint.as_record()).as_record() == endpoint.as_record()

    candidate_record = assessment.candidates[0].as_record()
    candidate_record["event_source"] = "prescribed_intervention"
    with pytest.raises(DamageValidationError, match="material_rupture"):
        RuptureCandidate.from_record(candidate_record)
    event_record = transition.event.as_record()
    event_record["new_alive"] = True
    with pytest.raises(DamageValidationError, match="alive-to-dead"):
        MaterialRuptureEvent.from_record(event_record)
    endpoint_record = build_failure_endpoints(
        [],
        terminal_load_coordinate=0.2,
        terminal_path_progress=0.2,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(),
    ).mechanical_instability.as_record()
    endpoint_record["physics_profile_id"] = "legacy_python_2026_03_12_v1"
    endpoint_record["physics_profile_hash"] = (
        "sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b"
    )
    replayed = EndpointObservation.from_record(endpoint_record)
    with pytest.raises(DamageValidationError, match="mix physics profile"):
        build_failure_endpoints(
            [],
            terminal_load_coordinate=0.2,
            terminal_path_progress=0.2,
            load_coordinate_unit="dimensionless",
            physics_profile_id=PROFILE_ID,
            physics_profile_hash=PROFILE_HASH,
            reference_state_id=REFERENCE_ID,
            **_endpoint_law_kwargs(),
            mechanical_instability=replayed,
        )


def test_trajectory_failure_endpoint_record_replay_is_strict() -> None:
    endpoints = build_failure_endpoints(
        [],
        terminal_load_coordinate=0.25,
        terminal_path_progress=0.25,
        load_coordinate_unit="dimensionless",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
        **_endpoint_law_kwargs(),
    )
    record = endpoints.as_record()
    assert type(endpoints).from_record(record).as_record() == record
    record["unexpected"] = True
    with pytest.raises(DamageValidationError, match="unexpected"):
        type(endpoints).from_record(record)
