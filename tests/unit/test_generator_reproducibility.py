from __future__ import annotations

from pathlib import Path
import random
import sys

import numpy as np
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import assemble_pg_network as pg_network
from lammps_PG_objects import Atom


def _small_generation(**overrides):
    arguments = {
        "Ny": 12,
        "mesh_density": 0.7,
        "anisotropy": 0.6,
        "distribution": pg_network.process_distribution_string("UNI=2=5", 12),
        "seed": 20261001,
        "return_metrics": True,
    }
    arguments.update(overrides)
    return pg_network.generate_pg_network(**arguments)


def _realized_graph(generated):
    _, _, glycans, atoms, bonds, angles, metrics = generated
    return glycans, atoms, bonds, angles, metrics


def test_seed_namespace_derivation_is_stable_and_complete() -> None:
    seeds = pg_network.RNGSeeds.from_master(20261001)

    assert pg_network.RNG_STREAM_NAMES == (
        "geometry",
        "material_disorder",
        "events",
        "model_training",
    )
    assert seeds.as_dict() == {
        "geometry": 3876982929329587919,
        "material_disorder": 13958106370667869940,
        "events": 5767726254553140904,
        "model_training": 8271043746876790297,
    }
    assert len(set(seeds.as_dict().values())) == len(pg_network.RNG_STREAM_NAMES)


def test_namespaced_streams_are_independent_and_repeatable() -> None:
    seeds = pg_network.RNGSeeds.from_master(41)
    event_stream = seeds.stream("events")
    event_reference = [event_stream.random() for _ in range(4)]

    geometry = seeds.stream("geometry")
    _ = [geometry.random() for _ in range(100)]
    independent_event_stream = seeds.stream("events")
    event_after_geometry_use = [independent_event_stream.random() for _ in range(4)]

    assert event_after_geometry_use == event_reference
    with pytest.raises(ValueError, match="unknown RNG stream"):
        seeds.stream("unregistered")


def test_material_disorder_draws_use_only_the_material_seed() -> None:
    def draw_eligibility(seeds):
        stream = seeds.stream("material_disorder")
        outcomes = []
        for atom_id in range(1, 33):
            atom = Atom(atom_id, 1, 1, 0.0, 0.0, 0.0)
            atom.run_bernoulli_trial(0.5, stream)
            outcomes.append(atom.is_inclined_to_peptide)
        return outcomes

    baseline = pg_network.RNGSeeds(11, 22, 33, 44)
    changed_geometry = pg_network.RNGSeeds(111, 22, 33, 44)
    changed_material = pg_network.RNGSeeds(11, 222, 33, 44)

    assert draw_eligibility(baseline) == draw_eligibility(changed_geometry)
    assert draw_eligibility(baseline) != draw_eligibility(changed_material)


def test_same_config_seed_and_backend_produce_identical_realized_graph() -> None:
    first = _small_generation()
    second = _small_generation()
    *_, first_metrics = first
    *_, second_metrics = second

    assert first_metrics.graph_sha256 == second_metrics.graph_sha256
    assert first_metrics == second_metrics


def test_non_geometry_seeds_do_not_change_generated_graph() -> None:
    original = pg_network.RNGSeeds(geometry=11, material_disorder=22, events=33, model_training=44)
    changed = pg_network.RNGSeeds(geometry=11, material_disorder=222, events=333, model_training=444)

    *_, original_metrics = _small_generation(seed=None, rng_seeds=original)
    *_, changed_metrics = _small_generation(seed=None, rng_seeds=changed)

    assert original_metrics.graph_sha256 == changed_metrics.graph_sha256


def test_geometry_seed_changes_generated_graph() -> None:
    first = pg_network.RNGSeeds(geometry=11, material_disorder=22, events=33, model_training=44)
    second = pg_network.RNGSeeds(geometry=12, material_disorder=22, events=33, model_training=44)

    *_, first_metrics = _small_generation(seed=None, rng_seeds=first)
    *_, second_metrics = _small_generation(seed=None, rng_seeds=second)

    assert first_metrics.graph_sha256 != second_metrics.graph_sha256


def test_seeded_generation_does_not_consume_global_rngs() -> None:
    random.seed(97531)
    python_state_before = random.getstate()
    np.random.seed(86420)
    numpy_state_before = np.random.get_state()

    _small_generation()

    assert random.getstate() == python_state_before
    numpy_state_after = np.random.get_state()
    assert numpy_state_after[0] == numpy_state_before[0]
    np.testing.assert_array_equal(numpy_state_after[1], numpy_state_before[1])
    assert numpy_state_after[2:] == numpy_state_before[2:]


def test_metrics_describe_realized_network_not_requested_values() -> None:
    generated = _small_generation()
    glycans, atoms, bonds, angles, metrics = _realized_graph(generated)
    achieved_density, achieved_crosslinks = pg_network.compute_crosslink_ratio(
        atoms,
        bonds,
        metrics.simbox_lx,
        metrics.simbox_ly,
    )

    assert metrics.atom_count == len(atoms)
    assert metrics.bond_count == len(bonds)
    assert metrics.angle_count == len(angles)
    assert metrics.glycan_count == len(glycans)
    assert metrics.glycan_lengths_dsu == tuple(
        sorted(len(glycan.atom_ids) for glycan in glycans.values())
    )
    assert max(metrics.glycan_lengths_dsu) == 6
    assert max(metrics.glycan_lengths_dsu) > max(
        pg_network.process_distribution_string("UNI=2=5", 12).support
    )
    assert metrics.achieved_mesh_density == pytest.approx(achieved_density)
    assert metrics.achieved_crosslink_fraction == pytest.approx(achieved_crosslinks)
    assert metrics.peptide_bond_count + metrics.glycan_bond_count == len(bonds)
    assert 1 <= metrics.connected_component_count <= len(atoms)
    assert 0.0 < metrics.largest_component_fraction <= 1.0
    assert metrics.orientation_observation_count == len(
        metrics.glycan_orientations_degrees
    )
    assert all(np.isfinite(metrics.glycan_orientations_degrees))
    assert len(metrics.graph_sha256) == 64


def test_datafile_export_measures_high_precision_coordinate_roundtrip(tmp_path) -> None:
    atom = Atom(
        id=1,
        mol_id=1,
        atom_type=1,
        x=1.2345678901234567,
        y=-4.567890123456789e-9,
        z=-0.12345678901234566,
    )
    destination = tmp_path / "precise.network"

    export_metrics = pg_network.write_to_laamps_datafile(
        destination,
        {atom.id: atom},
        {},
        {},
        simbox_lx=9.876543210987654,
        simbox_ly=8.765432109876543,
    )
    atom_line = next(
        line
        for line in destination.read_text(encoding="utf-8").splitlines()
        if line.startswith("1 1 1 ")
    )
    roundtripped = tuple(float(token) for token in atom_line.split()[3:6])
    measured_errors = tuple(
        abs(actual - expected)
        for actual, expected in zip(roundtripped, (atom.x, atom.y, atom.z))
    )

    assert export_metrics.coordinate_count == 3
    assert export_metrics.significant_digits == 17
    assert export_metrics.max_abs_coordinate_error == max(measured_errors)
    assert export_metrics.rms_coordinate_error == pytest.approx(
        float(np.sqrt(np.mean(np.square(measured_errors))))
    )
    assert export_metrics.max_abs_coordinate_error <= 1e-15


def test_rng_configuration_rejects_ambiguous_or_unknown_backend() -> None:
    with pytest.raises(ValueError, match="either seed or rng_seeds"):
        _small_generation(rng_seeds=pg_network.RNGSeeds.from_master(1))
    with pytest.raises(ValueError, match="unsupported RNG backend"):
        _small_generation(rng_backend="numpy")


@pytest.mark.parametrize("invalid_seed", [True, -1, 1.5, "1"])
def test_rng_seed_contract_rejects_ambiguous_values(invalid_seed) -> None:
    with pytest.raises(ValueError, match="seed must be a nonnegative integer"):
        pg_network.RNGSeeds(invalid_seed, 2, 3, 4)
    with pytest.raises(ValueError, match="master seed must be a nonnegative integer"):
        pg_network.RNGSeeds.from_master(invalid_seed)
