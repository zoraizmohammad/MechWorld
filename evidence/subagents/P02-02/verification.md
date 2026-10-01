# P02-02 verification evidence

## Immutable implementation

- Base: `7b2a025bdc7b74c7956cebf9787df59256403fce`
- Implementation commit: `24eb10712552171b93bc595fadd414b00a8ad3f7`
- Branch/worktree: `research/p02-02-damage-law` at
  `C:/Users/mzora/MechWorld-wt-p02-02`
- Python: CPython 3.11.9 from
  `C:/Users/mzora/MechWorld/.venv/Scripts/python.exe`
- Resource environment for verification:
  `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`,
  `MKL_NUM_THREADS=2`; one pytest process at a time.
- Author and committer inspected with `git var`: Mohammad Zoraiz
  `<zoraizmohammad@gmail.com>`.

Implementation path SHA-256 values:

| Path | SHA-256 |
|---|---|
| `src/pgworld/physics/damage.py` | `8a9257a9ad528161458433a7a35073d58b197b9f807631fc44e50bdcf30e69cb` |
| `tests/physics/test_damage_law.py` | `fa9d4df7fda74775070e972feb5e7206680f27f76d2ba740dc7cd771c9e71223` |
| `tests/release/test_wheel_install.py` | `f662ac8c8c2a6fe24144b0a69229a72b74d2384007c0f32fb6b2b6daf17da18d` |
| `docs/decisions/fracture_model.md` | `47c2bf7b143b9d9b4dd8bd1a3a86396d4ab2eb3cfc4a5314b1a72f2b334409f8` |

## Defect-first and adversarial evidence

The first relative-interpreter invocation used
`.venv/Scripts/python.exe` inside the isolated worktree. It did not launch
pytest because ignored virtual environments are not copied into worktrees; a
PowerShell pipeline also left a misleading shell status of zero. No JUnit from
that setup error is used as scientific or regression evidence. The lesson was
to use the inspected absolute interpreter path and to capture
`$LASTEXITCODE` immediately after every native pytest process.

The actual first regression command was:

```powershell
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest tests/physics/test_damage_law.py -q --junitxml=evidence/subagents/P02-02/red.xml
```

It exited 2 with one collection error:
`ModuleNotFoundError: No module named 'pgworld.physics.damage'`. Evidence:
`red.xml` SHA-256
`e2583b3f5cdfea90b155c6f47041819ecdfef0980438fbc5144e1002c9d489dc`.

Independent review drove fail-closed red-to-green rounds rather than accepting
the first green implementation:

| Evidence | Exact red result | Covered defect class | SHA-256 |
|---|---:|---|---|
| `review-red.xml` | 45 tests, 9 failures | registered profile binding, cross-law acceptance, forgeable candidate ordering, excluded-event replay/hash, immutable initial flags, standalone event provenance, endpoint duplicates/units, strict trajectory replay | `576824ab30b09dcba89329679b96bf9cfba03baa10b6eced816fe7a6648209e1` |
| `transition-invariants-red.xml` | 54 tests, 4 failures | event-to-post-state bond binding, sha256 event history, invalid-reference/history coexistence, endpoint material-event ID | `933bd5a899dac2596acbf264637558aed354e1c3ce1ddc414ec5734ba1d606df` |
| `mixed-law-endpoint-red.xml` | 1 test, 1 failure | mixed law/fingerprint/threshold realizations accepted in one endpoint summary | `7e8f69f5968af1c18a7d90de1ce1831309ad3eac3ed1fd96cc9b085a6e172bcf` |
| `assessment-reason-red.xml` | 1 test, 1 failure | solver-error assessment replay could be relabeled as physical failure | `6a663bf676afdc401d572a2e2e44e08add6bfa7ae859789c9bb82e9537851994` |

Earlier development failures are retained in this directory. They are not
reported as final passes. The reviewer independently reproduced the important
constructor/replay defects and cleared the corrected source before heavy
verification.

## Final commands and results

Focused current-source regression:

```powershell
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest tests/physics/test_damage_law.py -q --junitxml=evidence/subagents/P02-02/focused-post-heavy.xml
```

Exit 0: **58 passed in 0.43 s**; no failures, errors, or skips. JUnit SHA-256:
`aa18441a2a0e993d4b05409e81e3c30194a4c164e0d1e94bdd4eeb6135f94169`.

Installed-wheel verification:

```powershell
$env:PGWORLD_WHEEL_EVIDENCE='C:/Users/mzora/MechWorld-wt-p02-02/evidence/subagents/P02-02/wheel-verification-final.json'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest tests/release/test_wheel_install.py -q --junitxml=evidence/subagents/P02-02/wheel-final.xml
```

Exit 0: **1 passed in 122.26 s**. The fresh exact-lock environment passed
`pip check`; checkout paths were absent from installed `sys.path`; the strict
33-member wheel allowlist passed; private/generated paths remained excluded;
LAMMPS 20260902 fixtures closed; and the installed damage module materialized a
hidden deterministic threshold field without a time claim. Wheel SHA-256:
`e7123d0a0e428cdeab567750a3c2d08bac224a9268e0fd17f74ebe4166a81a08`.
Evidence SHA-256 values: `wheel-final.xml`
`9d7f38f2cf32e0edb5751772f8bc2d1d9b0c69073819b2169d8136127263b870`;
`wheel-verification-final.json`
`1b82b02313421f88a3b562d1a97e11f91aeca0bec21129d6e2faa2185b0a3959`.

Full repository verification:

```powershell
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/subagents/P02-02/full-final.xml
```

Exit 0: **271 passed in 114.80 s**, no failures/errors/skips, with 14 inherited
warnings (two documented legacy-elastic deprecations and twelve existing
invalid-escape deprecations surfaced by tracked-source compilation). JUnit
SHA-256:
`cff2b35b3afda2e1ffeda53b31a8d93aa907ef91e75b101ca995fd55e17a5f63`.

Final focused rerun after the heavy gates again passed 58/58. In addition:

```powershell
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -m compileall -q src
git diff --check
```

Both exited 0. `git diff --check` printed only Git's Windows checkout warning
that LF will be materialized as CRLF when Git next touches the already tracked
wheel test; it reported no whitespace error.

## What is verified

- Deterministic extension-ratio, tension, and energy threshold modes with exact
  units and an explicit non-biological mechanism claim.
- Stable-ID-keyed quenched U64 sampling, order/retry invariance, immutable
  threshold fields, sample-once semantics, and explicit predictor visibility.
- Registered physics-profile ID/hash plus fixed-reference binding throughout
  laws, states, assessments, events, and endpoint summaries.
- Initial-threshold-violation exclusion; accepted-equilibrium-only mechanical
  rupture; deterministic utilization/stable-ID tie order; content-hashed
  replay; and irreversible alive/rupture/prescribed-removal masks.
- Prescribed, computational-neighbor, rendering, and solver-error origins are
  excluded from damage initiation; solver errors cannot be relabeled physical
  failure.
- Damage initiation, load-bearing connectivity loss, load/stiffness
  degradation, and mechanical instability remain separate evidence types.
- No-event right censoring binds the law/fingerprint/threshold realization and
  separates instantaneous terminal lambda from monotone cumulative path
  progress. A cyclic fixture ends at lambda 0.0 with progress 0.4.

## Explicit limitations

P02-02 does not run a solver, mutate LAMMPS topology, remove dependent angles,
localize an event, execute/bound cascades, compute deletion energy accounting,
or prove restart/load-step sensitivity. Those are P02-03 and later gates. It
does not certify thresholds, coarse graining, biological cleavage, physical
time, three-dimensional stress, experiments, production compute, or release.
Hidden threshold records are privileged simulator/reference metadata; P03 and
model feature-selection code must enforce their exclusion from predictor
inputs. G2 is not accepted by this task alone.
