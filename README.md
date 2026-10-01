# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-10-01 after accepting P01-04 reproducible generation and precise serialization; P01-10 structural-observable validation is the next eligible task.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced, then regression-repaired | The original A01-A05 failures remain archived under `evidence/source_audit_live/`; the current pure-Python diagnostic observes all five repaired, without invoking LAMMPS |
| LAMMPS environment | Verified for bounded serial smoke work | P00-03 doctor exited 0 on a real bonded fixture; required styles and analytical component energies passed; actual rupture/MPI/GPU/production use remain unvalidated |
| Run isolation | Local adapter verified | P01-08 lifecycle/concurrency tests pass and a real serial LAMMPS `run 0` completed through its immutable run directory; inherited runners and restart equivalence are not yet migrated/validated |
| Inherited mechanics repair | In progress | P01-01 through P01-04, P01-08, and P01-09 are integrated; structural-observable validation and human-reviewed physics mapping remain before G1 |
| Physics/units contract | Software defect repaired; human review blocked | Current 2D tension conversion is sound and A16's factor-1000 energy-density defect is repaired; A12 coarse-grain stiffness/angle mapping, reference state, physical time, and any 3D thickness remain unapproved |
| Related work and claims | Current targeted audit complete | 29 cited primary records are validated; direct prior learned changing-graph fracture work rejects broad first-of-kind claims; refresh and independent review remain mandatory before manuscript claims |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | Blocked on human/data inputs | Actual lab protocol, acquisition, raw files, calibration, and review cannot be fabricated or replaced by synthetic data |
| Release | Foundation gate accepted only | G0 is accepted from preserved-source, environment, access, and isolated-workflow evidence; G1-G11 remain unaccepted and no public push, hosting, data release, or paper submission is authorized |

No simulation, training, viewer, or experimental job is currently running.

Latest integration verification: P01-04 passed 14 focused, 45 compatibility, and 93 total tests. Real LAMMPS 20260902 loaded all 108 deterministic fixture atoms, preserved all 324 emitted coordinate tokens with zero measured max/RMS error, and closed. Exact evidence is under `evidence/integration/P01-04/`.

## Active work

- P01-01 is done: its parser and periodic-identity slices now cover tilted bounds, unsupported-form rejection, arbitrary wrapping/image shifts, exact 2D minimum images, and persistent atom identity. Persistent per-edge image identity remains explicitly assigned to P03-01.
- P01-04 is done: deterministic namespaced seeds, achieved-network metrics, canonical graph fingerprints, and 17-significant-digit serialization are integrated. The event/model streams are reserved but not yet consumed, and this is not mechanics or experimental validation.
- P01-10 is now dependency-eligible: validate pore, orientation, and chemical-connectivity observables under PBC, rendering-resolution changes, and visually crossing but unbonded lines.
- P01-09 is done: derived moduli are rebuilt atomically without deleting raw records, interpolation stays within networks/replicates, ambiguous axes fail explicitly, and the verified factor-1000 energy-density label/conversion defect is repaired. Cross-cohort replicate pairing remains positional until the later manifest defines persistent IDs.
- P10-01 is done as a targeted 2026-10-01 claim audit: prior GNN, fracture, failure-learning, stochastic-simulation, uncertainty, and PG-mechanics work is explicit. The eventual contribution must be scoped to demonstrated PG-specific joint mechanics/event rollouts, calibrated uncertainty, real experiments, and the scientist workflow; no broad priority language is allowed.
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

Current verified result after the integrated control-flow, parser/periodic-identity, environment, distribution, run-isolation, analysis-regression, reference-validation, and reproducibility tests: 93 passed. The untouched bootstrap result was 5 passed after dependency repair. Neither result is by itself a mechanics, model, experiment, or release gate.
