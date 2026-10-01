# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-10-01 after accepting the independently reviewed P01-06 energy/force/virial oracle and assigning P01-07 tangent/coupling validation in an isolated worktree. Final biological parameter review remains blocked.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced, then regression-repaired | The original A01-A05 failures remain archived under `evidence/source_audit_live/`; the current pure-Python diagnostic observes all five repaired, without invoking LAMMPS |
| LAMMPS environment | Verified for bounded serial smoke work | P00-03 doctor exited 0 on a real bonded fixture; required styles and analytical component energies passed; actual rupture/MPI/GPU/production use remain unvalidated |
| Run isolation | Local adapter verified | P01-08 lifecycle/concurrency tests pass and a real serial LAMMPS `run 0` completed through its immutable run directory; inherited runners and restart equivalence are not yet migrated/validated |
| Inherited mechanics repair | Tangent/coupling validation active | P01-01 through P01-04, P01-05A, P01-06, and P01-08 through P01-10 are integrated; P01-07 is isolated and active, followed by P01-11 packaging/G1 |
| Physics/units contract | Immutable provisional profiles verified; biological review pending | Four route-specific hashes separate historical execution from the required new virial-only policy and reject tampered persisted snapshots. Coarse-graining, angle mapping, nonlinear-fit recovery, and the final reviewed profile remain unapproved |
| Related work and claims | Current targeted audit complete | 29 cited primary records are validated; direct prior learned changing-graph fracture work rejects broad first-of-kind claims; refresh and independent review remain mandatory before manuscript claims |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | P08-01 blocked on access | AFM plus matched morphology is the proposed target, but actual lab protocol, custodian, permissions, acquisition, raw files, calibration, and review remain unconfirmed |
| Release | Foundation gate accepted only | G0 is accepted from preserved-source, environment, access, and isolated-workflow evidence; G1-G11 remain unaccepted and no public push, hosting, data release, or paper submission is authorized |

No persistent simulation, training, viewer, or experimental job is running. Further mechanics work remains limited to bounded serial analytical/LAMMPS fixtures under the recorded smoke-test limits.

Latest integration verification: P01-06 passed 26 focused, 56 compatibility, and 153 total tests. Real LAMMPS 20260902 comparisons closed every solver instance; maximum energy, force, and virial errors were `0.0 pN nm`, `4.547473508864641e-13 pN`, and `1.8189894035458565e-12 pN nm`. Exact evidence is under `evidence/integration/P01-06/`.

## Current work and blockers

- P01-01 is done: its parser and periodic-identity slices now cover tilted bounds, unsupported-form rejection, arbitrary wrapping/image shifts, exact 2D minimum images, and persistent atom identity. Persistent per-edge image identity remains explicitly assigned to P03-01.
- P01-04 is done: deterministic namespaced seeds, achieved-network metrics, canonical graph fingerprints, and 17-significant-digit serialization are integrated. The event/model streams are reserved but not yet consumed, and this is not mechanics or experimental validation.
- P01-10 is done: periodic image-pore metrics record raster settings, orientation/attachment vectors use the supported 2D periodic convention, and chemical connectivity ignores rendered crossings unless a bond exists.
- P01-09 is done: derived moduli are rebuilt atomically without deleting raw records, interpolation stays within networks/replicates, ambiguous axes fail explicitly, and the verified factor-1000 energy-density label/conversion defect is repaired. Cross-cohort replicate pairing remains positional until the later manifest defines persistent IDs.
- P10-01 is done as a targeted 2026-10-01 claim audit: prior GNN, fracture, failure-learning, stochastic-simulation, uncertainty, and PG-mechanics work is explicit. The eventual contribution must be scoped to demonstrated PG-specific joint mechanics/event rollouts, calibrated uncertainty, real experiments, and the scientist workflow; no broad priority language is allowed.
- P00-06 is done as a governance decision: main claims are quasi-static; the primary endpoint is phenomenological damage initiation; compute remains bounded/local; public release and manuscript submission still require separate approval.
- P01-05A is done after two independent correction reviews: distinct legacy routes and `reviewed_physics_provisional_v0` are immutable, persisted snapshots are revalidated, mixed aggregation fails closed, and every historical entry point is source-linked. P01-05 remains blocked for actual Prof. Schmidt/Octavio review and final biological parameter certification.
- P01-06 is done after adversarial correction and independent main verification: analytical, finite-difference, and real-LAMMPS fixtures cover harmonic/nonlinear bonds, noncollinear angles, configurational virials, periodic geometry, native 2D signs/normalization, and fixed-reference total/incremental tension without claiming biological certification.
- P01-07 is active on `research/p01-07-elastic-tangent`: it must replace the inherited one-sided/symmetrized-only elastic output with verified perturbation convergence, explicit strain/stress conventions, complete unsymmetrized diagnostics, normal-shear coupling retention, and separately labeled one-sided irreversible tangents.
- Tasks left before G1: accept P01-07, then complete P01-11 clean packaging and gate review. G1 may establish numerical consistency under provisional profiles, not biological calibration.
- Optional physical-time task P02-07 is deferred by scope. It must be reactivated before any rate, relaxation-time, fatigue-time, or time-to-failure claim.
- Compatibility follow-up: seven inherited plotting/result scripts fail Python 3.11 compilation because of nested f-string quote syntax; targeted repaired files compile, and the broader issue is queued before P01-11.

## Remaining path

G0 environment/source acceptance is complete. The remaining critical sequence is G1 mechanics validation → G2 irreversible rupture → G3 canonical trajectories → G4 frozen nonleaking study cohorts → G5 baselines → G6 trained joint world model → G7 frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs exist; the explorer reaches G9 only with actual solver/model data; release and independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Current verified result after the integrated control-flow, parser/periodic-identity, environment, distribution, run-isolation, analysis-regression, reference-validation, reproducibility, structural-observable, immutable-profile, and energy/force/virial tests: 153 passed. The untouched bootstrap result was 5 passed after dependency repair. This accepts P01-06 numerical consistency, not mechanics gate G1, biological parameters, a trained model, experiments, or release readiness.
