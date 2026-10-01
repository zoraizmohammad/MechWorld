# Verification, Scientific Claims, and Release Gates

## 1. Evidence standard

Every completed task needs an actual command, environment, exit code, compact result, log/artifact path, and source/config/data hashes where relevant. Human tasks instead need an actual dated review/acquisition/approval record. No command execution means `[UNVERIFIED]`, even when code looks correct.

Allowed task states: `TODO`, `IN_PROGRESS`, `BLOCKED_ACCESS`, `BLOCKED_DATA`, `BLOCKED_HUMAN`, `READY_FOR_REVIEW`, `DONE`, `FAILED`, `DEFERRED_EXTENSION`. Only optional extensions may be deferred without blocking full mandatory scope. A failed hypothesis can still yield a completed, honest evaluation task.

The initial packet's evidence was collected in the review container, not this workstation. Target checks were first rerun on 2026-09-30 and are recorded in `../evidence/` and the root handoff; future sessions must still rerun checks affected by new changes. Historical handoff claims are context, not current verification.

## 2. Verification layers

| Layer | Mandatory checks | What it does not prove |
|---|---|---|
| Unit | Parsing, units, RNG, IDs, masks, distributions, boundary transforms | Biological fidelity |
| Analytical physics | Single spring/angle; energy gradient; virial; smooth elastic perturbation | Correct large-network calibration |
| Solver integration | Real LAMMPS run, topology deletion, post-event relaxation, restart | Learned accuracy |
| Dataset | Round-trip, counts, field provenance, nonleaking splits, missing-data handling | Statistical adequacy by itself |
| ML | Gradients, tiny-set fit, unseen-graph rollout, checkpoint resume | Strong OOD performance |
| Research evaluation | Frozen test, fair baselines, uncertainty, independent replicates | Experimental agreement |
| Experiment | Real data/calibration, observation model, held-out batches | Unique molecular mechanism |
| Viewer/service | Field identity, seams/events, bounds/security, actual inference | True 3D simulation from a 2D embedding |
| Release | Clean install, CPU inference, figure reproduction, rights review | Conference acceptance |

## 3. Proposed tolerance policy

Tolerances are provisional engineering starting points and must be adjusted using numerical conditioning, units, and reference convergence before final scientific evaluation. Record any change; never loosen a threshold solely to hide a regression.

- Pure ID, shape, topology, and split tests: exact equality.
- Unit conversion/analytic arithmetic: relative tolerance around `1e-10` in float64 when well conditioned, with a scale-aware absolute floor.
- Finite-difference energy gradient versus analytical force: start around `1e-5` relative away from singularities and zero force, sweeping difference step size.
- Small-system independent oracle versus LAMMPS energy/force: target `1e-6` relative where applicable, with declared absolute force/energy floors.
- Periodic bond distance reconstruction: tied to actual dump precision; high-precision fresh dumps should allow substantially tighter tolerance than inherited two-decimal coordinate files.
- Solver convergence: record normalized residual force and termination criterion, not simply a zero process exit code.
- Elastic perturbation: use a step-size sweep and a stable smooth-response window rather than a universal symmetry threshold at finite prestress.
- ML quality: predeclare dataset-specific thresholds from reference convergence, task utility, and baseline error on validation data. Do not arbitrarily demand 1% error or 10× speedup and then present those targets as findings.
- Browser performance: measure target hardware, scene size, frame time, load time, and memory. Unsupported hardware is a reported limitation.

A numerically converged result is not necessarily physically stable. A symmetrized tangent matrix's positive eigenvalues are not automatically a proof of stability of the full discrete network. Specify boundary conditions, prestress, rigid modes, and the appropriate Hessian/tangent object for any stability claim.

## 4. Required regression scenarios

Rectangular and sheared boxes; orthogonal headers; reordered dump columns/rows; negative tilt; periodic crossings in both directions; invalid IDs; more than one filter; repeated ONCE criteria; zero and tiny load increments; uniform distributions; seeded generation; all/none/one bond broken; removed dependent angles; disconnected components; rupture cascades; near-singular nonlinear bonds; interrupted output; restart; no-failure censoring; event draws invariant to retry bookkeeping; no test leakage; no ghost crosslinks in visualization.

For pore analysis, test resolution and line-width dependence, transparency and grayscale conversion, periodic pore boundaries, and non-crosslinked line crossings. Guard flood fills against periodic all-empty regions and loops. Do not treat a plotting-dependent binary image as an unqualified chemical-pore ground truth.

## 5. Fair research reporting

Compare each method using matched observable information, training data, evaluation horizons, and tuning budgets. Report neural forward time, physical correction time, graph construction, transfers, event handling, and output separately and end-to-end. Include model-loading cold start where relevant to scientist use. Measure rather than infer GPU acceleration.

Primary uncertainty/CI unit is an independent base network or experimental preparation/cell under the declared hierarchical design. Thousands of bonds or neighboring trajectory frames do not create thousands of independent experimental replicates.

Freeze final test IDs before final model selection. After any final-test-driven change, declare it and create a new validation/test protocol instead of quietly calling the same test untouched. Publish failed and rejected run counts. Keep the test data out of active learning.

## 6. Claim ledger

Maintain `reports/claim_ledger.jsonl` with:

```text
claim_id, exact_claim, status, scope, supporting_run_ids,
metric_table, figure_id, code_hash, dataset_split_hash,
uncertainty, limitations, reviewer, review_date
```

Statuses: `HYPOTHESIS`, `SUPPORTED`, `NOT_SUPPORTED`, `INCONCLUSIVE`, `UNVERIFIED`.

Examples of prohibited promotion:
- “The loss decreased” → “The model generalizes.”
- “A spring was manually removed” → “The model predicted molecular failure.”
- “A plane was wrapped” → “We simulated a 3D bacterium.”
- “A checkpoint saved” → “Scientists can reproduce inference.”
- “Pores resemble a published image” → “The model is experimentally calibrated.”
- “Software tests passed” → “The entire proposal is complete.”

## 7. Required final artifacts

**Software:** installable package, pinned/tested dependencies, CLI, tested local API, preserved compatibility, licenses/provenance, automated test and CI configuration.

**Model:** trained inference weights, configuration, normalizers, model card, training/split hashes, evaluation artifacts, load-on-CPU example, limitations/OOD policy.

**Data:** approved dataset/shards or access procedure, manifests/checksums, data card, source/run provenance, split construction, reproducible generation recipes, failed-run accounting.

**Experiment:** new acquisition/QC ledger, actual calibration records, raw/processed access policy, observation model, held-out results, uncertainty and interpretation.

**Visualization:** bundled real reference/prediction example, native/embedded/native-3D source labels, working inspection and counterfactual inference, export, performance and usability evidence.

**Research:** manuscript, references, source-generated figures/tables, ablation/generalization study, claim ledger, limitations, reproducibility instructions.

Public data, public hosting, release tags, submission, paid services, and irreversible remote changes need the appropriate owner permission. Local preparation is not authorization to disclose private lab work.

## 8. Closure report

`reports/completion_report.md` must report separately:

- Engineering completion and actual tested platforms.
- Simulation campaign completion and rejected/incomplete runs.
- Model training/evaluation completion and supported/unsupported hypotheses.
- Experimental completion and outstanding acquisition/analysis.
- Viewer/scientist workflow completion.
- Provenance, authorship, data rights, and release approval.

Include a table of every gate G0–G11, evidence links, remaining blockers, and the exact continuation command or responsible human action. Reproducible negative results are valid research outputs. A missing mandatory deliverable remains incomplete, regardless of demo quality.
