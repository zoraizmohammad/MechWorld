# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-10-01 after independently reviewing, integrating, verifying, and pushing P02-01, then assigning P02-02 damage/event definitions in an isolated worktree. Final biological parameter review remains blocked.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced, then regression-repaired | The original A01-A05 failures remain archived under `evidence/source_audit_live/`; the current pure-Python diagnostic observes all five repaired, without invoking LAMMPS |
| LAMMPS environment | Verified for bounded serial smoke work | P00-03 doctor exited 0 on a real bonded fixture; required styles and analytical component energies passed; actual rupture/MPI/GPU/production use remain unvalidated |
| Run isolation | Local adapter verified | P01-08 lifecycle/concurrency tests pass and a real serial LAMMPS `run 0` completed through its immutable run directory; inherited runners and restart equivalence are not yet migrated/validated |
| Inherited mechanics repair | G1 accepted | P01-01 through P01-11 are integrated or explicitly retained as provisional/blocked; the installable wheel and `pgworld doctor` passed fresh-environment real-LAMMPS checks |
| Physics/units contract | Immutable provisional profiles verified; biological review pending | Four route-specific hashes separate historical execution from the required new virial-only policy and reject tampered persisted snapshots. Coarse-graining, angle mapping, nonlinear-fit recovery, and the final reviewed profile remain unapproved |
| Related work and claims | Current targeted audit complete | 29 cited primary records are validated; direct prior learned changing-graph fracture work rejects broad first-of-kind claims; refresh and independent review remain mandatory before manuscript claims |
| Rupture, dataset, models, evaluation, explorer | P02-01 done; P02-02 active | Explicit quasi-static controls are accepted; the phenomenological damage/event contract is isolated on `research/p02-02-damage-law`, while topology mutation and later gates remain unaccepted |
| Experimental validation | P08-01 blocked on access | AFM plus matched morphology is the proposed target, but actual lab protocol, custodian, permissions, acquisition, raw files, calibration, and review remain unconfirmed |
| Release | Foundation and mechanics gates accepted | G0 and numerical/software mechanics gate G1 are accepted; G2-G11 remain unaccepted and no public hosting, data/model release, or paper submission is authorized |

No persistent simulation, training, viewer, or experimental job is running. Further mechanics work remains limited to bounded serial analytical/LAMMPS fixtures under the recorded smoke-test limits.

Latest integration verification: P02-01 passed 213 total tests on integrated `main` in 150.22 seconds, including 40 strict loading-control cases and a fresh installed-wheel check. Its separate clean-wheel evidence passed the strict allowlist and `pip check`, imported controls only from fresh site-packages, and retained the accepted external-LAMMPS checks. Exact evidence is under `evidence/integration/P02-01/` and `evidence/subagents/P02-01/`.

## Current work and blockers

- P01-01 is done: its parser and periodic-identity slices now cover tilted bounds, unsupported-form rejection, arbitrary wrapping/image shifts, exact 2D minimum images, and persistent atom identity. Persistent per-edge image identity remains explicitly assigned to P03-01.
- P01-04 is done: deterministic namespaced seeds, achieved-network metrics, canonical graph fingerprints, and 17-significant-digit serialization are integrated. The event/model streams are reserved but not yet consumed, and this is not mechanics or experimental validation.
- P01-10 is done: periodic image-pore metrics record raster settings, orientation/attachment vectors use the supported 2D periodic convention, and chemical connectivity ignores rendered crossings unless a bond exists.
- P01-09 is done: derived moduli are rebuilt atomically without deleting raw records, interpolation stays within networks/replicates, ambiguous axes fail explicitly, and the verified factor-1000 energy-density label/conversion defect is repaired. Cross-cohort replicate pairing remains positional until the later manifest defines persistent IDs.
- P10-01 is done as a targeted 2026-10-01 claim audit: prior GNN, fracture, failure-learning, stochastic-simulation, uncertainty, and PG-mechanics work is explicit. The eventual contribution must be scoped to demonstrated PG-specific joint mechanics/event rollouts, calibrated uncertainty, real experiments, and the scientist workflow; no broad priority language is allowed.
- P00-06 is done as a governance decision: main claims are quasi-static; the primary endpoint is phenomenological damage initiation; compute remains bounded/local; public release and manuscript submission still require separate approval.
- P01-05A is done after two independent correction reviews: distinct legacy routes and `reviewed_physics_provisional_v0` are immutable, persisted snapshots are revalidated, mixed aggregation fails closed, and every historical entry point is source-linked. P01-05 remains blocked for actual Prof. Schmidt/Octavio review and final biological parameter certification.
- P01-06 is done after adversarial correction and independent main verification: analytical, finite-difference, and real-LAMMPS fixtures cover harmonic/nonlinear bonds, noncollinear angles, configurational virials, periodic geometry, native 2D signs/normalization, and fixed-reference total/incremental tension without claiming biological certification.
- P01-07 is done after independent rejection/correction cycles: the immutable fixed reference is separate from the local tangent base, current-area native-2D conventions are explicit, all nine raw couplings survive, saved stencils replay on readback, branch-changing outputs are directional secants, and the inherited misleading route fails closed by default.
- P01-11 and G1 are done after two independent review cycles. The package bundles unchanged immutable profile identities, exposes `pgworld doctor`, makes the old elastic task explicitly forensic/fail-closed, compiles all 80 tracked Python files under Python 3.11, and passes a true isolated install against external LAMMPS 20260902.
- P02-01 is done after independent adversarial review. Forty focused cases enforce absolute/increment replay, coordinate covariance, cyclic path progress, closed-cylinder pressure assumptions, stable-ID intervention locality, and the separation of prescribed interventions from material rupture. Integrated `main` passed 213/213 tests; P02-02 is now eligible to define the phenomenological damage law and distinct failure endpoints.
- P02-02 is active from pushed main `7b2a025` in an isolated worktree. Its bounded contract covers deterministic and sample-once heterogeneous thresholds, irreversible masks, right-censored no-event outcomes, damage initiation, and separate connectivity/degradation/instability labels; its narrow wheel-test ownership only names/import-smokes the new public module without weakening exclusions. It cannot implement the later solver/topology cascade or claim molecular cleavage validation.
- Optional physical-time task P02-07 is deferred by scope. It must be reactivated before any rate, relaxation-time, fatigue-time, or time-to-failure claim.
- Compatibility follow-up complete: the seven inherited nested-f-string quote failures were repaired without changing plotting semantics, and the tracked-source compilation regression now covers all 80 Python files.

## Remaining path

G0 environment/source acceptance and G1 numerical mechanics validation are complete. The remaining critical sequence is G2 irreversible rupture, G3 canonical trajectories, G4 frozen nonleaking study cohorts, G5 baselines, G6 trained joint world model, and G7 frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs exist; the explorer reaches G9 only with actual solver/model data; release and independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Current verified result after the integrated control-flow, parser/periodic-identity, environment, distribution, run-isolation, analysis-regression, reference-validation, reproducibility, structural-observable, immutable-profile, energy/force/virial, tangent, packaging, quasi-static-control, legacy-safety, and tracked-compilation tests: 213 passed. The untouched bootstrap result was 5 passed after dependency repair. This accepts P02-01 controls, not the rupture law, irreversible topology, biological parameters, a trained model, experiments, or public-release readiness.
