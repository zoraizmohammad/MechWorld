import sys
from pathlib import Path

import numpy as np
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import lammps_PG_objects as pg_objects
from import_data_from_dumps import (
    import_2D_triclinic_box_bounds_from_dump,
    import_atoms_from_dump,
)
from lammps_PG_objects import Atom, GlycanMolecule


def _write_dump(tmp_path: Path, bounds_header: str, bounds_rows: list[str]) -> Path:
    dump_path = tmp_path / "bounds.dump"
    dump_path.write_text(
        "\n".join(
            [
                "ITEM: TIMESTEP",
                "0",
                "ITEM: NUMBER OF ATOMS",
                "0",
                bounds_header,
                *bounds_rows,
                "ITEM: ATOMS id mol type x y",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return dump_path


def _write_atom_dump(
    tmp_path: Path,
    filename: str,
    atom_columns: list[str],
    atom_rows: list[str],
) -> Path:
    dump_path = tmp_path / filename
    dump_path.write_text(
        "\n".join(
            [
                "ITEM: TIMESTEP",
                "0",
                "ITEM: NUMBER OF ATOMS",
                str(len(atom_rows)),
                "ITEM: BOX BOUNDS pp pp pp",
                "-2.0 8.0",
                "-5.0 15.0",
                "-0.5 0.5",
                f"ITEM: ATOMS {' '.join(atom_columns)}",
                *atom_rows,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return dump_path


def test_reads_non_square_orthogonal_bounds(tmp_path: Path) -> None:
    dump_path = _write_dump(
        tmp_path,
        "ITEM: BOX BOUNDS pp pp pp",
        ["-2.0 8.0", "-7.5 4.5", "-0.5 0.5"],
    )

    bounds = import_2D_triclinic_box_bounds_from_dump(str(dump_path))

    assert bounds == (-2.0, 8.0, 0.0, -7.5, 4.5)


@pytest.mark.parametrize(
    ("xy", "xlo_bound", "xhi_bound"),
    [
        (3.0, -5.0, 10.0),
        (-3.0, -8.0, 7.0),
    ],
)
def test_converts_restricted_triclinic_dump_bounds_to_true_bounds(
    tmp_path: Path, xy: float, xlo_bound: float, xhi_bound: float
) -> None:
    dump_path = _write_dump(
        tmp_path,
        "ITEM: BOX BOUNDS xy xz yz pp pp pp",
        [
            f"{xlo_bound} {xhi_bound} {xy}",
            "-4.0 6.0 0.0",
            "-0.5 0.5 0.0",
        ],
    )

    bounds = import_2D_triclinic_box_bounds_from_dump(str(dump_path))

    assert bounds == (-5.0, 7.0, xy, -4.0, 6.0)


def test_rejects_unsupported_general_triclinic_header(tmp_path: Path) -> None:
    dump_path = _write_dump(
        tmp_path,
        "ITEM: BOX BOUNDS abc origin pp pp pp",
        [
            "10.0 0.0 0.0 -2.0",
            "3.0 20.0 0.0 -5.0",
            "0.0 0.0 1.0 -0.5",
        ],
    )

    with pytest.raises(ValueError, match="general triclinic"):
        import_2D_triclinic_box_bounds_from_dump(str(dump_path))


def test_rejects_nonzero_out_of_plane_restricted_triclinic_tilts(
    tmp_path: Path,
) -> None:
    dump_path = _write_dump(
        tmp_path,
        "ITEM: BOX BOUNDS xy xz yz pp pp pp",
        [
            "-5.0 10.0 3.0",
            "-4.0 7.5 1.5",
            "-0.75 0.5 -0.25",
        ],
    )

    with pytest.raises(ValueError, match="nonzero xz/yz"):
        import_2D_triclinic_box_bounds_from_dump(str(dump_path))


@pytest.mark.parametrize(
    ("xy", "unwrapped", "expected_wrapped", "expected_shift"),
    [
        (0.0, (35.25, -47.5), (5.25, 12.5), (3, -3)),
        (3.0, (59.7, -77.0), (1.7, 3.0), (7, -4)),
        (-3.0, (-75.7, 103.0), (-0.7, 3.0), (-6, 5)),
    ],
)
def test_wraps_large_signed_offsets_and_reports_image_shift(
    xy: float,
    unwrapped: tuple[float, float],
    expected_wrapped: tuple[float, float],
    expected_shift: tuple[int, int],
) -> None:
    atom = Atom(11, 2, 1, unwrapped[0], unwrapped[1], 0.0)

    applied_shift = atom.correct_triclinic_PCB(-2.0, 8.0, xy, -5.0, 15.0)

    np.testing.assert_allclose(
        (atom.x, atom.y), expected_wrapped, rtol=0.0, atol=1e-12
    )
    assert applied_shift == expected_shift
    assert tuple(atom.image_shift) == expected_shift

    cell = np.array([[10.0, xy], [0.0, 20.0]])
    reconstructed = np.array([atom.x, atom.y]) + cell @ np.array(atom.image_shift)
    np.testing.assert_allclose(reconstructed, unwrapped, rtol=0.0, atol=1e-12)


def test_accumulates_image_shifts_across_repeated_wrapping() -> None:
    atom = Atom(12, 2, 1, 1.7, 3.0, 0.0)

    atom.translate(31.0, -60.0, 0.0)  # H @ (4, -3), with xy = 3.
    first_shift = atom.correct_triclinic_PCB(-2.0, 8.0, 3.0, -5.0, 15.0)
    atom.translate(-66.0, 160.0, 0.0)  # H @ (-9, 8).
    second_shift = atom.correct_triclinic_PCB(-2.0, 8.0, 3.0, -5.0, 15.0)

    assert first_shift == (4, -3)
    assert second_shift == (-9, 8)
    assert tuple(atom.image_shift) == (-5, 5)
    np.testing.assert_allclose(
        (atom.x, atom.y), (1.7, 3.0), rtol=0.0, atol=1e-12
    )


@pytest.mark.parametrize(
    ("xy", "position_i", "position_j", "expected_displacement"),
    [
        (0.0, (7.5, 14.0), (-1.5, -4.0), (1.0, 2.0)),
        (3.0, (9.7, 13.0), (-0.7, -3.0), (2.6, 4.0)),
        (-3.0, (4.3, 13.0), (-1.3, -3.0), (1.4, 4.0)),
    ],
)
def test_minimum_image_in_non_square_and_restricted_triclinic_cells(
    xy: float,
    position_i: tuple[float, float],
    position_j: tuple[float, float],
    expected_displacement: tuple[float, float],
) -> None:
    atom_i = Atom(1, 1, 1, position_i[0], position_i[1], 0.0)
    atom_j = Atom(2, 1, 1, position_j[0], position_j[1], 0.0)

    displacement, image_offset = pg_objects.minimum_image_displacement_2d(
        atom_i, atom_j, (-2.0, 8.0, xy, -5.0, 15.0)
    )

    assert tuple(image_offset) == (1, 1)
    np.testing.assert_allclose(
        displacement, expected_displacement, rtol=0.0, atol=1e-12
    )
    direct = np.array(position_j) - np.array(position_i)
    cell = np.array([[10.0, xy], [0.0, 20.0]])
    np.testing.assert_allclose(
        displacement, direct + cell @ image_offset, rtol=0.0, atol=1e-12
    )


def test_glycan_orientation_vector_uses_triclinic_minimum_image() -> None:
    atoms = {
        1: Atom(1, 4, 1, 9.7, 13.0, 0.0),
        2: Atom(2, 4, 2, -0.7, -3.0, 0.0),
    }
    glycan = GlycanMolecule(4)
    glycan.add_atom_id(1)
    glycan.add_atom_id(2)

    vector = glycan.get_orientation_vector(
        atoms, (-2.0, 8.0, 3.0, -5.0, 15.0)
    )

    np.testing.assert_allclose(vector, (2.6, 4.0), rtol=0.0, atol=1e-12)


def test_atom_import_preserves_ids_across_reordered_columns_and_rows(
    tmp_path: Path,
) -> None:
    first_dump = _write_atom_dump(
        tmp_path,
        "first.dump",
        ["y", "id", "type", "x", "mol", "ix", "iy"],
        [
            "3.0 42 2 4.0 9 7 -4",
            "-2.0 7 1 -1.0 3 -6 5",
        ],
    )
    reordered_dump = _write_atom_dump(
        tmp_path,
        "reordered.dump",
        ["mol", "iy", "x", "id", "y", "ix", "type"],
        [
            "3 5 -1.0 7 -2.0 -6 1",
            "9 -4 4.0 42 3.0 7 2",
        ],
    )

    first_atoms = import_atoms_from_dump(str(first_dump))
    reordered_atoms = import_atoms_from_dump(str(reordered_dump))

    assert all(type(atom_id) is int for atom_id in first_atoms)
    assert all(type(atom_id) is int for atom_id in reordered_atoms)
    assert set(first_atoms) == set(reordered_atoms) == {7, 42}
    assert tuple(first_atoms[7].image_shift) == (-6, 5)
    assert tuple(first_atoms[42].image_shift) == (7, -4)
    for atom_id in (7, 42):
        first = first_atoms[atom_id]
        reordered = reordered_atoms[atom_id]
        assert (first.id, first.mol_id, first.atom_type) == (
            reordered.id,
            reordered.mol_id,
            reordered.atom_type,
        )
        np.testing.assert_allclose(
            (first.x, first.y, first.z),
            (reordered.x, reordered.y, reordered.z),
            rtol=0.0,
            atol=0.0,
        )
        assert tuple(first.image_shift) == tuple(reordered.image_shift)


def test_atom_import_rejects_duplicate_persistent_ids(tmp_path: Path) -> None:
    dump_path = _write_atom_dump(
        tmp_path,
        "duplicate.dump",
        ["id", "mol", "type", "x", "y"],
        [
            "7 3 1 -1.0 -2.0",
            "7 9 2 4.0 3.0",
        ],
    )

    with pytest.raises(ValueError, match="Duplicate atom ID 7"):
        import_atoms_from_dump(str(dump_path))
