# P01-08 integration verification — 2026-10-01

Integrated source commit: `9429b4ca530ef3307bd0dd693d05e6c32f8ececd`.

- Path/identity review: the returned commit changed only assigned run-manager, compute-config, focused-test, evidence, and report paths. Author and committer are solely Mohammad Zoraiz `<zoraizmohammad@gmail.com>`.
- Red evidence: the isolated pre-implementation test collection exited 1 with the expected `ModuleNotFoundError: No module named 'pgworld'`; see `evidence/subagents/P01-08/red.txt`.
- Targeted integration: `.venv\Scripts\python.exe -m pytest tests/integration/test_run_isolation.py -q --junitxml=evidence/integration/P01-08/targeted.xml`; exit 0; 10 passed in 0.97s.
- Full integration: `.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/integration/P01-08/full_suite.xml`; exit 0; 50 passed in 7.73s.
- Compile: `.venv\Scripts\python.exe -m compileall -q src\pgworld`; exit 0.
- Sanitization: `rg -n -i "jrrm|/u/home|c:\\users|qsub|sbatch|@" configs/compute -g '*.json'`; no matches (ripgrep no-match exit normalized to a passing audit result).
- Actual adapter smoke: the installed LAMMPS Python library ran a one-atom `run 0` through `RunManager`; version 20260902, exit 0, accepted status, solver close recorded successful. The immutable run record, expanded config, provenance, solver log, and screen are under `actual_runs/serial-lammps-run0/`.

SHA-256 after integration:

```text
4c4a64165eb168a9c9451214989fd0d8faf1d3ef4c4b5429973a5cc6ee90b119  src/pgworld/simulation/run_manager.py
afa0018ac399cf0d03f565102a01b6f1fae8d6ddb6b86b84993eb48ae1573d9b  tests/integration/test_run_isolation.py
372fd48a3b63ae5da335e82f4e05c5e1020daf82def8d0d76fd0c91bd53c2457  configs/compute/local_smoke.json
af72bd469dcb8c048d951e08c4091e872b4ed445c07f890e84e3ec15d643e438  configs/compute/scheduler_disabled.json
```

The fake-solver tests validate lifecycle and isolation behavior; the real smoke validates local LAMMPS construction, scoped log/screen arguments, execution, status, and close. Inherited runners are not migrated, restart resume/equivalence is absent, walltime is cooperative, memory is declarative, and cross-process/remote production scheduling remains unimplemented and unauthorized.
