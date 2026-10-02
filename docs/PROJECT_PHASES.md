# MechWorld PG Project Phases

This document is a short, PI-facing roadmap for extending the inherited PG Network of Springs simulator into a verified topology-changing mechanics and machine-learning research project. It summarizes the intended sequence of work without replacing `docs/RESEARCH_PLAN.md`, `TASKS.json`, or the evidence gates in `docs/VERIFICATION_AND_RELEASE.md`.

## Current position

The foundation through commit `44dbbf0` established the transactional rupture
cascade. The current 2026-10-02 integrated state additionally includes reviewed
P02-04 event localization/accounting and the P03-01 trajectory/access schema.
The repository has:

- preserved the inherited simulator, provenance, authorship, and parameter routes;
- reproduced and repaired documented software and analysis defects;
- verified energy, forces, virials, periodic geometry, native two-dimensional tension, and elastic response against analytical calculations and bounded serial LAMMPS fixtures;
- implemented explicit quasi-static controls and a transactional rupture cascade with irreversible bond and dependent-angle removal, rollback, and fresh cascade reassessment; and
- passed 487 tests on the current integrated main revision.

G0 environment and source acceptance and G1 numerical mechanics validation are
accepted. Deterministic localization/accounting and the in-memory trajectory
contract are accepted within their bounded scopes. Material-disorder provenance,
restart/sensitivity, canonical solver export/storage, trained models, frozen
evaluation, the scientist-facing explorer, and release review remain incomplete.

## Phase 1 Repository foundation and reproducibility

Preserve provenance, reproduce historical defects, establish the supported environment, package the code, and record auditable tests and evidence.

**Status:** Complete for the accepted foundation scope.

## Phase 2 Mechanics and parameter contract

Verify coefficient conventions, units, periodic geometry, reference states, membrane tension, forces, virials, and elastic response without silently changing inherited physics.

**Status:** Numerical implementation checks are complete. Biological interpretation remains provisional until the coarse-graining, bending, attachment, and nonlinear peptide conventions receive scientific review.

## Phase 3 Quasi static loading and topology change

Apply controlled loading, identify mechanically triggered rupture, remove physical bonds and dependent angles irreversibly, localize events, and separate loading, deletion, held-control boundary work, and relaxation terms.

**Status:** In progress. The transactional cascade, deterministic event
localization, and phase-specific accounting are integrated for the certified
tiny harmonic fixture. Sample-once material-disorder provenance and
restart/load-step sensitivity remain before G2; the work does not yet establish
general nonlinear-peptide fracture or biological rupture parameters.

## Phase 4 Trajectory data and study cohorts

Define a versioned graph-trajectory format with persistent identities, complete provenance, immutable reference state, topology events, observed and hidden fields, censoring rules, and grouped nonleaking splits.

**Status:** In progress. The strict opaque-ID in-memory/replay schema passed
adversarial review. Canonical solver export, HDF5 shards, grouped splits, loader
round trips, and G3 remain incomplete.

## Phase 5 Simulation campaign and baseline models

Generate bounded simulation trajectories across network architectures, loading paths, localized interventions, and documented rupture laws. Train mechanistic and learned baselines under identical grouped splits.

**Status:** Planned after fracture and schema acceptance. A measured pilot will precede any larger compute request.

## Phase 6 Physics structured world model and evaluation

Train a model that predicts deformation, mechanical redistribution, and irreversible topology changes over closed-loop rollouts. Evaluate generalization, physical consistency, uncertainty, and computational efficiency at matched prediction error.

**Status:** Planned. Claims require trained checkpoints, frozen test cohorts, calibrated uncertainty, ablations, and reproducible baseline comparisons.

## Phase 7 Scientist facing explorer

Provide access to verified simulator and model outputs, including graph state, rupture history, mechanical fields, uncertainty, and a cylindrical display with the correct axial and hoop conventions.

**Status:** Planned after the data and model interfaces stabilize. Cylindrical views will be labeled as displays of two-dimensional mechanics unless native three-dimensional predictions are separately validated.

## Phase 8 Open source comparison and evidence backed release

Compare the simulator and learned model with suitable open-source data or published observables when reuse terms, units, preparation conditions, and observation mappings are documented. Complete independent scientific review, contribution records, release checks, and manuscript approval.

**Status:** Planned. Public release and manuscript submission remain separate human decisions after the required evidence gates are satisfied.

## Data strategy

Simulation-generated trajectories are the primary controlled data source because they provide complete loading histories, mechanical states, topology changes, and rupture labels. Suitable open-source datasets and published measurements can support comparison and validation when their access and reuse terms are verified and their observables can be mapped to the model without inventing missing labels.

Related trajectories from the same base network will remain in one split. Normalizers will be fitted from training data only, and predictors will not receive future states, hidden rupture seeds, or test-derived information.

## Immediate next steps

1. Complete sample-once material-disorder/conditional-replicate provenance.
2. Validate restart equivalence and load-step/refinement sensitivity; accept G2
   only if the real bounded rupture workflow passes.
3. Export accepted solver states/events into the reviewed schema, implement
   immutable storage and grouped splits, and accept G3 only after round-trip
   evidence.
4. Profile a small simulation pilot and report runtime, memory, storage, and
   convergence before requesting a larger campaign.
5. Generate grouped study cohorts and evaluate mechanistic and learned
   baselines.
6. Train and evaluate the joint topology-and-mechanics world model.
7. Build the scientist-facing explorer from verified solver and model outputs.
8. Complete open-source comparison, independent review, and release evidence.

## Scientific guidance requested

- Review the glycan coarse-graining and whether the repository's 1.03 nm edges represent a two-edge refinement of the published approximately 2.0 nm glycan representation.
- Confirm or correct the harmonic coefficient, bending interactions, peptide attachment placement, and nonlinear peptide energy parameter, with Octavio's input on inherited implementation provenance where useful.
- Advise which open-source measurements and published structural or mechanical observables provide defensible comparisons for the simulation-first study.
- Review the scientific scope and claims before the larger simulation campaign, model release, or manuscript preparation.
- Establish contribution, authorship, rights, and release approvals when the model and evaluation evidence are complete.

## Study boundaries

- The main study is quasi-static. Loading increments and minimized states are not physical-time samples.
- Primary mechanical outputs remain native two-dimensional membrane quantities. Three-dimensional modulus or stress claims require an approved thickness model.
- Damage initiation is the first accepted mechanically triggered irreversible physical-bond rupture, not catastrophic cell failure. Later cascades and mechanical degradation remain part of the evaluation.
- A saved checkpoint is not a research result until it has been trained and evaluated on frozen, nonleaking cohorts with reproducible evidence.
- Release and manuscript claims must remain narrower than the evidence and preserve inherited scientific and software attribution.

## Completion criteria

The project is complete only when the verified simulator produces reproducible topology-changing trajectories, the model is trained and evaluated against strong baselines, uncertainty and physical consistency are measured, the explorer exposes real solver and model outputs, open-source comparisons are documented within their permitted terms, and the final evidence package passes independent scientific and release review.
