# P02-03 fracture cascade implementation report

## Scope and provenance

- Task: P02-03, quasi-static fracture cascade and topology mutation.
- Base: `0ee619434daa414e76d70aacb914e6393c6652e7`.
- Branch/worktree: `research/p02-03-fracture-cascade` at
  `C:\Users\mzora\MechWorld-wt-p02-03`.
- Runtime: CPython 3.11.9 from
  `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`; real solver evidence
  used the serial LAMMPS 2Sep2026 Python module at
  `C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python`.
- Resource bounds: one pytest/LAMMPS or wheel-build process at a time;
  `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=2`.
- No private/lab data, inherited provenance, root ledger, shared damage law,
  shared control contract, profile, or canonical storage schema was changed.

## Delivered contract

P02-03 adds an immutable opaque-ID topology registry with explicit signed
source image offsets and strict hash-bound replay. It implements a
backend-separated transaction that audits the solver, applies one supported
quasi-static control, minimizes, stages only the rank-zero accepted material
rupture, deletes its exact dependent angles and physical bond, captures the
same-position unrelaxed phase, re-minimizes at unchanged control/cell, and
commits only after convergence and topology/mechanics audits. Failed mutations
restore and compare the complete last accepted state; incomplete restoration
is explicit and cannot be published as rollback success.

Observations and results contain persistent identities, full 2D cell and PBC,
tag-ordered copied positions/forces, authoritative source and decoded current
image offsets, topology/damage masks, raw phase energies, total/reference/
incremental 2D tension, convergence diagnostics, P02-01 control provenance,
and replay-bound boundary-condition provenance. Privileged law, frozen
ThresholdField, and registry records support audit without exposing hidden
thresholds, seeds, realization identities, accepted-event IDs, or future
states through the predictor-visible projection.

The real fixture starts from an actually minimized fixed-cell reference. Its
periodic crossing edge has explicit `n_ij=(1,0)`. The constrained control
stretches two 1.03 nm bonds to 1.236 nm, crosses a deterministic 1.1 extension
threshold, removes exactly the selected bond and angle, records the one-bond
unrelaxed energy at unchanged coordinates, and then measures the free middle
node moving about 0.206 nm while the surviving bond returns to about 1.03 nm.
This is implementation evidence, not biological validation.

## Exact verification

All commands ran from the worktree root. The final focused commands used the
system CPython 3.11.9 at
`C:\Users\mzora\AppData\Local\Programs\Python\Python311\python.exe` with
`PYTHONPATH=<worktree>\src;<LAMMPS Python path>`. The full, wheel, and compile
commands used the repository `.venv` interpreter. All used the thread caps
above.

| Check | Exact command (interpreter prefix abbreviated only in this table) | Result | Evidence |
|---|---|---|---|
| Topology contract | `python -B -m pytest tests/unit/test_fracture_topology.py -q --junitxml=evidence/subagents/P02-03/final-topology.xml` | exit 0; 18 passed | `final-topology.xml` |
| Fake/replay cascade | `python -B -m pytest tests/integration/test_fracture_cascade.py -q -k "not lammps" --junitxml=evidence/subagents/P02-03/final-focused-fake-reference.xml` | exit 0; 39 passed, 3 deselected | `final-focused-fake-reference.xml` |
| Real serial LAMMPS | `python -B -m pytest tests/integration/test_fracture_cascade.py -q -k "lammps" --junitxml=evidence/subagents/P02-03/final-focused-real-reference.xml` | exit 0; 3 passed, 39 deselected | `final-focused-real-reference.xml` |
| Full suite, dependency-complete environment | `...\.venv\Scripts\python.exe -B -m pytest -q --junitxml=evidence/subagents/P02-03/full-suite-venv.xml` | exit 0; 331 passed, 14 warnings; 365.63 s | `full-suite-venv.xml` |
| Isolated wheel retry | `$env:PGWORLD_WHEEL_EVIDENCE='<worktree>\evidence\subagents\P02-03\wheel-report-retry.json'; ...\.venv\Scripts\python.exe -B -m pytest tests/release/test_wheel_install.py -q --junitxml=evidence/subagents/P02-03/wheel-install-retry.xml` | exit 0; 1 passed; 306.09 s | `wheel-install-retry.xml`, `wheel-report-retry.json` |
| Compilation | `...\.venv\Scripts\python.exe -B -m py_compile src/pgworld/simulation/fracture.py src/pgworld/simulation/topology.py src/pgworld/simulation/__init__.py tests/integration/test_fracture_cascade.py tests/unit/test_fracture_topology.py tests/release/test_wheel_install.py` | exit 0; no output | console |

The wheel report records strict allowlist success, no private/generated payload,
checkout paths absent from installed `sys.path`, clean `pip check`, hash-tamper
rejection, installed `pgworld.simulation.fracture` and `topology` imports, and
wheel SHA-256
`617d4d540a73ab4cdc4902f4e1a74c1a352be6481c3b8b997739fbd75bd844fd`.

## Preserved red and failed-correction evidence

The first exact missing-module regressions are `red.xml` and `red-exact.xml`.
The expanded source and replay failures are retained rather than overwritten,
including topology mutability/dependency/replay, partial rollback, observation
binding, control/cell forgery, hidden threshold provenance, zero-event result,
generator consumption, no-snapshot control, and fixed-reference tension
mixing. Their corresponding final focused suites above are green.

Several historical filenames contain `green` or `pass` even though their
JUnit contents are failures; they are not claimed as passing evidence:

- `topology-first-green.xml`: collection failed with `IndentationError`.
- `adversarial-replay-green.xml` and
  `adversarial-replay-actual-green.xml`: one failure each.
- `real-boundary-energy-pass.xml`: immutable `mappingproxy` serialization
  failure.
- `full-control-result-pass.xml`: one rejection-message assertion failure.
- `final-focused-fake.xml`: one failure after introducing the fixed-reference
  tension invariant.

The bare system-Python full attempt, `full-suite.xml`, exited 1 with ten
collection errors because that interpreter lacks pandas and matplotlib. The
same unchanged suite passed in the repository dependency-complete environment.
The first isolated wheel artifact, `wheel-install.xml`, exited 1 because the
fresh-environment dependency installation exceeded its fixed 300-second
subprocess limit. The one authorized diagnosed-transient retry completed the
same install in 191.39 seconds and passed; no additional retry was made.

## Final hashes before commit

| Artifact | SHA-256 |
|---|---|
| `src/pgworld/simulation/fracture.py` | `948b789f412ded05ff9ab155528dbc8d6c82a3bf58fe34e1d776eddd542c1f5a` |
| `src/pgworld/simulation/topology.py` | `62c6192e389863dc83dc231048a99068f4dc5ef564c1fd3de3a64bf865a82aee` |
| `tests/integration/test_fracture_cascade.py` | `fe76d5bc0b0800ab38f5a73ce817633a2e42dfaf8ef5afe6be2bf1a401166c9b` |
| `tests/unit/test_fracture_topology.py` | `d0165e05b2c2d7d22468399f7c2bf03af03697ade190c8a0627b7549b6135848` |
| `final-topology.xml` | `9734ed69d7f3469956eaaa81998f7b3ed1aebddd33b74cc172c56aa7a5c010ae` |
| `final-focused-fake-reference.xml` | `e0585c45b7151303fb9df1f956385be9acf52fac2ba01c6321ebd90db33118a0` |
| `final-focused-real-reference.xml` | `36f0f0f1bef5557c3ae6bc2c3ab4b631f33e7e72bf9216f3a8ca704ca972ce11` |
| `full-suite-venv.xml` | `a9b2bba36a2e10a480a537b437598aef8dfa5317f9cc8ff367192b17e958905e` |
| `wheel-install-retry.xml` | `bc425ee5142f5e7d3d4ec5552644d7fbbde9158ab54a64b6a8647168ccd36a5b` |
| `wheel-report-retry.json` | `a9fe3bc43e55df6635c58f3743a80fe6af719f6b1da5380eeede17418758073f` |

## Explicit limitations and next owners

- Real solver evidence is one serial, orthogonal, sequential-tag
  `tiny_harmonic_fixture` with fixture-only degree-one endpoint constraints.
  It is not a production/general PG adapter and does not implement the
  nonlinear peptide law.
- Endpoint reactions are unavailable; reported forces and convergence
  residuals are post-constraint/free-DOF quantities, not unconstrained global
  force balance.
- Execution is restricted to identity-axis diagonal deformation-gradient
  controls and the dimensionless extension-ratio criterion. Pressure, shear,
  rotated/general mappings, tension, and energy rupture criteria fail closed.
- `run_step` owns and closes one backend for one controlled step. There is no
  persistent multi-step trajectory runner or restart continuation yet.
- P02-04 owns event localization and derived deletion/work/relaxation energy
  accounting. P02-03 raw phase energies are evidence only.
- P02-06 owns restart portability and sensitivity; P02-03 restart handling is
  transaction-local rollback only.
- P03 owns canonical storage, dataset splitting, encoders, and enforcement of
  model-visible fields. No G2 data gate is claimed here.
- No physical-time, rate, fatigue, rigidity, or mechanical-instability claim;
  no biological parameter certification, experimental validation, cluster
  production, public release, or manuscript approval.
