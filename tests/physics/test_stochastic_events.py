"""P02-05 sample-once material-disorder and conditional-replicate contract."""

from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import json
from types import MappingProxyType

import pytest

from pgworld.physics.damage import (
    CriterionObservation,
    DamageLaw,
    ThresholdField,
    assess_material_rupture,
    initialize_damage_state,
)
from pgworld.physics.stochasticity import (
    EVENT_PROCESS_DISABLED,
    MATERIAL_SAMPLING_BACKEND,
    ConditionalReplicate,
    ConditionalReplicateCohort,
    PredictorReplicateView,
    RNGNamespaceRecord,
    StochasticityValidationError,
    build_conditional_material_cohort,
    build_quenched_replicate,
)


PROFILE_ID = "reviewed_physics_provisional_v0"
PROFILE_HASH = (
    "sha256:22bde60ac1400a9627e520dad9d3e501f2328ab7b3c80315f61d0b7cddd9aba5"
)
REFERENCE_ID = "fixed-cell-equilibrated-stochastic-fixture-v1"
BONDS = ("bond-a", "bond-b", "bond-c")
GRAPH_HASH = "sha256:" + "1" * 64
GEOMETRY_ID = "sha256:" + "2" * 64
OBSERVABLE_STATE_ID = "sha256:" + "3" * 64


def _record_hash(record: dict[str, object]) -> str:
    payload = json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _law(
    *,
    visibility: str = "hidden_from_predictor",
    reference_state_id: str = REFERENCE_ID,
    criterion: str = "bond_energy",
    relative_half_width: float = 0.2,
) -> DamageLaw:
    units = {
        "bond_extension_ratio": "dimensionless",
        "bond_tension": "pN",
        "bond_energy": "pN nm",
    }
    return DamageLaw(
        law_id=f"quenched-{criterion}-fixture-v1",
        law_kind="quenched_heterogeneous_threshold",
        criterion=criterion,
        criterion_unit=units[criterion],
        base_threshold=10.0,
        distribution={
            "kind": "uniform_relative",
            "relative_half_width": relative_half_width,
        },
        predictor_visibility=visibility,
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=reference_state_id,
    )


def _seeds(
    *,
    geometry: int = 11,
    material_disorder: int = 22,
    events: int = 33,
    model_training: int = 44,
) -> RNGNamespaceRecord:
    return RNGNamespaceRecord.from_p01_04_mapping(
        {
            "geometry": geometry,
            "material_disorder": material_disorder,
            "events": events,
            "model_training": model_training,
        }
    )


def _replicate(
    *,
    index: int = 0,
    material_seed: int = 22,
    event_seed: int = 33,
    geometry_seed: int = 11,
    model_training_seed: int = 44,
    visibility: str = "hidden_from_predictor",
    bonds: tuple[str, ...] = BONDS,
    parent_network_id: str = "parent-network-fixture-v1",
    graph_identity_hash: str = GRAPH_HASH,
    geometry_realization_id: str = GEOMETRY_ID,
    conditioned_observable_state_id: str = OBSERVABLE_STATE_ID,
    cohort_id: str = "conditional-material-fixture-v1",
    law: DamageLaw | None = None,
) -> ConditionalReplicate:
    return build_quenched_replicate(
        cohort_id=cohort_id,
        replicate_index=index,
        parent_network_id=parent_network_id,
        graph_identity_hash=graph_identity_hash,
        geometry_realization_id=geometry_realization_id,
        conditioned_observable_state_id=conditioned_observable_state_id,
        physical_bond_ids=bonds,
        rng_namespace=_seeds(
            geometry=geometry_seed,
            material_disorder=material_seed,
            events=event_seed,
            model_training=model_training_seed,
        ),
        law=law or _law(visibility=visibility),
    )


def _cohort() -> ConditionalReplicateCohort:
    return build_conditional_material_cohort(
        (_replicate(index=1, material_seed=222), _replicate(index=0, material_seed=22))
    )


def _rewrite_hash(record: dict[str, object], id_key: str) -> None:
    body = copy.deepcopy(record)
    body.pop(id_key)
    record[id_key] = _record_hash(body)


def _walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key.lower())
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def test_p01_04_seed_mapping_is_exact_stable_and_allows_coincident_values() -> None:
    record = RNGNamespaceRecord.from_p01_04_mapping(
        {
            "geometry": 7,
            "material_disorder": 7,
            "events": 7,
            "model_training": 7,
        }
    )
    assert record.as_seed_mapping() == {
        "geometry": 7,
        "material_disorder": 7,
        "events": 7,
        "model_training": 7,
    }
    assert record.namespace_version == "pgworld-pg-rng-v1"
    assert record.roles == (
        "geometry",
        "material_disorder",
        "events",
        "model_training",
    )

    with pytest.raises(StochasticityValidationError, match="keys mismatch"):
        RNGNamespaceRecord.from_p01_04_mapping(
            {"geometry": 1, "material_disorder": 2, "events": 3}
        )


def test_rng_namespace_consumes_the_actual_p01_04_record_without_drift() -> None:
    import assemble_pg_network as pg_network

    upstream = pg_network.RNGSeeds.from_master(20261001)
    record = RNGNamespaceRecord.from_p01_04_mapping(upstream.as_dict())

    assert pg_network.RNG_STREAM_NAMES == record.roles
    assert record.as_seed_mapping() == upstream.as_dict() == {
        "geometry": 3876982929329587919,
        "material_disorder": 13958106370667869940,
        "events": 5767726254553140904,
        "model_training": 8271043746876790297,
    }
    with pytest.raises(StochasticityValidationError, match="keys mismatch"):
        RNGNamespaceRecord.from_p01_04_mapping(
            {
                "geometry": 1,
                "material_disorder": 2,
                "events": 3,
                "model_training": 4,
                "master_seed": 5,
            }
        )
    with pytest.raises(StochasticityValidationError, match="mapping"):
        RNGNamespaceRecord.from_p01_04_mapping([1, 2, 3, 4])  # type: ignore[arg-type]
    with pytest.raises(StochasticityValidationError, match="nonnegative integer"):
        RNGNamespaceRecord.from_p01_04_mapping(
            {
                "geometry": True,
                "material_disorder": 2,
                "events": 3,
                "model_training": 4,
            }
        )


def test_materialization_delegates_to_p02_02_and_is_order_retry_invariant() -> None:
    first = _replicate(bonds=("bond-c", "bond-a", "bond-b"))
    retry = _replicate(bonds=("bond-b", "bond-c", "bond-a"))
    extended = _replicate(
        bonds=("bond-z", "bond-c", "bond-a", "bond-b"),
        graph_identity_hash="sha256:" + "7" * 64,
        geometry_realization_id="sha256:" + "8" * 64,
        conditioned_observable_state_id="sha256:" + "9" * 64,
    )

    assert first.physical_bond_ids == BONDS
    assert first.threshold_field.as_record() == retry.threshold_field.as_record()
    assert {
        bond_id: extended.threshold_field.threshold_for(bond_id)
        for bond_id in BONDS
    } == dict(first.threshold_field.thresholds)
    assert first.material_sampling_backend == MATERIAL_SAMPLING_BACKEND
    assert first.threshold_field.material_disorder_seed == 22
    assert first.threshold_field.material_disorder_seed != first.rng_namespace.events_seed


def test_rejected_solver_and_localization_retries_do_not_resample_opportunities() -> None:
    replicate = _replicate()
    field_before = replicate.threshold_field.as_record()
    law = replicate.damage_law
    observations = [
        CriterionObservation(bond_id, law.criterion, law.criterion_unit, 100.0)
        for bond_id in BONDS
    ]
    state = initialize_damage_state(
        law,
        replicate.threshold_field,
        [
            CriterionObservation(bond_id, law.criterion, law.criterion_unit, 1.0)
            for bond_id in BONDS
        ],
    )

    rejected = assess_material_rupture(
        law,
        replicate.threshold_field,
        state,
        observations,
        phase="rejected_numerical_trial",
        control_id="trial-control",
        load_coordinate=0.2,
        load_coordinate_unit="dimensionless",
        path_progress=0.2,
    )
    retry = assess_material_rupture(
        law,
        replicate.threshold_field,
        state,
        list(reversed(observations)),
        phase="rejected_numerical_trial",
        control_id="trial-control",
        load_coordinate=0.2,
        load_coordinate_unit="dimensionless",
        path_progress=0.2,
    )
    solver_error = assess_material_rupture(
        law,
        replicate.threshold_field,
        state,
        observations,
        phase="solver_error",
        control_id="trial-control",
        load_coordinate=0.2,
        load_coordinate_unit="dimensionless",
        path_progress=0.2,
    )

    assert rejected.as_record() == retry.as_record()
    assert rejected.candidates == solver_error.candidates == ()
    assert replicate.threshold_field.as_record() == field_before
    assert replicate.events_seed_consumed is False
    assert not hasattr(replicate, "event_rng_state")
    assert not hasattr(replicate, "event_draw_count")


def test_event_seed_is_reserved_and_cannot_change_quenched_outcomes() -> None:
    first = _replicate(event_seed=33)
    changed_event_seed = _replicate(event_seed=999)
    assert first.threshold_field.thresholds == changed_event_seed.threshold_field.thresholds
    assert first.threshold_field.realization_id == changed_event_seed.threshold_field.realization_id
    assert first.event_process_kind == EVENT_PROCESS_DISABLED
    assert first.events_seed_consumed is False
    assert first.event_process_exposure_unit is None


def test_material_seed_changes_hidden_field_under_one_observable_condition() -> None:
    first = _replicate(index=0, material_seed=22)
    second = _replicate(index=1, material_seed=222)
    assert first.conditioned_observable_state_id == second.conditioned_observable_state_id
    assert first.graph_identity_hash == second.graph_identity_hash
    assert first.threshold_field.realization_id != second.threshold_field.realization_id
    assert first.threshold_field.thresholds != second.threshold_field.thresholds
    assert first.predictor_view().as_record() == second.predictor_view().as_record()


def test_hidden_predictor_projection_is_an_exact_recursive_allowlist() -> None:
    replicate = _replicate()
    view = replicate.predictor_view()
    record = view.as_record()
    view.validate_against(replicate)

    assert set(record) == {
        "schema_version",
        "projection_id",
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

    forbidden_fragments = (
        "seed",
        "namespace",
        "replicate",
        "cohort",
        "realization",
        "graph_identity",
        "threshold",
        "private",
        "event_rng",
        "draw_count",
        "future",
        "outcome",
    )
    assert all(
        not any(fragment in key for fragment in forbidden_fragments)
        for key in _walk_keys(record)
    )
    serialized = json.dumps(record, sort_keys=True)
    for secret in (
        replicate.threshold_field.realization_id,
        replicate.replicate_id,
        replicate.rng_namespace.namespace_id,
        replicate.graph_identity_hash,
        replicate.geometry_realization_id,
        replicate.conditioned_observable_state_id,
    ):
        assert secret not in serialized


def test_visible_threshold_projection_exposes_only_declared_values_not_seeds() -> None:
    replicate = _replicate(visibility="visible_to_predictor")
    record = replicate.predictor_view().as_record()
    assert record["threshold_values"] == [
        {
            "physical_bond_id": bond_id,
            "unit": "pN nm",
            "value": replicate.threshold_field.threshold_for(bond_id),
        }
        for bond_id in BONDS
    ]
    keys = _walk_keys(record)
    assert not any("seed" in key or "realization" in key for key in keys)
    assert replicate.threshold_field.realization_id not in json.dumps(record)


def test_predictor_projection_validation_rejects_unbound_self_consistent_view() -> None:
    replicate = _replicate()
    body = replicate.predictor_view().as_record()
    body["criterion"] = "bond_tension"
    body["criterion_unit"] = "pN"
    _rewrite_hash(body, "projection_id")
    forged = PredictorReplicateView.from_record(body)
    with pytest.raises(StochasticityValidationError, match="derived from replicate"):
        forged.validate_against(replicate)


def test_conditional_material_cohort_is_canonical_and_varies_only_material_seed() -> None:
    cohort = _cohort()
    assert tuple(r.replicate_index for r in cohort.replicates) == (0, 1)
    assert cohort.variation_axis == "hidden_quenched_material_disorder"
    assert len({r.rng_namespace.material_disorder_seed for r in cohort.replicates}) == 2
    assert len({r.rng_namespace.geometry_seed for r in cohort.replicates}) == 1
    assert len({r.rng_namespace.events_seed for r in cohort.replicates}) == 1
    assert len({r.conditioned_observable_state_id for r in cohort.replicates}) == 1
    assert cohort.event_process_kind == EVENT_PROCESS_DISABLED


@pytest.mark.parametrize(
    ("second", "message"),
    [
        (_replicate(index=1, material_seed=22), "material_disorder seeds"),
        (
            build_quenched_replicate(
                cohort_id="conditional-material-fixture-v1",
                replicate_index=1,
                parent_network_id="parent-network-fixture-v1",
                graph_identity_hash="sha256:" + "4" * 64,
                geometry_realization_id=GEOMETRY_ID,
                conditioned_observable_state_id=OBSERVABLE_STATE_ID,
                physical_bond_ids=BONDS,
                rng_namespace=_seeds(material_disorder=222),
                law=_law(),
            ),
            "observable graph",
        ),
        (_replicate(index=1, material_seed=222, event_seed=999), "only material_disorder"),
        (_replicate(index=1, material_seed=222, geometry_seed=999), "only material_disorder"),
        (_replicate(index=1, material_seed=222, model_training_seed=999), "only material_disorder"),
        (
            _replicate(index=1, material_seed=222, parent_network_id="foreign-parent"),
            "observable graph",
        ),
        (
            _replicate(
                index=1,
                material_seed=222,
                geometry_realization_id="sha256:" + "5" * 64,
            ),
            "observable graph",
        ),
        (
            _replicate(
                index=1,
                material_seed=222,
                conditioned_observable_state_id="sha256:" + "6" * 64,
            ),
            "observable graph",
        ),
        (
            _replicate(
                index=1,
                material_seed=222,
                law=_law(reference_state_id="foreign-reference"),
            ),
            "law/profile/reference",
        ),
        (
            _replicate(index=1, material_seed=222, bonds=("bond-a", "bond-b")),
            "bond universe",
        ),
    ],
)
def test_cohort_rejects_duplicate_or_confounded_replicates(
    second: ConditionalReplicate, message: str
) -> None:
    with pytest.raises(StochasticityValidationError, match=message):
        build_conditional_material_cohort((_replicate(), second))

    with pytest.raises(StochasticityValidationError, match="contiguous"):
        build_conditional_material_cohort(
            (_replicate(index=0), _replicate(index=2, material_seed=222))
        )
    with pytest.raises(StochasticityValidationError, match="replicate indices"):
        build_conditional_material_cohort(
            (_replicate(index=0), _replicate(index=0, material_seed=222))
        )


def test_event_process_randomness_hazard_and_physical_time_fail_closed() -> None:
    replicate = _replicate()
    with pytest.raises(StochasticityValidationError, match="event-process randomness"):
        replace(replicate, event_process_kind="load_progress_hazard")
    with pytest.raises(StochasticityValidationError, match="exposure unit"):
        replace(replicate, event_process_exposure_unit="dimensionless")
    with pytest.raises(StochasticityValidationError, match="physical time"):
        replace(replicate, physical_time_valid=True)
    with pytest.raises(StochasticityValidationError, match="event-process randomness"):
        build_quenched_replicate(
            cohort_id="conditional-material-fixture-v1",
            replicate_index=0,
            parent_network_id="parent-network-fixture-v1",
            graph_identity_hash=GRAPH_HASH,
            geometry_realization_id=GEOMETRY_ID,
            conditioned_observable_state_id=OBSERVABLE_STATE_ID,
            physical_bond_ids=BONDS,
            rng_namespace=_seeds(),
            law=_law(),
            event_process_kind="bernoulli_per_minimizer_call",
        )

    deterministic = DamageLaw(
        law_id="deterministic-energy-fixture-v1",
        law_kind="deterministic_threshold",
        criterion="bond_energy",
        criterion_unit="pN nm",
        base_threshold=10.0,
        distribution=None,
        predictor_visibility="hidden_from_predictor",
        physics_profile_id=PROFILE_ID,
        physics_profile_hash=PROFILE_HASH,
        reference_state_id=REFERENCE_ID,
    )
    with pytest.raises(StochasticityValidationError, match="quenched heterogeneous"):
        _replicate(law=deterministic)


def test_all_public_records_roundtrip_strictly_and_are_deeply_immutable() -> None:
    namespace = _seeds()
    replicate = _replicate()
    view = replicate.predictor_view()
    cohort = _cohort()
    records = (
        (RNGNamespaceRecord, namespace.as_record()),
        (ConditionalReplicate, replicate.as_record()),
        (PredictorReplicateView, view.as_record()),
        (ConditionalReplicateCohort, cohort.as_record()),
    )
    for record_type, record in records:
        assert record_type.from_record(copy.deepcopy(record)).as_record() == record
        forged = copy.deepcopy(record)
        forged["unexpected"] = "field"
        with pytest.raises(StochasticityValidationError, match="unexpected"):
            record_type.from_record(forged)

    with pytest.raises((AttributeError, TypeError)):
        namespace.geometry_seed = 99  # type: ignore[misc]
    with pytest.raises(TypeError):
        replicate.threshold_field.thresholds["bond-a"] = 1.0  # type: ignore[index]
    with pytest.raises((AttributeError, TypeError)):
        cohort.replicates += (_replicate(index=2, material_seed=333),)  # type: ignore[misc]
    assert isinstance(replicate.threshold_field.thresholds, MappingProxyType)


def test_replay_rejects_forged_hashes_and_cross_record_provenance() -> None:
    replicate = _replicate()
    record = replicate.as_record()
    record["replicate_id"] = "sha256:" + "f" * 64
    with pytest.raises(StochasticityValidationError, match="replicate_id"):
        ConditionalReplicate.from_record(record)

    with pytest.raises(StochasticityValidationError, match="material seed"):
        replace(replicate, rng_namespace=_seeds(material_disorder=999))
    with pytest.raises(StochasticityValidationError, match="bond universe"):
        replace(replicate, physical_bond_ids=("bond-a", "bond-b"))
    with pytest.raises(StochasticityValidationError, match="law fingerprint"):
        replace(replicate, damage_law=_law(relative_half_width=0.3))
    with pytest.raises(StochasticityValidationError, match="reference state"):
        replace(replicate, reference_state_id="foreign-reference")
    with pytest.raises(StochasticityValidationError, match="criterion"):
        replace(replicate, criterion="bond_tension")
    with pytest.raises(StochasticityValidationError, match="criterion unit"):
        replace(replicate, criterion_unit="pN")
    with pytest.raises(StochasticityValidationError, match="visibility"):
        replace(replicate, predictor_visibility="visible_to_predictor")


def test_replicate_rejects_hash_valid_field_not_produced_by_p02_02_sampler() -> None:
    replicate = _replicate()
    field_record = replicate.threshold_field.as_record()
    field_record["thresholds"][0]["threshold"] = 999.0  # type: ignore[index]
    field_body = copy.deepcopy(field_record)
    field_body.pop("realization_id")
    field_record["realization_id"] = _record_hash(field_body)
    forged_field = ThresholdField.from_record(field_record)

    with pytest.raises(StochasticityValidationError, match="canonical P02-02"):
        ConditionalReplicate.create(
            cohort_id=replicate.cohort_id,
            replicate_index=replicate.replicate_index,
            parent_network_id=replicate.parent_network_id,
            graph_identity_hash=replicate.graph_identity_hash,
            geometry_realization_id=replicate.geometry_realization_id,
            conditioned_observable_state_id=replicate.conditioned_observable_state_id,
            physical_bond_ids=replicate.physical_bond_ids,
            rng_namespace=replicate.rng_namespace,
            damage_law=replicate.damage_law,
            threshold_field=forged_field,
        )

    record = replicate.as_record()
    record["threshold_field"] = forged_field.as_record()
    record["threshold_realization_id"] = forged_field.realization_id
    _rewrite_hash(record, "replicate_id")
    with pytest.raises(StochasticityValidationError, match="canonical P02-02"):
        ConditionalReplicate.from_record(record)


def test_namespace_projection_and_cohort_hashes_are_bound() -> None:
    namespace_record = _seeds().as_record()
    namespace_record["namespace_id"] = "sha256:" + "f" * 64
    with pytest.raises(StochasticityValidationError, match="namespace_id"):
        RNGNamespaceRecord.from_record(namespace_record)

    view_record = _replicate().predictor_view().as_record()
    view_record["projection_id"] = "sha256:" + "f" * 64
    with pytest.raises(StochasticityValidationError, match="projection_id"):
        PredictorReplicateView.from_record(view_record)

    cohort_record = _cohort().as_record()
    cohort_record["cohort_record_id"] = "sha256:" + "f" * 64
    with pytest.raises(StochasticityValidationError, match="cohort_record_id"):
        ConditionalReplicateCohort.from_record(cohort_record)


def test_input_and_serialized_record_mutation_cannot_change_objects() -> None:
    seeds = {
        "geometry": 11,
        "material_disorder": 22,
        "events": 33,
        "model_training": 44,
    }
    namespace = RNGNamespaceRecord.from_p01_04_mapping(seeds)
    seeds["events"] = 999
    assert namespace.events_seed == 33

    replicate = _replicate()
    record = replicate.as_record()
    record["physical_bond_ids"].append("forged-bond")  # type: ignore[union-attr]
    record["threshold_field"]["thresholds"][0]["threshold"] = 999.0  # type: ignore[index]
    assert replicate.physical_bond_ids == BONDS
    assert replicate.threshold_field.threshold_for("bond-a") != 999.0

    record = replicate.as_record()
    record["threshold_field"]["reference_state_id"] = "foreign-reference"  # type: ignore[index]
    threshold_body = copy.deepcopy(record["threshold_field"])  # type: ignore[arg-type]
    threshold_body.pop("realization_id")
    record["threshold_field"]["realization_id"] = _record_hash(threshold_body)  # type: ignore[index]
    record["threshold_realization_id"] = record["threshold_field"]["realization_id"]  # type: ignore[index]
    _rewrite_hash(record, "replicate_id")
    with pytest.raises(StochasticityValidationError, match="reference"):
        ConditionalReplicate.from_record(record)


def test_replay_rejects_duplicate_bonds_nonsequences_and_one_shot_generators() -> None:
    replicate = _replicate()
    for invalid in (
        ("bond-a", "bond-a"),
        "bond-a",
        {"bond-a": True},
        (bond for bond in BONDS),
    ):
        with pytest.raises(StochasticityValidationError, match="physical_bond_ids"):
            replace(replicate, physical_bond_ids=invalid)  # type: ignore[arg-type]

    with pytest.raises(StochasticityValidationError, match="replicates"):
        ConditionalReplicateCohort.create((item for item in _cohort().replicates))

    with pytest.raises(StochasticityValidationError, match="at least two"):
        build_conditional_material_cohort((_replicate(),))
    for invalid_index in (True, -1, 1.5):
        with pytest.raises(StochasticityValidationError, match="nonnegative integer"):
            _replicate(index=invalid_index)  # type: ignore[arg-type]

    with pytest.raises(StochasticityValidationError, match="hidden_from_predictor"):
        build_conditional_material_cohort(
            (
                _replicate(index=0, visibility="visible_to_predictor"),
                _replicate(
                    index=1,
                    material_seed=222,
                    visibility="visible_to_predictor",
                ),
            )
        )


def test_material_seed_produces_reproducible_conditional_first_event_difference() -> None:
    first = _replicate(index=0, material_seed=22)
    first_retry = _replicate(index=0, material_seed=22)
    second = _replicate(index=1, material_seed=222)
    values = [
        CriterionObservation(bond_id, "bond_energy", "pN nm", 10.0)
        for bond_id in BONDS
    ]

    def candidates(replicate: ConditionalReplicate) -> tuple[str, ...]:
        state = initialize_damage_state(
            replicate.damage_law,
            replicate.threshold_field,
            [
                CriterionObservation(bond_id, "bond_energy", "pN nm", 1.0)
                for bond_id in BONDS
            ],
        )
        assessment = assess_material_rupture(
            replicate.damage_law,
            replicate.threshold_field,
            state,
            values,
            phase="accepted_equilibrium",
            control_id="same-visible-control",
            load_coordinate=0.1,
            load_coordinate_unit="dimensionless",
            path_progress=0.1,
        )
        return tuple(candidate.physical_bond_id for candidate in assessment.candidates)

    assert candidates(first) == candidates(first_retry)
    assert candidates(first) != candidates(second)


def test_records_make_no_time_rate_probability_or_biological_claim() -> None:
    replicate = _replicate()
    record_text = json.dumps(replicate.as_record(), sort_keys=True)
    assert replicate.load_coordinate_kind == "quasi_static_not_physical_time"
    assert replicate.physical_time is None
    assert replicate.physical_time_valid is False
    assert replicate.conditional_dynamics == "deterministic_given_frozen_threshold_field"
    for forbidden in ("hazard_rate", "probability_per_step", "biological_time"):
        assert forbidden not in record_text
