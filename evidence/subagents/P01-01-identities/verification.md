# P01-01 periodic-identities verification

## Context

- Base commit: `833273ea7560f4caa1d5e3d715b7c4e460c5a284`
- Branch: `research/p01-01-periodic-identities`
- Working directory: `C:\Users\mzora\MechWorld-wt-p01-01-identities`
- Interpreter: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`
- Runtime: Python 3.11.9, NumPy 2.2.2, pytest 7.4.3
- Resources: local CPU only; no network, LAMMPS solver campaign, model, or lab data

## Red regressions

Initial requested scenarios:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_periodic_geometry.py`

Exit 1 before either owned source file was edited: `9 failed, 3 passed in 4.07s`. Failures covered silent general-triclinic parsing, one-step-only wrapping, missing image shifts, absent restricted-triclinic minimum-image behavior, and fixed atom dump column order. Exact capture: `red-regression-exact.txt`.

Existing-caller integration:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_periodic_geometry.py::test_glycan_orientation_vector_uses_triclinic_minimum_image`

Exit 1: `1 failed in 7.55s`; the old caller returned `(-0.4, 4.0)` instead of the sheared-cell vector `(2.6, 4.0)`. Exact capture: `red-orientation-integration-exact.txt`.

Independent-review finding:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_periodic_geometry.py::test_rejects_nonzero_out_of_plane_restricted_triclinic_tilts`

Exit 1: `1 failed in 7.30s`; the nominal 2D parser silently accepted nonzero `xz/yz`. Exact capture: `red-out-of-plane-rejection-exact.txt`.

Terminal-only right padding was stripped when storing the text captures; failure content and result lines are otherwise retained as emitted.

## Final green verification

Focused suite:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q tests/unit/test_periodic_geometry.py`

Exit 0:

```text
...............                                                          [100%]
15 passed in 6.00s
```

Inherited full suite:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q`

Exit 0:

```text
..........................                                               [100%]
26 passed in 7.96s
```

Targeted compilation:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m py_compile src/import_data_from_dumps.py src/lammps_PG_objects.py tests/unit/test_periodic_geometry.py`

Exit 0 with no output.

Independent brute-force oracle:

`$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe evidence/subagents/P01-01-identities/minimum_image_oracle.py`

Exit 0:

```text
1000 randomized restricted-triclinic minimum-image cases matched brute force
```

The oracle uses a fixed seed and compares the helper against all lattice offsets in `[-30, 30]^2` for each bounded fixture. The independent read-only reviewer separately reported 20,000 randomized cases passing, then reran the focused suite (`15 passed in 5.55s`), full suite (`26 passed in 6.64s`), and `git diff --check` (exit 0).

Diff integrity:

`git diff --check`

Exit 0. Git printed only configured LF-to-CRLF checkout warnings for modified Python files.

## Pre-commit hashes

- `src/import_data_from_dumps.py`: SHA-256 `76F206F8B346F2DD84EF01FCC47EBBD759D933A84E59F4E8A23CF535AC9C238F`
- `src/lammps_PG_objects.py`: SHA-256 `DC31A3FCB02D46F54549EF167A9E2BE454BD60631CB889A218C3F4D0FCA9755C`
- `tests/unit/test_periodic_geometry.py`: SHA-256 `A88218FF23B4FBF3585CCC01A891456B4FA46E53BEDE0960A9E2F9577E8D8C58`
- `minimum_image_oracle.py`: SHA-256 `B1AE0A472168E1BC4D444AA228FDE39EED5C09E7110F723208018033DE0A4C8D`

There was no task configuration or dataset input. Every dump fixture was generated in pytest's temporary directory.
