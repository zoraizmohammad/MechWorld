import json
import math
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from pgworld.config.physics_profiles import (  # noqa: E402
    PhysicsProfile,
    PhysicsProfileError,
    ProfileMixingError,
    available_profile_ids,
    canonical_profile_hash,
    load_physics_profile,
    load_physics_profile_file,
    validate_expanded_profile_snapshot,
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


def test_registered_identity_cannot_forge_an_unvalidated_expanded_snapshot() -> None:
    registered = load_physics_profile("legacy_python_2026_03_12_v1")
    forged = registered.expanded_snapshot()
    forged["potentials"]["harmonic_bond"]["parameters"]["K_pN_per_nm"] = 1.0

    with pytest.raises(PhysicsProfileError):
        PhysicsProfile(
            profile_id=registered.profile_id,
            canonical_hash=registered.canonical_hash,
            _snapshot_json=json.dumps(forged, sort_keys=True),
        )

    validated = validate_expanded_profile_snapshot(registered.expanded_snapshot())
    assert validated.identity == registered.identity

    forged["canonical_hash"] = canonical_profile_hash(forged)
    with pytest.raises(PhysicsProfileError, match="route-specific inherited values"):
        validate_expanded_profile_snapshot(forged)


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
    assert direct_elastic["historical_execution"]["tangent_output"][
        "declared_tangent_unit"
    ] == "GPa"
    assert direct_elastic["historical_execution"]["tangent_output"][
        "tangent_conversion_factor"
    ] == pytest.approx(1.01325e-8)
    assert direct_elastic["historical_execution"]["tangent_output"][
        "dimensional_status"
    ] == (
        "known_invalid_3d_label_without_thickness"
    )
    assert direct_isotropic["historical_execution"]["tangent_output"] == {
        "status": "not_applicable",
        "declared_tangent_unit": None,
        "tangent_conversion_factor": None,
        "dimensional_status": "script_does_not_compute_tangent_output",
    }


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
    assert snapshot["provenance"]["provisional_base_identity"] == {
        "profile_id": "legacy_python_2026_03_12_v1",
        "canonical_hash": EXPECTED_HASHES["legacy_python_2026_03_12_v1"],
    }


@pytest.mark.parametrize("profile_id", PROFILE_IDS)
def test_equations_units_reference_axes_and_claim_prohibitions(profile_id: str) -> None:
    snapshot = load_physics_profile(profile_id).expanded_snapshot()

    assert snapshot["schema_version"] == "pgworld.physics_profile.v2"
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
    assert snapshot["required_new_output_policy"]["scope"] == (
        "required_for_new_runs_and_reanalysis_not_historical_fact"
    )
    assert snapshot["required_new_output_policy"]["source"] == (
        "configurational_virial"
    )
    assert snapshot["required_new_output_policy"]["kinetic_term_included"] is False
    assert snapshot["required_new_output_policy"]["primary"] == "total"
    assert snapshot["required_new_output_policy"]["secondary"] == (
        "incremental_from_reference"
    )
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


def test_historical_execution_is_not_rewritten_as_virial_only_policy() -> None:
    current = load_physics_profile("legacy_python_2026_03_12_v1").expanded_snapshot()
    isotropic = load_physics_profile(
        "legacy_direct_isotropic_pre_unit_fix_v1"
    ).expanded_snapshot()
    elastic = load_physics_profile(
        "legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1"
    ).expanded_snapshot()
    provisional = load_physics_profile(
        "reviewed_physics_provisional_v0"
    ).expanded_snapshot()

    assert current["historical_execution"]["nve_deform_segment"] is True
    assert "run_isotropic_prestrain_minimize" in " ".join(
        current["historical_execution"]["entry_points"]
    )
    assert "run_isotropic_prestrain_nve" in " ".join(
        current["historical_execution"]["entry_points"]
    )
    assert "default_pressure_includes_kinetic_and_virial_terms" in current[
        "historical_execution"
    ]["kinetic_term_semantics"]

    for historical in (
        isotropic["historical_execution"],
        elastic["historical_execution"],
    ):
        assert historical["pressure_compute"] == "default_LAMMPS_thermo_pressure"
        assert historical["nve_deform_segment"] is True
        assert "kinetic_and_virial" in historical["kinetic_term_semantics"]

    assert isotropic["historical_execution"]["tangent_output"]["status"] == (
        "not_applicable"
    )
    assert provisional["historical_execution"]["scope"] == (
        "not_applicable_new_provisional_profile"
    )
    assert provisional["historical_execution"]["entry_points"] == []


def test_parameter_unknowns_fit_artifact_sources_and_provenance_are_explicit() -> None:
    required_urls = {
        "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/units.rst",
        "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_harmonic.rst",
        "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/bond_nonlinear.rst",
        "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/angle_harmonic.rst",
        "https://github.com/lammps/lammps/blob/patch_2Sep2026/doc/src/compute_pressure.rst",
    }
    current_paths = {
        "src/simulation_constants_settings.py",
        "src/units.py",
        "src/assemble_pg_network.py",
        "src/run_lammps_isotropic_strain.py",
        "src/run_lammps_elastic_tensor.py",
        "src/process_network_ensembles.py",
    }

    for profile_id in PROFILE_IDS:
        snapshot = load_physics_profile(profile_id).expanded_snapshot()
        for potential in snapshot["potentials"].values():
            assert set(potential["parameter_metadata"]) == set(potential["parameters"])
            for metadata in potential["parameter_metadata"].values():
                assert metadata == {
                    "uncertainty_status": "unknown",
                    "range_status": "not_reported",
                    "range": None,
                }
        assert snapshot["potentials"]["nonlinear_bond"]["fit_artifact"] == {
            "artifact_status": "unavailable",
            "path": None,
            "sha256_status": "unavailable",
            "sha256": None,
        }
        assert required_urls.issubset(
            {source["citation_or_path"] for source in snapshot["sources"]}
        )

    for profile_id in (
        "legacy_python_2026_03_12_v1",
        "reviewed_physics_provisional_v0",
    ):
        snapshot = load_physics_profile(profile_id).expanded_snapshot()
        assert current_paths.issubset(set(snapshot["provenance"]["source_routes"]))
        scoped_paths = {
            source["citation_or_path"]
            for source in snapshot["sources"]
            if source["kind"] == "repository_source"
        }
        assert current_paths.issubset(scoped_paths)


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
        validate_profile_aggregation([current, provisional.expanded_snapshot()])

    grouping = validate_profile_aggregation(
        [current, provisional.expanded_snapshot()],
        comparison_mode="stratified_by_profile",
    )
    assert grouping == {
        current.profile_id: current.canonical_hash,
        provisional.profile_id: provisional.canonical_hash,
    }


def test_compact_identity_is_not_accepted_as_an_expanded_validated_profile() -> None:
    current = load_physics_profile("legacy_python_2026_03_12_v1")

    with pytest.raises(ProfileMixingError, match="complete expanded snapshots"):
        validate_profile_aggregation([current.identity])
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
