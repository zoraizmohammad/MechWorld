# P02-05 integrated-main verification

Date: 2026-10-02 (America/New_York)

Working directory: `C:\Users\mzora\MechWorld`

Accepted subagent base/tip:
`3fdb17af5a1f7309255788f4df1cb38f0df4bd03..6f8e7f8db3c3bdd1d3127823fafccb1a433d08b1`

The five accepted commits were cherry-picked above the pushed P02-05 assignment
commit. Every pytest command used `.venv\Scripts\python.exe`, one process,
`PYTHONHASHSEED=0`, and two-thread ceilings for OMP, OpenBLAS, MKL, and NumExpr.
`PYTHONPATH` was prefixed with the integrated checkout's `src` directory.

## Commands and results

1. Focused/upstream compatibility:
   `.venv\Scripts\python.exe -B -m pytest tests/physics/test_stochastic_events.py tests/unit/test_generator_reproducibility.py tests/physics/test_damage_law.py -q -o junit_family=legacy --junitxml=evidence/integration/P02-05/focused-compatibility.xml`
   exited 0 with 101 passed in 3.36 s.
2. Full integrated suite:
   `.venv\Scripts\python.exe -B -m pytest -q -o junit_family=legacy --junitxml=evidence/integration/P02-05/full-suite.xml`
   exited 0 with 516 passed and 14 warnings in 110.83 s. The warnings are the
   already documented legacy elastic-route deprecation and inherited invalid
   escape-sequence warnings found by tracked-source compilation.
3. Isolated installed-wheel check:
   `.venv\Scripts\python.exe -B -m pytest tests/release/test_wheel_install.py -q -o junit_family=legacy --junitxml=evidence/integration/P02-05/wheel-install.xml`
   exited 0 with 1 passed in 97.55 s. The strict wheel allowlist includes only
   the new stochasticity module; the installed smoke resolved it inside the
   fresh site-packages, verified hidden projection, disabled event-process
   randomness, an unconsumed event seed, and passed the existing `pip check`
   and external-LAMMPS package checks.

## Artifact SHA-256 values

- `focused-compatibility.xml`:
  `245286a83de479682ab99e47eb150872ead43b718ac372ce95a7898b08a05d44`
- `full-suite.xml`:
  `a20377040ae676d61940f2e90f6fa6a06bb50524444e6f71aef936eebe5a3afa`
- `wheel-install.xml`:
  `0ebf0ef95dec2845c946935965a432867bf2478745d9bbc1160584a629502ba7`

## Acceptance boundary

P02-05 accepts reproducible sample-once quenched material-threshold variability
and conditional-replicate/cohort records. Conditional evolution is
deterministic once the frozen hidden field is fixed. The event seed is reserved
and unconsumed; event-process randomness, hazards, physical time/rates, and
fresh rupture lotteries fail closed. Graph/state IDs are caller-supplied,
hash-bound identities rather than independently derived geometry identities.

This task does not establish restart/load-step sensitivity, G2, a stochastic
event mechanism, biological fracture parameters, a dataset/model, a production
campaign, experiments, G3, or public-release readiness.
