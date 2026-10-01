import json
import math
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from pgworld.config.physics_profiles import (  # noqa: E402
    PhysicsProfileError,
    ProfileMixingError,
    available_profile_ids,
    canonical_profile_hash,
    load_physics_profile,
    load_physics_profile_file,
    validate_profile_aggregation,
)


PROFILE_IDS = (
    "legacy_python_2026_03_12_v1",
    "legacy_direct_isotropic_pre_unit_fix_v1",
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1",
    "reviewed_physics_provisional_v0",
)
PROFILE_CONFIG_DIRECTORY = REPOSITORY_ROOT / "configs" / "physics"

EXPECTED_HASHES = {
    "legacy_python_2026_03_12_v1": (
        "sha256:47a96afb4aca5abc413fd0d75ea68b8a45e470cb4bf2a0a398a32a45d9ed022b"
    ),
    "legacy_direct_isotropic_pre_unit_fix_v1": (
        "sha256:9b4c3963f2123984a0822a67d3bbc3080f0edce943c3846e18bd83dbb7607ac5"
    ),
    "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1": (
        "sha256:bc2f7532284d1ac35363aa8f01fcfadf6c0368b86abd986a7546d721499bb8c8"
    ),
    "reviewed_physics_provisional_v0": (
        "sha256:d9c1e83e911bb5623d65df6238cb6daa6b10fc4445059ee32397596972326d38"
    ),
}


def test_all_route_specific_profiles_load_with_exact_immutable_identity() -> None:
    assert available_profile_ids() == PROFILE_IDS
    assert {path.name for path in PROFILE_CONFIG_DIRECTORY.glob("*.json")} == {
        f"{profile_id}.json" for profile_id in PROFILE_IDS
    }

    profiles = [load_physics_profile(profile_id) for profile_id in PROFILE_IDS]

    assert [profile.profile_id for profile in profiles] == list(PROFILE_IDS)
    assert {profile.profile_id: profile.canonical_hash for profile in profiles} == (
        EXPECTED_HASHES
    )
    assert len({profile.canonical_hash for profile in profiles}) == len(profiles)
    for profile in profiles:
        snapshot = profile.expanded_snapshot()
        assert snapshot["profile_id"] == profile.profile_id
        assert snapshot["canonical_hash"] == profile.canonical_hash
        assert canonical_profile_hash(snapshot) == profile.canonical_hash
        assert json.loads(json.dumps(snapshot, allow_nan=False)) == snapshot

    detached = profiles[0].expanded_snapshot()
    detached["route"] = "mutated_copy"
    assert profiles[0].expanded_snapshot()["route"] == "current_python"


def test_legacy_routes_remain_distinct_and_exact() -> None:
    current = load_physics_profile("legacy_python_2026_03_12_v1").expanded_snapshot()
    direct_isotropic = load_physics_profile(
        "legacy_direct_isotropic_pre_unit_fix_v1"
    ).expanded_snapshot()
    direct_elastic = load_physics_profile(
        "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1"
    ).expanded_snapshot()

    assert current["spacing"]["code_edge_rest_length_nm"] == 1.03
    assert current["mass"] == {
        "status": "placeholder",
        "value_ag": 0.0004271587301788674,
        "physical_time_valid": False,
    }
    assert current["potentials"]["harmonic_bond"]["parameters"] == {
        "K_pN_per_nm": 5570.0,
        "r0_nm": 1.03,
    }
    assert current["potentials"]["nonlinear_bond"]["parameters"] == {
        "epsilon_pN_nm": 185.328520541486,
        "r0_nm": 1.0,
        "lambda_nm": 4.034069292365436,
    }
    assert current["potentials"]["harmonic_angle"]["parameters"] == {
        "K_pN_nm": 41.8,
        "theta0_degrees": 180.0,
    }

    assert direct_isotropic["potentials"]["harmonic_bond"]["parameters"] == {
        "K_pN_per_nm": 5.57,
        "r0_nm": 1.03,
    }
    assert direct_isotropic["potentials"]["nonlinear_bond"]["parameters"] == {
        "epsilon_pN_nm": 0.185567402281798,
        "r0_nm": 1.0,
        "lambda_nm": 4.035190236993014,
    }
    assert direct_isotropic["potentials"]["harmonic_angle"]["parameters"] == {
        "K_pN_nm": 0.0418,
        "theta0_degrees": 180.0,
    }

    assert direct_elastic["potentials"]["harmonic_bond"]["parameters"] == {
        "K_pN_per_nm": 5.57,
        "r0_nm": 1.03,
    }
    assert direct_elastic["potentials"]["nonlinear_bond"]["parameters"] == {
        "epsilon_pN_nm": 0.1709,
        "r0_nm": 0.9065,
        "lambda_nm": 4.0878,
    }
    assert direct_elastic["legacy_output"]["declared_tangent_unit"] == "GPa"
    assert direct_elastic["legacy_output"]["tangent_conversion_factor"] == pytest.approx(
        1.01325e-8
    )
    assert direct_elastic["legacy_output"]["dimensional_status"] == (
        "known_invalid_3d_label_without_thickness"
    )


def test_provisional_profile_is_fail_closed_for_scientific_claims() -> None:
    snapshot = load_physics_profile(
        "reviewed_physics_provisional_v0"
    ).expanded_snapshot()
    current = load_physics_profile("legacy_python_2026_03_12_v1").expanded_snapshot()

    assert snapshot["review_status"] == "pending"
    assert snapshot["biological_parameter_certified"] is False
    assert snapshot["coarse_graining_status"] == "unresolved"
    assert snapshot["nonlinear_fit_status"] == "unreproduced"
    assert snapshot["angle_resolution_status"] == "unreviewed"
    assert snapshot["mass"]["status"] == "placeholder"
    assert snapshot["mass"]["physical_time_valid"] is False
    assert snapshot["dimensional_scope"]["thickness_nm"] is None
    assert snapshot["dimensional_scope"]["stress_3d_allowed"] is False
    assert snapshot["final_science_campaign_allowed"] is False
    assert snapshot["spacing"] == current["spacing"]
    assert snapshot["mass"] == current["mass"]
    assert {
        name: potential["parameters"]
        for name, potential in snapshot["potentials"].items()
    } == {
        name: potential["parameters"]
        for name, potential in current["potentials"].items()
    }
    assert snapshot["review_requests"] == [
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


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_equations_units_reference_axes_and_claim_prohibitions(profile_id: str) -> None:
    snapshot = load_physics_profile(profile_id).expanded_snapshot()

    assert snapshot["schema_version"] == "pgworld.physics_profile.v1"
    assert snapshot["profile_version"]
    assert snapshot["family"]
    assert snapshot["route"]
    assert snapshot["intended_use"]
    assert snapshot["units"] == {
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
    assert snapshot["potentials"]["harmonic_bond"]["equation"] == "E=K*(r-r0)^2"
    assert snapshot["potentials"]["nonlinear_bond"]["equation"] == (
        "E=epsilon*(r-r0)^2/(lambda^2-(r-r0)^2)"
    )
    assert snapshot["potentials"]["harmonic_angle"]["equation"] == (
        "E=K*(theta-theta0)^2"
    )
    assert snapshot["reference_state"]["name"] == "fixed_cell_equilibrated"
    assert snapshot["reference_state"]["zero_tension_claim"] is False
    assert snapshot["tension"]["source"] == "configurational_virial"
    assert snapshot["tension"]["kinetic_term_included"] is False
    assert snapshot["tension"]["primary"] == "total"
    assert snapshot["tension"]["secondary"] == "incremental_from_reference"
    assert snapshot["axes"] == {
        "x": "axial",
        "y": "hoop",
        "laboratory_mapping_status": "dataset_specific_unconfirmed",
    }
    assert snapshot["dimensional_scope"]["thickness_nm"] is None
    assert snapshot["dimensional_scope"]["stress_3d_allowed"] is False
    assert snapshot["mass"]["physical_time_valid"] is False
    assert snapshot["biological_parameter_certified"] is False
    assert snapshot["final_science_campaign_allowed"] is False
    assert snapshot["rupture_law"]["status"] == "phenomenological_provisional"
    assert snapshot["rupture_law"]["primary_endpoint"] == "damage_initiation"
    assert snapshot["sources"]
    assert snapshot["provenance"]


def test_numerical_derivations_are_explicit_not_biological_certification() -> None:
    snapshot = load_physics_profile(
        "reviewed_physics_provisional_v0"
    ).expanded_snapshot()
    derived = snapshot["derived_numerical_facts"]

    assert derived == {
        "one_edge_harmonic_tangent_pN_per_nm": 11140.0,
        "two_edge_series_tangent_pN_per_nm": 5570.0,
        "two_edge_series_rest_length_nm": 2.06,
        "nonlinear_local_tangent_pN_per_nm": 22.776424425306164,
        "nonlinear_extension_pole_nm": 5.034069292365436,
        "angle_curvature_pN_nm_per_rad2": 83.6,
        "status": "mechanical_derivations_not_biological_certification",
    }
    nonlinear = snapshot["potentials"]["nonlinear_bond"]["parameters"]
    assert 2 * nonlinear["epsilon_pN_nm"] / nonlinear["lambda_nm"] ** 2 == pytest.approx(
        derived["nonlinear_local_tangent_pN_per_nm"], rel=0.0, abs=1e-14
    )
    assert snapshot["spacing"]["candidate_angle_scaling"] == "not_frozen_pending_review"


def test_silent_mixed_profile_aggregation_fails_closed() -> None:
    current = load_physics_profile("legacy_python_2026_03_12_v1")
    provisional = load_physics_profile("reviewed_physics_provisional_v0")

    with pytest.raises(ProfileMixingError, match="silent mixed-profile aggregation"):
        validate_profile_aggregation([current.identity, provisional.identity])

    grouping = validate_profile_aggregation(
        [current.identity, provisional.identity],
        comparison_mode="stratified_by_profile",
    )
    assert grouping == {
        current.profile_id: current.canonical_hash,
        provisional.profile_id: provisional.canonical_hash,
    }


def test_profile_identity_rejects_id_hash_conflicts_and_unknown_profiles() -> None:
    current = load_physics_profile("legacy_python_2026_03_12_v1")

    with pytest.raises(ProfileMixingError, match="multiple hashes"):
        validate_profile_aggregation(
            [
                current.identity,
                {
                    "profile_id": current.profile_id,
                    "canonical_hash": "sha256:" + "0" * 64,
                },
            ],
            comparison_mode="stratified_by_profile",
        )
    with pytest.raises(PhysicsProfileError, match="unknown profile ID"):
        load_physics_profile("not_a_profile")


def test_tamper_unknown_field_nonfinite_and_malformed_values_are_rejected(
    tmp_path: Path,
) -> None:
    snapshot = load_physics_profile(
        "reviewed_physics_provisional_v0"
    ).expanded_snapshot()

    tampered = json.loads(json.dumps(snapshot))
    tampered["potentials"]["harmonic_bond"]["parameters"]["K_pN_per_nm"] = 1.0
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(PhysicsProfileError, match="canonical hash mismatch"):
        load_physics_profile_file(tampered_path)

    unknown = json.loads(json.dumps(snapshot))
    unknown["unexpected"] = True
    unknown["canonical_hash"] = canonical_profile_hash(unknown)
    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(PhysicsProfileError, match="unknown field"):
        load_physics_profile_file(unknown_path)

    nonfinite = json.loads(json.dumps(snapshot))
    nonfinite["potentials"]["harmonic_bond"]["parameters"]["K_pN_per_nm"] = math.inf
    nonfinite_path = tmp_path / "nonfinite.json"
    nonfinite_path.write_text(json.dumps(nonfinite), encoding="utf-8")
    with pytest.raises(PhysicsProfileError, match="non-finite"):
        load_physics_profile_file(nonfinite_path)

    malformed = json.loads(json.dumps(snapshot))
    malformed["mass"]["physical_time_valid"] = "false"
    malformed["canonical_hash"] = canonical_profile_hash(malformed)
    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(PhysicsProfileError, match="must be a boolean"):
        load_physics_profile_file(malformed_path)

    repinned = json.loads(json.dumps(snapshot))
    repinned["provenance"]["notes"] = "unauthorized mutation under an existing ID"
    repinned["canonical_hash"] = canonical_profile_hash(repinned)
    repinned_path = tmp_path / "repinned.json"
    repinned_path.write_text(json.dumps(repinned), encoding="utf-8")
    with pytest.raises(PhysicsProfileError, match="registered hash mismatch"):
        load_physics_profile_file(repinned_path)
