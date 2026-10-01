"""Independent bounded brute-force check for the 2D minimum-image helper."""

import math
import random
import sys
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from lammps_PG_objects import Atom, minimum_image_displacement_2d


rng = random.Random(240101)
for case in range(1000):
    lx = rng.uniform(1.0, 20.0)
    ly = rng.uniform(1.0, 20.0)
    xy = rng.uniform(-20.0, 20.0)
    xlo = rng.uniform(-5.0, 5.0)
    ylo = rng.uniform(-5.0, 5.0)
    fractions = [rng.random() for _ in range(4)]
    position_1 = (
        xlo + lx * fractions[0] + xy * fractions[1],
        ylo + ly * fractions[1],
    )
    position_2 = (
        xlo + lx * fractions[2] + xy * fractions[3],
        ylo + ly * fractions[3],
    )
    atom_1 = Atom(1, 1, 1, *position_1, 0.0)
    atom_2 = Atom(2, 1, 1, *position_2, 0.0)

    displacement, _ = minimum_image_displacement_2d(
        atom_1,
        atom_2,
        (xlo, xlo + lx, xy, ylo, ylo + ly),
    )
    direct = np.array(position_2) - np.array(position_1)
    oracle_distance_squared = min(
        float(np.dot(candidate, candidate))
        for image_y in range(-30, 31)
        for image_x in range(-30, 31)
        for candidate in [
            direct
            + np.array(
                [lx * image_x + xy * image_y, ly * image_y], dtype=float
            )
        ]
    )
    observed_distance_squared = float(np.dot(displacement, displacement))
    if not math.isclose(
        observed_distance_squared,
        oracle_distance_squared,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise AssertionError(
            (case, observed_distance_squared, oracle_distance_squared)
        )

print("1000 randomized restricted-triclinic minimum-image cases matched brute force")
