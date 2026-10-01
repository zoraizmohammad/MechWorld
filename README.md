# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-09-30, three isolated subagent assignments active from base `c0ec8aa`.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced | A01-A05 reproduced against the live source under `evidence/source_audit_live/`; no solver was used by that diagnostic |
| LAMMPS environment | In progress | LAMMPS 2 Sep 2026 instantiated and completed a bounded `run 0`; repeatable doctor/integration test is assigned under P00-03 |
| Inherited mechanics repair | In progress | P01-02 A03/A04/A06 control-flow defects are fixed with 4 targeted tests; first A01/A02 dump-parser integration remains active |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | Blocked on human/data inputs | Actual lab protocol, acquisition, raw files, calibration, and review cannot be fabricated or replaced by synthetic data |
| Release | Not started | G0-G11 remain unaccepted; no public push, hosting, data release, or paper submission is authorized |

No simulation, training, viewer, or experimental job is currently running.

Latest integrated verification before this commit: the P01-02 target passed 4 tests and the complete suite passed 9 tests. Exact pre/post logs are under `evidence/regressions/P01-02/`.

## Active work

- P00-03 on `research/p00-03-environment`: commit a repeatable environment doctor and real required-style LAMMPS smoke test.
- P00-05: review the three isolated worktree reports/commits and verify that no shared path was edited.
- P01-01 on `research/p01-01-periodic-bounds`: add the first failing A01/A02 regression, repair orthogonal/restricted-triclinic bounds parsing, and verify compatibility.
- P01-05 support on `research/p01-05-physics-audit`: perform a source-only physics/units audit without self-approving lab-dependent coefficients.
- Compatibility follow-up: seven inherited plotting/result scripts fail Python 3.11 compilation because of nested f-string quote syntax; targeted repaired files compile, and the broader issue is queued before P01-11.

## Remaining path

The critical sequence is G0 environment/source acceptance → G1 mechanics validation → G2 irreversible rupture → G3 canonical trajectories → G4 frozen nonleaking study cohorts → G5 baselines → G6 trained joint world model → G7 frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs exist; the explorer reaches G9 only with actual solver/model data; release and independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Expected verified bootstrap result: 5 passed. This result covers only the inherited tests and is not a mechanics, model, experiment, or release gate.
