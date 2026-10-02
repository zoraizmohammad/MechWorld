# P03-01 correction verification

Date: 2026-10-02 (America/New_York)

Worktree/branch: `C:\Users\mzora\MechWorld-wt-p03-01`,
`research/p03-01-schema`

Accepted assignment base:
`0222b6d6fdee180e2e2daa86ccfebb276c91f1f6`

First-pass commits `c489b8f7b1560ad1e18157303cc00633dd9fdae6` and
`c38e4ab735b0c73ff229cc831d705b2433dfca49` were independently rejected.
The first correction through `ebde2164211286dd5d2db09de733d26b9aeb5f74`
was also independently rejected by ten immutable audit probes. Both earlier
returns and their evidence remain history, but neither green result is the
acceptance basis. The second exact-red commit is
`be578d70cfbd28c4d4a21079fea466dbe6c0717d`, followed by implementation
`e8f0ba03543fc7b1cea80a3ee6f32f4b34cf6e05`. A subsequent projection audit
was preserved at `9e70bf6b4b64bea7badb1164b1383ac4403f9cd9`; the final implementation
for that round was `b888d6591c2d2290cdcdff8cf0fa0e9ca499f7bf`.
The final state/control projection reds are at
`11359743bc1fba8a648b910d005dc27569fc3d31`; the final implementation
revision evaluated here is `9f94f79f238aab251245c8381baf666cb55d9011`.

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

## Superseded first-correction green evidence

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

## Second immutable-audit correction

Independent review rejected the first correction because ten exact probes
exposed unsupported capability claims, incomplete threshold/status binding,
unstable topology labels/images, intervention and event-order gaps, a
post-event target replay failure, and pre-normalization reference hashing.
Before fixes, this exact selection ran against `ebde216...`:

```powershell
python -B -m pytest -q tests/unit/test_schema.py -k 'unrepresented_local_stress or one_immutable_threshold_per_edge or invalid_reference_cannot or observed_material_event_id or component_labels_cannot or surviving_edge_image or normalized_integer_reals or intervention_cannot_advance or event_sequence_order or target_projection_after_first_event' --junitxml=evidence/subagents/P03-01/correction2-red.xml
```

Exit 1; **10 failed, 89 deselected in 0.70 s**. The red artifact was committed
at `be578d70cfbd28c4d4a21079fea466dbe6c0717d` before implementation changes.

At implementation `e8f0ba03543fc7b1cea80a3ee6f32f4b34cf6e05`:

- Exact probe selection: exit 0; **10 passed, 89 deselected in 0.31 s**.
- Commit-sensitive schema suite: exit 0; **99 passed in 0.97 s**.
- Loading/damage/tracked compilation: exit 0; **99 passed in 2.11 s**, with
  the same 12 inherited invalid-escape warnings.
- Broader no-wheel suite: exit 0; **369 passed in 20.93 s**, with 14 inherited/
  expected warnings and the authorized LAMMPS path.
- Targeted `py_compile`: exit 0.

## Final projection-delta correction

Independent review then found that a rehashed target damage context and
observed/target events were typed but not fully bound to graph universes,
state deltas, pre-state mechanics, or available endpoint provenance. These
seven exact regressions ran before the final fix:

```powershell
python -B -m pytest -q tests/unit/test_schema.py -k 'target_damage_context or future_damage_context or target_future_event or observed_event_history_must or observed_material_criterion or target_material_criterion' --junitxml=evidence/subagents/P03-01/correction3-red.xml
```

Exit 1; **7 failed, 99 deselected in 0.67 s**. The red artifact was committed
at `9e70bf6b4b64bea7badb1164b1383ac4403f9cd9` before the final implementation.

At final implementation `b888d6591c2d2290cdcdff8cf0fa0e9ca499f7bf`:

- Exact projection probes: exit 0; **7 passed, 99 deselected in 0.27 s**.
- Commit-sensitive full schema suite: exit 0; **106 passed in 0.98 s**.
- Loading/damage/tracked compilation: exit 0; **99 passed in 0.84 s**, with
  12 inherited invalid-escape warnings.
- Broader no-wheel suite: exit 0; **376 passed in 9.40 s**, with 14 inherited/
  expected warnings and the authorized LAMMPS path.
- Targeted `py_compile`: exit 0.

The final target context is checked against graph/control/angle universes. A
future damage context must equal the first future material event exactly; a
historical context must precede the target event boundary. Observed and target
events must match exact edge/angle deltas, preserve same-position survivor
images, derive their criterion from the linked pre-state mechanics, and, for
target events, match available law/realization/profile/reference identities.

## Final shared control-replay correction

The last independent audit showed that observed states and the target anchor
could be rehashed with load coordinate/progress `0.05` while their referenced
control remained at `0.1`. The two exact tests ran before the fix:

```powershell
python -B -m pytest -q tests/unit/test_schema.py -k 'observed_state_load_and_progress or target_anchor_load_and_progress' --junitxml=evidence/subagents/P03-01/correction4-red.xml
```

Exit 1; **2 failed, 106 deselected in 0.24 s**. The red artifact was committed
at `11359743bc1fba8a648b910d005dc27569fc3d31` before implementation.

At final implementation `9f94f79f238aab251245c8381baf666cb55d9011`:

- Exact state/control probes: exit 0; **2 passed, 106 deselected in 0.19 s**.
- Commit-sensitive full schema suite: exit 0; **108 passed in 0.96 s**.
- Loading/damage/tracked compilation: exit 0; **99 passed in 0.87 s**, with
  12 inherited invalid-escape warnings.
- Broader no-wheel suite: exit 0; **378 passed in 8.12 s**, with 14 inherited/
  expected warnings and the authorized LAMMPS path.
- Targeted `py_compile`: exit 0.

Full trajectories and both nonprivileged projections now use the same control
sequence and state-binding validators. They enforce control/load IDs, family
and unit continuity, absolute-coordinate progress, deformation/tension
composition, zero-advance intervention inheritance, graph references,
state/control coordinates and progress, and active `F_absolute @ H_reference`
cell binding.

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
| `correction2-red.xml` | `6692c05d60a8525d3dc3a94c3abee06e37aa525460a289ee216ba1c22949f5a9` |
| `correction2-probes-green.xml` | `29777084cf8ed95a33c7c95abd900c8c2bbfe4d15faec919badb13c29ca2c2f6` |
| `correction2-focused.xml` | `a5872fe797721adce59b8d462ba3e33d848c9ab1b3c2bb6c696767e5de06c1ae` |
| `correction2-compatibility.xml` | `8bbef0d063fd32d2262ddf55fead2098fb5dee6aefbeeca1306959f4ad57cb0b` |
| `correction2-no-wheel.xml` | `1f20c0f836e4ddc2d7ee28132f9c22f34a7961af2a4b9fcc94547fddcfabc9ec` |
| `correction3-red.xml` | `660c434548666931a0d1bc056af69afb3b685e3a1ffe8eefae925f07e6df7abf` |
| `correction3-probes-green.xml` | `ff7ed04fba9c6e8f364e31b221f029d62bfeb4508c6e7c3e91a30a9fed106458` |
| `correction3-focused.xml` | `175f3268ff4c2d65c5ee3176bd0c9b1b43ef30f304ae32800c28c89df4d60b7c` |
| `correction3-compatibility.xml` | `b47e425ced523ecbcd6acdd0bed9e3bc185b13521fb2800b7776966174eb4a5a` |
| `correction3-no-wheel.xml` | `33a708048e8dcd3081d5180b6fd52de985568286365e8655fe485b1a79f7f207` |
| `correction4-red.xml` | `ebb77900d9d816dc844142ff75b91d9800e53d5083c534f33f55081d6bc55348` |
| `correction4-probes-green.xml` | `da997e7d010c57d2f7092a5cc29a2b5b9ad7b90018c5346eae870e8d1c0e7dcd` |
| `correction4-focused.xml` | `719c0759ab216035c697df2880ac36c2e4a961351533c59cf16e2674d445371a` |
| `correction4-compatibility.xml` | `0802706eda8ec8308dbf545da09e8439736e229c1f8809b9877ae2d8fbbfffb0` |
| `correction4-no-wheel.xml` | `91e42de3dc04997fb850b5c55816bd77f05bdd9cfcc74fd94d95979da7452a93` |

The superseded first-pass verification contained stale text hashes after line
normalization. The actual committed hashes are: `red.xml`
`dfd039f7db3a635e3f8120faa6803e39125232ea60fa20a5ab51f979010ed004`,
`control-contract-red.xml`
`8e47ab2fcca56a8c68967ff2fe281ec031a09f2f78d2a23bfa30940dc8db563d`,
and failed environmental `no-wheel-full.xml`
`ec26bfe0a0ab2c691f5d758048d08db18442e1d8030ff394a0e59b7eb53f0c00`.

The same twenty-three correction hashes are stored in `artifact-hashes.sha256`. A
post-freeze check reads each immutable blob through `git cat-file`, compares
its SHA-256 to the manifest, exits 0, and prints `verified 23 committed artifact
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
