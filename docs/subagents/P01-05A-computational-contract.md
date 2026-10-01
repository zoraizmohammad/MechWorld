# P01-05A return: provisional computational physics contract

## Assignment and boundary

- Task: P01-05A, freeze the provisional computational physics contract.
- Base: `78da30ffd8b374125a34edaacc71ae7650b8f722`.
- Branch/worktree: `research/p01-05a-computational-contract` at
  `C:\Users\mzora\MechWorld-wt-p01-05a`.
- Author/committer identity: Mohammad Zoraiz
  `<zoraizmohammad@gmail.com>`.
- Owned paths only: `docs/physics_parameters.md`, `configs/physics/**`,
  `src/pgworld/config/physics_profiles.py`,
  `tests/physics/test_physics_profiles.py`,
  `evidence/subagents/P01-05A/**`, and this report.
- No root ledger, README, task state, ownership file, inherited constant,
  runner, dependency, packet file, private data, or external system was changed.

This return completes only the computational slice. P01-05 final biological
parameter review remains blocked.

## Pre-integration review correction

The integrator rejected the first return before acceptance. Two defects were
confirmed and corrected in schema v2:

1. The first schema applied the new configurational-virial policy without a
   separate record of historical execution. Schema v2 records default thermo
   pressure and NVE/deform history independently from the mandatory virial-only
   policy for new outputs. Direct isotropic tangent output is now explicitly
   `not_applicable`.
2. The first frozen dataclass could be constructed directly with a registered
   ID/hash and an arbitrary `_snapshot_json`. A pre-fix regression demonstrated
   that `K=1` was accepted. Construction now revalidates the complete snapshot,
   a public persisted-snapshot validator is available, and aggregation accepts
   only validated objects or complete validated snapshots.

The rejected schema-v1 hashes were not integrated or used by an accepted run.
All schema-v2 records were repinned before acceptance review.

## Delivered contract

Four complete versioned JSON records are committed under `configs/physics/`:

1. `legacy_python_2026_03_12_v1` preserves the current Python values.
2. `legacy_direct_isotropic_pre_unit_fix_v1` preserves the exact retained
   direct `IsotropicPrestrain` values.
3. `legacy_direct_elastic_2d_zero_temp_pre_unit_fix_v1` preserves the exact
   retained elastic values, its distinct nonlinear fit, and the invalid
   thickness-free GPa interpretation as provenance.
4. `reviewed_physics_provisional_v0` copies current-Python values only for
   bounded numerical fixtures/development and is fail-closed for final science.

The current-Python date records the final inherited coefficient/unit changes on
2026-03-12 (`8f413573` and `41548169`); `v1` is the first immutable profile
capture, not a claim of review or a new attribution.

Every record includes schema/profile version; ID and canonical SHA-256;
family/route/intended use; equations and actual nano units; spacing/mapping and
mass status; fixed-cell reference requirements; primary total and secondary
incremental configurational-virial 2D tension; axes; no-time/no-thickness/no-3D
flags; rupture-law status; numerical derivations; sources/provenance; review
state; and proposed-unconfirmed reviewer requests. Per-parameter uncertainty is
`unknown`, ranges are `not_reported`/null, and nonlinear fit artifact/path/hash
status is explicitly unavailable.

The loader is standard-library-only. It returns a frozen object backed by a
canonical JSON string and supplies a detached expanded snapshot for run/artifact
metadata. It validates exact fields and types, finite/positive numerics,
route-specific values, cross-field constraints, embedded and registry-pinned
hashes, and registered IDs. Direct construction and persisted read-back use the
same complete validation. Silent profile mixing fails. The only multi-profile
mode is an explicitly declared `stratified_by_profile` comparison, which returns
separate ID/hash strata. Compact ID/hash dictionaries are indexing metadata,
not sufficient validation input.

Historical default thermo pressure is not relabeled as virial-only. The current
Python profile distinguishes its minimize, NVE/deform, and elastic entry points;
both direct retained routes record their NVE/deform segments and the possibility
of kinetic pressure. The required new-output block separately excludes kinetic
pressure. Official LAMMPS sources are pinned to `patch_2Sep2026`, and current
repository sources have narrow claim scopes for constants, units, generator
serialization, runners, and ensemble analysis.

## Numerical facts recorded without certification

For the inherited current-Python values, the contract records:

- code spacing `1.03 nm` and placeholder mass
  `0.0004271587301788674 ag`;
- harmonic `K=5570 pN/nm`, `r0=1.03 nm`;
- nonlinear `epsilon=185.328520541486 pN nm`, `r0=1.0 nm`,
  `lambda=4.034069292365436 nm`;
- angle `K=41.8 pN nm/rad²`, `theta0=180 degrees`;
- one-edge tangent `11140 pN/nm`;
- two-edge series tangent `5570 pN/nm` and rest length `2.06 nm`;
- nonlinear local tangent `22.776424425306164 pN/nm` and pole
  `5.034069292365436 nm`; and
- angle-energy curvature `83.6 pN nm/rad²`.

The two-edge interpretation remains a provisional axial hypothesis. No angle
scaling is frozen. Nonlinear fit provenance and all biological mappings remain
unreviewed.

## Verification

The exact red output, JUnit files, commands, timings, file hashes, and path proof
are in `evidence/subagents/P01-05A/verification.md`.

- Required red: import failed before production implementation with one
  collection error (`pgworld.config` absent).
- Initial schema-v1 focused/full evidence is retained but was rejected before
  integration.
- Forged-snapshot red: **1 failed in 0.44s**, exit `1`, because the old direct
  constructor did not raise.
- Corrected schema-v2 focused: **14 passed in 0.53s**, exit `0`.
- Corrected full repository suite: **126 passed in 10.43s**, exit `0`.
- Final entry-point provenance red: **1 failed in 0.25s**, exit `1`, because
  both direct-elastic execution files were absent from source provenance.
- Final corrected focused: **15 passed in 0.21s**, exit `0`.
- Final corrected full suite: **127 passed in 6.65s**, exit `0`.
- Targeted `py_compile`: exit `0`.
- Four-file strict JSON parse/round-trip and production load: exit `0`.
- `git diff --check`: exit `0`.
- Ownership proof: no path outside the assignment.

The tests cover exact hashes/snapshots, constructor/read-back tamper and
repinning rejection, historical versus new-output pressure semantics, distinct
routes, unavailable parameter uncertainty/fit evidence, pinned official source
URLs, provisional base identity, fail-closed fields, units/equations,
no-time/no-3D claims, mixed-profile handling, and all requested numerical
derivations.

## Limitations and next action

- No LAMMPS oracle was executed; P01-06 owns energy/force/virial comparisons.
- Simulation runners do not yet consume these profiles because those files were
  deliberately outside this assignment. A later owned migration must persist
  the expanded profile snapshot in every manifest and artifact.
- Direct-route data-file masses are not established.
- Prof. Christoph Schmidt and Octavio are proposed reviewers/checkers only;
  neither assignment nor approval is claimed.
- `reviewed_physics_provisional_v0` is not permitted for a final science
  campaign. A new immutable ID/hash is required after actual review.

On acceptance, the integrator should update `README.md`, `handoff.md`,
`TASKS.json`, and `docs/ownership.md` together, leave P01-05 blocked on human
review, and make P01-06 eligible under the provisional computational contract.
