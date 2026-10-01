import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from import_data_from_dumps import import_2D_triclinic_box_bounds_from_dump


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
