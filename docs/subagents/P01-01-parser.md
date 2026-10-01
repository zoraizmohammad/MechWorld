# P01-01 parser-slice return report

## Scope and result

Starting from `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`, this slice reproduced the live A01/A02 parser defects and repaired only LAMMPS dump `BOX BOUNDS` parsing. The legacy return order remains `(xlo, xhi, xy, ylo, yhi)`.

The parser now:

- reads the second bounds row for `ylo`/`yhi`;
- accepts two-column orthogonal bounds and returns `xy = 0.0`;
- recognizes restricted-triclinic headers carrying `xy xz yz`; and
- converts LAMMPS bounding extents to true bounds with the documented restricted-triclinic min/max correction before returning them.

Callers inspected were `import_atoms_from_dump`, `import_all_from_dump`, `process_bond_strain.py`, and `process_pores.py`. They consume the existing tuple order, so no compatibility change was introduced.

## Verification evidence

All commands ran from `C:\Users\mzora\MechWorld-wt-p01-01` with `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe` (Python 3.11.9, pytest 7.4.3), local CPU only.

1. Before the source edit, `python -m pytest -q tests/unit/test_periodic_geometry.py` exited 1 with three failures: orthogonal input raised `IndexError`; both signs of `xy` returned bounding rather than true x extents and copied x extents into y. The failure was reproduced again with the baseline parser temporarily restored; exact concise capture: `evidence/subagents/P01-01/red-regression-exact.txt`.
2. After restoring the fix following the preserved red rerun, `$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q tests/unit/test_periodic_geometry.py` exited 0: `3 passed in 7.59s`.
3. `$env:PYTHONDONTWRITEBYTECODE='1'; & C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q` exited 0: `8 passed in 7.97s`.
4. `git diff --check` exited 0 with no whitespace error.

Detailed commands, outputs, environment, and source/test SHA-256 values are in `evidence/subagents/P01-01/verification.md`.

## Limitations and remaining P01-01 work

- This slice does not repair or validate arbitrary/large periodic image offsets, repeated wrapping, persistent identity, image flags, minimum-image bond vectors, or topology-aware unwrapping.
- It does not validate general-triclinic (`abc origin`) dump syntax; the repair targets orthogonal and restricted-triclinic LAMMPS output only.
- Positive/negative `xy` conversion is covered. Nonzero `xz`/`yz` participates in the implemented documented conversion, but this 2D slice has no dedicated nonzero-`xz`/`yz` regression.
- No LAMMPS solver run, simulation, model training, or experimental data was needed or claimed.
- The main integrator still owns `TASKS.json`, `handoff.md`, and `README.md`, including the requested synchronized README status update at handoff.
