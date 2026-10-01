# P01-08 isolated-run manager return report

## Assignment and boundary

- Base: `833273ea7560f4caa1d5e3d715b7c4e460c5a284` on
  `research/p01-08-run-isolation` in
  `C:\Users\mzora\MechWorld-wt-p01-08`.
- Owned implementation paths: `src/pgworld/simulation/run_manager.py`,
  `configs/compute/`, `tests/integration/test_run_isolation.py`,
  `evidence/subagents/P01-08/`, and this report.
- Root `README.md`, `handoff.md`, `TASKS.json`, shared contracts, dependencies,
  and inherited runner/scheduler files were not edited.

The inherited isotropic and elastic runners write logs, dumps, images, output,
and restarts beside shared inputs and close LAMMPS only after the normal path.
The inherited submission generator embeds a prior email, account home, and
absolute cluster checkout. Those provenance-bearing files remain unchanged.

## Implemented behavior

`RunConfig` and `LocalComputeConfig` are typed, strict standard-library
dataclasses. `RunManager` now provides the migration boundary for local solver
runs:

- A safe run ID reserves exactly one direct child of the configured output root
  with an atomic, non-overwriting directory creation. Existing run roots are
  always refused, including accepted results.
- Every run receives separate `solver/`, `restarts/`, `dumps/`, `images/`,
  `raw/`, and `metadata/` trees. Absolute `-log` and `-screen` solver arguments
  are supplied to the injected factory; no process-global working-directory
  change is used.
- Canonically sorted expanded configuration and provenance JSON are written
  once with exclusive creation. Portable artifact locations are relative in
  config; the output-root path is deliberately not hashed into the scientific
  configuration. The provenance record includes config SHA-256, source commit,
  source tree, dirty flag, Python, and platform.
- The configured concurrency bound is enforced by an in-process bounded
  semaphore. The callback receives a cooperative walltime deadline.
- The solver handle is closed after success, ordinary exceptions, interrupts,
  and serialization failures. Accepted, rejected, incomplete/interrupted,
  factory-error, execution-error, and close-error outcomes are written to an
  atomically replaced lifecycle record before the original failure is reraised.
  Partial failed-run artifacts are retained as diagnostics, not silently
  deleted or relabeled as accepted results.
- The local compute policy disables scheduler submission, MPI, and GPU use. A
  second non-executable scheduler field template keeps submission disabled and
  contains no user/account/email/home path or submit command.

## Regression and verification evidence

The first test run failed during collection because `pgworld` did not exist:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/integration/test_run_isolation.py -q
exit 1: ModuleNotFoundError: No module named 'pgworld'
```

After implementation:

```text
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest tests/integration/test_run_isolation.py -q
exit 0: 10 passed in 0.87s

C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m pytest -q
exit 0: 24 passed in 7.78s

C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m compileall -q src\pgworld
C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -m py_compile tests\integration\test_run_isolation.py
exit 0; no output
```

The tests cover deterministic config/provenance bytes across different host
output roots, live Git/runtime provenance, path traversal rejection,
accepted-result collision refusal,
success metadata, factory failure, execution failure, keyboard interruption,
close failure, handle closure, temporary-file cleanup, sanitized configs, and
two barrier-synchronized concurrent runs with disjoint logs/images/restarts.
Detailed output and context are in `evidence/subagents/P01-08/`.

## Scientific and operational limitations

- The lifecycle tests use an injected fake solver. They validate adapter
  behavior, not LAMMPS mechanics, minimization, fracture, dynamics, or restart
  equivalence. No solver, MPI, GPU, scheduler, remote, or production job was
  launched for this task.
- Inherited entry points have not yet been migrated. They remain capable of
  their historical shared-path behavior when called directly. A future adapter
  must construct LAMMPS with `RunContext.solver_arguments` and direct every
  output to the supplied paths.
- Restart files have a collision-free location, but physics-complete resume
  orchestration and suffix-equivalence tests are later work; this change does
  not claim them.
- Concurrency limiting is per `RunManager` process. Exclusive directory
  reservation is cross-process on the local filesystem, but a future scheduler
  needs its own global resource policy.
- Walltime enforcement is cooperative and memory is recorded rather than
  operating-system-enforced. A callback that does not check the deadline cannot
  be safely preempted in-process. Production compute remains human-gated.
