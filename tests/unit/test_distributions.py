from __future__ import annotations

from pathlib import Path
import random
import sys

import numpy as np
import pytest
from scipy.stats import lognorm


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from assemble_pg_network import (
    DiscreteDistribution,
    create_FlorySchulz_distribution,
    generate_pg_network,
    get_sample_of_DSU_lengths_no_gaps,
    normalized_length_distribution,
    process_distribution_string,
)


SAMPLE_COUNT = 50_000
MOMENT_SIGMA_TOLERANCE = 6.0


def test_uniform_distribution_from_parser_is_accepted_by_generator() -> None:
    distribution = process_distribution_string("UNI=2=4", 10)

    generated = generate_pg_network(
        Ny=10,
        mesh_density=1.0,
        anisotropy=0.75,
        distribution=distribution,
    )

    assert len(generated) == 6


def test_uniform_distribution_is_explicit_and_normalized() -> None:
    distribution = process_distribution_string("UNI=2=4", 10)

    assert isinstance(distribution, DiscreteDistribution)
    assert distribution.law == "discrete_uniform"
    assert distribution.support == (2, 3, 4)
    assert distribution.probabilities == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert distribution.mean == pytest.approx(3.0)


def test_fs_preserves_number_fraction_and_separates_weight_fraction() -> None:
    p = 0.6
    support = np.arange(2, 7)
    number = process_distribution_string(f"FS=2=6={p}", 20)
    weight = process_distribution_string(f"WFS=2=6={p}", 20)

    expected_number = (1 - p) * p ** (support - 1)
    expected_number /= expected_number.sum()
    expected_weight = support * (1 - p) ** 2 * p ** (support - 1)
    expected_weight /= expected_weight.sum()

    assert number.law == "flory_schulz_number_fraction"
    assert weight.law == "flory_schulz_weight_fraction"
    assert number.probabilities == pytest.approx(expected_number)
    assert weight.probabilities == pytest.approx(expected_weight)
    assert weight.mean > number.mean


def test_lognormal_uses_truncated_normalized_integer_grid_pdf() -> None:
    shape, loc, scale = 0.55, -1.0, 12.0
    support = np.arange(2, 16)
    distribution = process_distribution_string(
        f"LN=2=15={shape}={loc}={scale}",
        30,
    )
    expected = lognorm.pdf(support, shape, loc=loc, scale=scale)
    expected /= expected.sum()

    assert distribution.law == "integer_grid_lognormal_pdf"
    assert distribution.support == tuple(support)
    assert distribution.probabilities == pytest.approx(expected)
    assert sum(distribution.probabilities) == pytest.approx(1.0)


def test_normalized_length_distribution_accepts_compact_distribution() -> None:
    distribution = process_distribution_string("FS=2=8=0.7", 20)

    support, probabilities = normalized_length_distribution(distribution)

    assert support == list(distribution.support)
    assert probabilities == pytest.approx(distribution.probabilities)


def test_legacy_explicit_list_remains_accepted_by_sampling_helper() -> None:
    lengths = get_sample_of_DSU_lengths_no_gaps(20, [2, 3, 4])

    assert sum(lengths) == 20
    assert all(length > 0 for length in lengths)


def test_legacy_entry_count_does_not_expand_distribution() -> None:
    distribution = create_FlorySchulz_distribution(2, 100, 0.9, int(1E8))

    assert isinstance(distribution, DiscreteDistribution)
    assert len(distribution) == 99
    assert len(distribution.probabilities) == 99
    assert sum(distribution.probabilities) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("specification", "size"),
    [
        ("", 10),
        ("UNI-2-4", 10),
        ("UNKNOWN=2=4", 10),
        ("UNI=4=2", 10),
        ("UNI=0=4", 10),
        ("UNI=2=10", 10),
        ("FS=2=8=0", 10),
        ("FS=2=8=1", 10),
        ("FS=2=8=nan", 10),
        ("FS=2=8=0.9=extra", 10),
        ("LN=2=8=0=-1=12", 10),
        ("LN=2=8=0.5=-1=0", 10),
        ("LN=2=8=0.5=100=1", 10),
    ],
)
def test_invalid_distribution_specs_raise_value_error(
    specification: str,
    size: int,
) -> None:
    with pytest.raises(ValueError):
        process_distribution_string(specification, size)


@pytest.mark.parametrize(
    "distribution",
    [
        process_distribution_string("UNI=2=9", 20),
        process_distribution_string("FS=2=12=0.75", 20),
        process_distribution_string("WFS=2=12=0.75", 20),
        process_distribution_string("LN=2=12=0.55=-1=10", 20),
    ],
    ids=["uniform", "number-fraction", "weight-fraction", "lognormal"],
)
def test_seeded_sampling_matches_first_two_declared_moments(
    distribution: DiscreteDistribution,
) -> None:
    seeded_rng = random.Random(20260930)
    samples = np.fromiter(
        (distribution.sample(seeded_rng) for _ in range(SAMPLE_COUNT)),
        dtype=float,
        count=SAMPLE_COUNT,
    )

    expected_mean = distribution.raw_moment(1)
    expected_second = distribution.raw_moment(2)
    mean_standard_error = np.sqrt(distribution.variance / SAMPLE_COUNT)
    second_variance = distribution.raw_moment(4) - expected_second**2
    second_standard_error = np.sqrt(max(second_variance, 0.0) / SAMPLE_COUNT)

    assert abs(float(np.mean(samples)) - expected_mean) <= (
        MOMENT_SIGMA_TOLERANCE * mean_standard_error + 1e-12
    )
    assert abs(float(np.mean(samples**2)) - expected_second) <= (
        MOMENT_SIGMA_TOLERANCE * second_standard_error + 1e-12
    )


def test_seeded_sampler_is_reproducible() -> None:
    distribution = process_distribution_string("FS=2=12=0.75", 20)
    first_rng = random.Random(4815162342)
    second_rng = random.Random(4815162342)

    first = [distribution.sample(first_rng) for _ in range(100)]
    second = [distribution.sample(second_rng) for _ in range(100)]

    assert first == second


def test_sampler_never_selects_zero_probability_support_at_zero_draw() -> None:
    class ZeroRandom:
        @staticmethod
        def random() -> float:
            return 0.0

    distribution = DiscreteDistribution((2, 3), (0.0, 1.0), "zero-mass-fixture")

    assert distribution.sample(ZeroRandom()) == 3
