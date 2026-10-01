# MechWorld-PG

Physics-structured world models for bacterial cell-wall mechanics, built on the inherited PG Network of Springs simulator. The target is a verified topology-changing mechanics pipeline, reproducible graph trajectories, trained and evaluated models, actual experimental integration, and a scientist-facing explorer. Planning files, passing software tests, synthetic fixtures, saved untrained weights, and visualization-only demonstrations do not constitute project completion.

## Current status

Last synchronized with `handoff.md` and `TASKS.json`: 2026-09-30 after accepting G0 and assigning the bounded distribution, periodic-identity, and run-isolation repairs.

| Area | Status | Evidence or limitation |
|---|---|---|
| Source and packet | Preflight complete | Live inherited base `2486440`; packet hashes 21/21; original ZIP absent, so its historical archive hash is not locally recomputed |
| Python baseline | Verified after local dependency repair | Initial collection failed on missing `pandas`; ignored `.venv` rerun passed 5 tests in 12.32s under `evidence/baseline/` |
| Historical defects | Reproduced | A01-A05 reproduced against the live source under `evidence/source_audit_live/`; no solver was used by that diagnostic |
| LAMMPS environment | Verified for bounded serial smoke work | P00-03 doctor exited 0 on a real bonded fixture; required styles and analytical component energies passed; actual rupture/MPI/GPU/production use remain unvalidated |
| Inherited mechanics repair | In progress | P01-02 A03/A04/A06 and the A01/A02 parser slice are integrated; broader periodic image/identity work and A05 distribution repair remain |
| Physics/units contract | Audit complete; human review blocked | Current 2D tension conversion is sound; A16 has a definite factor-1000 energy-density defect; A12 coarse-grain stiffness/angle mapping, reference state, physical time, and any 3D thickness remain unapproved |
| Rupture, dataset, models, evaluation, explorer | Not started | Dependency-gated behind verified mechanics and actual topology-changing trajectories |
| Experimental validation | Blocked on human/data inputs | Actual lab protocol, acquisition, raw files, calibration, and review cannot be fabricated or replaced by synthetic data |
| Release | Foundation gate accepted only | G0 is accepted from preserved-source, environment, access, and isolated-workflow evidence; G1-G11 remain unaccepted and no public push, hosting, data release, or paper submission is authorized |

No simulation, training, viewer, or experimental job is currently running.

Latest integration verification: the LAMMPS target passed 2 tests with no skips and the complete suite passed 14 tests. Parser integration separately passed 3 targeted and 12 total tests. Exact evidence is under `evidence/integration/`.

## Active work

- P01-01 on `research/p01-01-periodic-identities`: add general-triclinic rejection and repeated/large-offset image-shift and persistent-identity coverage; the parser slice alone does not complete the task.
- P01-03 on `research/p01-03-distributions`: reproduce A05 first, then implement and statistically test a bounded, explicitly defined distribution sampler without changing the inherited number-law meaning.
- P01-08 on `research/p01-08-run-isolation`: add typed local run configuration, unique work directories, bounded concurrency checks, and failure-safe solver cleanup without launching production jobs.
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

Current verified result after the integrated control-flow, parser, and environment tests: 14 passed. The untouched bootstrap result was 5 passed after dependency repair. Neither result is by itself a mechanics, model, experiment, or release gate.
