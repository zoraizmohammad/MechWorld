from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import process_network_ensembles
from run_lammps_isotropic_strain import to_write_or_not_to_write
from utils_helpers import apply_band_filters_to_df


def test_apply_band_filters_accumulates_every_filter() -> None:
    frame = pd.DataFrame({"x": [1, 2, 3], "y": [0, 9, 0]})

    filtered = apply_band_filters_to_df(
        frame,
        [(0, "x", 4), (-1, "y", 1)],
    )

    assert filtered.index.tolist() == [0, 2]


def test_once_output_criterion_is_consumed_across_calls() -> None:
    criteria = [("ONCE", 0.1, 0.3)]

    assert to_write_or_not_to_write(criteria, 0.15, False) is True
    assert to_write_or_not_to_write(criteria, 0.20, False) is False
    assert criteria == [(None, None, None)]


@pytest.mark.parametrize("remap", [False, True])
def test_minimize_wrapper_uses_named_current_arguments(
    monkeypatch: pytest.MonkeyPatch,
    remap: bool,
) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        process_network_ensembles,
        "find_files",
        lambda _directory, _pattern: {"sample.network"},
    )
    monkeypatch.setattr(process_network_ensembles.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(
        process_network_ensembles,
        "run_isotropic_prestrain_minimize",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    process_network_ensembles.run_networks_minimize(
        "unused-directory",
        r".*\.network",
        rerun=False,
        remap=remap,
    )

    assert calls == [
        (
            (),
            {
                "network_filepath": "sample.network",
                "max_strain": 0.3,
                "number_strain_steps": None,
                "write_debug_images": True,
                "dump_specs": [
                    ("INITIAL", None, None),
                    ("FINAL", None, None),
                ],
                "restart_specs": None,
                "remap": remap,
            },
        )
    ]
