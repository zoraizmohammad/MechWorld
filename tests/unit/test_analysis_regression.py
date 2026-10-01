from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import process_elastic_tensor
import process_network_ensembles


def _raw_thermo_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lx": [2.0, 4.0],
            "ly": [5.0, 5.0],
            "pe": [10.0, 20.0],
            "pxx": [-1.0, -2.0],
            "pyy": [-3.0, -4.0],
            "pxy": [0.5, -0.5],
            "glycan_pe": [2.0, 4.0],
            "angle_pe": [3.0, 6.0],
            "peptide_pe": [5.0, 10.0],
            "rho_0": [0.25, 0.25],
        }
    )


def test_energy_density_and_tension_use_declared_2d_units() -> None:
    raw = _raw_thermo_frame()

    energy = process_network_ensembles.calc_energy_df_from_file_df(raw)
    tension = process_network_ensembles.calculate_tension_df_from_file_df(raw)

    # LAMMPS nano energy is pN nm = 1e-3 aJ. Dividing by nm^2
    # therefore requires a factor of 1e-3 for an aJ/nm^2 label.
    np.testing.assert_allclose(energy["energy_density_aJ_per_nm2"], [1e-3, 1e-3])
    np.testing.assert_allclose(energy["energy_density"], [1e-3, 1e-3])
    np.testing.assert_allclose(energy["energy_density_pN_per_nm"], [1.0, 1.0])

    # The audited 2D virial conversion is 1 raw unit = 1e-3 N/m.
    np.testing.assert_allclose(tension["tension_xx"], [1e-3, 2e-3])
    np.testing.assert_allclose(tension["tension_yy"], [3e-3, 4e-3])
    np.testing.assert_allclose(tension["tension_xy"], [-0.5e-3, 0.5e-3])


def _elastic_line(strain: float, scale: float = 1.0) -> str:
    return (
        f"{strain} {10 * scale} {20 * scale} {5 * scale} "
        f"{2 * scale} 0 0 MPa*nm\n"
    )


def test_elastic_aggregation_is_idempotent_and_preserves_raw_files(tmp_path: Path) -> None:
    raw_paths = [
        tmp_path / "network_alpha_prestr0.0.elastic_constants",
        tmp_path / "network_alpha_prestr0.1.elastic_constants",
    ]
    raw_paths[0].write_text(_elastic_line(0.0), encoding="utf-8")
    raw_paths[1].write_text(_elastic_line(0.1, scale=2.0), encoding="utf-8")
    raw_before = {path: path.read_bytes() for path in raw_paths}

    first_outputs = process_elastic_tensor.combine_elastic_constant_files_into_one_file_per_network(
        str(tmp_path)
    )
    combined_path = tmp_path / "network_alpha.moduli"
    first_combined = combined_path.read_bytes()

    second_outputs = process_elastic_tensor.combine_elastic_constant_files_into_one_file_per_network(
        str(tmp_path)
    )

    assert first_outputs == second_outputs == [str(combined_path)]
    assert combined_path.read_bytes() == first_combined
    assert combined_path.read_text(encoding="utf-8").count("\n") == 3
    assert {path: path.read_bytes() for path in raw_paths} == raw_before


def _tension_frame(strain: list[float], xx: list[float], yy: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "strain": strain,
            "tension_xx": xx,
            "tension_yy": yy,
        }
    )


def test_tension_interpolation_is_per_replicate_and_handles_descending_axis() -> None:
    numerators = [
        _tension_frame([0.0, 0.5, 1.0], [2.0, 4.0, 6.0], [4.0, 8.0, 12.0]),
        _tension_frame([0.0, 0.5, 1.0], [3.0, 6.0, 9.0], [6.0, 12.0, 18.0]),
    ]
    denominators = [
        _tension_frame([1.0, 0.5, 0.0], [3.0, 2.0, 1.0], [6.0, 4.0, 2.0]),
        _tension_frame([0.0, 1.0], [1.0, 3.0], [2.0, 6.0]),
    ]

    ratios = process_network_ensembles.calculate_paired_tension_ratios(
        numerators, denominators
    )

    assert len(ratios) == 2
    np.testing.assert_allclose(ratios[0]["comparison_ratio_xx"], [2.0, 2.0, 2.0])
    np.testing.assert_allclose(ratios[1]["comparison_ratio_xx"], [3.0, 3.0, 3.0])
    assert ratios[0]["replicate_index"].unique().tolist() == [0]
    assert ratios[1]["replicate_index"].unique().tolist() == [1]


@pytest.mark.parametrize(
    ("axis", "message"),
    [
        ([0.0, 0.5, 0.5, 1.0], "duplicate"),
        ([0.0, 1.0, 0.5], "strictly monotonic"),
    ],
)
def test_tension_interpolation_rejects_ambiguous_axes(
    axis: list[float], message: str
) -> None:
    numerator = _tension_frame([0.0, 0.5, 1.0], [2.0, 4.0, 6.0], [4.0, 8.0, 12.0])
    denominator = _tension_frame(axis, [1.0] * len(axis), [2.0] * len(axis))

    with pytest.raises(ValueError, match=message):
        process_network_ensembles.calculate_paired_tension_ratios(
            [numerator], [denominator]
        )


def test_grouped_elastic_interpolation_never_crosses_networks() -> None:
    frame = pd.DataFrame(
        {
            "network_id": ["first", "first", "second", "second"],
            "strain": [1.0, 0.0, 0.0, 1.0],
            "Ex": [30.0, 10.0, 100.0, 300.0],
            "Ey": [60.0, 20.0, 200.0, 600.0],
        }
    )

    interpolated = process_elastic_tensor.interpolate_grouped_values_at(
        frame,
        target_x=0.5,
        value_columns=["Ex", "Ey"],
    ).set_index("network_id")

    assert interpolated.loc["first", "Ex"] == pytest.approx(20.0)
    assert interpolated.loc["second", "Ex"] == pytest.approx(200.0)
    assert interpolated.loc["first", "Ey"] == pytest.approx(40.0)
    assert interpolated.loc["second", "Ey"] == pytest.approx(400.0)
