# Task and edit ownership

The integrator owns `README.md`, `AGENTS.md`, `handoff.md`, `TASKS.json`, shared contracts, root dependency files, integration commits, and gate decisions. Every handoff update includes a matching README status/task refresh. Editing subagents receive dedicated Git branches/worktrees and non-overlapping paths. A worktree separates Git files; it does not authorize shared output directories, production compute, remote publication, or private-data access.

## Initial wave

All initial assignments use base `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Geometry/data | `research/p01-01-periodic-bounds`; `C:/Users/mzora/MechWorld-wt-p01-01` | P01-01: reproduce A01/A02 with regression tests and make the smallest legacy-compatible dump parser repair | `src/import_data_from_dumps.py`, `tests/unit/test_periodic_geometry.py`, `evidence/subagents/P01-01/`, `docs/subagents/P01-01-parser.md` | No ledger/shared-contract edits; parser slice does not claim all periodic-identity work complete |
| Environment/simulation | `research/p00-03-environment`; `C:/Users/mzora/MechWorld-wt-p00-03` | P00-03: create a repeatable doctor and actual LAMMPS smoke integration test | `tools/doctor.py`, `tests/integration/test_lammps_smoke.py`, `evidence/subagents/P00-03/`, `docs/subagents/P00-03-environment.md` | No dependency, ledger, environment-summary, or physics-source edits |
| Physics reviewer | `research/p01-05-physics-audit`; `C:/Users/mzora/MechWorld-wt-p01-05-audit` | P01-05 supporting read-only audit of coefficients, units, and LAMMPS conventions | `docs/subagents/P01-05-physics-audit.md` only; inherited source/specifications are read-only | No source edits and no self-approval of lab-dependent parameter values |

Editing worktrees were verified with `git worktree list --porcelain` before delegation. Native subagents were launched for all three assignments; their branch commits require integrator diff review and rerun before integration.

Integration state: the parser commit was reviewed and integrated as `912c9cc`; its integration rerun passed 3 targeted and 12 total tests. The environment commit was reviewed and integrated as `4faeab1`; its doctor exited 0 and integration rerun passed 2 targeted and 14 total tests. The physics audit was path-reviewed and integrated as `59ecfdc`; it remains evidence supporting a human-reviewed task, not a self-approved parameter decision. Generated untracked bytecode in isolated worktrees was neither committed nor treated as user source.

Exact branch, worktree, base revision, commands, runtime limit, and return-report path are recorded when each assignment is launched. The main checkout is the integration worktree. Subagent reports are evidence inputs, not automatic task acceptance.

## Second wave

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Distribution/data | `research/p01-03-distributions`; `C:/Users/mzora/MechWorld-wt-p01-03` | P01-03: first capture A05 in an exact red regression, then replace expanded legacy arrays with a bounded discrete sampler while preserving and documenting number- versus weight-fraction semantics | `src/assemble_pg_network.py`, `tests/unit/test_distributions.py`, `evidence/subagents/P01-03/`, `docs/subagents/P01-03-distributions.md` | No ledger, README, shared-contract, or unrelated source edits; no task-completion or scientific-validation claim |
| Periodic identities/data | `research/p01-01-periodic-identities`; `C:/Users/mzora/MechWorld-wt-p01-01-identities` | P01-01 remaining slice: reject unsupported general-triclinic dumps explicitly and verify repeated/large-offset wrapping, image shifts, minimum image, and persistent atom identity | `src/import_data_from_dumps.py`, `src/lammps_PG_objects.py`, `tests/unit/test_periodic_geometry.py`, `evidence/subagents/P01-01-identities/`, `docs/subagents/P01-01-identities.md` | Build on the integrated parser slice; no ledger/README/shared-contract edits and no unrelated geometry redesign |
| Run isolation/simulation | `research/p01-08-run-isolation`; `C:/Users/mzora/MechWorld-wt-p01-08` | P01-08: implement typed local run configuration/manager, unique directories, failure-safe solver lifecycle, and bounded concurrency/isolation tests | `src/pgworld/simulation/run_manager.py`, `configs/compute/`, `tests/integration/test_run_isolation.py`, `evidence/subagents/P01-08/`, `docs/subagents/P01-08-run-isolation.md` | No production jobs, scheduler submission, inherited account paths, ledger/README/shared-contract/dependency edits, or unrelated runner refactor |
| Related work/research | `research/p10-01-related-work`; `C:/Users/mzora/MechWorld-wt-p10-01` | P10-01: current primary-source search and matrix across learned simulators, fracture/damage/topology, stochastic hybrid models, and PG mechanics; constrain contribution claims to evidence | `docs/related_work.md`, `paper/references.bib`, `tools/check_references.py`, `tests/unit/test_references.py`, `evidence/subagents/P10-01/`, `docs/subagents/P10-01-related-work.md` | No manuscript claims beyond evidence, no fabricated exhaustive/priority claim, no ledger/README/shared-source/dependency edits, and no paywalled/private data access |

The distribution assignment uses base `d4274c14ed0da667a9e67e50138e20363a03457a`; the periodic-identity and run-isolation assignments use base `833273ea7560f4caa1d5e3d715b7c4e460c5a284`; the related-work assignment uses base `a2805a61305aae0e3fc1b8ab0fb737759ca36cd1`. They may run only bounded unit/integration/research work and must return exact commands, limitations, and sole-author commits for integrator review.

Integration state: the P01-03 distribution return was path-reviewed and integrated as `eef253f`. Independent integration verification passed 26 focused tests and 40 total tests, plus `py_compile` and the historical five-case diagnostic. P01-04 is now dependency-eligible but shares `src/lammps_PG_objects.py` with the active P01-01 identity worktree, so no overlapping edit assignment is launched until that ownership clears.

The P01-08 run-isolation return was path-reviewed and integrated as `9429b4c`. Independent integration verification passed 10 focused lifecycle tests and 50 total tests. A real serial LAMMPS one-atom `run 0` then completed through the manager with an accepted lifecycle record and successful close; this is adapter compatibility evidence, not restart, fracture, MPI, scheduler, or production validation.

The remaining P01-01 periodic-identity return was path-reviewed and integrated as `71a5700`. Independent main-tree verification passed 15 focused tests and 62 total tests, targeted compilation, and a 1,000-case exact minimum-image oracle. Its ownership is cleared. Canonical persistent edge/image identity remains deferred to the P03-01 schema rather than inferred from per-frame geometry.

## Third wave

Both assignments use accepted main revision `a79a7aaf337f32dd459a00444babe2851633046d` and have disjoint source/test/evidence paths.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Generator reproducibility/data | `research/p01-04-reproducibility`; `C:/Users/mzora/MechWorld-wt-p01-04` | P01-04: exact red-first named RNG independence, same-seed graph reproducibility, achieved-network metrics, and measured precise-export round trip | `src/assemble_pg_network.py`, `src/lammps_PG_objects.py`, `tests/unit/test_generator_reproducibility.py`, `evidence/subagents/P01-04/`, `docs/subagents/P01-04-reproducibility.md` | No ledger/README/shared-contract/dependency edits, no unapproved parameter selection, no production simulation, and no changes outside owned paths |
| Analysis regression/evaluation | `research/p01-09-analysis`; `C:/Users/mzora/MechWorld-wt-p01-09` | P01-09: exact red-first non-destructive/idempotent grouping, per-network monotonic interpolation, and A16 dimensional conversion/label repair | `src/process_network_ensembles.py`, `src/process_elastic_tensor.py`, `tests/unit/test_analysis_regression.py`, `evidence/subagents/P01-09/`, `docs/subagents/P01-09-analysis.md` | No ledger/README/shared-contract/dependency edits, no material-parameter changes, no deletion/overwrite of raw evidence, and no unrelated plotting redesign |

Each return requires a sole-author Mohammad Zoraiz commit, exact commands and results, limitations, path-boundary proof, and integrator review plus rerun before acceptance.

Integration state: the P01-09 analysis return was path-reviewed and integrated as `6df2a91` and `717f678`. Independent main-tree verification passed 6 focused tests and 68 total tests plus targeted compilation and diff checking. Its ownership is cleared. The lack of persistent cross-cohort replicate IDs remains an explicit later manifest/data-contract limitation rather than being hidden by positional pairing.

Integration state: the P10-01 audit and review expansion were path-reviewed and integrated as `8dfdfef` and `08cf163`. Independent main-tree verification accepted 29 bibliography/citation pairs, passed 11 focused tests and 79 total tests, and spot-checked eight decisive/current DOI records plus the key changing-graph full-text claim. Its ownership is cleared; the search-refresh and independent manuscript-claim review remain later release obligations.

Integration state: the P01-04 reproducibility return was path-reviewed and integrated as `1f90577`. Independent main-tree verification passed 14 focused tests, 45 compatibility tests, and 93 total tests plus targeted compilation and diff checking. Real LAMMPS 20260902 loaded 108/108 atoms from the deterministic fixture, preserved all 324 emitted coordinate tokens with zero measured max/RMS error, and closed. Its ownership is cleared. This is generator/serialization evidence, not approval of physics parameters, rupture behavior, training, or production use.

## Fourth wave

The assignment uses accepted main revision `9280b5d1486496b705e0c178c43da7a488568c67`.

| Assignment | Branch and worktree | Task and objective | Owned paths | Output restriction |
|---|---|---|---|---|
| Structural observables/physics | `research/p01-10-observables`; `C:/Users/mzora/MechWorld-wt-p01-10` | P01-10: exact red-first validation of pore, 2D orientation, and chemical-connectivity observables on known structures, including PBC, rendering resolution/line width, periodic seams, and visually crossing unbonded lines | `src/process_pores.py`, `src/process_orientation.py`, `tests/physics/test_structural_observables.py`, `evidence/subagents/P01-10/`, `docs/subagents/P01-10-observables.md` | No ledger/README/shared-contract/dependency edits, no physics-parameter approval, no production solver work, no invention of chemical crosslinks from rendered crossings, and no edits outside owned paths |

The return requires a sole-author Mohammad Zoraiz commit, exact commands/results/limitations, path-boundary proof, and integrator review plus rerun before acceptance.
