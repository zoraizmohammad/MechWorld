# P10-01 subagent handoff: related work and claim boundary

## Result

Implemented the bounded P10-01 related-work audit on `research/p10-01-related-work` from base
`a2805a61305aae0e3fc1b8ab0fb737759ca36cd1`.

The deliverable, including the integrator-requested follow-up, includes:

- a 29-source, primary-record bibliography;
- a scientist-readable comparison matrix covering peer-review status, geometry, physics,
  state/control, stochasticity, topology-change semantics, data, baselines, artifact availability,
  and project overlap/distinction;
- explicit separation of material-edge deletion from proximity graphs, adaptive remeshing, and
  diffuse phase-field damage;
- a conservative claim boundary that disallows generic GNN/fracture novelty and conditions any
  contribution on PG-specific joint mechanics/event rollouts, controlled topology change, OOD
  tests, calibrated uncertainty, independent experiments, and the scientist-facing workflow;
- a dependency-free BibTeX/citation validator and focused tests; and
- dated source/search and red/green verification evidence.

The initial search identified Karapiperis and Kochmann (2023) as a decisive direct-overlap paper: their
model consumes a changing graph and predicts the next failed beam. Feng and Zhou's 2024--2026
sequence and recent 2025 phase-field, silica-network, earthquake-rupture, and fibrous-network work
further narrow the contribution boundary. No first-of-kind or exhaustive-search claim is made.

Integrator review then added four verified primary precedents: Perera and Agrawal's ACCURATE
transfer-learning fracture framework (2023), their multiscale AMR phase-field GNN (2024), Wang et
al.'s non-GNN StressNet history-to-stress model (2021), and Font-Clos et al.'s non-GNN initial-silica-
structure failure predictor (2022). The matrix now distinguishes staged fine-tuning from zero-shot
OOD generalization, AMR from material topology, supplied fracture history from generated events,
and experimental structure transfer from experimental fracture validation.

## Verification summary

- Red regression: `python -m pytest tests/unit/test_references.py -q` -> exit 2,
  `ModuleNotFoundError: check_references` before implementation.
- Initial validator: 25 entries, 25 cited keys, exit 0; follow-up validator: 29 entries,
  29 cited keys, exit 0.
- Focused tests: initially 10 passed; follow-up adds uncited-entry rejection for 11 passed.
- Full inherited suite in `C:\Users\mzora\MechWorld\.venv`: 50 passed.
- Compile check: exit 0.
- `git diff --check`: exit 0.
- Exact commands, outputs, hashes, and the initial bare-Python environment failure are in
  `evidence/subagents/P10-01/verification.md`.

## Evidence

- `evidence/subagents/P10-01/red-regression.txt`
- `evidence/subagents/P10-01/search-audit.md`
- `evidence/subagents/P10-01/verification.md`
- `evidence/subagents/P10-01/follow-up-red.txt`
- `evidence/subagents/P10-01/follow-up-verification.md`

## Limitations and acceptance dependencies

- The search is targeted and current through 2026-10-01, not exhaustive.
- Some publisher records did not establish full baseline or code/data inventories; those cells are
  marked `unknown` rather than inferred.
- The Hu et al. item is labeled as an arXiv preprint and its administrative overlap note is retained.
- No external paper's code/data was executed or reproduced.
- No scientific validation, trained-model result, experiment, or project-completion claim is made.
- A reviewer-agent spawn was attempted but unavailable because the four-agent capacity was full.
  The integrator has explicitly retained acceptance ownership and will independently review sources,
  claims, bibliography metadata, DOI/URL resolution, and rerun checks before integration.
- The integrator, not this subagent, updates `TASKS.json`, `handoff.md`, and `README.md` together.
