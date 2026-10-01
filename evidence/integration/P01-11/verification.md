# P01-11 integration and G1 verification

Date: 2026-10-01 (America/New_York)

## Integrated revisions

- Assignment base on `main`: `9fbb2f0d7aac7207b1acb1facaebbf124e89e24f`.
- Package implementation: `2143d6c6d6e2406ce59717086c79efe412cb8c5f`.
- EOF-whitespace correction: `f819c25318c573902f47efd9bcb64d44b57f397e`.
- Candidate evidence: `7e6295a8cfa1dd2300ff351a7bd3511550fe02d8`.
- Cross-platform profile-comparison correction: `f3746f45cd3e3a3c64cd0e4fda18f3f96710b7f1`.
- Correction evidence: `adf9d7d220b78fed697dab77a4e8ca6612d6fbe2`.

All five new commits have effective author and committer
`Mohammad Zoraiz <zoraizmohammad@gmail.com>`. The independent reviewer accepted
the initial package and the newline correction. `git diff --check
9fbb2f0..adf9d7d` exited 0. The only unrelated worktree path was the preserved
untracked `PG_WORLD_MODEL_EXECUTION_PACKET/`.

## Reproduced integration-only defect

Working directory: `C:\Users\mzora\MechWorld`.

The first integrated full run used the project `.venv`, Python 3.11, at most
two BLAS/OpenMP threads, repository `src`, and the authorized external LAMMPS
Python path. It exited 1 with 171 passed and one failure in 151.11 s:

```text
.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence\integration\P01-11\full.xml
```

The failing assertion compared LF bytes returned by `git show` with CRLF bytes
materialized by Windows `core.autocrlf=true`. `git ls-files --eol` and
newline-insensitive comparison showed that the configuration and packaged
profile Git blobs matched. Registered profile IDs and canonical hashes were
unchanged. Evidence: `full.xml`, SHA-256
`f5c77b65110f27c48f57708ab9469b7bff5f7534a1c56755c3b0026367c36af5`.

The reviewed correction permits only CRLF-to-LF checkout normalization before
requiring exact remaining byte equality. It rejects bare carriage returns and
every individually mutated non-newline byte in its fixture. The runtime loader,
profile resources, registered hashes, and installed-resource tamper rejection
were not changed.

## Final verification on integrated main

Environment for every command below:

```text
cwd=C:\Users\mzora\MechWorld
PYTHONPATH=C:\Users\mzora\MechWorld\src;C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python
OMP_NUM_THREADS=2
MKL_NUM_THREADS=2
OPENBLAS_NUM_THREADS=2
```

Focused packaging/legacy-safety regression:

```text
.venv\Scripts\python.exe -B -m pytest tests\release\test_packaging_contract.py -q --junitxml=evidence\integration\P01-11\focused.xml
```

Exit 0: 7 passed in 0.72 s. JUnit SHA-256:
`2ffc1a425046803adff293a43685dd284e8a7af2fd3994bf3fdea0821db92d85`.

Final full suite:

```text
.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence\integration\P01-11\full-final.xml
```

Exit 0: 173 passed, 0 failed/errors/skips, 14 known warnings in 153.52 s.
The suite includes the tracked-source compilation test for all 80 Git-tracked
Python files and the isolated wheel test. JUnit SHA-256:
`eb33b228df1fd3f9065f36d85cf1ff1ed6ca9abc4ffa554687aa6747661f8c9c`.

The isolated wheel test was repeated with its detailed evidence hook:

```text
PGWORLD_WHEEL_EVIDENCE=evidence\integration\P01-11\wheel-install-final.json
.venv\Scripts\python.exe -B -m pytest tests\release\test_wheel_install.py -q --junitxml=evidence\integration\P01-11\wheel-final.xml
```

Exit 0: 1 passed in 152.46 s. JUnit SHA-256:
`05e5f22bb8515350cfce3fc2d4aa82ce68cebb9f66064a22a6c85668478df281`.
Detailed JSON SHA-256:
`2211c469569b21d007f255b02576196151a0352184c6f48ae362d7ce64e48e50`.

Measured installed-artifact results:

- Isolated PEP 517 wheel SHA-256:
  `0c7efae76ea4de0319c783067aca3dd96b11dce26d5c713cf1a0078e399afdfa`.
- The strict 31-member allowlist passed; private/generated/test/evidence/result
  payloads were absent.
- A new venv without system site packages installed the exact lock; `pip check`
  returned `No broken requirements found.`
- `PYTHONPATH` was cleared inside the installed test. Every project module
  resolved under the fresh venv; no checkout path was present on `sys.path`.
- `lammps` resolved only to
  `C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python\lammps\__init__.py`.
- Literal installed `pgworld.exe doctor` exited 0 against LAMMPS `20260902`,
  closed the solver, matched all bonded-fixture component energies, recorded
  `legacy_python_2026_03_12_v1` and hash
  `sha256:d4469fdf77c3a1102f5d086dc00b9b0be295763c976d3879559d97fb03274b0b`,
  and kept biological certification false.
- Installed P01-06 harmonic-fixture energy, maximum force, and maximum
  configurational-virial errors were all `0.0`; the solver closed.
- Installed P01-07 started and closed 7/7 LAMMPS instances with solver version
  `20260902` and no physical-time claim.
- All four immutable profile IDs/hashes matched their registry values; mutation
  of an installed profile failed closed with `PhysicsProfileError`.

## Acceptance boundary

This evidence accepts G1 only as bounded numerical/software consistency for the
packaged inherited mechanics under immutable legacy/provisional profiles. It
does not certify biological parameters, molecular coarse-graining, rupture,
physical-time dynamics, experiments, production compute, trained models,
public release rights, manuscript authorship, or manuscript submission. LAMMPS
is an external native installer dependency without Python distribution
metadata, so the exact lock is workstation-specific rather than universal.
