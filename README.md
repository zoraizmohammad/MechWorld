# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-10-01 after accepting the periodic-identity repair and assigning P01-04 reproducibility plus P01-09 analysis repair in isolated worktrees; P10-01 current related-work review also remains active.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced, then regression-repaired | The original A01-A05 failures remain archived under `evidence/source_audit_live/`; the current pure-Python diagnostic observes all five repaired, without invoking LAMMPS |
| LAMMPS environment | Verified for bounded serial smoke work | P00-03 doctor exited 0 on a real bonded fixture; required styles and analytical component energies passed; actual rupture/MPI/GPU/production use remain unvalidated |
| Run isolation | Local adapter verified | P01-08 lifecycle/concurrency tests pass and a real serial LAMMPS `run 0` completed through its immutable run directory; inherited runners and restart equivalence are not yet migrated/validated |
| Inherited mechanics repair | In progress | P01-01 through P01-03 and P01-08 are integrated; canonical edge schema, reproducible generation, dimensional analysis repair, and human-reviewed physics mapping remain |
| Physics/units contract | Audit complete; human review blocked | Current 2D tension conversion is sound; A16 has a definite factor-1000 energy-density defect; A12 coarse-grain stiffness/angle mapping, reference state, physical time, and any 3D thickness remain unapproved |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | Blocked on human/data inputs | Actual lab protocol, acquisition, raw files, calibration, and review cannot be fabricated or replaced by synthetic data |
| Release | Foundation gate accepted only | G0 is accepted from preserved-source, environment, access, and isolated-workflow evidence; G1-G11 remain unaccepted and no public push, hosting, data release, or paper submission is authorized |

No simulation, training, viewer, or experimental job is currently running.

Latest integration verification: P01-01 passed 15 focused periodic-geometry tests and the complete merged suite passed 62 tests; its 1,000-case restricted-triclinic minimum-image oracle also passed. P01-08 separately completed a real serial LAMMPS 2 Sep 2026 one-atom `run 0` through the new manager and closed successfully. Exact evidence is under `evidence/integration/`.

## Active work

- P01-01 is done: its parser and periodic-identity slices now cover tilted bounds, unsupported-form rejection, arbitrary wrapping/image shifts, exact 2D minimum images, and persistent atom identity. Persistent per-edge image identity remains explicitly assigned to P03-01.
- P01-04 on `research/p01-04-reproducibility`: add namespaced RNG streams, achieved-network metrics, and measured high-precision serialization error.
- P01-09 on `research/p01-09-analysis`: make grouped analysis idempotent and non-destructive, preserve independent-network interpolation, and repair the verified factor-1000 energy-density label/conversion defect without changing unapproved material parameters.
- P10-01 on `research/p10-01-related-work`: verify the current primary-source overlap matrix and bibliography; prior fracture GNNs already rule out any broad “first learned fracture simulator” claim.
- P01-05 is blocked for Mohammad/lab review: choose the coarse-grain mapping and parameter profile, reference/observable conventions, physical-time scope, and any thickness; do not apply a blind factor-of-two coefficient edit.
- Compatibility follow-up: seven inherited plotting/result scripts fail Python 3.11 compilation because of nested f-string quote syntax; targeted repaired files compile, and the broader issue is queued before P01-11.

## Remaining path

G0 environment/source acceptance is complete. The remaining critical sequence is G1 mechanics validation → G2 irreversible rupture → G3 canonical trajectories → G4 frozen nonleaking study cohorts → G5 baselines → G6 trained joint world model → G7 frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs exist; the explorer reaches G9 only with actual solver/model data; release and independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Current verified result after the integrated control-flow, parser/periodic-identity, environment, distribution, and run-isolation tests: 62 passed. The untouched bootstrap result was 5 passed after dependency repair. Neither result is by itself a mechanics, model, experiment, or release gate.
