# Task and edit ownership

The integrator owns `README.md`, `AGENTS.md`, `handoff.md`, `TASKS.json`, shared contracts, root dependency files, integration commits, and gate decisions. Every handoff update includes a matching README status/task refresh. Editing subagents receive dedicated Git branches/worktrees and non-overlapping paths. A worktree separates Git files; it does not authorize shared output directories, production compute, remote publication, or private-data access.

## Initial wave

| Assignment | Task and objective | Owned paths | Output restriction |
|---|---|---|---|
| Geometry/data | P01-01: reproduce A01/A02 with regression tests and make the smallest legacy-compatible dump parser repair | `src/import_data_from_dumps.py`, `tests/unit/test_periodic_geometry.py`, task return report only | No ledger/shared-contract edits; parser slice does not claim all periodic-identity work complete |
| Environment/simulation | P00-03: create a repeatable doctor and actual LAMMPS smoke integration test | `tools/doctor.py`, `tests/integration/test_lammps_smoke.py`, task return report only | No dependency, ledger, or physics-source edits |
| Physics reviewer | P01-05 supporting read-only audit of coefficients, units, and LAMMPS conventions | Read-only inherited source and specifications; return report only | No source edits and no self-approval of lab-dependent parameter values |

Exact branch, worktree, base revision, commands, runtime limit, and return-report path are recorded when each assignment is launched. The main checkout is the integration worktree. Subagent reports are evidence inputs, not automatic task acceptance.
