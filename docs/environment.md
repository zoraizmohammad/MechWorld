# Verified execution environment

Observed on 2026-09-30 in `C:/Users/mzora/MechWorld`.

## Host and resources

- OS: Windows 11 / NT `10.0.26200.0`
- CPU: 11th Gen Intel Core i7-1185G7, 4 physical cores / 8 logical processors
- RAM: 15.71 GiB
- GPU: NVIDIA T500, 4,096 MiB, driver 573.91; Intel Iris Xe also present
- Free space on `C:` at preflight: 48.67 GiB
- No relevant Python, LAMMPS, MPI, or scheduler process was running during the initial process scan.

This supports bounded local smoke work only. No production simulation/training budget or cluster allocation has been authorized.

## Python environment

The system interpreter is Python 3.11.9 at `C:/Users/mzora/AppData/Local/Programs/Python/Python311/python.exe`. Its initial package state had NumPy 2.2.2, SciPy 1.16.1, Pydantic 2.11.7, pytest 7.4.3, and PyTorch 2.8.0, but lacked the declared `pandas` and `matplotlib` requirements. The untouched test collection therefore failed with two `ModuleNotFoundError: pandas` errors; see `evidence/baseline/pytest.txt` and `pytest.xml`.

An ignored `.venv` was created with `--system-site-packages` so it can use the installed LAMMPS Python module. `pandas 3.0.6`, `matplotlib 3.11.2`, and `h5py 3.16.0` were installed there. The inherited suite then passed: 5 tests in 12.32 seconds. See `evidence/baseline/pytest_after_dependencies.txt` and `pytest_after_dependencies.xml`.

The environment is not yet a pinned release environment. Dependency locking remains part of P01-11.

## LAMMPS

- Executable: `C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/bin/lmp.exe`
- Python module: `C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/Python/lammps/__init__.py`
- Solver version: 20260902 / 2 Sep 2026
- Build: Windows serial MPI stubs, OpenMP, KOKKOS OpenMP/Serial, OpenCL GPU package; the executable reported no compatible GPU for its GPU package.
- Required names observed in `lmp -h`: harmonic and nonlinear bond styles, harmonic angle style, and `fix bond/break`.

P00-03 now has a repeatable doctor and integration test. In the integration worktree, `tools/doctor.py` exited 0 with LAMMPS version 20260902, all required styles present, and a 3-atom/2-bond/1-angle `run 0` fixture. Harmonic-bond, nonlinear-bond, and harmonic-angle component energies matched the independent formulas at `1e-9` relative/absolute tolerance; the total matched their sum. The solver closed, the targeted test passed 2 tests with no skips, and the full suite passed 14 tests. Evidence is in `evidence/integration/P00-03/`.

`fix bond/break` was configured and immediately removed without dynamics. No rupture occurred or was claimed. This establishes serial runtime/style/fixture capability, not inherited parameter provenance, minimization convergence, PG mechanics correctness, actual fracture, MPI behavior, or GPU acceleration.

## Missing or unavailable tooling

`mpiexec`, `qsub`, and `qstat` were not found. No active Hoffman2 session or scheduler identity was inferred from historical scripts. `pandas`, `matplotlib`, and `h5py` were absent before local environment repair. Any skipped solver integration must be reported as skipped/blocked rather than passed.
