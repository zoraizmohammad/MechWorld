"""Acceptance tests for explicit quasi-static loading and intervention controls."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from pgworld.simulation.controls import (  # noqa: E402
    CONTROL_SCHEMA_VERSION,
    AxisFrame,
    ControlValidationError,
    PhysicalInteraction,
    apply_prescribed_intervention,
    build_deformation_schedule,
    build_pressure_schedule,
    load_control_config,
    transform_control_step,
)


LOAD_CONFIG_DIR = REPOSITORY_ROOT / "configs" / "loads"


def _deformation_config(mode: str, **updates: object) -> dict[str, object]:
    config: dict[str, object] = {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "config_id": f"fixture-{mode}-v1",
        "control_family": "deformation",
        "mode": mode,
        "axes": {"x": "axial", "y": "hoop"},
        "fixed_reference_id": "fixed-cell-equilibrated-fixture-v1",
        "absolute_reference": "fixed_cell_equilibrated",
        "reference_reset_policy": "never",
        "load_coordinate_kind": "quasi_static_not_physical_time",
        "strain_unit": "dimensionless",
        "lambda_values": [0.0, 0.01, 0.02],
    }
    config.update(updates)
    return config


@pytest.mark.parametrize(
    ("mode", "updates", "expected"),
    [
        ("isotropic", {}, [[1.02, 0.0], [0.0, 1.02]]),
        ("axial", {}, [[1.02, 0.0], [0.0, 1.0]]),
        ("hoop", {}, [[1.0, 0.0], [0.0, 1.02]]),
        (
            "unequal_biaxial",
            {"strain_direction": {"epsilon_xx": 1.0, "epsilon_yy": 0.4}},
            [[1.02, 0.0], [0.0, 1.008]],
        ),
        (
            "engineering_simple_shear",
            {"shear_component": "xy"},
            [[1.0, 0.02], [0.0, 1.0]],
        ),
    ],
)
def test_deformation_modes_have_absolute_and_multiplicative_increment_contracts(
    mode: str, updates: dict[str, object], expected: list[list[float]]
) -> None:
    schedule = build_deformation_schedule(_deformation_config(mode, **updates))
    final = schedule.steps[-1]
    np.testing.assert_allclose(final.absolute_deformation_gradient, expected)
    previous = schedule.steps[-2].absolute_deformation_gradient
    np.testing.assert_allclose(
        final.incremental_deformation_gradient @ previous,
        final.absolute_deformation_gradient,
    )
    assert schedule.reference_state_id == "fixed-cell-equilibrated-fixture-v1"
    assert schedule.reference_reset_policy == "never"
    assert all(step.reference_state_id == schedule.reference_state_id for step in schedule.steps)
    assert all(step.physical_time is None for step in schedule.steps)
    assert all(step.physical_time_valid is False for step in schedule.steps)
    assert final.as_record()["absolute_control_semantics"] == (
        "F_absolute_maps_fixed_reference_to_target"
    )
    assert final.as_record()["increment_control_semantics"] == (
        "F_increment_maps_previous_accepted_state_to_target"
    )


def test_simple_shear_requires_explicit_engineering_component() -> None:
    schedule = build_deformation_schedule(
        _deformation_config(
            "engineering_simple_shear",
            shear_component="yx",
            lambda_values=[0.1],
        )
    )
    np.testing.assert_allclose(
        schedule.steps[0].absolute_deformation_gradient,
        [[1.0, 0.0], [0.1, 1.0]],
    )
    with pytest.raises(ControlValidationError, match="shear_component"):
        build_deformation_schedule(_deformation_config("engineering_simple_shear"))


def test_cyclic_progress_is_monotone_through_unloading_without_time_claims() -> None:
    config = _deformation_config(
        "cyclic",
        base_mode="axial",
        lambda_values=[0.0, 0.03, 0.01, 0.04, 0.0],
    )
    schedule = build_deformation_schedule(config)
    assert [step.lambda_load for step in schedule.steps] == [0.0, 0.03, 0.01, 0.04, 0.0]
    assert [step.progress_increment for step in schedule.steps] == pytest.approx(
        [0.0, 0.03, 0.02, 0.03, 0.04]
    )
    assert [step.path_progress for step in schedule.steps] == pytest.approx(
        [0.0, 0.03, 0.05, 0.08, 0.12]
    )
    assert schedule.progress_semantics == "cumulative_absolute_lambda_increment"
    assert schedule.load_coordinate_kind == "quasi_static_not_physical_time"
    assert schedule.as_record()["mode_parameters"] == {"base_mode": "axial"}


@pytest.mark.parametrize(
    ("field", "value"),
    [("strain_direction", {"epsilon_xx": 1.0, "epsilon_yy": 0.5}), ("shear_component", "xy")],
)
def test_cyclic_config_rejects_fields_unused_by_its_base_mode(
    field: str, value: object
) -> None:
    config = _deformation_config(
        "cyclic", base_mode="axial", lambda_values=[0.0, 0.01, 0.0]
    )
    config[field] = value
    with pytest.raises(ControlValidationError, match="unexpected"):
        build_deformation_schedule(config)


def test_rotation_transforms_deformation_and_axis_basis_covariantly() -> None:
    step = build_deformation_schedule(
        _deformation_config(
            "unequal_biaxial",
            strain_direction={"epsilon_xx": 1.0, "epsilon_yy": 0.25},
            lambda_values=[0.04],
        )
    ).steps[0]
    angle = 0.37
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    )
    transformed = transform_control_step(step, rotation)
    np.testing.assert_allclose(
        transformed.absolute_deformation_gradient,
        rotation @ step.absolute_deformation_gradient @ rotation.T,
    )
    np.testing.assert_allclose(
        transformed.incremental_deformation_gradient,
        rotation @ step.incremental_deformation_gradient @ rotation.T,
    )
    np.testing.assert_allclose(transformed.axes.basis, rotation @ step.axes.basis)
    assert transformed.axes.axis_meanings == ("axial", "hoop")
    with pytest.raises(ControlValidationError, match="orthogonal"):
        transform_control_step(step, np.array([[1.0, 0.2], [0.0, 1.0]]))


def test_direct_deformation_step_rejects_inversion_and_schedule_replays_increments() -> None:
    schedule = build_deformation_schedule(_deformation_config("axial"))
    with pytest.raises(ControlValidationError, match="positive determinant|inverted"):
        replace(
            schedule.steps[1],
            absolute_deformation_gradient=np.array([[-1.0, 0.0], [0.0, 1.0]]),
        )
    forged_step = replace(
        schedule.steps[1], incremental_deformation_gradient=np.eye(2)
    )
    with pytest.raises(ControlValidationError, match="increment|replay"):
        replace(schedule, steps=(schedule.steps[0], forged_step, schedule.steps[2]))


def test_schedule_rejects_mode_relabeling_and_progress_not_derived_from_lambda() -> None:
    schedule = build_deformation_schedule(_deformation_config("axial"))
    forged_steps = []
    previous = np.eye(2)
    for step in schedule.steps:
        absolute = np.array([[1.0, step.lambda_load], [0.0, 1.0]])
        forged_steps.append(
            replace(
                step,
                absolute_deformation_gradient=absolute,
                incremental_deformation_gradient=absolute @ np.linalg.inv(previous),
            )
        )
        previous = absolute
    with pytest.raises(ControlValidationError, match="mode|lambda|semantic"):
        replace(schedule, steps=tuple(forged_steps))

    forged_progress = tuple(
        replace(step, progress_increment=0.7, path_progress=0.7 * (index + 1))
        for index, step in enumerate(schedule.steps)
    )
    with pytest.raises(ControlValidationError, match="progress|lambda"):
        replace(schedule, steps=forged_progress)


def test_pressure_targets_encode_only_declared_closed_cylinder_balance() -> None:
    config = {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "config_id": "pressure-cylinder-fixture-v1",
        "control_family": "pressure_derived_tension",
        "mode": "pressure_derived_tension",
        "axes": {"x": "axial", "y": "hoop"},
        "fixed_reference_id": "fixed-cell-equilibrated-fixture-v1",
        "absolute_reference": "fixed_cell_equilibrated",
        "reference_reset_policy": "never",
        "load_coordinate_kind": "quasi_static_not_physical_time",
        "pressure_values": [0.0, 2.0, 3.0],
        "pressure_unit": "pN/nm^2",
        "radius": 5.0,
        "radius_unit": "nm",
        "tension_unit": "pN/nm",
        "shell_geometry": "closed_thin_cylinder",
        "location_assumption": "away_from_end_effects",
    }
    schedule = build_pressure_schedule(config)
    final = schedule.steps[-1]
    np.testing.assert_allclose(
        final.absolute_tension_target_pN_per_nm,
        [[7.5, 0.0], [0.0, 15.0]],
    )
    np.testing.assert_allclose(
        final.incremental_tension_target_pN_per_nm,
        [[2.5, 0.0], [0.0, 5.0]],
    )
    record = final.as_record()
    assert record["pressure_derivation"]["equations"] == {
        "N_axial": "p*R/2",
        "N_hoop": "p*R",
    }
    assert record["pressure_derivation"]["isotropic_strain_relabelled_as_turgor"] is False
    assert record["loading_mode"] == "pressure_derived_tension"
    assert record["absolute_deformation_gradient"] is None
    with pytest.raises(TypeError):
        final.pressure_derivation["equations"]["N_axial"] = "FORGED"
    assert final.as_record()["pressure_derivation"]["equations"]["N_axial"] == "p*R/2"


def test_pressure_tension_transforms_as_second_order_tensor() -> None:
    loaded = load_control_config(LOAD_CONFIG_DIR / "pressure_closed_cylinder_v1.json")
    step = loaded.steps[-1]
    angle = 0.41
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    )
    transformed = transform_control_step(step, rotation)
    np.testing.assert_allclose(
        transformed.absolute_tension_target_pN_per_nm,
        rotation @ step.absolute_tension_target_pN_per_nm @ rotation.T,
    )
    np.testing.assert_allclose(
        transformed.incremental_tension_target_pN_per_nm,
        rotation @ step.incremental_tension_target_pN_per_nm @ rotation.T,
    )


def test_pressure_schedule_replays_additive_target_increments() -> None:
    schedule = load_control_config(LOAD_CONFIG_DIR / "pressure_closed_cylinder_v1.json")
    forged_step = replace(
        schedule.steps[1],
        incremental_tension_target_pN_per_nm=np.zeros((2, 2)),
    )
    with pytest.raises(ControlValidationError, match="increment|replay"):
        replace(schedule, steps=(schedule.steps[0], forged_step, schedule.steps[2]))

    relabeled_steps = []
    previous = np.zeros((2, 2))
    for step in schedule.steps:
        pressure = step.lambda_load
        target = np.diag((pressure * 5.0 / 2.0, pressure * 5.0 * 9.0))
        relabeled_steps.append(
            replace(
                step,
                absolute_tension_target_pN_per_nm=target,
                incremental_tension_target_pN_per_nm=target - previous,
            )
        )
        previous = target
    with pytest.raises(ControlValidationError, match="pressure|tension|semantic"):
        replace(schedule, steps=tuple(relabeled_steps))


def test_mode_parameters_retain_unequal_biaxial_and_shear_definitions() -> None:
    biaxial = load_control_config(LOAD_CONFIG_DIR / "unequal_biaxial_v1.json")
    shear = load_control_config(LOAD_CONFIG_DIR / "engineering_simple_shear_v1.json")
    assert biaxial.as_record()["mode_parameters"] == {
        "strain_direction": {"epsilon_xx": 1.0, "epsilon_yy": 0.5}
    }
    assert shear.as_record()["mode_parameters"] == {"shear_component": "xy"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pressure_unit", "Pa"),
        ("radius_unit", "m"),
        ("tension_unit", "Pa"),
        ("shell_geometry", "sphere"),
        ("location_assumption", "unspecified"),
    ],
)
def test_pressure_target_rejects_ambiguous_units_or_assumptions(
    field: str, value: str
) -> None:
    raw = json.loads(
        (LOAD_CONFIG_DIR / "pressure_closed_cylinder_v1.json").read_text(
            encoding="utf-8"
        )
    )
    raw[field] = value
    with pytest.raises(ControlValidationError, match=field):
        build_pressure_schedule(raw)


def test_prescribed_weakening_is_per_interaction_and_preserves_chemical_type() -> None:
    interactions = (
        PhysicalInteraction(
            interaction_id="glycan:0001",
            chemical_type="glycan_harmonic",
            parameters={"K_pN_per_nm": 5570.0, "r0_nm": 1.03},
        ),
        PhysicalInteraction(
            interaction_id="glycan:0002",
            chemical_type="glycan_harmonic",
            parameters={"K_pN_per_nm": 5570.0, "r0_nm": 1.03},
        ),
    )
    intervention = load_control_config(
        LOAD_CONFIG_DIR / "prescribed_local_weakening_v1.json"
    )
    result = apply_prescribed_intervention(interactions, intervention)
    by_id = {item.interaction_id: item for item in result.interactions}
    assert by_id["glycan:0001"].effective_parameters["K_pN_per_nm"] == pytest.approx(
        2785.0
    )
    assert by_id["glycan:0001"].effective_parameters["r0_nm"] == pytest.approx(1.03)
    assert by_id["glycan:0002"].effective_parameters == {
        "K_pN_per_nm": 5570.0,
        "r0_nm": 1.03,
    }
    assert all(item.chemical_type == "glycan_harmonic" for item in result.interactions)
    assert result.event["source"] == "prescribed_intervention"
    assert result.event["counts_as_damage_initiation"] is False
    assert result.event["shared_lammps_type_coefficient_mutated"] is False
    assert result.event["load_coordinate_kind"] == "quasi_static_not_physical_time"
    assert result.event["lambda_load"] == pytest.approx(0.02)
    assert result.event["load_coordinate_unit"] == "dimensionless"
    assert result.event["path_progress"] == pytest.approx(0.02)
    assert result.event["progress_increment"] == pytest.approx(0.0)
    assert result.event["progress_unit"] == "dimensionless"
    assert result.event["physical_time"] is None
    assert result.event["physical_time_valid"] is False
    assert result.alive_mask == {"glycan:0001": True, "glycan:0002": True}
    json.dumps(result.as_record(), allow_nan=False, sort_keys=True)


def test_prescribed_removal_uses_alive_mask_not_material_rupture_semantics() -> None:
    interactions = (
        PhysicalInteraction(
            interaction_id="peptide:0001",
            chemical_type="peptide_nonlinear",
            parameters={"epsilon_pN_nm": 185.0, "r0_nm": 1.0},
        ),
        PhysicalInteraction(
            interaction_id="peptide:0002",
            chemical_type="peptide_nonlinear",
            parameters={"epsilon_pN_nm": 185.0, "r0_nm": 1.0},
        ),
    )
    intervention = load_control_config(
        LOAD_CONFIG_DIR / "prescribed_local_removal_v1.json"
    )
    result = apply_prescribed_intervention(interactions, intervention)
    assert result.alive_mask == {"peptide:0001": False, "peptide:0002": True}
    assert result.event["source"] == "prescribed_intervention"
    assert result.event["event_kind"] == "prescribed_removal"
    assert result.event["event_kind"] != "material_rupture"
    assert result.event["counts_as_damage_initiation"] is False


def test_intervention_rejects_unknown_or_duplicate_stable_ids() -> None:
    base = (
        PhysicalInteraction(
            interaction_id="edge:1",
            chemical_type="glycan_harmonic",
            parameters={"K_pN_per_nm": 5570.0},
        ),
    )
    unknown = {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "config_id": "bad-unknown-v1",
        "control_family": "prescribed_intervention",
        "action": "remove",
        "source": "prescribed_intervention",
        "selection_kind": "stable_physical_interaction_id",
        "interaction_ids": ["edge:missing"],
        "fixed_reference_id": "fixed-cell-equilibrated-fixture-v1",
        "absolute_reference": "fixed_cell_equilibrated",
        "reference_reset_policy": "never",
        "load_coordinate_kind": "quasi_static_not_physical_time",
        "load_coordinate_unit": "dimensionless",
        "progress_unit": "dimensionless",
        "lambda_load": 0.02,
        "path_progress": 0.02,
        "progress_increment": 0.0,
    }
    with pytest.raises(ControlValidationError, match="unknown"):
        apply_prescribed_intervention(base, load_control_config(unknown))
    duplicate = dict(unknown, config_id="bad-duplicate-v1", interaction_ids=["edge:1", "edge:1"])
    with pytest.raises(ControlValidationError, match="duplicate"):
        load_control_config(duplicate)
    duplicate_universe = (
        base[0],
        PhysicalInteraction(
            interaction_id="edge:1",
            chemical_type="glycan_harmonic",
            parameters={"K_pN_per_nm": 1.0},
        ),
    )
    valid = dict(unknown, config_id="valid-remove-v1", interaction_ids=["edge:1"])
    with pytest.raises(ControlValidationError, match="duplicate"):
        apply_prescribed_intervention(duplicate_universe, load_control_config(valid))


@pytest.mark.parametrize(
    "mutation",
    [
        {"lambda_values": [0.0, float("nan")]},
        {"lambda_values": [0.0, -1.0]},
        {"fixed_reference_id": ""},
        {"strain_unit": "percent"},
        {"reference_reset_policy": "reset_each_step"},
        {"axes": {"x": "hoop", "y": "axial"}},
    ],
)
def test_deformation_controls_reject_nonfinite_singular_or_ambiguous_input(
    mutation: dict[str, object]
) -> None:
    config = _deformation_config("axial")
    config.update(mutation)
    with pytest.raises(ControlValidationError):
        build_deformation_schedule(config)


def test_axis_frame_rejects_singular_or_nonfinite_basis() -> None:
    with pytest.raises(ControlValidationError, match="basis"):
        AxisFrame("axial", "hoop", [[1.0, 0.0], [0.0, 0.0]])
    with pytest.raises(ControlValidationError, match="finite"):
        AxisFrame("axial", "hoop", [[1.0, np.inf], [0.0, 1.0]])


def test_all_versioned_configs_are_deterministic_parseable_and_cover_required_modes() -> None:
    paths = sorted(LOAD_CONFIG_DIR.glob("*.json"))
    assert {path.name for path in paths} == {
        "axial_v1.json",
        "cyclic_loading_unloading_v1.json",
        "engineering_simple_shear_v1.json",
        "hoop_v1.json",
        "isotropic_v1.json",
        "prescribed_local_removal_v1.json",
        "prescribed_local_weakening_v1.json",
        "pressure_closed_cylinder_v1.json",
        "unequal_biaxial_v1.json",
    }
    loaded = [load_control_config(path) for path in paths]
    assert len({item.config_id for item in loaded}) == len(paths)
    for path, item in zip(paths, loaded):
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["schema_version"] == CONTROL_SCHEMA_VERSION
        assert item.as_record() == load_control_config(raw).as_record()
        json.dumps(item.as_record(), allow_nan=False, sort_keys=True)


def test_unknown_fields_and_wrong_schema_fail_closed() -> None:
    config = _deformation_config("axial")
    config["time_ns"] = 1.0
    with pytest.raises(ControlValidationError, match="unexpected"):
        load_control_config(config)
    config.pop("time_ns")
    config["schema_version"] = "unversioned"
    with pytest.raises(ControlValidationError, match="schema_version"):
        load_control_config(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "forged"),
        ("absolute_reference", "reset_reference"),
        ("reference_reset_policy", "reset_each_step"),
        ("load_coordinate_kind", "physical_time"),
        ("progress_semantics", "signed_lambda"),
    ],
)
def test_direct_schedule_construction_cannot_bypass_contract(
    field: str, value: object
) -> None:
    schedule = build_deformation_schedule(_deformation_config("axial"))
    with pytest.raises(ControlValidationError):
        replace(schedule, **{field: value})


def test_direct_intervention_construction_cannot_bypass_contract() -> None:
    intervention = load_control_config(
        LOAD_CONFIG_DIR / "prescribed_local_weakening_v1.json"
    )
    for field, value in (
        ("schema_version", "forged"),
        ("control_family", "material_rupture"),
        ("reference_reset_policy", "reset_each_step"),
        ("load_coordinate_kind", "physical_time"),
    ):
        with pytest.raises(ControlValidationError):
            replace(intervention, **{field: value})


def test_weakening_parameter_names_must_be_nonempty_strings() -> None:
    raw = json.loads(
        (LOAD_CONFIG_DIR / "prescribed_local_weakening_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for invalid in ([1], [""], ["K_pN_per_nm", "K_pN_per_nm"]):
        raw["parameter_names"] = invalid
        with pytest.raises(ControlValidationError, match="parameter_names"):
            load_control_config(raw)
