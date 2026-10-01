import sys
from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lammps_PG_objects import Atom, Bond, GlycanMolecule
from process_orientation import (
    calculate_absolute_orientation_of_glycan_molecules,
    calculate_strain_and_attachment_orientation,
    signed_glycan_orientation_degrees,
)
from process_pores import (
    analyze_periodic_network_image,
    analyze_periodic_pore_mask,
    bool_me,
    calculate_pixel_scale,
    chemical_connected_components,
    periodic_pore_components,
    rasterize_periodic_network,
)
from simulation_constants_settings import BOND_TYPE_GLYCAN, BOND_TYPE_PEPTIDE


def test_grayscale_white_image_is_supported_as_empty_pore_space() -> None:
    image = np.ones((4, 6), dtype=float)

    occupied = bool_me(image)

    assert occupied.shape == image.shape
    assert not occupied.any()


def test_rgba_transparency_and_white_background_are_not_network() -> None:
    image = np.array(
        [
            [[1.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0]],
            [[0.0, 0.0, 0.0, 0.0], [0.5, 0.5, 0.5, 1.0]],
        ]
    )

    occupied = bool_me(image)

    np.testing.assert_array_equal(
        occupied, np.array([[False, True], [False, True]])
    )


def test_periodic_all_empty_mask_is_one_finite_pore() -> None:
    pores = periodic_pore_components(np.zeros((5, 7), dtype=bool))

    assert pores == (frozenset(np.ndindex(5, 7)),)


def test_periodic_pore_connects_across_both_image_seams() -> None:
    occupied = np.ones((3, 4), dtype=bool)
    free_pixels = {(0, 1), (2, 1), (0, 0), (0, 3)}
    for pixel in free_pixels:
        occupied[pixel] = False

    pores = periodic_pore_components(occupied)

    assert pores == (frozenset(free_pixels),)


def test_known_mask_reports_pixel_area_and_explicit_raster_metadata() -> None:
    occupied = np.zeros((6, 5), dtype=bool)
    occupied[1, :] = True
    occupied[4, :] = True

    metrics = analyze_periodic_pore_mask(
        occupied, cell_area=15.0, line_width_pixels=1
    )

    assert metrics.pixel_shape == (6, 5)
    assert metrics.pixel_area == pytest.approx(0.5)
    assert metrics.occupied_fraction == pytest.approx(1 / 3)
    assert metrics.pore_pixel_counts == (10, 10)
    assert metrics.pore_areas == pytest.approx((5.0, 5.0))
    assert metrics.line_width_pixels == 1


def _atom(atom_id: int, molecule_id: int, x: float, y: float) -> Atom:
    return Atom(atom_id, molecule_id, 1, x, y, 0.0)


def test_periodic_bond_raster_uses_short_seam_image() -> None:
    atoms = {1: _atom(1, 1, 9.0, 5.0), 2: _atom(2, 1, 1.0, 5.0)}
    bonds = {1: Bond(1, BOND_TYPE_GLYCAN, 1, 2)}

    mask = rasterize_periodic_network(
        atoms,
        bonds,
        (0.0, 10.0, 0.0, 0.0, 10.0),
        image_shape=(40, 40),
        line_width_pixels=1,
    )

    assert mask[:, :5].any()
    assert mask[:, -5:].any()
    assert not mask[:, 18:22].any()


def test_restricted_triclinic_raster_uses_lattice_seam() -> None:
    atoms = {1: _atom(1, 1, 11.0, 5.0), 2: _atom(2, 1, 3.0, 5.0)}
    bonds = {1: Bond(1, BOND_TYPE_GLYCAN, 1, 2)}

    mask = rasterize_periodic_network(
        atoms,
        bonds,
        (0.0, 10.0, 4.0, 0.0, 10.0),
        image_shape=(40, 40),
        line_width_pixels=1,
    )

    assert mask[:, :5].any()
    assert mask[:, -5:].any()
    assert not mask[:, 18:22].any()


def test_pixel_scale_uses_image_columns_for_x_resolution(tmp_path: Path) -> None:
    image_path = tmp_path / "rectangular.png"
    plt.imsave(image_path, np.ones((3, 7)), cmap="gray", vmin=0.0, vmax=1.0)

    scale = calculate_pixel_scale(
        str(image_path), (0.0, 7.0, 0.0, 0.0, 3.0)
    )

    assert scale == pytest.approx(1.0)


def test_resolution_and_line_width_are_measured_not_hidden() -> None:
    atoms = {1: _atom(1, 1, 2.0, 5.0), 2: _atom(2, 1, 8.0, 5.0)}
    bonds = {1: Bond(1, BOND_TYPE_GLYCAN, 1, 2)}
    bounds = (0.0, 10.0, 0.0, 0.0, 10.0)

    low = analyze_periodic_network_image(
        atoms, bonds, bounds, image_shape=(40, 40), line_width_pixels=1
    )
    high = analyze_periodic_network_image(
        atoms, bonds, bounds, image_shape=(80, 80), line_width_pixels=1
    )
    thick = analyze_periodic_network_image(
        atoms, bonds, bounds, image_shape=(40, 40), line_width_pixels=5
    )

    assert low.pixel_shape == (40, 40)
    assert high.pixel_shape == (80, 80)
    assert low.pixel_area == pytest.approx(4 * high.pixel_area)
    assert thick.line_width_pixels == 5
    assert thick.occupied_fraction > low.occupied_fraction


def test_rendered_crossing_does_not_create_a_chemical_crosslink() -> None:
    atoms = {
        1: _atom(1, 1, 3.0, 5.0),
        2: _atom(2, 1, 7.0, 5.0),
        3: _atom(3, 2, 5.0, 3.0),
        4: _atom(4, 2, 5.0, 7.0),
    }
    bonds = {
        1: Bond(1, BOND_TYPE_GLYCAN, 1, 2),
        2: Bond(2, BOND_TYPE_GLYCAN, 3, 4),
    }

    mask = rasterize_periodic_network(
        atoms,
        bonds,
        (0.0, 10.0, 0.0, 0.0, 10.0),
        image_shape=(41, 41),
        line_width_pixels=1,
    )
    components = chemical_connected_components(atoms, bonds)

    assert mask[20, 20]
    assert components == (frozenset({1, 2}), frozenset({3, 4}))
    assert not any(b.bond_type == BOND_TYPE_PEPTIDE for b in bonds.values())

    bonds[3] = Bond(3, BOND_TYPE_PEPTIDE, 2, 4)
    assert chemical_connected_components(atoms, bonds) == (
        frozenset({1, 2, 3, 4}),
    )


def test_chemical_connectivity_rejects_missing_atom_endpoint() -> None:
    atoms = {1: _atom(1, 1, 0.0, 0.0)}
    bonds = {1: Bond(1, BOND_TYPE_GLYCAN, 1, 99)}

    with pytest.raises(ValueError, match="unknown atom ID 99"):
        chemical_connected_components(atoms, bonds)


@pytest.mark.parametrize(
    ("vector", "expected"),
    [
        ((0.0, 2.0), 0.0),
        ((2.0, 0.0), -90.0),
        ((-2.0, 0.0), 90.0),
        ((2.0, 2.0), -45.0),
        ((-2.0, 2.0), 45.0),
    ],
)
def test_signed_orientation_is_deviation_from_positive_hoop_axis(
    vector: tuple[float, float], expected: float
) -> None:
    assert signed_glycan_orientation_degrees(vector) == pytest.approx(expected)


def test_signed_orientation_rejects_zero_or_nonfinite_vectors() -> None:
    with pytest.raises(ValueError, match="nonzero finite"):
        signed_glycan_orientation_degrees((0.0, 0.0))
    with pytest.raises(ValueError, match="nonzero finite"):
        signed_glycan_orientation_degrees((np.nan, 1.0))


def test_absolute_orientation_uses_periodic_minimum_image() -> None:
    atoms = {1: _atom(1, 7, 5.0, 9.0), 2: _atom(2, 7, 5.0, 1.0)}
    glycan = GlycanMolecule(7)
    glycan.add_atom_id(1)
    glycan.add_atom_id(2)

    orientations = calculate_absolute_orientation_of_glycan_molecules(
        atoms, {7: glycan}, (0.0, 10.0, 0.0, 0.0, 10.0)
    )

    assert orientations == pytest.approx([0.0])


def test_attachment_orientation_uses_periodic_peptide_vector() -> None:
    atoms = {
        1: _atom(1, 1, 9.0, 1.0),
        2: _atom(2, 1, 1.0, 1.0),
        3: _atom(3, 2, 9.0, 9.0),
        4: _atom(4, 2, 1.0, 9.0),
    }
    molecule_1 = GlycanMolecule(1)
    molecule_2 = GlycanMolecule(2)
    for atom_id in (1, 2):
        molecule_1.add_atom_id(atom_id)
    for atom_id in (3, 4):
        molecule_2.add_atom_id(atom_id)
    peptide = Bond(3, BOND_TYPE_PEPTIDE, 2, 3)
    peptide.dist = 1.0

    orientations, strains = calculate_strain_and_attachment_orientation(
        atoms,
        {3: peptide},
        {1: molecule_1, 2: molecule_2},
        (0.0, 10.0, 0.0, 0.0, 10.0),
    )

    assert orientations == pytest.approx([135.0, 135.0])
    assert len(strains) == 2
