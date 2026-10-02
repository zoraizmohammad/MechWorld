# P02-04 localization and fracture-accounting implementation report

## Scope and provenance

- Task: P02-04, bounded first-event localization and phase-correct fracture
  accounting.
- Base: `056dd985b0dd27e5419df5f72b63d88fbd6c133f`.
- Branch/worktree: `research/p02-04-localization` at
  `C:\Users\mzora\MechWorld-wt-p02-04`.
- Verified source/tests/decision commit:
  `d73df3dd27375b8866351442dd7d7b8f8534fbcc`.
- Owned edits: `src/pgworld/simulation/fracture.py`,
  `tests/physics/test_fracture_accounting.py`, this report,
  `docs/decisions/fracture_accounting.md`, and
  `evidence/subagents/P02-04/` only.
- Resource boundary: one test/solver process at a time and at most two compute
  threads. No private/lab data, external service, cluster allocation, shared
  schema, physics profile, root ledger, or release gate was modified.

## Delivered contract

P02-04 adds a bounded transaction that verifies a live accepted lower state,
localizes the first crossing on one certified monotone control segment, and
then invokes the exact P02-03 deletion/re-relaxation cascade. Every nonfinal
trial restores and verifies the original lower checkpoint. Nonfinite,
unsupported, nonconverged, exception, and failed-restore paths are typed and
cannot publish events or accounting labels. Only the diagnosed transient
reason `diagnosed_transient_solver_interruption` may retry, once.

The executable domain is intentionally restricted to the exact collinear,
orthogonal, three-node/two-glycan-bond/one-angle harmonic fixture and a
backend-bound monotone axial response on one diagonal P02-01 segment. Peptide,
nonlinear endpoint-only pole certificates, bent chains, skew cells,
nonmonotone backends, pressure/tension control, shear, and rotated/general
cell mappings reject before trial control.

The accounting record embeds five raw phase snapshots and separately records
instantaneous conservative control input, equilibrium stored-energy change,
pre-event relaxation loss, signed same-coordinate deletion energy change,
held-control boundary work, and post-delete relaxation loss. It does not call
the deletion term toughness or dissipation and does not impose a global
energy-decrease claim.

## Preserved red and correction evidence

The evidence directory retains the initial missing-contract collection reds,
intermediate correction failures, and the exact adversarial regressions for:

- trial exceptions and restore failure;
- live-lower mismatch;
- peptide/nonmonotone certificate bypass;
- loading-work/relaxation conflation;
- upper incremental-F and localized-result identity forgery;
- retry/count/status replay forgery;
- adjacent P02-01 step-lineage and stale budget-detail forgery;
- nonlinear certificate substitution after successful execution;
- folded angle-order geometry hidden by reversed bond endpoint storage;
- a localized label wrapped around an incomplete/non-stable cascade;
- ambiguous nonlocalized observable labels;
- blind retries of reproducible nonconvergence;
- initial-reference threshold violation; and
- bent-chain/skew-cell certificate overreach.

Files whose names include `correction` are claimed as passing only when their
JUnit content and the verification table below report exit 0. In particular,
`first-implementation-correction.xml` and
`reviewer-blockers-correction-02.xml` are preserved failures, not green
evidence.

## Verification

All commands ran from the worktree root with
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=2`.
The focused solver commands used CPython 3.11 at
`C:\Users\mzora\AppData\Local\Programs\Python\Python311\python.exe` and
`PYTHONPATH=C:/Users/mzora/MechWorld-wt-p02-04/src;C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/Python`.
Compatibility/full/wheel/compile commands used
`C:\Users\mzora\MechWorld\.venv\Scripts\python.exe`; compatibility and full
also used the solver-enabled `PYTHONPATH` above. Every command exited zero
unless it is explicitly identified as preserved failed evidence.

| Check | Exact command after the environment above | Result | Evidence |
|---|---|---|---|
| Corrected targeted real solver | `python -m pytest tests/physics/test_fracture_accounting.py -k "real_serial_lammps" -q -o junit_family=legacy --junitxml=evidence/subagents/P02-04/real-localization-accounting-pass-02.xml` | 1 passed, 47 deselected; 0.43 s | `real-localization-accounting-pass-02.xml` |
| Final focused contract including real solver | `python -m pytest tests/physics/test_fracture_accounting.py -q -o junit_family=legacy --junitxml=evidence/subagents/P02-04/final-focused-all.xml` | 48 passed; 3.64 s | `final-focused-all.xml` |
| Relevant P02 compatibility | `.venv\Scripts\python.exe -m pytest tests/physics/test_damage_law.py tests/integration/test_fracture_cascade.py tests/unit/test_fracture_topology.py tests/unit/test_legacy_control_flow.py -q --junitxml=evidence/subagents/P02-04/relevant-compatibility-pass-02.xml` | 122 passed; 2.92 s | `relevant-compatibility-pass-02.xml` |
| Full repository suite | `.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/subagents/P02-04/full-suite.xml` | 379 passed, 15 warnings; 176.03 s | `full-suite.xml` |
| Isolated wheel | `$env:PGWORLD_WHEEL_EVIDENCE='C:/Users/mzora/MechWorld-wt-p02-04/evidence/subagents/P02-04/wheel-report.json'; .venv\Scripts\python.exe -m pytest tests/release/test_wheel_install.py -q --junitxml=evidence/subagents/P02-04/wheel-install.xml` | 1 passed; 141.52 s | `wheel-install.xml`, `wheel-report.json` |
| Compilation | `$env:PYTHONPYCACHEPREFIX='C:/Users/mzora/AppData/Local/Temp/p0204-pycache'; .venv\Scripts\python.exe -m py_compile src/pgworld/simulation/fracture.py tests/physics/test_fracture_accounting.py` | exit 0; no output | console |
| Whitespace/path check | `git diff --check` and `git diff --name-only` | exit 0; only the five assigned path roots | console |

The wheel report records a strict payload allowlist, checkout paths absent
from installed `sys.path`, an installed
`pgworld.simulation.fracture` import, and wheel SHA-256
`aeebcde16d5d267ea401369c7510b839c85cab520c9464524e0d9dea18d93ea8`.

The targeted real JUnit embeds the raw bounded-fixture evidence. The fixed-box
reference criteria were `b12=0.9999999999999993` and `b23=1.0`; convergence
used one iteration with `7.420730696594546e-12 pN` residual against a
`1e-8 pN` limit. The localized bracket was
`[0.09843750000000001, 0.1]` in both load and cumulative path coordinates.
Actual-value P02-02 ranking selected `b23` at `0.1`; exact removal left bond
`b12`, no angle, and components `(n1,n2)` plus `(n3)`, with solver audit
`3 atoms / 1 bond / 0 angles`.

The five raw energies in `pN nm` were respectively
`2.4715998236705826e-27`, `118.18426000000301`,
`118.1842600000025`, `59.09213000000099`, and
`2.4715998236705826e-27`. The conservative control input was
`118.18426000000301`, equilibrium stored change
`118.1842600000025`, pre-event relaxation loss
`5.115907697472721e-13`, signed deletion change
`-59.092130000001504`, held-control work `0`, and post-delete relaxation loss
`59.09213000000099`; the recorded partition residual was exactly zero. The
trace recorded 10 checkpoints, 9 restores, no live temporary groups, and a
closed backend.

### Evidence SHA-256

| Artifact | SHA-256 |
|---|---|
| `final-focused-all.xml` | `f8811468a1c45dd4c9fe50e94d2ce135c19b6e568d1c01d598b49273a22e1507` |
| `real-localization-accounting-pass-02.xml` | `21fa678e5e18c0cec9900861381154d1beac872e09a527d063d9b1457dd6c20c` |
| `relevant-compatibility-pass-02.xml` | `c5afbe1a45e5cd235d4145ceabd1a6d21840ecbb4163e9e96a7e7c1588f13193` |
| `full-suite.xml` | `e7809357d728091be3b2854207768e311d3dd22f394a5ac2a577a42745f3a81a` |
| `wheel-install.xml` | `fda7388837743c35245847e0334e8858c123164559e33cf460b5ad5289689ec6` |
| `wheel-report.json` | `b7fd02aee1994183cb57757ce1a8e09a64cfabd2adc79d730cdd15d66e9bf0b3` |

Runtime working-tree byte hashes at verification were as follows. These hash
the exact Windows-materialized files used by the test commands; they are not
Git blob object IDs. Commit
`d73df3dd27375b8866351442dd7d7b8f8534fbcc` is the immutable source content
identity.

| Path | SHA-256 |
|---|---|
| `src/pgworld/simulation/fracture.py` | `3f788ff1ce676d715022b90e580404e2f6da45fd03a7ed84f23bd320af5e9745` |
| `tests/physics/test_fracture_accounting.py` | `9b62fc366ff3991f900a7d3849ecdf41167746e76d6c5ed584ac330ee9a6156a` |
| `docs/decisions/fracture_accounting.md` | `042ddc062b9914e3a6d1acefdbea3c233d471e3b516cfb252bc9d37bd5f68f61` |

### Preserved verification failures

- `real-junit-logging-option-failure.txt`: the first requested JUnit option was
  unsupported by the system pytest and failed in command-line parsing before
  collection, import, or solver startup.
- `real-localization-accounting-01.xml`: the first actual real run completed
  and closed correctly but failed one hard-coded test oracle expecting `b12`
  to win a tie. The actual criteria were not exactly equal; P02-02 correctly
  ranks actual utilization before stable ID. The corrected assertion binds
  the final topology to the recorded event rather than inventing a tie.
- `relevant-compatibility.xml`: the first compatibility command had one
  collection error and zero tests because its main-venv `PYTHONPATH` omitted
  the external LAMMPS module. The unchanged four-file command passed after
  adding the authorized LAMMPS Python directory.
- All earlier red/correction artifacts remain in the evidence directory. No
  failed artifact is represented as a pass.

## Explicit limitations

- The real solver evidence is limited to P02-03's serial orthogonal,
  sequential-tag `tiny_harmonic_fixture`, with fixed degree-one endpoints,
  free-DOF/post-constraint residuals, and unavailable reaction forces.
- The monotone path certificate is fixture-specific. It is not a proof for a
  general harmonic network and is not executable for the nonlinear peptide
  potential.
- The serialized localization record carries final bracket controls, but not
  private trial observation/assessment digests. It cannot independently
  replay-prove lower-no-cross/upper-cross without the live execution evidence.
- One call owns/closes one backend and handles one control segment. Persistent
  multi-step execution and restart continuation remain P02-06 work.
- No event-location probability, physical time, rate/fatigue behavior,
  toughness, rigidity, instability, catastrophic failure, biological
  certification, sensitivity campaign, experiment, P03 canonical dataset,
  G2 acceptance, cluster production, or public release is claimed.
