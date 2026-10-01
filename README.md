# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-09-30 bootstrap, before the first repair integration.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced | A01-A05 reproduced against the live source under `evidence/source_audit_live/`; no solver was used by that diagnostic |
| LAMMPS environment | In progress | LAMMPS 2 Sep 2026 instantiated and completed a bounded `run 0`; repeatable doctor/integration test is assigned under P00-03 |
| Inherited mechanics repair | In progress | First A01/A02 dump-parser regression and minimal fix is the next integration target |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | Blocked on human/data inputs | Actual lab protocol, acquisition, raw files, calibration, and review cannot be fabricated or replaced by synthetic data |
| Release | Not started | G0-G11 remain unaccepted; no public push, hosting, data release, or paper submission is authorized |

No simulation, training, viewer, or experimental job is currently running.

## Active work

- P00-03: commit a repeatable environment doctor and real required-style LAMMPS smoke test.
- P00-05: establish and record isolated subagent worktrees/ownership.
- P01-01: add the first failing A01/A02 regression, repair orthogonal/restricted-triclinic bounds parsing, and verify compatibility.
- P01-05 support: perform a read-only physics/units audit without self-approving lab-dependent coefficients.

## Remaining path

The critical sequence is G0 environment/source acceptance → G1 mechanics validation → G2 irreversible rupture → G3 canonical trajectories → G4 frozen nonleaking study cohorts → G5 baselines → G6 trained joint world model → G7 frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs exist; the explorer reaches G9 only with actual solver/model data; release and independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Expected verified bootstrap result: 5 passed. This result covers only the inherited tests and is not a mechanics, model, experiment, or release gate.
