# P03-01 verification record

Date: 2026-10-01 (America/New_York)

Worktree: `C:\Users\mzora\MechWorld-wt-p03-01`

Branch/base: `research/p03-01-schema` at
`0222b6d6fdee180e2e2daa86ccfebb276c91f1f6` before the P03-01 commits.

Evaluated implementation revision:
`c489b8f7b1560ad1e18157303cc00633dd9fdae6`.

Runtime: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`, Python
3.11.9, pytest 7.4.3. All verification used `-B`. Test commands set
`OMP_NUM_THREADS=2` and `OPENBLAS_NUM_THREADS=2`. The successful broader run
also set `PYTHONPATH` to this worktree's resolved `src` followed by the
authorized external LAMMPS path
`C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python`.
That module resolves to the same path and reports version 20260902.

## Red evidence

1. Initial missing-schema regression:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/unit/test_schema.py -q --junitxml=evidence/subagents/P03-01/red.xml
   ```

   Exit 1 in 1.68 s. Collection failed exactly with
   `ModuleNotFoundError: No module named 'pgworld.data'`; 0 tests ran.

2. Expanded P02-control/provenance regression:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/unit/test_schema.py -q --junitxml=evidence/subagents/P03-01/control-contract-red.xml
   ```

   Exit 1 in 1.94 s. Collection failed exactly because the stricter tests
   required `PressureDerivation`, which did not yet exist; 0 tests ran.

## Green evidence

1. Final focused schema suite:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/unit/test_schema.py -q --junitxml=evidence/subagents/P03-01/focused.xml
   ```

   Exit 0 in 2.12 s wall time; **46 passed in 0.78 s**, 0 failed, 0 errors,
   0 skipped. The JUnit includes the final control/provenance and adversarial
   tests. `focused-initial.xml` separately preserves the earlier 33-pass
   checkpoint before those requested contract expansions.

2. Relevant accepted-control/damage/tracked-source compatibility:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest tests/physics/test_loading.py tests/physics/test_damage_law.py tests/release/test_tracked_python_compiles.py -q --junitxml=evidence/subagents/P03-01/compatibility.xml
   ```

   Exit 0 in 6.53 s wall time; **99 passed in 4.31 s**, 0 failed/errors/skips.
   Twelve inherited invalid-escape deprecation warnings were reported by the
   tracked-source compilation test; no P03-01 file produced a warning.

3. Broader no-wheel run, first environmental attempt:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest -q --ignore=tests/release/test_wheel_install.py --junitxml=evidence/subagents/P03-01/no-wheel-full.xml
   ```

   Exit 1 in 23.00 s wall time with 3 collection errors because replacing
   `PYTHONPATH` with `src` alone hid the external, non-pip LAMMPS installation.
   The affected inherited modules imported `lammps`; this was not a schema
   assertion failure. The failed JUnit is retained rather than relabeled.

4. Broader no-wheel run with the authorized external solver path restored:

   ```powershell
   $src=(Resolve-Path src).Path
   $lammps='C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python'
   $env:PYTHONPATH="$src;$lammps"
   $env:OMP_NUM_THREADS='2'
   $env:OPENBLAS_NUM_THREADS='2'
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m pytest -q --ignore=tests/release/test_wheel_install.py --junitxml=evidence/subagents/P03-01/no-wheel-full-with-lammps.xml
   ```

   Exit 0 in 16.13 s wall time; **316 passed in 14.27 s**, 0 failed/errors/skips.
   Fourteen warnings were the same twelve inherited invalid-escape warnings
   plus two expected legacy elastic-output deprecation warnings.

5. Targeted compile:

   ```powershell
   $env:PYTHONPATH=(Resolve-Path src).Path
   C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B -m py_compile src/pgworld/data/schema.py src/pgworld/data/__init__.py tests/unit/test_schema.py
   ```

   Exit 0 in 0.80 s with no output.

The strict wheel-install test was intentionally excluded: its payload allowlist
is integrator-owned and has not yet been updated for the new `pgworld.data`
package. This return makes no installed-wheel or G3 claim.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| `red.xml` | `a7884bd5fb5c5bbd27805eb5cb5d75062429d10df72b4ca2355e549a4ce99b1b` |
| `control-contract-red.xml` | `ac834f8a60c893cba1c1c1edfa9cb3f7aeb006655d44da2ec851c7662fa970d4` |
| `focused-initial.xml` | `8534488e9820696b4c2f5499b63c359705396ce0aa87835d2a65014c0225b830` |
| `focused.xml` | `00d6d6e2a9e67a2901e4217377172eee33c5d09761de20ef9ab7c7ac7d01d13e` |
| `compatibility.xml` | `430051dbe5f814c097ff9f67b1dd344d11f43446fdeda8501ed02d0676384259` |
| `no-wheel-full.xml` | `2ad1c3f8c4bcc2c37c9461bde3f2d6ab5e319a724d4edd509ac6285c96b90d45` |
| `no-wheel-full-with-lammps.xml` | `dafa00c3b2ee6d64e819adadf17ae4c8f83181d5bdefb92d9c8d555a92b26dd3` |

## Limitations

- The schema is an in-memory/JSON-compatible contract. It does not write or
  validate HDF5 and does not migrate old persisted records.
- No actual solver trajectory, dataset, experimental file, private data, or
  model input was produced.
- P03-02 still must adapt accepted P02 records and compare exported values to
  the source solver; P03-04 still owns shards/manifests/atomic completion.
- Local stress, physical time, storage restart, split generation, and
  observation-operator validation remain capability-gated or later work.
- G3 remains not accepted.
