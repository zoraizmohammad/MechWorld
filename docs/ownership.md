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

The distribution assignment uses base `d4274c14ed0da667a9e67e50138e20363a03457a`; the periodic-identity and run-isolation assignments use base `833273ea7560f4caa1d5e3d715b7c4e460c5a284`. They may run only bounded unit/integration smoke work locally and must return exact red/green commands, limitations, and sole-author commits for integrator review.

Integration state: the P01-03 distribution return was path-reviewed and integrated as `eef253f`. Independent integration verification passed 26 focused tests and 40 total tests, plus `py_compile` and the historical five-case diagnostic. P01-04 is now dependency-eligible but shares `src/lammps_PG_objects.py` with the active P01-01 identity worktree, so no overlapping edit assignment is launched until that ownership clears.
