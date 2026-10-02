# P03-01 correction verification

Date: 2026-10-02 (America/New_York)

Worktree/branch: `C:\Users\mzora\MechWorld-wt-p03-01`,
`research/p03-01-schema`

Accepted assignment base:
`0222b6d6fdee180e2e2daa86ccfebb276c91f1f6`

First-pass commits `c489b8f7b1560ad1e18157303cc00633dd9fdae6` and
`c38e4ab735b0c73ff229cc831d705b2433dfca49` were independently rejected.
They and their evidence remain history, but their green result is not the
acceptance basis. Corrected implementation revision evaluated here:
`e54bbb4a0161a3e292bb0255b6b3dc508dab3810`.

Runtime: `C:\Users\mzora\MechWorld\.venv\Scripts\python.exe -B`, Python
3.11.9, pytest 7.4.3, `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`. Commands
that exercise inherited solver tests set `PYTHONPATH` to this worktree's
resolved `src` followed by the authorized external LAMMPS directory
`C:\Users\mzora\AppData\Local\LAMMPS 64-bit 2Sep2026 with GUI\Python`.
The imported module resolves there; a bounded open/version/close command
returned `20260902`, exit 0 in 0.72 s.

## Correction red evidence

All red runs used the worktree `src` on `PYTHONPATH` and the shared Python
above. No implementation fix had been applied for the named regression when
its artifact was recorded.

1. Projection-relational replay:

   ```powershell
   python -B -m pytest -q tests/unit/test_schema.py -k 'untyped_event_history or noncontiguous_state_sequence or forged_event_pre_state or inconsistent_censor_coordinate' --junitxml=evidence/subagents/P03-01/correction-projection-red.xml
   ```

   Exit 1; 5 failed, 46 deselected in 3.19 s. Rehashed observed views accepted
   string event sequence/criterion values and state sequence `[77,1]`; target
   views accepted a forged pre-state and censor coordinate 99.

2. Typed reference/convergence/multigraph/dead-image contract:

   ```powershell
   python -B -m pytest -q tests/unit/test_schema.py -k 'reference_state_is_typed or convergence_preserves_budget or selector_unambiguous or dead_edge_does_not_claim' --junitxml=evidence/subagents/P03-01/correction-contract-red.xml
   ```

   Exit 1; 4 failed, 51 deselected in 2.29 s. The typed reference, convergence
   budget/tolerance, solver selector, and nullable dead-edge image contracts
   were absent.

3. Geometry/connectivity replay:

   ```powershell
   python -B -m pytest -q tests/unit/test_schema.py -k 'component_partition_must or image_offsets_must or alive_edge_length_is' --junitxml=evidence/subagents/P03-01/correction-geometry-red.xml
   ```

   Exit 1; 3 failed, 76 deselected in 0.54 s. Incorrect connected-component
   partitions, nonperiodic-axis images, and forged stored length were accepted.

4. Threshold/event/angle physics:

   ```powershell
   python -B -m pytest -q tests/unit/test_schema.py -k 'threshold_values_obey or material_event_criterion_is or angle_dependencies_are' --junitxml=evidence/subagents/P03-01/correction-physics-red.xml
   ```

   Exit 1; 5 failed, 79 deselected in 3.06 s. Negative/wrong-unit thresholds,
   forged criterion values, and incomplete angle dependencies were accepted.

5. Control path and rotated pressure tensor:

   ```powershell
   python -B -m pytest -q tests/unit/test_schema.py -k 'absolute_control_change or mixed_continuous_control or pressure_path_intervention or rotates_principal' --junitxml=evidence/subagents/P03-01/correction-control-red.xml
   ```

   Exit 1; 4 failed, 85 deselected in 3.11 s. Progress was not derived from
   absolute load-coordinate change, mixed units/families were accepted,
   pressure-path intervention was rejected, and the rotated pressure tensor
   was rejected.

## Corrected green evidence

1. Commit-sensitive focused schema suite:

   ```powershell
   $env:PYTHONPATH='C:\Users\mzora\MechWorld-wt-p03-01\src'
   python -B -m pytest -q tests/unit/test_schema.py --junitxml=evidence/subagents/P03-01/correction-focused.xml
   ```

   Exit 0; **89 passed in 1.80 s**, 0 failed/errors/skips. This run occurred at
   committed implementation `e54bbb4a...`.

2. Loading/damage/tracked-source compatibility:

   ```powershell
   python -B -m pytest -q tests/physics/test_loading.py tests/physics/test_damage_law.py tests/release/test_tracked_python_compiles.py --junitxml=evidence/subagents/P03-01/correction-compatibility.xml
   ```

   Exit 0; **99 passed in 9.67 s**, 0 failed/errors/skips, with 12 inherited
   invalid-escape deprecation warnings from legacy plotting sources.

3. Broader no-wheel suite with authorized external LAMMPS path:

   ```powershell
   python -B -m pytest -q --ignore=tests/release/test_wheel_install.py --junitxml=evidence/subagents/P03-01/correction-no-wheel.xml
   ```

   Exit 0; **359 passed in 84.05 s**, 0 failed/errors/skips, with 14 inherited
   warnings (the 12 compilation warnings plus 2 expected legacy elastic-output
   deprecations). The wheel test remains excluded because its payload allowlist
   is integrator-owned.

4. Targeted compilation:

   ```powershell
   python -B -m py_compile src/pgworld/data/schema.py src/pgworld/data/__init__.py tests/unit/test_schema.py
   ```

   Exit 0 in 1.30 s with no output before the implementation commit, and exit
   0 again in the 3.41 s combined commit-sensitive focused/compile command.

## Frozen artifact SHA-256

These values are SHA-256 hashes of the immutable Git blob bytes after the files
stopped changing. This avoids ambiguity from Windows working-tree newline
materialization.

| Artifact | SHA-256 |
|---|---|
| `correction-projection-red.xml` | `51ad8919385b93ceaa22b9036d242f7fbe35e92134bb7e305b90dfe947886bd3` |
| `correction-contract-red.xml` | `e272f00ee909757e8df425ca27d342fb67ad8e78f32cbc145ee7ad7ef9a1573c` |
| `correction-geometry-red.xml` | `6a654b6a18e11f2adf7f425e13b0483705f95a046d5b82e0d2b6a31949b28578` |
| `correction-physics-red.xml` | `a168342d08526abb8633607da50e533789c022db72d1c2a6d2ba46d4ae1ff43c` |
| `correction-control-red.xml` | `87489fe0b2cf4c4217357d6ad4df256341ec5ed9f5772fdd2b48840ff5d5f14a` |
| `correction-focused.xml` | `11b1e15b58d55d039dbda9a822206a99300c8afc3b47dda9b1aaacd2274fd829` |
| `correction-compatibility.xml` | `212ed5fc43d17e60471c52e215ffa5e33433bb29b426b0c0124cb56a2fe1d054` |
| `correction-no-wheel.xml` | `4f0bad2c4191215c09b2d9ba7e99f406e0564e3ef7de9fd67e5caaa8752770d3` |

The superseded first-pass verification contained stale text hashes after line
normalization. The actual committed hashes are: `red.xml`
`dfd039f7db3a635e3f8120faa6803e39125232ea60fa20a5ab51f979010ed004`,
`control-contract-red.xml`
`8e47ab2fcca56a8c68967ff2fe281ec031a09f2f78d2a23bfa30940dc8db563d`,
and failed environmental `no-wheel-full.xml`
`ec26bfe0a0ab2c691f5d758048d08db18442e1d8030ff394a0e59b7eb53f0c00`.

The same eight correction hashes are stored in `artifact-hashes.sha256`. A
post-freeze check reads each immutable blob through `git cat-file`, compares
its SHA-256 to the manifest, exits 0, and prints `verified 8 committed artifact
hashes`:

```text
For each manifest row, read `git cat-file blob HEAD:<path>`, compute SHA-256,
and require equality with the recorded digest.
```

## Limitations

- This is an in-memory/JSON-compatible schema and replay contract, not an
  HDF5/NPZ writer, dataset, migration tool, or trained model.
- Profile identity strings are internally bound but registry membership is
  not proven here.
- P03-02 still owns full accepted-P02-to-schema solver value agreement; P03-04
  owns canonical storage/manifests/splits. The integrator must reconcile the
  older shared draft data contract after accepting this correction.
- No real/private/experimental data or biological certification was used.
  G3 remains unaccepted.
