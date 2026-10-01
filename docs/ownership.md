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

Exact branch, worktree, base revision, commands, runtime limit, and return-report path are recorded when each assignment is launched. The main checkout is the integration worktree. Subagent reports are evidence inputs, not automatic task acceptance.
