# MechWorld-PG: Full Research and Implementation Plan

**Project:** Physics-Structured World Models for Bacterial Cell-Wall Mechanics

**Project lead:** Mohammad Zoraiz

**Requested identity for new project commits:** Mohammad Zoraiz <zoraizmohammad@gmail.com>

**Planning baseline:** uploaded `PG-Network-of-Springs-main.zip`, reviewed September 30, 2026.
**Status:** implementation specification, not a completed model, executed simulation campaign, or experimental result.

“MechWorld-PG” is a working project label. Preserve the proposal's scientific scope even if the repository or paper is renamed. Refer to `SOURCES.md` for source IDs and `SOURCE_AUDIT.md` for archive-specific evidence. The machine-readable execution queue is `../TASKS.json`.

## 1. What completion actually means

Deliver an experimentally evaluated, reproducible framework that predicts the mechanical evolution of heterogeneous PG networks under controlled perturbations, including continuous deformation, stress redistribution, irreversible damage, and discrete bond loss. Deliver the trained model and the means for another scientist to run, inspect, challenge, and reproduce it.

The full project has six inseparable deliverables:

1. **A verified mechanistic simulator:** preserve and extend the existing network generator and LAMMPS mechanics; add defensible fracture and intervention models.
2. **A versioned graph-trajectory dataset:** complete state/control/event records, independent splits, provenance, and failure diagnostics.
3. **A trained physics-structured world model:** deployable checkpoints, autoregressive rollout, uncertainty, dynamic topology, and documented applicability limits.
4. **A research evaluation:** strong baselines, ablations, held-out architectures and loads, long-horizon tests, a generic fracture benchmark, and honest negative results.
5. **An experimental study:** established lab workflows, new measurements collected by Mohammad with lab supervision, computational observation models, and held-out validation.
6. **A scientist-facing release:** a usable browser-based 3D explorer, local inference tools, documentation, reproducible figures, and a manuscript ready for human review.

A passing software test suite is not experimental validation. A saved checkpoint is not evidence of useful prediction. A cylinder-shaped rendering is not evidence of a 3D mechanical simulation. A complete research study may reject a hypothesis; it must not manufacture a positive finding to satisfy a milestone.

### Proposal-to-deliverable map

| Proposal requirement | Required implementation | Completion evidence |
|---|---|---|
| Vary glycan length, density, orientation, stiffness, defects | Typed generator configs and achieved-network measurements | Reproducible sweeps, measured distributions, feasibility report |
| Turgor-related and external loading | Biaxial/shear/local perturbation controls; explicit membrane-tension/pressure relationship | Analytical checks and loading-mode tests |
| Local bond weakening/removal | Versioned intervention and fracture engines | Pre/post event states, irreversibility and cascade tests |
| Joint evolving graph and mechanical state | Coupled mechanics/topology transition model | Closed-loop test rollouts with predicted topology |
| Stochastic material variability | Explicit disorder and event-noise models | Repeated conditional trials and calibration results |
| Unseen architectures and loads | Grouped out-of-distribution evaluation | Frozen split manifest and independent-network confidence intervals |
| Comparison against mechanics/data-driven models | Matched-input baselines and runtime accounting | Accuracy–cost tables and ablations |
| Experimental bacterial mechanics | AFM/microscopy acquisition and observation operator | Raw data, metadata, QC, held-out predictions |
| General framework beyond bacteria | Generic spring/fracture benchmark | Reused architecture and separately reported transfer/retraining |
| Accessible 3D model and scientific use | Browser explorer, local API/CLI, model/data cards | Browser/inference integration tests and scientist usability review |

## 2. Starting point and limits of the existing code

The uploaded archive contains 49 Python files and simulation/analysis/cluster scripts. The original five tests pass in the review environment. This verifies only those tests. LAMMPS is not installed in that environment, so no existing LAMMPS run or scientific output was validated here. The archive has no `.git` directory and does not include the historical results campaign or trained ML checkpoints.

Preserve the existing scientific work in `src/assemble_pg_network.py`, `lammps_PG_objects.py`, `run_lammps_isotropic_strain.py`, `run_lammps_elastic_tensor.py`, and the pore/orientation/modulus analysis modules. Wrap and repair this foundation rather than discarding it for a visually attractive toy simulator.

Do not infer authorship from the ZIP filename, comments, or this plan. Preserve inherited notices and record upstream provenance. New commits can use the requested identity without rewriting inherited authorship or silently removing collaborators from a manuscript.

## 3. Scientific questions and predeclared hypotheses

**Primary question:** Does explicitly coupling mechanical equilibrium updates with irreversible topology transitions improve the accuracy, stability, and computational efficiency of long rollouts in heterogeneous networks relative to matched learned and mechanistic baselines?

**H1, continuous mechanics:** physical structure reduces rollout drift or achieves a better accuracy–cost tradeoff than an unconstrained graph predictor.

**H2, topology:** a jointly conditioned event/mechanics model predicts post-damage load redistribution better than a fixed-topology model or an uncoupled bond classifier.

**H3, generalization:** improvements persist on unseen graph realizations, loading paths, architecture regimes, and sizes, not merely nearby frames from the same network.

**H4, uncertainty:** predicted event and failure distributions are calibrated on repeated stochastic realizations conditioned on the same observable state.

**H5, experiment:** the model's macroscopic observables predict held-out experimental measurements within stated uncertainty and outperform or match an appropriate calibrated mechanistic baseline at a useful computational cost.

Graph-based learned simulation and constraint-based simulation already exist [S12–S14]. The novelty claim must be supported by an updated literature comparison, not the words “world model” or “physics-informed.” Explicitly compare chemical/material bond deletion with adaptive remeshing: they are not the same change of graph.

A fine-resolution simulator is the reference for simulation-generated labels. Do not claim to be more accurate than that same reference on its own labels. Test speed at matched error, error at matched cost, and separately test experimental agreement.

## 4. Lock the physical problem before generating the main dataset

### 4.1 Quasi-static first, physical time only when justified

The active workflow repeatedly minimizes energy after changes of box size. Its frame index is a **loading-step index**, not elapsed biological time. The primary model should initially be a controlled quasi-static transition model:

`p(G[k+1], X[k+1], damage[k+1] | G[k], X[k], damage[k], history, control[k], material)`.

Use a full deformation gradient or boundary displacement as the control. Record its increment. Separate progress coordinate `lambda_load` from physical time `time_ns`.

A rate-dependent/time-series claim requires a separate dynamics branch with validated masses or mobility, damping, temperature/noise if used, timestep convergence, and a calibrated relationship to measurement times. Do not relabel minimizer iterations as nanoseconds. This branch becomes required if the final paper claims relaxation times, loading-rate dependence, or stochastic time-to-failure. Otherwise report quasi-static evolution and event-to-failure in loading units precisely.

### 4.2 Known mechanics and parameter governance

Retain glycan extension, peptide extension, and glycan-angle bending. Implement a unit-audited independent energy/force oracle for small networks. Audit every coefficient against its actual LAMMPS potential, not its variable name.

LAMMPS harmonic bonds use `E = K(r-r0)^2`; the conventional small-strain spring stiffness is `2K` [S06]. LAMMPS nonlinear bonds take an **energy** coefficient epsilon [S07]. The existing label `pN/nm` on the peptide coefficient needs investigation; it is not a sufficient basis for choosing a corrected number. Verify the original fit, DSU convention, rest lengths, and energy conversion with the lab.

Keep two parameter profiles if necessary: `legacy_reproduction` and `reviewed_physics`. Mark the former as reproduction-only when unresolved. Never mix their outputs into one undocumented dataset. Freeze a parameter table containing value, unit, definition, evidence, uncertainty/range, reviewer, and version.

### 4.3 Stress, tension, elasticity, and pressure

In a two-dimensional LAMMPS simulation, virial normalization uses area [S05]. Store membrane tension/stiffness in force-per-length units, preferably pN/nm internally and N/m in summaries. Convert to a three-dimensional stress/modulus only with an explicit thickness assumption and its uncertainty.

Distinguish total prestress from incremental stress. Use consistent finite-strain measures and work-conjugate stress/strain definitions when interpreting tangent stiffness. Store the unsymmetrized tangent matrix before deriving a symmetric constitutive approximation. The current formulas ignore normal–shear couplings in deriving orthotropic moduli; validate that approximation rather than assuming it for each disordered sample.

For a closed, thin cylindrical shell away from end effects, the membrane-equilibrium idealization gives hoop tension `N_hoop = p R` and axial tension `N_axial = p R / 2`. These are force-balance relations, not a command to apply isotropic strain to any network and call it turgor loading. A pressure-consistent patch calculation should solve for the biaxial state that meets the target tensions within the declared shell assumptions. A flat patch cannot experience normal inflation merely by changing a pressure label.

### 4.4 Geometry and topological truth

Keep separate: persistent molecular IDs, current connected components, physical bond topology, any computational neighbor graph, image segmentation, and display geometry. Two rendered glycan lines crossing do not establish a chemical crosslink. A disconnected fragment is not automatically deleted from the physical state; prescribe its handling and its mechanical/visual accounting.

For sheared cells, use a cell matrix, origin, image offsets, and a tested periodic-image algorithm. Cartesian-coordinate minima and maxima are not simulation-cell bounds. Fractional-coordinate rounding alone is not a universal nearest-image algorithm for arbitrary skew cells; either restrict and test the supported tilt domain or perform a validated nearest-lattice-image search.

## 5. Work packages and gates

### WP0 — Recover the project and establish trustworthy execution

**Inputs:** source archive or authorized live checkout, existing local instructions, this packet.

**Actions:**
- Inspect the working directory, Git status/remotes/history, current instructions, available data, and existing jobs before any edit.
- Preserve the archive and source hash. Prefer the authorized upstream checkout if available. If starting from ZIP, record an archive import; do not invent missing history.
- Verify the actual Python interpreter and LAMMPS shared-library instantiation, required styles/packages, MPI mode, GPU allocation if any, free disk, and small-file behavior.
- Confirm access only to user-authorized repository, scheduler, storage, and model artifacts. Check authentication without printing secrets; an installed client is not authenticated access.
- Create the root ledger, evidence directory, task state, issues list, and role ownership. Set the local commit identity after confirming the intended repository.
- Run the untouched baseline suite and capture command, environment, exit status, and logs.

**Outputs:** `docs/environment.md`, `docs/provenance.md`, baseline logs, `handoff.md`, updated task statuses.

**Gate G0:** source preserved; target environment status known; no ambiguous destructive changes. LAMMPS-dependent work stays blocked until an actual smoke run passes. Independent parsing, tests, and documentation may continue.

### WP1 — Repair and validate the inherited mechanics platform

**Actions:**
- Reproduce each issue in `SOURCE_AUDIT.md` with a failing test before fixing it.
- Fix box parsing, multi-filter logic, output scheduling, outdated call signatures, distribution compatibility, coordinate precision, and portable path handling.
- Replace expanded million-entry distribution lists with explicit normalized discrete distributions while testing sampling statistics and documenting changed random streams.
- Use one seed namespace for network geometry, material disorder, intervention, stochastic event draws, and training; derive independent streams instead of accidental reuse.
- Record achieved density, realized length/orientation distributions, connectivity, and crosslink fraction. Do not equate requested and realized quantities.
- Add small analytical force/energy/virial tests; compare the independent oracle against LAMMPS.
- Validate elastic differences on smooth fixed-topology branches at several perturbation sizes. Use central differences for smooth benchmarks; report one-sided tangents when irreversibility/branch changes prohibit a central derivative.
- Stop overwriting shared `log.lammps` and image names; use isolated run directories. Close solver instances on success and failure.
- Make aggregation non-destructive, idempotent, and grouped by network. Repair invalid interpolation of concatenated unsorted ensemble samples.

**Outputs:** compatible repaired baseline, unit report, physics fixtures, convergence report, migration notes.

**Gate G1:** analytical/independent checks pass; core parameter definitions are reviewed or explicitly isolated as provisional. No large data sweep before this gate.

### WP2 — Implement controlled loading and irreversible fracture

**Actions:**
- Generalize controls to isotropic, axial, hoop, unequal biaxial, shear, cyclic/unloading, and localized prescribed weakening/removal.
- Implement deterministic strain/tension/energy-threshold rupture as a clearly labeled phenomenological reference law, not a verified molecular mechanism.
- Add quenched heterogeneous thresholds and, if scientifically justified, a separate stochastic event law. Distinguish randomness across networks from conditional stochasticity within one network.
- For the quasi-static backend use: apply control, relax the current topology, assess rupture/intervention, record event, change connectivity and dependent angles, relax again, repeat until the step is stable or explicitly fails.
- Include adaptive load-step reduction or event localization near singular bond limits and cascades. A trial that crosses a nonlinear pole must be rejected before it produces a training label.
- Implement local weakening through genuinely local effective parameters. LAMMPS bond coefficients are assigned by bond type; changing one type coefficient must not accidentally weaken every bond of that type. Use a verified subtype/grouped assignment or another tested per-bond representation, retain chemical type separately, and export effective parameters at each state.
- Implement controlled cascades with bounded event/iteration budgets. Detect duplicate events and zero-progress loops.
- Preserve all atom IDs. Maintain persistent edge IDs and a separate component map. Handle removal of angles that depend on deleted glycan bonds.
- Compute and record energy released by deletion, external work where defined, and relaxation loss. Do not enforce conservation across artificial bond deletion without an energy-accounting model.
- Add a true dynamics adapter only under the physical-time contract above. LAMMPS `fix bond/break` is not invoked during minimization [S08]; merely configuring it does not implement quasi-static rupture.

**Failure definitions:** report first bond rupture, load-bearing connectivity loss, load/stiffness reduction, and instability separately. Select a primary failure endpoint before final evaluation. Connectivity by itself is not proof of rigidity; a minimizer error is not proof of biological failure.

**Outputs:** loading and event engines, rupture fixtures, intervention configs, event-sensitivity report.

**Gate G2:** end-to-end loading with genuine recorded topology changes passes conservation/accounting, irreversibility, restart, and timestep/load-step sensitivity tests.

### WP3 — Build the learning-ready trajectory pipeline

**Actions:**
- Adopt the state/action/event schema in `DATA_AND_MODEL_CONTRACTS.md`.
- Export every accepted loading state and every rupture subevent, rather than only the existing sparse 0.1-strain snapshots.
- Align nodes and bonds by persistent IDs, not dump row order or local-row index [S09–S10].
- Include atom forces, bond lengths/tensions/energies, angle definitions, cell matrices, full controls, accepted/rejected status, and convergence diagnostics.
- Define consistent local-stress coarse graining. Raw per-atom virials are not already spatially normalized stresses [S11]. Check that aggregated local quantities reproduce global quantities under the same convention.
- Write immutable raw outputs and atomically completed, versioned trajectory shards. Index by explicit run/network IDs rather than filename regex.
- Create grouped splits, fit normalizers using training data only, and make a leakage test fail for any shared parent network across partitions.
- Create two-event, boundary-crossing, irregular-step, and stochastic-restart fixtures.

**Outputs:** schema, exporter, validator, dataset loader, manifest, split report, visual fixture.

**Gate G3:** round trips preserve state, topology, control, units, and event identity. Exporter statistics match the source solver on fixtures.

### WP4 — Design and execute the simulation study

**Actions:**
- Run a pilot before estimating a full campaign. Suggested first pilot: 12 feasible parameter configurations × 2 independent networks × 3 loading paths × 2 intervention/fracture conditions = 144 trajectories. This is a planning example, not a minimum justified sample size or an authorized job submission.
- Start with small smoke graphs, for example `Ny=32` and maximum strand length 12. A pilot might use `Ny=64`, maximum length 30. Larger intended-size and OOD tests must respect `max_strand_length < Ny` until the generator is deliberately generalized.
- A size-generalization experiment must hold the strand distribution fixed; silently truncating long strands in small graphs confounds size with architecture. Evaluate long-strand OOD separately.
- Use feasible stratified/space-filling parameter designs rather than an enormous full Cartesian grid. Density and crosslink ratio are constrained by network-generation rules, so measure and report their joint attainable region.
- Include intact controls, diffuse weakening, localized weakening, random defects, and pressure-consistent loading states. Keep prescribed deletion distinct from spontaneously predicted failure.
- Reserve architecture, loading-path, and size-OOD cohorts. Do not use test outcomes to guide active learning or parameter selection.
- Add repeated fracture realizations for fixed observable networks when measuring conditional uncertainty.
- Use pilot runtime, failure rates, storage, and independent-network variance to choose the approved production campaign. Stop or shrink the campaign when infrastructure budgets are reached, not when an expected result fails to appear.
- Reproduce relevant historical tension/modulus trends using reviewed configs; document disagreements, including changes caused by old unit or distribution fixes.

**Outputs:** study design, accepted and rejected-run manifest, timing/cost report, frozen development and test cohorts.

**Gate G4:** reproducible datasets with nonleaking partitions and a documented adequacy argument. Failed solver trajectories are retained as diagnostics, not converted into physical-failure labels.

### WP5 — Establish the mechanics-only and learned baselines

**Baselines:**
- Fine LAMMPS reference, with explicit numerical tolerance.
- Reduced-cost mechanics: fewer relaxation iterations or coarser representation, selected on validation data.
- Affine/no-nonaffine-update predictor; simple observable regression where appropriate.
- Data-driven message-passing graph simulator using matched inputs [S12–S13].
- Physics-aware mechanics predictor with fixed topology.
- Topology classifier coupled only loosely to mechanics.
- Simple mechanistic rupture rule available to the predictor under the same information restrictions.

**Actions:** implement common adapters, fair data access and tuning budgets, shared metrics, and measured end-to-end runtime. First overfit a tiny training set to verify training mechanics; then demonstrate an unseen-network rollout. Saved random weights and a decreasing training loss do not pass this gate.

**Outputs:** baseline checkpoints/configs, one-step and closed-loop evaluations, compute accounting.

**Gate G5:** each baseline is actually trained/evaluated or marked failed with a reason. The reference is not misrepresented as a weaker competitor on its own labels.

### WP6 — Build and train the full hybrid graph world model

**Recommended core:** graph encoder + mechanics proposal/learned relaxation update + physical validation/projection + irreversible event decoder + optional history/latent state. Explicitly represent angular interactions, boundary conditions, and applied loading.

**Actions:**
- Start with continuous next-state prediction on intact graphs; move to teacher-topology damage data; finally train/evaluate coupled predicted topology.
- Condition on current geometry, bond type/rest parameters/alive state, forces or mechanical features available at inference, cell matrix, material metadata, and controls.
- Predict nonaffine displacements relative to known affine loading. Use equivariant vector operations or explicit augmentation and invariance tests; rotate controls and tensors along with coordinates.
- Use known energy/force information to construct a fixed-budget corrector or learned relaxation operator. Report the runtime and error before and after correction. A full reference solve hidden inside every prediction is not a fast learned simulator.
- Decode event hazards or persistent thresholds through a declared stochastic model. Use survival likelihoods and repeated conditional experiments to establish meaningful probabilities.
- Feed predicted graph changes into subsequent mechanics. Delete dependent angles, rebuild physical message masks, and update components without inventing new chemical bonds.
- Restrict global computational communication edges so they cannot be confused with force-bearing bonds. Test whether limited message-passing range misses long-range force chains; add a hierarchical/coarse path if justified by results.
- If adding a residual learned energy, specify exactly what unresolved physics it represents. Relearning an already known teacher energy is not automatically a new physical contribution.
- Save optimizer, scheduler, RNG, split and config hashes, model version, and exact resume state. Validate interrupted-run recovery.

**Losses:** scaled displacement/nonaffine error, tension/stress and energy consistency, event/survival likelihood, multi-step rollout error, and explicit validity penalties. Select weights on validation data. Do not add a generic “energy must always decrease” penalty across loading steps; externally driven systems can gain energy.

**Outputs:** full-model checkpoints, training curves, inference adapter, uncertainty samples, ablation-ready configurations.

**Gate G6:** held-out autoregressive rollouts update their own topology, return calibrated or honestly uncalibrated uncertainty, and pass physical validity checks. Quantitative usefulness must be measured, not assumed.

### WP7 — Conduct the full evaluation and generalization study

**Actions:**
- Freeze the primary metrics, split hash, training protocol, and decision thresholds before final testing.
- Evaluate horizons in loading intervals and, for calibrated dynamics only, physical time. Include horizons longer than training windows.
- Measure position/bond-length error, nonaffine displacement, membrane tension error, force-chain/hotspot localization, event precision/recall and PR-AUC, first-event error, failure-load distribution, and rollout validity.
- Report no-break accuracy only as a secondary diagnostic; it is a misleading primary score for rare rupture.
- Compare stochastic rollouts as distributions when exact event correspondence is not meaningful. Use proper probability scores and empirical interval coverage, not just point RMSE.
- Evaluate architecture, load, size, defect, and combined OOD separately. Clearly label retraining versus zero-shot transfer.
- Use independent-network paired/bootstrap comparisons; cluster repeated trajectories from the same graph. Use multiple training seeds, with at least three as a development target and five for final estimates when the approved budget permits.
- Run ablations: no physical correction, no angles, fixed topology, no history/stochasticity, uncoupled events, no multistep training, and no hierarchy where implemented.
- Add a generic disordered spring/fracture benchmark with the same interface. Do not claim cross-domain generality from an identical PG generator with renamed parameters.
- Inspect worst-case rollouts and numerical instabilities. Report distributions and effect sizes, not just a best-case movie.

**Outputs:** frozen evaluation report, raw metrics, confidence intervals, ablations, generalization figures, error taxonomy.

**Gate G7:** another script reproduces the quantitative tables from immutable predictions; negative/null results are retained.

### WP8 — Execute the experimental program in parallel

Start this in WP0 rather than after the model is trained. Details are in `EXPERIMENTAL_PLAN.md`.

**Actions:** obtain lab-approved training, sample/calibration records, existing dataset formats, and new data collection. Establish the observation operator linking network mechanics to AFM indentation or observable morphology. For AFM, connect the network's effective in-plane mechanics to a validated curved-shell/contact calculation; do not fit an arbitrary spring constant directly to a cell force curve and call that microstructural validation.

Use prior data for development and newly acquired independent batches for validation when feasible. Keep culture/day/cell/curve IDs and calibration uncertainty. Report identifiable parameter combinations and avoid claiming a unique nanoscale network from a few aggregate measurements.

**Outputs:** approved acquisition plan, actual acquisition ledger, raw/processed measurements, observation-model checks, calibrated and held-out prediction reports.

**Gate G8:** real new experimental evidence and held-out quantitative comparison are present, or the full proposal remains explicitly blocked on experiments. Simulated AFM fixtures can test software but cannot satisfy this gate.

### WP9 — Deliver MechWorld Explorer and accessible inference

Implement the full specification in `VISUALIZATION_SPEC.md`. Begin the exact-geometry reader after G3; build prediction comparison after G5/G6.

**Required:** native 2D-in-3D view, physically labeled cylindrical embedding, native 3D shell-results support, synchronized LAMMPS/model comparison, loading/event playback, uncertainty, node/bond inspection, counterfactual branching, exports, and local inference.

Use a browser-first viewer with bundled assets and a Python model service/CLI. Large reference simulations run as explicitly authorized asynchronous jobs, not an unbounded browser request. A public prerecorded demonstration and local private-data workflow are separate deployment modes. The live model must be available through a tested checkpoint loader and documented interface, not only screenshots.

**Gate G9:** scientific identity/units/topology tests, performance measurements, and a scientist usability check pass; the interface never disguises unvalidated embeddings as simulated 3D mechanics.

### WP10 — Write and package the research outputs

**Actions:**
- Generate every quantitative figure from an experiment/run manifest. Export provenance beside images.
- Assemble methods, related-work comparison, physical assumptions, data splits, baseline tuning budgets, experiments, uncertainty, limitations, and reproducibility instructions.
- Link each numerical claim to its exact source table and run IDs. Mark any prose without evidence as a draft claim.
- Package a minimal public dataset subset if permitted, full dataset access procedure, trained weights, configs, model/data cards, release notes, known limitations, and versioned citation metadata.
- Preserve upstream licenses/acknowledgments. Resolve unknown code/data reuse rights and manuscript authorship with Mohammad and the lab before publication. Do not automatically submit, publish, pay, or disclose private data.
- Reproduce the release in a clean environment, load the published-form checkpoint on CPU, execute a demo rollout, and inspect the browser UI.

**Outputs:** manuscript draft, reproducible figure bundle, software/model/data release candidate, documentation, demo package.

**Gate G10:** traceable research release candidate approved for scientific and provenance review. Conference acceptance is outside the definition of project implementation completion.

### WP11 — Final independent audit and closure

The reviewer checks every proposal row, tests a clean install, reproduces selected figures and model outputs, verifies dataset separation, and checks that public artifacts contain no private inputs or fabricated claims. Mohammad reviews the scientific conclusions and release permissions.

Produce `reports/completion_report.md` separating software, simulation study, experimental study, scientific findings, and release approval. A remaining human/data dependency is a named blocker with an exact next action, not an excuse to abandon independent work and not a reason to declare total completion.

**Gate G11:** all mandatory work packages have evidence-backed acceptance, or the ledger reports exactly which remain incomplete. Do not loop forever trying to force H1–H5 to be true.

## 6. Repository architecture

Preserve the existing `src/` entry points initially. Introduce an installable package beside them, then migrate through tested compatibility wrappers.

```text
README.md                         # current public-facing status and tasks; update with every handoff
AGENTS.md
handoff.md
TASKS.json
pyproject.toml
src/                              # inherited commands, retained during migration
src/pgworld/
  config/                         # typed config and physics profiles
  geometry/                       # cell matrices, periodic bonds, mappings
  physics/                        # energy, forces, angles, stress conventions
  simulation/                     # LAMMPS adapter, loads, rupture, restarts
  data/                           # schema, exporters, manifests, splits
  models/                         # baselines, hybrid transition, uncertainty
  training/                       # trainer, loss, checkpoint, curriculum
  evaluation/                     # rollout, OOD, metrics, bootstrap
  experiments/                    # AFM/microscopy import and observation operator
  visualization/                  # scientific scene export
  api/                            # bounded local inference API
  cli.py
viewer/                           # browser application
configs/{smoke,pilot,study,models,experiments}/
tests/{unit,physics,integration,data,models,experiments,visualization,release}/
tools/
docs/{decisions,sessions,subagents}/
reports/
artifacts/                        # ignored/versioned outside ordinary Git as appropriate
data/{raw,processed,manifests}/    # raw protected; no private data in Git
paper/
```

`handoff.md` is the detailed current snapshot. `README.md` is its concise scientist/developer-facing status and remaining-task view and must be updated with every handoff. `docs/sessions/` contains append-only historical summaries. `TASKS.json` is the task state, not a replacement for evidence. Only the integrator changes the root README, handoff, task state, or package-wide interface integrations.

## 7. Milestone sequencing and resource plan

**Critical path:** G0 → G1 → G2/G3 → G4 → G5 → G6 → G7 → G10 → G11. G8 starts in parallel at G0 and must finish before claiming the complete experimentally grounded proposal. G9 starts at G3 and converges with the release.

**First execution session:** inspect source/access; capture baseline; create target ledger; delegate non-overlapping audits; reproduce the parser/filter failures; commit the first tested repair. Do not spend the first session rewriting the repository or installing every ML/UI dependency.

**First integrated milestone:** a genuinely simulated, small PG trajectory with recorded rupture, exported IDs/events, an exact-geometry viewer, and no claim of trained-model accuracy yet.

**Second integrated milestone:** trained baseline and hybrid model on pilot data, synchronized closed-loop comparison, measured error/runtime, and experimental data ingestion demonstrated on actual lab files.

**Final milestone:** full held-out research evaluation, new experimental validation, model/scientist tools, manuscript, and clean-environment reproduction.

Planning estimates should be revised from measurements. A full computational-plus-experimental study is a multi-month effort at part-time undergraduate availability, not an overnight coding task. Agent parallelism accelerates engineering, but does not remove experimental scheduling, convergence studies, scientific decisions, or training time. Do not invent a conference deadline or guarantee publication.

Start with local, bounded smoke jobs. Recommended default policy until Mohammad approves more: no paid cloud resources, no public deployment, one small local simulator job at a time, and a per-task runtime cap chosen after inspecting the machine. GPU work is permitted only on a verified authorized allocation. Estimate the full campaign from pilot wall time, allocated cores, measured failure rate, graph sizes, storage per accepted state, and output retention; include re-runs and hyperparameter trials.

For stalled external access, continue independent tests, schema, literature, and UI fixtures. Record the blocker once with owner and requested artifact; do not repeatedly retry failed authentication or submit duplicate cluster jobs.

## 8. Research decisions requiring Mohammad/lab input

Track these as tasks, with a recommendation and evidence rather than an open-ended request:

- Reviewed PG parameters and the original coefficient-fit sources.
- Approved experimental specimen/conditions, training, and access to existing/new datasets.
- Primary failure definition and whether rupture laws are phenomenological or experimentally constrained.
- Whether physical-time/rate-dependent claims belong in the main study.
- Observation operator for the selected AFM/microscopy measurement geometry.
- Compute/storage quota and long-job authorization.
- Upstream code/data provenance, release permissions, manuscript authorship, and publication target.

The agent may prototype clearly marked alternatives while waiting. It must not silently settle a physical parameter, invent a measurement, or convert a provisional assumption into an experimentally established claim.
