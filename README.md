# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-10-02 after
independently accepting and integrating P02-04 event localization/accounting
and the corrected P03-01 trajectory/access schema on top of the preserved
project-phase documentation. Final biological parameter review remains
blocked.

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
| Rupture, dataset, models, evaluation, explorer | P02-01 through P02-04 and P03-01 done; P02-05 active | Deterministic bounded localization/phase accounting and strict in-memory trajectory/access replay are integrated; sample-once material-disorder provenance is assigned in an isolated worktree, while restart/sensitivity, solver export/storage, datasets, models, evaluation, and the explorer remain incomplete; G2 and later gates remain unaccepted |
| Experimental validation | P08-01 blocked on access | AFM plus matched morphology is the proposed target, but actual lab protocol, custodian, permissions, acquisition, raw files, calibration, and review remain unconfirmed |
| Release | Foundation and mechanics gates accepted | G0 and numerical/software mechanics gate G1 are accepted; G2-G11 remain unaccepted and no public hosting, data/model release, or paper submission is authorized |

No persistent simulation, training, viewer, or experimental job is running. Further mechanics work remains limited to bounded serial analytical/LAMMPS fixtures under the recorded smoke-test limits.

Latest integration verification: the combined P02-04/P03-01 acceptance passed
163 focused/package tests in 3.98 seconds, 487 full-suite tests in 119.37
seconds, and one isolated installed-wheel test in 115.98 seconds on integrated
`main`. The focused set includes the bounded real serial-LAMMPS localization
fixture and 108 adversarial schema tests. Exact commands, hashes, and limits
are under `evidence/integration/P02-04-P03-01/`; preserved subagent red/green
evidence remains under `evidence/subagents/P02-04/` and
`evidence/subagents/P03-01/`.

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
- P02-01 is done after independent adversarial review. Forty focused cases enforce absolute/increment replay, coordinate covariance, cyclic path progress, closed-cylinder pressure assumptions, stable-ID intervention locality, and the separation of prescribed interventions from material rupture.
- P02-02 is done after multiple independent defect rounds. Fifty-eight focused cases enforce registered-profile/reference binding, immutable threshold/event/state replay, stable-ID sample-once disorder, invalid-reference handling, irreversible masks, excluded event origins, cyclic path-progress censoring, and separate failure endpoints. Integrated `main` passed 271/271 tests. P02-03 is now eligible to implement the actual solver/topology cascade; G2 is not yet accepted.
- P02-03 is done after independent adversarial review. The integrated contract uses opaque stable IDs and authoritative edge images; deletes exact dependent angles and the physical bond; captures pre/delete-unrelaxed/post-relaxed mechanics; rolls back failed mutations; reassesses fresh cascades; and retains disconnected atoms. Real evidence is deliberately limited to a constrained serial orthogonal harmonic fixture with diagonal deformation and extension-ratio rupture—not a production/general PG or nonlinear-peptide adapter.
- P02-04 is done after independent review and integrated verification. It
  localizes the first accepted crossing with bounded deterministic refinement,
  restores every discarded trial, and separates loading, deletion,
  held-control boundary, and relaxation terms. Its real evidence is still the
  exact tiny harmonic fixture with diagonal deformation and extension-ratio
  rupture; persistent schedule/restart, nonlinear-peptide localization,
  sensitivity, and G2 remain later work.
- P03-01 is done after four preserved adversarial correction rounds. The v1
  schema keeps opaque identities, fixed-reference prestress, signed periodic
  images, controls, phases, convergence, topology events, endpoints, and
  relationally checked observed/target/privileged views. The wheel installs
  these in-memory/replay modules without installing private/generated data.
  P03-02/P03-04 still own real solver export and HDF5 storage, so no canonical
  dataset or G3 claim exists yet.
- P02-05 is active from pushed main `3fdb17a` in the isolated
  `research/p02-05-stochasticity` worktree. It must bind
  sample-once material disorder and conditional replicates to the existing
  damage/localization contracts without adding an unvalidated event lottery or
  physical-time claim. The event seed stays reserved and unconsumed; core work
  requires no LAMMPS. P02-06 then owns restart/load-step sensitivity and G2.
- Optional physical-time task P02-07 is deferred by scope. It must be reactivated before any rate, relaxation-time, fatigue-time, or time-to-failure claim.
- Compatibility follow-up complete: the seven inherited nested-f-string quote failures were repaired without changing plotting semantics, and the tracked-source compilation regression now covers all 80 Python files.

## Remaining path

G0 environment/source acceptance and G1 numerical mechanics validation are
complete. P02-04 and P03-01 are integrated, but neither G2 nor G3 is accepted.
The remaining critical sequence starts with active P02-05 material-disorder provenance,
P02-06 restart/sensitivity and G2, P03-02 through P03-06 and G3, G4 frozen
nonleaking study cohorts, G5 baselines, G6 trained joint world model, and G7
frozen evaluation. Experimental G8 proceeds in parallel when real lab inputs
exist; the explorer reaches G9 only with actual solver/model data; release and
independent audit are G10-G11.

The machine-readable source of task truth is `TASKS.json`. The detailed current state, commands, evidence, active ownership, and blockers are in `handoff.md`. With every future handoff, this README must be updated in the same logical change so the status and tasks left do not drift.

## Reproduce the current baseline

```powershell
cd C:\Users\mzora\MechWorld
.venv\Scripts\python.exe -m pytest -q
```

Current verified result after integrating deterministic localization/accounting
and the strict trajectory/access schema: 487 passed. The untouched bootstrap
result was 5 passed after dependency repair. This accepts bounded software and
fixture contracts, not G2/G3, a production/general PG fracture campaign,
biological parameters, a canonical dataset, a trained model, experiments, or
public-release readiness.
