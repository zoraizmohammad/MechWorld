# P02-05 implementation return

## Scope

- Base: `3fdb17af5a1f7309255788f4df1cb38f0df4bd03`
- Branch/worktree: `research/p02-05-stochasticity`;
  `C:/Users/mzora/MechWorld-wt-p02-05`
- Core: sample-once quenched material thresholds, conditional-replicate
  provenance, strict replay, and predictor privacy.
- No root ledger, shared schema, damage/fracture implementation, profile,
  dependency, gate, private-data, or unrelated path is owned.

## Implementation

`src/pgworld/physics/stochasticity.py` adds strict immutable records for the
P01-04 seed namespace, one conditional material replicate, its predictor-safe
projection, and a material-only conditional cohort. It delegates threshold
materialization and replay reconstruction to P02-02. Event-process randomness
is disabled and the event seed is recorded but unconsumed.

The scientific and privacy decision is recorded in
`docs/decisions/stochasticity.md`.

## Defect-first evidence

All commands used the main dependency-complete virtual environment, this
worktree's `src` on `PYTHONPATH`, one pytest process, and at most two numerical
threads.

| Artifact | Result |
|---|---|
| `initial-missing-module-red.xml` | exit 2; expected missing-module collection error |
| `privacy-corrected-pre-source-red.xml` | exit 2; corrected exact privacy test still captured the missing module |
| `first-source-correction.xml` | exit 2; constructor field omission exposed during collection |
| `focused-correction-2.xml` | exit 1; 24 passed, 3 precise test-oracle/error-order failures |
| `focused-first-green.xml` | exit 0; 27 passed |
| `canonical-field-forgery-red.xml` | exit 1; 27 passed, one forged hash-valid threshold field accepted |
| `canonical-field-forgery-green.xml` | exit 0; 28 passed after exact P02-02 rematerialization check |
| `focused-post-upstream-compat.xml` | exit 0; 29 passed including actual P01-04 namespace compatibility |
| `compatibility-first.xml` | exit 0; 101 P01-04/P02-02/P02-05 tests passed |
| `compatibility-accounting-schema.xml` | exit 0; 155 passed, 1 real-LAMMPS test deselected |
| `final-focused.xml` | exit 0; 29 passed in 2.25 s |
| `full-suite.xml` | exit 0; 516 passed, 15 warnings in 109.02 s |
| `wheel-install.xml` / `wheel-report.json` | exit 0; 1 passed in 97.32 s; strict isolated-wheel allowlist/import/contract smoke passed |

The warning set contains the inherited elastic-adapter deprecations, existing
invalid-escape warnings, and the known pytest xunit2 `record_property` warning.
No P02-05 warning or skipped test occurred.

## Exact final commands

Working directory for every command was
`C:/Users/mzora/MechWorld-wt-p02-05`. The common thread limits were
`OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`, and `MKL_NUM_THREADS=2`.

Focused:

```powershell
$env:PYTHONPATH='C:/Users/mzora/MechWorld-wt-p02-05/src'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -B -m pytest tests/physics/test_stochastic_events.py -q --junitxml=evidence/subagents/P02-05/final-focused.xml
```

P01-04/P02-02/P02-05 compatibility:

```powershell
$env:PYTHONPATH='C:/Users/mzora/MechWorld-wt-p02-05/src;C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/Python'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -B -m pytest tests/unit/test_generator_reproducibility.py tests/physics/test_damage_law.py tests/physics/test_stochastic_events.py -q --junitxml=evidence/subagents/P02-05/compatibility-first.xml
```

Separately authorized non-real accounting/schema compatibility:

```powershell
$env:PYTHONPATH='C:/Users/mzora/MechWorld-wt-p02-05/src'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -B -m pytest tests/physics/test_fracture_accounting.py tests/unit/test_schema.py -q -k 'not real_serial_lammps and not real_lammps' --junitxml=evidence/subagents/P02-05/compatibility-accounting-schema.xml
```

Full suite:

```powershell
$env:PYTHONPATH='C:/Users/mzora/MechWorld-wt-p02-05/src;C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/Python'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -B -m pytest -q --junitxml=evidence/subagents/P02-05/full-suite.xml
```

Isolated wheel, after the full suite completed:

```powershell
$env:PYTHONPATH='C:/Users/mzora/MechWorld-wt-p02-05/src;C:/Users/mzora/AppData/Local/LAMMPS 64-bit 2Sep2026 with GUI/Python'
$env:PGWORLD_WHEEL_EVIDENCE='C:/Users/mzora/MechWorld-wt-p02-05/evidence/subagents/P02-05/wheel-report.json'
C:/Users/mzora/MechWorld/.venv/Scripts/python.exe -B -m pytest tests/release/test_wheel_install.py -q --junitxml=evidence/subagents/P02-05/wheel-install.xml
```

The wheel was `mechworld_pg-0.1.0.dev0-py3-none-any.whl`, SHA-256
`1b29a82e4a8a97af899657ffaf8495c8adb8373e4c091aab7996fb7b721ddeb3`.
The installed module resolved inside the fresh environment, the strict member
allowlist passed, `pip check` passed, and the installed smoke confirmed hidden
projection, disabled event process, and unconsumed event seed.

## Immutable source and hashes

Source commit:
`7b88dd30272d380d321a6fec6fada07f84c4d528`
(`Add reproducible conditional material replicas`). Author and committer are
both solely `Mohammad Zoraiz <zoraizmohammad@gmail.com>`.

SHA-256 values below are over exact Git-blob bytes in that source commit, not
over Windows checkout materialization:

| Path | Git-blob-byte SHA-256 |
|---|---|
| `src/pgworld/physics/stochasticity.py` | `955c85b10418016d5bbbfc54c54aa7282cfdcfd52d17e9df49b5e73cb8c0b428` |
| `tests/physics/test_stochastic_events.py` | `1bed72a5aabad9b7f4b66b96a251eb9be59b51d0f70e4a23a16a72508bdc9c40` |
| `tests/release/test_wheel_install.py` | `7ed7a2bb5f80a0e4ba3665a8b01386b1d179bd278cf372de91a453192b8ab94a` |
| `docs/decisions/stochasticity.md` | `482a822bb5db043fc6d1b93293d6a9329c60663fae20433c120dfd449225c0ed` |

Evidence hashes are SHA-256 over the runtime working-tree bytes committed in
the evidence return:

| Artifact | SHA-256 |
|---|---|
| `initial-missing-module-red.xml` | `3b899f5d90d1520d20ffcb4f43192d3bb0da938f9f34e12e78639d6a5c3f806c` |
| `corrected-pre-source-red.xml` | `af05712993ef4320b3f5314f6aa0829fbb1bae5d270e812ff1f9d23c028a4dce` |
| `privacy-corrected-pre-source-red.xml` | `cb08a2f3ceacf5066e702ba7070abb6a983a79a0577fc830263013d31af245a6` |
| `first-source-correction.xml` | `1623306834e6de20b40a88fb29e30f65504af76d8c6986aa6ea06f67ef10b275` |
| `focused-correction-2.xml` | `bfe0bcdde85ef817438c499e115ba8f2cb3bbcb63db6fb4f0d05d391f5170ff5` |
| `focused-first-green.xml` | `6f2b6fe7d2228de2488e6a03c1e325d5bcb597ece767b5e0d60fe6fbd69e1625` |
| `focused-post-graph-fixture.xml` | `e4201c6d93dcea046c925f7ac709e13599f538249359c256a77b9eb29262f0b2` |
| `canonical-field-forgery-red.xml` | `3bcd78b3a626d53a95a174feffdea6e18dc75354243371437d483878e1b8510c` |
| `canonical-field-forgery-green.xml` | `a548d7c5ee070041cb3155879f25c2bf2a32bb78743a7ad487ef325d2777ddd2` |
| `focused-post-upstream-compat.xml` | `abaa5fac7d987dd019fca44962db32a9ac716b68e34bebbcaaace513daa00932` |
| `compatibility-first.xml` | `de95280e3c512a4b0b6ef150a6de6a21c058d5f56cbbe3e6a37f8b9648250d69` |
| `compatibility-accounting-schema.xml` | `0aac5aedeba3ea4de9c821800271d80075daa2f0e754b2f15f509869c6c839cf` |
| `final-focused.xml` | `94cbb7a3b283ea7ad015c05432af26838268ed0e96e8c4391cffc8a5e9c524e7` |
| `full-suite.xml` | `e9b5369a70674ebfa934747b569db8309d00f2f5a24178591dd8f72a2bba0b20` |
| `wheel-install.xml` | `ad9e26013e4ba0734ea87d2868ba45647210fbaeae146c2829508a65ff62fc28` |
| `wheel-report.json` | `48f590e679587d393e3c02d77d5cff4fd14652835ed2ce32d688a158f970cce6` |

## Path and identity boundary

The source commit changes only the four authorized implementation/decision/
test paths listed above. The evidence return adds only this report and
`evidence/subagents/P02-05/`. Repository-local identity and effective
`GIT_AUTHOR_IDENT`/`GIT_COMMITTER_IDENT` were verified before commit. No
coauthor footer was used and no push was performed.

## Current limitations

- Conditional randomness is hidden quenched material variation; there is no
  stochastic event process conditional on a fixed field.
- The reserved event seed has no draws or mutable state in this version.
- Threshold distribution parameters remain phenomenological and provisional.
- The predictor projection is an API boundary; P03 dataset exporters must
  still use their reviewed access projection and leakage checks.
- Parent-network, graph, geometry-realization, and conditioned-state IDs are
  caller-supplied, hash-bound values; this task does not derive them from a
  P01 graph or P03 state object.
- P02-06 owns persistent restart execution and sensitivity evidence.
- The full/wheel suites reran existing bounded LAMMPS fixtures for
  compatibility; P02-05 adds no LAMMPS stochastic-event mechanics evidence.
- No production campaign, dataset, model, experiment, public release, or
  G2/G3 gate acceptance is supplied by this task.
