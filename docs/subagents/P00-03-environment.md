# P00-03 environment verification return report

## Contract and result

- Base: `c0ec8aa7ed99ecf8cb21f0a9bf8223447743fc39`
- Branch/worktree: `research/p00-03-environment` / `C:/Users/mzora/MechWorld-wt-p00-03`
- Owned paths only were changed. Root `README.md`, `handoff.md`, `TASKS.json`, shared environment documentation, dependencies, and inherited physics source were not edited.
- Result: ready for integrator review. The installed Python library instantiated LAMMPS version `20260902`, evaluated the bounded bonded fixture, accepted configuration of `fix bond/break`, and closed normally. The integration tests also exercise a deterministic post-instantiation error path and prove that it exits nonzero and calls `close()`.

## Implementation

`tools/doctor.py` emits sorted JSON to stdout, optionally persists the identical report with `--output`, and exits nonzero when an import, instantiation, required-style, topology/energy, bond-break configuration, or close check fails. It records the Python executable/version, LAMMPS module/version/build information, MPI support, installed packages, accelerator configuration, and availability of:

- `bond harmonic`
- `bond nonlinear`
- `angle harmonic`
- `fix bond/break`

The actual solver fixture contains three atoms, two physical bonds (one harmonic and one nonlinear), and one harmonic angle. It uses the tuples currently exported by `src/simulation_constants_settings.py` without modifying them. A `run 0` yields nonzero per-style energies and the total matches their sum:

| Component | Observed | Analytical fixture value |
|---|---:|---:|
| Harmonic bond | 160.9730000000003 | 160.97299999999987 |
| Nonlinear bond | 0.45665091424033105 | 0.45665091424033305 |
| Harmonic angle | 11.45970733237597 | 11.45970733237597 |
| Total potential | 172.8893582466166 | component sum |

The doctor configures `fix bond/break` for the nonlinear bond type and immediately removes it without running dynamics. Its report sets `invoked_by_dynamics=false`, `rupture_events_observed=null`, and `quasistatic_fracture_validated=false`.

## Exact verification

Working directory for every command: `C:/Users/mzora/MechWorld-wt-p00-03`. Interpreter: `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe`.

1. `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe tools/doctor.py --output evidence/subagents/P00-03/doctor.json`
   - Exit 0; `ok=true`; all four styles available; fixture checks passed; solver closed.
2. `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest tests/integration/test_lammps_smoke.py -q --junitxml=evidence/subagents/P00-03/pytest.xml`
   - Exit 0; 2 passed in 1.65 s; no failures, errors, or skips.
3. `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/subagents/P00-03/pytest_full.xml`
   - Exit 0; 7 passed in 9.44 s; no failures, errors, or skips.
4. `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m py_compile tools/doctor.py tests/integration/test_lammps_smoke.py`
   - Exit 0.
5. `git diff --check`
   - Exit 0.

Exact context, hashes, results, and the one discarded negative-test approach are in `evidence/subagents/P00-03/verification_context.json`. The machine report is `doctor.json`; JUnit artifacts are `pytest.xml` and `pytest_full.xml` in the same directory.

## Failed approach retained as a lesson

Running this interpreter with `-S` did not make the separately registered Windows LAMMPS installation unavailable, so a wrapper that expected doctor exit 1 instead exited 99. The misleading temporary output was removed. The committed negative-path test now shadows `lammps` with a bounded temporary module that reports all required styles missing. It verifies exit 1, actionable structured diagnostics, and a `close()` marker after the instance-level failure.

## Boundaries and integration request

This verifies a serial local capability only. It does not validate minimization, fracture events, the required quasi-static event loop, MPI, GPU execution, physical time, production scale, whole-PG mechanics, or the scientific provenance/units of the inherited coefficients. It must not be cited as evidence for any of those claims.

On integration, the integrator should independently run the doctor and targeted test, then update `TASKS.json`, `handoff.md`, and the root `README.md` together as required by the current handoff policy.
